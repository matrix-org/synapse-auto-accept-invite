# Copyright 2021 The Matrix.org Foundation C.I.C.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import asyncio
from typing import Any, cast
from unittest.mock import Mock

import aiounittest
from frozendict import frozendict

from synapse_auto_accept_invite import InviteAutoAccepter
from tests import MockEvent, create_module, make_awaitable


class InviteAutoAccepterTestCase(aiounittest.AsyncTestCase):
    def setUp(self) -> None:
        self.module = create_module()
        self.user_id = "@peter:test"
        self.invitee = "@lesley:test"
        self.remote_invitee = "@thomas:remote"

        # We know our module API is a mock, but mypy doesn't.
        self.mocked_update_membership: Mock = self.module._api.update_room_membership  # type: ignore[assignment]

    async def test_simple_accept_invite(self) -> None:
        """Tests that receiving an invite for a local user makes the module attempt to
        make the invitee join the room. This test verifies that it works if the call to
        update membership returns a join event on the first try.
        """
        invite = MockEvent(
            sender=self.user_id,
            state_key=self.invitee,
            type="m.room.member",
            content={"membership": "invite"},
        )

        join_event = MockEvent(
            sender="someone",
            state_key="someone",
            type="m.room.member",
            content={"membership": "join"},
        )
        self.mocked_update_membership.return_value = make_awaitable(join_event)

        # Stop mypy from complaining that we give on_new_event a MockEvent rather than an
        # EventBase.
        await self.module.on_new_event(event=invite)  # type: ignore[arg-type]

        await self.retry_assertions(
            self.mocked_update_membership,
            1,
            sender=invite.state_key,
            target=invite.state_key,
            room_id=invite.room_id,
            new_membership="join",
        )

    async def test_accept_invite_with_failures(self) -> None:
        """Tests that receiving an invite for a local user makes the module attempt to
        make the invitee join the room. This test verifies that it works if the call to
        update membership returns exceptions before successfully completing and returning an event.
        """
        invite = MockEvent(
            sender=self.user_id,
            state_key=self.invitee,
            type="m.room.member",
            content={"membership": "invite"},
        )

        join_event = MockEvent(
            sender="someone",
            state_key="someone",
            type="m.room.member",
            content={"membership": "join"},
        )
        # the first two calls raise an exception while the third call is successful
        self.mocked_update_membership.side_effect = [
            Exception(),
            Exception(),
            make_awaitable(join_event),
        ]

        # Stop mypy from complaining that we give on_new_event a MockEvent rather than an
        # EventBase.
        await self.module.on_new_event(event=invite)  # type: ignore[arg-type]

        await self.retry_assertions(
            self.mocked_update_membership,
            3,
            sender=invite.state_key,
            target=invite.state_key,
            room_id=invite.room_id,
            new_membership="join",
        )

    async def test_accept_invite_failures(self) -> None:
        """Tests that receiving an invite for a local user makes the module attempt to
        make the invitee join the room. This test verifies that if the update_membership call
        fails consistently, _retry_make_join will break the loop after the set number of retries and
        execution will continue.
        """
        invite = MockEvent(
            sender=self.user_id,
            state_key=self.invitee,
            type="m.room.member",
            content={"membership": "invite"},
        )
        self.mocked_update_membership.side_effect = Exception()

        # Stop mypy from complaining that we give on_new_event a MockEvent rather than an
        # EventBase.
        await self.module.on_new_event(event=invite)  # type: ignore[arg-type]

        await self.retry_assertions(
            self.mocked_update_membership,
            5,
            sender=invite.state_key,
            target=invite.state_key,
            room_id=invite.room_id,
            new_membership="join",
        )

    async def test_accept_invite_direct_message(self) -> None:
        """Tests that receiving an invite for a local user makes the module attempt to
        make the invitee join the room even if the invite is for a direct message room.
        Moreover, check that the room is marked as a direct message in this case.
        """
        invite = MockEvent(
            sender=self.user_id,
            state_key=self.invitee,
            type="m.room.member",
            content={"membership": "invite", "is_direct": True},
            room_id="!the:room",
        )

        join_event = MockEvent(
            sender="someone",
            state_key="someone",
            type="m.room.member",
            content={"membership": "join"},
        )
        self.mocked_update_membership.return_value = make_awaitable(join_event)

        # We will mock out the account data get/put methods to check that the flags
        # are properly set.
        account_data_put: Mock = cast(
            Mock, self.module._api.account_data_manager.put_global
        )
        account_data_put.return_value = make_awaitable(None)

        account_data_get: Mock = cast(
            Mock, self.module._api.account_data_manager.get_global
        )
        account_data_get.return_value = make_awaitable(
            frozendict(
                {
                    "@someone:random": ("!somewhere:random",),
                }
            )
        )

        # Stop mypy from complaining that we give on_new_event a MockEvent rather than an
        # EventBase.
        await self.module.on_new_event(event=invite)  # type: ignore[arg-type]

        await self.retry_assertions(
            self.mocked_update_membership,
            1,
            sender=invite.state_key,
            target=invite.state_key,
            room_id=invite.room_id,
            new_membership="join",
        )

        account_data_get.assert_called_once_with(self.invitee, "m.direct")

        # Check that the account data was correctly updated; notably that it doesn't
        # overwrite the existing associations!
        account_data_put.assert_called_once_with(
            self.invitee,
            "m.direct",
            {
                "@someone:random": ("!somewhere:random",),
                self.user_id: ("!the:room",),
            },
        )

    async def test_remote_user(self) -> None:
        """Tests that receiving an invite for a remote user does nothing."""
        invite = MockEvent(
            sender=self.user_id,
            state_key=self.remote_invitee,
            type="m.room.member",
            content={"membership": "invite"},
        )

        # Stop mypy from complaining that we give on_new_event a MockEvent rather than an
        # EventBase.
        await self.module.on_new_event(event=invite)  # type: ignore[arg-type]

        self.mocked_update_membership.assert_not_called()

    async def test_not_state(self) -> None:
        """Tests that receiving an invite that's not a state event does nothing."""
        invite = MockEvent(
            sender=self.user_id, type="m.room.member", content={"membership": "invite"}
        )

        # Stop mypy from complaining that we give on_new_event a MockEvent rather than an
        # EventBase.
        await self.module.on_new_event(event=invite)  # type: ignore[arg-type]

        self.mocked_update_membership.assert_not_called()

    async def test_not_invite(self) -> None:
        """Tests that receiving a membership update that's not an invite does nothing."""
        invite = MockEvent(
            sender=self.user_id,
            state_key=self.user_id,
            type="m.room.member",
            content={"membership": "join"},
        )

        # Stop mypy from complaining that we give on_new_event a MockEvent rather than an
        # EventBase.
        await self.module.on_new_event(event=invite)  # type: ignore[arg-type]

        self.mocked_update_membership.assert_not_called()

    async def test_not_membership(self) -> None:
        """Tests that receiving a state event that's not a membership update does
        nothing.
        """
        invite = MockEvent(
            sender=self.user_id,
            state_key=self.user_id,
            type="org.matrix.test",
            content={"foo": "bar"},
        )

        # Stop mypy from complaining that we give on_new_event a MockEvent rather than an
        # EventBase.
        await self.module.on_new_event(event=invite)  # type: ignore[arg-type]

        self.mocked_update_membership.assert_not_called()

    async def test_accept_invite_direct_message_if_only_enabled_for_direct_messages(
        self,
    ) -> None:
        """Tests that, if the module is configured to only accept DM invites, invites to DM rooms are still
        automatically accepted.
        """
        module = create_module(
            config_override={"accept_invites_only_for_direct_messages": True},
        )

        # Patch out the account data get and put methods with dummy awaitables.
        account_data_put: Mock = cast(Mock, module._api.account_data_manager.put_global)
        account_data_put.return_value = make_awaitable(None)

        account_data_get: Mock = cast(Mock, module._api.account_data_manager.get_global)
        account_data_get.return_value = make_awaitable({})

        mocked_update_membership: Mock = module._api.update_room_membership  # type: ignore[assignment]
        join_event = MockEvent(
            sender="someone",
            state_key="someone",
            type="m.room.member",
            content={"membership": "join"},
        )
        mocked_update_membership.return_value = make_awaitable(join_event)

        invite = MockEvent(
            sender=self.user_id,
            state_key=self.invitee,
            type="m.room.member",
            content={"membership": "invite", "is_direct": True},
        )

        # Stop mypy from complaining that we give on_new_event a MockEvent rather than an
        # EventBase.
        await module.on_new_event(event=invite)  # type: ignore[arg-type]

        await self.retry_assertions(
            mocked_update_membership,
            1,
            sender=invite.state_key,
            target=invite.state_key,
            room_id=invite.room_id,
            new_membership="join",
        )

    async def test_ignore_invite_if_only_enabled_for_direct_messages(self) -> None:
        """Tests that, if the module is configured to only accept DM invites, invites to non-DM rooms are ignored."""
        module = create_module(
            config_override={"accept_invites_only_for_direct_messages": True},
        )

        invite = MockEvent(
            sender=self.user_id,
            state_key=self.invitee,
            type="m.room.member",
            content={"membership": "invite"},
        )

        # Stop mypy from complaining that we give on_new_event a MockEvent rather than an
        # EventBase.
        await module.on_new_event(event=invite)  # type: ignore[arg-type]

        mocked_update_membership: Mock = module._api.update_room_membership  # type: ignore[assignment]
        mocked_update_membership.assert_not_called()

    def test_config_parse(self) -> None:
        """Tests that a correct configuration passes parse_config."""
        config = {
            "accept_invites_only_for_direct_messages": True,
        }
        parsed_config = InviteAutoAccepter.parse_config(config)

        self.assertTrue(parsed_config.accept_invites_only_for_direct_messages)

    def test_runs_on_only_one_worker(self) -> None:
        """
        Tests that the module only runs on the specified worker.
        """
        # By default, we run on the main process...
        main_module = create_module(worker_name=None)
        cast(
            Mock, main_module._api.register_third_party_rules_callbacks
        ).assert_called_once()

        # ...and not on other workers (like synchrotrons)...
        sync_module = create_module(worker_name="synchrotron42")
        cast(
            Mock, sync_module._api.register_third_party_rules_callbacks
        ).assert_not_called()

        # ...unless we configured them to be the designated worker.
        specified_module = create_module(
            config_override={"worker_to_run_on": "account_data1"},
            worker_name="account_data1",
        )
        cast(
            Mock, specified_module._api.register_third_party_rules_callbacks
        ).assert_called_once()

    async def retry_assertions(
        self, mock: Mock, call_count: int, **kwargs: Any
    ) -> None:
        """
        This is a hacky way to ensure that the assertions are not called before the other coroutine
        has a chance to call `update_room_membership`. It catches the exception caused by a failure,
        and sleeps the thread before retrying, up until 5 tries.

        Args:
            call_count: the number of times the mock should have been called
            mock: the mocked function we want to assert on
            kwargs: keyword arguments to assert that the mock was called with
        """

        i = 0
        while i < 5:
            try:
                # Check that the mocked method is called the expected amount of times and with the right
                # arguments to attempt to make the user join the room.
                mock.assert_called_with(**kwargs)
                self.assertEqual(call_count, mock.call_count)
                break
            except AssertionError as e:
                i += 1
                if i == 5:
                    # we've used up the tries, force the test to fail as we've already caught the exception
                    self.fail(e)
                await asyncio.sleep(1)

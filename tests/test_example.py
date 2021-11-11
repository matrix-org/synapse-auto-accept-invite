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
from unittest.mock import Mock

import aiounittest

from tests import MockEvent, create_module


class InviteAutoAccepterTestCase(aiounittest.AsyncTestCase):
    def setUp(self) -> None:
        self.module = create_module()
        self.user_id = "@peter:test"
        self.invitee = "@lesley:test"
        self.remote_invitee = "@thomas:remote"

        # We know our module API is a mock, but mypy doesn't.
        self.mocked_update_membership: Mock = self.module._api.update_room_membership  # type: ignore[assignment]

    async def test_accept_invite(self) -> None:
        """Tests that receiving an invite for a local user makes the module attempt to
        make the invitee join the room.
        """
        invite = MockEvent(
            sender=self.user_id,
            state_key=self.invitee,
            type="m.room.member",
            content={"membership": "invite"},
        )

        # Stop mypy from complaining that we give on_new_event a MockEvent rather than an
        # EventBase.
        await self.module.on_new_event(event=invite)  # type: ignore[arg-type]

        # Check that the mocked method is called exactly once.
        self.mocked_update_membership.assert_called_once()

        # Check that the mocked method is called with the right arguments to attempt to
        # make the user join the room.
        kwargs = self.mocked_update_membership.call_args[1]
        self.assertEqual(kwargs["sender"], invite.state_key)
        self.assertEqual(kwargs["target"], invite.state_key)
        self.assertEqual(kwargs["room_id"], invite.room_id)
        self.assertEqual(kwargs["new_membership"], "join")

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

        self.assertEqual(self.mocked_update_membership.call_count, 0)

    async def test_not_state(self) -> None:
        """Tests that receiving an invite that's not a state event does nothing."""
        invite = MockEvent(
            sender=self.user_id, type="m.room.member", content={"membership": "invite"}
        )

        # Stop mypy from complaining that we give on_new_event a MockEvent rather than an
        # EventBase.
        await self.module.on_new_event(event=invite)  # type: ignore[arg-type]

        self.assertEqual(self.mocked_update_membership.call_count, 0)

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

        self.assertEqual(self.mocked_update_membership.call_count, 0)

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

        self.assertEqual(self.mocked_update_membership.call_count, 0)

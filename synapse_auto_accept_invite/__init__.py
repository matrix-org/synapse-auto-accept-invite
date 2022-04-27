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
import logging
from typing import Any, Dict, List, Optional

import attr
from synapse.module_api import EventBase, ModuleApi

logger = logging.getLogger(__name__)
ACCOUNT_DATA_DIRECT_MESSAGE_LIST = "m.direct"


@attr.s(auto_attribs=True, frozen=True)
class InviteAutoAccepterConfig:
    accept_invites_only_for_direct_messages: bool = False
    worker_to_run_on: Optional[str] = None


class InviteAutoAccepter:
    def __init__(self, config: InviteAutoAccepterConfig, api: ModuleApi):
        # Keep a reference to the Module API.
        self._api = api
        self._config = config

        should_run_on_this_worker = config.worker_to_run_on == self._api.worker_name

        if not should_run_on_this_worker:
            logger.info(
                "Not accepting invites on this worker (configured: %r, here: %r)",
                config.worker_to_run_on,
                self._api.worker_name,
            )
            return

        logger.info(
            "Accepting invites on this worker (here: %r)", self._api.worker_name
        )

        # Register the callback.
        self._api.register_third_party_rules_callbacks(
            on_new_event=self.on_new_event,
        )

    @staticmethod
    def parse_config(config: Dict[str, Any]) -> InviteAutoAccepterConfig:
        """Checks that the required fields are present and at a correct value, and
        instantiates a InviteAutoAccepterConfig.

        Args:
            config: The raw configuration dict.

        Returns:
            A InviteAutoAccepterConfig generated from this configuration
        """
        accept_invites_only_for_direct_messages = config.get(
            "accept_invites_only_for_direct_messages", False
        )

        worker_to_run_on = config.get("worker_to_run_on", None)

        return InviteAutoAccepterConfig(
            accept_invites_only_for_direct_messages=accept_invites_only_for_direct_messages,
            worker_to_run_on=worker_to_run_on,
        )

    async def on_new_event(self, event: EventBase, *args: Any) -> None:
        """Listens for new events, and if the event is an invite for a local user then
        automatically accepts it.

        Args:
            event: The incoming event.
        """
        # Check if the event is an invite for a local user.
        if (
            event.type == "m.room.member"
            and event.is_state()
            and event.membership == "invite"
            and self._api.is_mine(event.state_key)
        ):
            is_direct_message = event.content.get("is_direct", False)

            # Only accept invites for direct messages if the configuration mandates it, otherwise accept all invites.
            if (
                not self._config.accept_invites_only_for_direct_messages
                or is_direct_message is True
            ):
                # Make the user join the room.
                await self._api.update_room_membership(
                    sender=event.state_key,
                    target=event.state_key,
                    room_id=event.room_id,
                    new_membership="join",
                )

                if is_direct_message:
                    # Mark this room as a direct message!
                    await self._mark_room_as_direct_message(
                        event.state_key, event.sender, event.room_id
                    )

    async def _mark_room_as_direct_message(
        self, user_id: str, dm_user_id: str, room_id: str
    ) -> None:
        """
        Marks a room (`room_id`) as a direct message with the counterparty `dm_user_id`
        from the perspective of the user `user_id`.
        """

        # This dict of User IDs to lists of Room IDs
        dm_map: Dict[str, List[str]] = (
            await self._api.account_data_manager.get_global(
                user_id, ACCOUNT_DATA_DIRECT_MESSAGE_LIST
            )
            or {}
        )

        if dm_user_id not in dm_map:
            dm_map[dm_user_id] = [room_id]
        else:
            if not isinstance(dm_map[dm_user_id], list):
                # Don't mangle the data if we don't understand it.
                logger.warning(
                    "Not marking room as DM for auto-accepted invitatation; dm_map[%r] not a list.",
                    dm_user_id,
                )
                return

            dm_map[dm_user_id].append(room_id)

        await self._api.account_data_manager.put_global(
            user_id, ACCOUNT_DATA_DIRECT_MESSAGE_LIST, dm_map
        )

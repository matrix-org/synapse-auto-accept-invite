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
from typing import Any, Dict

from synapse.module_api import EventBase, ModuleApi


class InviteAutoAccepter:
    def __init__(self, config: Dict[str, Any], api: ModuleApi):
        # Keep a reference to the Module API.
        self._api = api

        # Register the callback.
        self._api.register_third_party_rules_callbacks(
            on_new_event=self.on_new_event,
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
            # Make the user join the room.
            await self._api.update_room_membership(
                sender=event.state_key,
                target=event.state_key,
                room_id=event.room_id,
                new_membership="join",
            )

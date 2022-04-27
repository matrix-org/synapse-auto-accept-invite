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
from typing import Any, Dict, Optional, TypeVar
from unittest.mock import Mock

import attr
from synapse.module_api import ModuleApi

from synapse_auto_accept_invite import InviteAutoAccepter


@attr.s(auto_attribs=True)
class MockEvent:
    """Mocks an event. Only exposes properties the module uses."""

    sender: str
    type: str
    content: Dict[str, Any]
    room_id: str = "!someroom"
    state_key: Optional[str] = None

    def is_state(self) -> bool:
        """Checks if the event is a state event by checking if it has a state key."""
        return self.state_key is not None

    @property
    def membership(self) -> str:
        """Extracts the membership from the event. Should only be called on an event
        that's a membership event, and will raise a KeyError otherwise.
        """
        membership: str = self.content["membership"]
        return membership


T = TypeVar("T")


async def make_awaitable(value: T) -> T:
    return value


def create_module(
    config_override: Dict[str, Any] = {}, worker_name: Optional[str] = None
) -> InviteAutoAccepter:
    # Create a mock based on the ModuleApi spec, but override some mocked functions
    # because some capabilities are needed for running the tests.
    module_api = Mock(spec=ModuleApi)
    module_api.is_mine.side_effect = lambda a: a.split(":")[1] == "test"
    module_api.worker_name = worker_name

    # Python 3.6 doesn't support awaiting on a mock, so we make it return an awaitable
    # value.
    module_api.update_room_membership.return_value = make_awaitable(None)
    config = InviteAutoAccepter.parse_config(config_override)

    return InviteAutoAccepter(config, module_api)

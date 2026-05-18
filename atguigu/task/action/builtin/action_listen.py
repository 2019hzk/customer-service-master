from typing import Any

from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult


class ActionListen(Action):
    name = "action_listen"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        pass

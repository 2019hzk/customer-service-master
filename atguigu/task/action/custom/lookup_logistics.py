from typing import Any

from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.custom.shared import fetch_logistics
from atguigu.domain.state import DialogueState


class LookupLogisticsAction(Action):
    """Fetches logistics tracking information from the e-commerce service."""

    name = "action_lookup_logistics"

    async def run(
        self,
        state: DialogueState,
        action_kwargs: dict[str, Any],
    ) -> ActionResult:
        order_number = state.active_task.slots.get("order_number")
        payload = await fetch_logistics(order_number)

        if payload is None:
            return ActionResult(slot_updates={
                "tracking_number": "未知",
                "logistics_company": "未知",
                "logistics_status": "暂时无法查到物流信息，请稍后再试。",
            })

        return ActionResult(slot_updates={
            "tracking_number": payload.get("tracking_number") or "未知",
            "logistics_company": payload.get("logistics_company") or "未知",
            "logistics_status": payload.get("status_desc") or payload.get("status") or "未知",
        })

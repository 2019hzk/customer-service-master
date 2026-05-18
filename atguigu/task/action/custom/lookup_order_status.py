from typing import Any

from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.custom.shared import _build_order_summary, fetch_order
from atguigu.domain.state import DialogueState


class LookupOrderStatusAction(Action):
    """Fetches order status and summary from the e-commerce service."""

    name = "action_lookup_order_status"

    async def run(
        self,
        state: DialogueState,
        action_kwargs: dict[str, Any],
    ) -> ActionResult:
        order_number = state.active_task.slots.get("order_number")
        payload = await fetch_order(order_number)

        if payload is None:
            return ActionResult(slot_updates={
                "order_status": "查询失败",
                "order_summary": "暂时无法查到该订单信息，请稍后再试。",
            })

        return ActionResult(slot_updates={
            "order_status": payload.get("status_desc") or payload.get("status") or "未知",
            "order_summary": _build_order_summary(payload),
        })

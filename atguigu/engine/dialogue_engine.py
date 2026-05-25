import time

from atguigu.chitchat.handler import ChitchatHandler
from atguigu.clarify.responder import ClarifyResponder
from atguigu.domain.messages import UserMessage, ProcessResult, MessageType, BotMessage
from atguigu.domain.state import DialogueState, FocusedObject
from atguigu.knowledge.handler import KnowledgeHandler
from atguigu.plan.models import ClarifyReason
from atguigu.plan.turn_planner import TurnPlanner
from atguigu.plan.validator import TurnPlanValidator
from atguigu.task.command.models import Command, SetSlotsCommand
from atguigu.task.flow.models import FlowsList
from atguigu.task.flow.steps import CollectSlotStep
from atguigu.task.handler import TaskHandler


class DialogueEngine:

    def __init__(
            self,
            turn_planner: TurnPlanner,
            task_handler: TaskHandler,
            knowledge_handler: KnowledgeHandler,
            chitchat_handler: ChitchatHandler,
            clarify_responder: ClarifyResponder,
            turn_plan_validator: TurnPlanValidator
    ) -> None:
        self.turn_planner = turn_planner
        self.task_handler = task_handler
        self.knowledge_handler = knowledge_handler
        self.chitchat_handler = chitchat_handler
        self.clarify_responder = clarify_responder
        self.turn_plan_validator = turn_plan_validator

    async def process_message(self, state: DialogueState, user_message: UserMessage) -> ProcessResult:
        """处理一条消息，直接修改 state，返回本轮结果。"""
        self._prepare_session(state)
        self._begin_turn(state, user_message)

        if user_message.type is MessageType.TEXT:
            messages = await self._handle_text_message(
                state=state,
            )
        else:
            state.set_focused_object(FocusedObject.from_dict(user_message.object.to_dict()))
            messages = await self._handle_object_message(
                message=user_message,
                state=state,
            )

        state.pending_turn.bot_messages.extend(messages)
        state.commit_pending_turn()

        return ProcessResult(
            sender_id=user_message.sender_id,
            message_id=user_message.message_id,
            messages=messages,
        )

    def _prepare_session(self, state: DialogueState) -> None:
        session = state.current_session()
        now = time.time()
        if session is None:
            state.start_session()
            return
        if now - session.last_activity_at > 60 * 60:
            state.close_current_session()
            state.reset_runtime_state_for_new_session()
            state.start_session()
        else:
            session.last_activity_at = now

    @staticmethod
    def _begin_turn(state: DialogueState, message: UserMessage) -> None:
        state.begin_turn(message)

    async def _handle_text_message(
            self,
            state: DialogueState,
    ) -> list[BotMessage]:
        turn_plan = await self.turn_planner.predict(
            state, self.task_handler.flows, self.knowledge_handler.knowledge_intents
        )
        validation = self.turn_plan_validator.validate(
            turn_plan, state=state, knowledge_intents=self.knowledge_handler.knowledge_intents,
            flows=self.task_handler.flows,
        )
        if not validation.valid:
            return await self.clarify_responder.respond(
                state=state,
                reason=validation.reason
            )

        if turn_plan.task is not None:
            return await self.task_handler.handle(
                commands=turn_plan.task.commands,
                state=state,
            )
        elif turn_plan.knowledge is not None:
            return await self.knowledge_handler.handle(
                state=state,
                intents=turn_plan.knowledge.intents,
            )

        return await self.chitchat_handler.handle(state=state)

    async def _handle_object_message(
            self,
            message: UserMessage,
            state: DialogueState,
    ) -> list[BotMessage]:
        commands = self._resolve_object_commands(
            message=message,
            state=state,
            flows=self.task_handler.flows,
        )
        if commands:
            return await self.task_handler.handle(commands=commands, state=state)

        # 没有匹配到 slot。如果用户正在一个流程中，不打断，让流程继续。
        if state.active_task is not None:
            return await self.task_handler.handle(commands=[], state=state)

        return await self.clarify_responder.respond(
            state=state,
            reason=ClarifyReason.OBJECT_REQUIRES_INTENT,
        )

    def _resolve_object_commands(
            self,
            message: UserMessage,
            state: DialogueState,
            flows: FlowsList,
    ) -> list[Command]:
        message_object = message.object
        if message_object is None:
            return []

        object_type = message_object.type.strip().lower()

        if object_type == "order":
            if self._flow_has_unfilled_collect_slot(state, flows, "order_number"):
                return [SetSlotsCommand(
                    command="set_slots",
                    slots={"order_number": message_object.id},
                )]
            return []

        if object_type == "product":
            if self._flow_has_unfilled_collect_slot(state, flows, "product_id"):
                return [SetSlotsCommand(
                    command="set_slots",
                    slots={"product_id": message_object.id},
                )]
            return []

        return []

    @staticmethod
    def _flow_has_unfilled_collect_slot(
            state: DialogueState,
            flows: FlowsList,
            slot_name: str,
    ) -> bool:
        """检查当前流程是否定义了名为 slot_name 的收集槽且尚未填充。"""
        active_task = state.active_task
        if active_task is None:
            return False
        flow = flows.get_flow_by_id(active_task.flow_id)
        if flow is None:
            return False
        if active_task.slots.get(slot_name):
            return False
        for step in flow.steps:
            if isinstance(step, CollectSlotStep) and step.slot_name == slot_name:
                return True
        return False

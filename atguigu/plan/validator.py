from atguigu.domain.state import DialogueState
from atguigu.knowledge.intents import KnowledgeIntent
from atguigu.plan.models import TurnPlan, TurnPlanValidationResult, ClarifyReason
from atguigu.task.command.models import StartFlowCommand, SetSlotsCommand, CancelFlowCommand, ResumeFlowCommand
from atguigu.task.flow.models import FlowsList


class TurnPlanValidator:
    def validate(
            self,
            turn_plan: TurnPlan,
            state: DialogueState,
            knowledge_intents: dict[str, KnowledgeIntent],
            flows: FlowsList,
    ) -> TurnPlanValidationResult:
        active_tracks = self._active_tracks(turn_plan)
        if not active_tracks:
            return self._reject(ClarifyReason.MISSING_TRACK)
        if len(active_tracks) > 1:
            return self._reject(ClarifyReason.MULTIPLE_TRACKS)

        track = active_tracks[0]
        if track == "task":
            return self._validate_task(turn_plan, flows=flows)
        if track == "knowledge":
            return self._validate_knowledge(turn_plan, state=state, knowledge_intents=knowledge_intents)
        return TurnPlanValidationResult(valid=True)

    @staticmethod
    def _active_tracks(turn_plan: TurnPlan) -> list[str]:
        tracks: list[str] = []
        if turn_plan.task is not None:
            tracks.append("task")
        if turn_plan.knowledge is not None:
            tracks.append("knowledge")
        if turn_plan.chitchat is not None:
            tracks.append("chitchat")
        return tracks

    def _reject(
            self,
            reason: ClarifyReason,
    ) -> TurnPlanValidationResult:
        return TurnPlanValidationResult(
            valid=False,
            reason=reason,
        )

    def _validate_task(
            self,
            turn_plan: TurnPlan,
            *,
            flows: FlowsList,
    ) -> TurnPlanValidationResult:
        task_plan = turn_plan.task
        if task_plan is None or not task_plan.commands:
            return self._reject(ClarifyReason.MISSING_TASK_COMMANDS)

        allowed = (StartFlowCommand, ResumeFlowCommand, CancelFlowCommand, SetSlotsCommand)
        if not all(isinstance(cmd, allowed) for cmd in task_plan.commands):
            return self._reject(ClarifyReason.INVALID_TASK_COMMANDS)

        start_commands = [cmd for cmd in task_plan.commands if isinstance(cmd, StartFlowCommand)]
        if len(start_commands) > 1:
            return self._reject(ClarifyReason.MULTIPLE_TASK_FLOWS)
        if start_commands:
            flow = flows.get_flow_by_id(start_commands[0].flow)
            if flow is None:
                return self._reject(ClarifyReason.UNKNOWN_TASK_FLOW)

        return TurnPlanValidationResult(valid=True)

    def _validate_knowledge(
            self,
            turn_plan: TurnPlan,
            state: DialogueState,
            knowledge_intents: dict[str, KnowledgeIntent],
    ) -> TurnPlanValidationResult:
        knowledge_plan = turn_plan.knowledge
        if knowledge_plan is None or not knowledge_plan.intents:
            return self._reject(ClarifyReason.MISSING_KNOWLEDGE_INTENT)

        focused_object = state.focused_object
        for intent in knowledge_plan.intents:
            intent_meta = knowledge_intents[intent]
            required_object = intent_meta.requires_object
            if required_object is not None:
                if focused_object is None or focused_object.type != required_object:
                    return self._reject(ClarifyReason.MISSING_FOCUSED_OBJECT)

        return TurnPlanValidationResult(valid=True)

from dataclasses import asdict

from atguigu.domain.contexts import CollectSystemContext
from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import ActionResult
from atguigu.task.action.runner import ActionCall, ActionRunner
from atguigu.task.flow.links import FlowStepLink, StaticLink, ConditionalLink, FallbackLink
from atguigu.task.flow.models import FlowsList, Flow
from atguigu.task.flow.steps import FlowStep, StartFlowStep, EndFlowStep, CollectSlotStep, ActionFlowStep


class FlowExecutor:

    async def run_task(self, state: DialogueState, flows: FlowsList, action_runner: ActionRunner) -> list[BotMessage]:
        messages: list[BotMessage] = []
        while True:
            action_call: ActionCall = self.advance_until_action(state, flows)
            if action_call.action_name == "action_listen":
                break
            else:
                action_result: ActionResult = await action_runner.run(action_call, state)
                state.set_slots(action_result.slot_updates)
                messages.extend(action_result.messages)
        return messages

    def advance_until_action(self, state: DialogueState, flows: FlowsList) -> ActionCall:
        while True:
            current_task = state.current_task()  # 系统任务优先
            if current_task is None:
                return ActionCall(action_name="action_listen")

            flow: Flow = flows.get_flow_by_id(current_task.flow_id)
            step: FlowStep = flow.get_step_by_id(current_task.step_id)
            step_result: ActionCall | None = self._run_step(step, state, flows)

            if step_result is not None:
                return step_result

    def _run_step(self, step: FlowStep, state: DialogueState, flows: FlowsList) -> ActionCall | None:
        if isinstance(step, StartFlowStep):
            return self._run_start_step(step, state)
        if isinstance(step, EndFlowStep):
            return self._run_end_step(state)
        if isinstance(step, CollectSlotStep):
            return self._run_collect_step(step, state, flows)
        if isinstance(step, ActionFlowStep):
            return self._run_action_step(step, state)

    def _run_start_step(self, step: StartFlowStep, state: DialogueState) -> ActionCall | None:
        self._advance_to_next_step(step, state)
        return None

    def _run_end_step(self, state: DialogueState) -> ActionCall | None:
        if state.active_system_task:
            state.end_system_task()
            return None
        else:
            state.end_active_task()
            return None

    def _run_collect_step(self, step: CollectSlotStep, state: DialogueState, flows: FlowsList) -> ActionCall | None:
        self._try_to_fill_slot_from_focused_object(step, state)
        if state.active_task.slots.get(step.slot_name):
            # 有值
            if step.validation:
                # 校验
                condition = step.validation.condition
                if self._eval_condition(condition, state):
                    # 校验通过
                    self._advance_to_next_step(step, state)
                    return None
                else:
                    # 校验失败
                    state.remove_slot(step.slot_name)
                    if step.validation.failure_response:
                        # 失败响应
                        return ActionCall(action_name="action_response",
                                          action_kwargs=asdict(step.validation.failure_response))
                    else:
                        # 校验失败, 没有定义 failure_response 时也应给用户反馈，而非静默重问
                        return ActionCall(action_name="action_response",
                                          action_kwargs={"text": "你提供的信息有误，请重新输入。"})
            else:
                # 无需校验
                self._advance_to_next_step(step, state)
                return None
        else:
            # 无值, 激活系统collect flow
            state.start_system_task(CollectSystemContext(
                flow_id="system_collect_information",
                step_id=flows.get_flow_by_id("system_collect_information").start_step().id,
                slot_name=step.slot_name,
                response=asdict(step.response)
            ))
            return None

    def _run_action_step(self, step: ActionFlowStep, state: DialogueState) -> ActionCall | None:
        # 推进到下一个step
        self._advance_to_next_step(step, state)
        # 封装ActionCall
        action_call: ActionCall = self._build_action_call(step, state)
        return action_call

    def _select_next_step(self, step: FlowStep, state: DialogueState) -> str:
        """
        选择下一个step_id
        :param step:
        :param state:
        :return: next step id
        """
        links: list[FlowStepLink] = step.next
        for link in links:
            if isinstance(link, StaticLink):
                return link.target
            if isinstance(link, ConditionalLink):
                if self._eval_condition(link.condition, state):
                    return link.target
            if isinstance(link, FallbackLink):
                return link.target

    def _eval_condition(self, condition: str, state: DialogueState) -> bool:
        data = {
            "slots": state.active_task.slots,
            "context": asdict(state.current_task())
        }
        return bool(eval(condition, {}, data))

    def _advance_to_next_step(self, step: FlowStep, state: DialogueState):
        # 选择下一个step
        next_step_id = self._select_next_step(step, state)
        # 设置state的当前的task的step_id
        state.current_task().step_id = next_step_id

    def _build_action_call(self, step: ActionFlowStep, state: DialogueState) -> ActionCall:
        action_name = step.action
        args = step.args
        if isinstance(args, str):
            args = asdict(state.current_task())[args.split('.')[1]]
        return ActionCall(action_name=action_name, action_kwargs=args)

    def _try_to_fill_slot_from_focused_object(self, step: CollectSlotStep, state: DialogueState):
        if state.focused_object is None:
            return
        if step.slot_name == 'order_number' and state.focused_object.type == "order":
            state.set_slots({step.slot_name: state.focused_object.id})
        if step.slot_name == "product_id" and state.focused_object.type == "product":
            state.set_slots({step.slot_name: state.focused_object.id})


if __name__ == '__main__':
    f = "a>b"
    print(eval(f, {}, {"a": 1, "b": 2}))

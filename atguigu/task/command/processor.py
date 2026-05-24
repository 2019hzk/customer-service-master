from atguigu.domain.contexts import TaskContext, StartedSystemContext, InterruptedSystemContext, CanceledSystemContext, \
    ResumedSystemContext
from atguigu.domain.state import DialogueState
from atguigu.task.command.models import Command, StartFlowCommand, SetSlotsCommand, CancelFlowCommand, ResumeFlowCommand
from atguigu.task.flow.models import FlowsList, Flow


class CommandProcessor:
    def run(
            self,
            commands: list[Command],
            state: DialogueState,
            flows: FlowsList,
    ) -> None:
        for command in commands:
            self._apply(command, state, flows)

    def _apply(
            self,
            command: Command,
            state: DialogueState,
            flows: FlowsList,
    ) -> None:
        if isinstance(command, StartFlowCommand):
            self._handle_start_flow(command, state, flows)
        elif isinstance(command, SetSlotsCommand):
            self._handle_set_slots(command, state)
        elif isinstance(command, CancelFlowCommand):
            self._handle_cancel_flow(state, flows)
        elif isinstance(command, ResumeFlowCommand):
            self._handle_resume_flow(command, state, flows)

    def _handle_start_flow(self, command: StartFlowCommand, state: DialogueState, flows: FlowsList):
        # 清理系统任务的上下文
        state.end_system_task()
        # 获取目标flow
        target_flow: Flow = flows.get_flow_by_id(command.flow)

        # 判断当前是否有正在执行的task
        active_task = state.active_task
        if active_task:
            # 挂起旧任务
            state.interrupt_active_task()
            # 启动新任务
            state.start_task(
                TaskContext(
                    flow_id=target_flow.id,
                    step_id=target_flow.start_step().id
                )
            )
            # 启动system_task_started
            state.start_system_task(InterruptedSystemContext(
                flow_id="system_task_interrupted",
                step_id=flows.get_flow_by_id("system_task_interrupted").start_step().id,
                interrupted_flow_id=active_task.flow_id,
                interrupted_flow_name=flows.get_flow_by_id(active_task.flow_id).name,
                started_flow_id=target_flow.id,
                started_flow_name=target_flow.name
            ))
        else:
            state.start_task(
                TaskContext(
                    flow_id=target_flow.id,
                    step_id=target_flow.start_step().id
                )
            )
            state.start_system_task(StartedSystemContext(
                flow_id="system_task_started",
                step_id=flows.get_flow_by_id("system_task_started").start_step().id,
                started_flow_id=target_flow.id,
                started_flow_name=target_flow.name
            ))

    def _handle_set_slots(self, command: SetSlotsCommand, state: DialogueState):
        if state.active_task:
            state.set_slots(command.slots)

    def _handle_cancel_flow(self, state: DialogueState, flows: FlowsList):
        # 获取当前正在执行的flow
        active_task = state.active_task
        target_flow = flows.get_flow_by_id(active_task.flow_id)
        # 取消当前task
        state.cancel_active_task()
        # 启动system_task_canceled
        state.start_system_task(
            CanceledSystemContext(
                flow_id="system_task_canceled",
                step_id=flows.get_flow_by_id("system_task_canceled").start_step().id,
                canceled_flow_id=target_flow.id,
                canceled_flow_name=target_flow.name
            )
        )

    def _handle_resume_flow(self, command: ResumeFlowCommand, state: DialogueState, flows: FlowsList):
        target_flow: Flow = flows.get_flow_by_id(command.flow)
        active_task: TaskContext = state.active_task
        if active_task:
            if active_task.flow_id == target_flow.id:
                return
            else:
                # 暂停当前任务
                state.interrupt_active_task()
                # 恢复目标任务
                if not state.resume_task(target_flow.id):
                    state.resume_task()  # 回退：恢复刚才中断的任务
                    return
                # 启动system_task_interrupted
                state.start_system_task(InterruptedSystemContext(
                    flow_id="system_task_interrupted",
                    step_id=flows.get_flow_by_id("system_task_interrupted").start_step().id,
                    interrupted_flow_id=active_task.flow_id,
                    interrupted_flow_name=flows.get_flow_by_id(active_task.flow_id).name,
                    started_flow_id=target_flow.id,
                    started_flow_name=target_flow.name
                ))
        else:
            # 恢复目标任务
            if not state.resume_task(target_flow.id):
                return
            # 启动system_task_resumed
            state.start_system_task(
                ResumedSystemContext(
                    flow_id="system_task_resumed",
                    step_id=flows.get_flow_by_id("system_task_resumed").start_step().id,
                    resumed_flow_id=target_flow.id,
                    resumed_flow_name=target_flow.name
                )
            )

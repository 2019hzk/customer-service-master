from atguigu.domain.contexts import TaskContext, StartedSystemContext, InterruptedSystemContext, CanceledSystemContext, \
    ResumedSystemContext
from atguigu.domain.state import DialogueState
from atguigu.task.command.models import Command, StartFlowCommand, SetSlotsCommand, CancelFlowCommand, ResumeFlowCommand
from atguigu.task.flow.models import FlowsList


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

    def _handle_start_flow(self, command: StartFlowCommand, state: DialogueState, flows: FlowsList) -> None:
        # 清除当前系统流程（不再阻塞新任务启动），当前上下文变为业务任务
        state.end_system_task()

        if command.flow.startswith("system_"):
            raise ValueError(
                f"Cannot start internal system flow '{command.flow}' directly."
            )

        target_flow = flows.get_flow_by_id(command.flow)
        if target_flow is None:
            raise ValueError(f"Unknown flow '{command.flow}'.")
        start_step = target_flow.start_step()
        if start_step is None:
            raise ValueError(f"Flow '{command.flow}' has no start step.")

        active_task = state.active_task

        # 当前有业务任务
        if active_task is not None:
            if active_task.flow_id == command.flow:
                # 同一个流程，不重复启动
                return

            # 打断当前任务，尝试恢复暂停中的同名任务
            interrupted_flow_id = active_task.flow_id
            interrupted_flow_name = self._readable_flow_name(active_task.flow_id, flows)
            state.interrupt_active_task()

            resumed = state.resume_task(command.flow)
            if not resumed:
                # 正在做A，用户要B，B不在暂停栈 → 新建B，A进暂停栈
                state.start_task(TaskContext(
                    flow_id=command.flow,
                    step_id=start_step.id
                ))
                started_flow_id = command.flow
                started_flow_name = self._readable_flow_name(command.flow, flows)
            else:
                # 正在做A，用户要B，B在暂停栈 → 恢复B，A进暂停栈
                started_flow_id = command.flow
                started_flow_name = self._readable_flow_name(command.flow, flows)

            self._activate_interruption_system_flow(
                state, flows,
                interrupted_flow_id=interrupted_flow_id,
                interrupted_flow_name=interrupted_flow_name,
                started_flow_id=started_flow_id,
                started_flow_name=started_flow_name,
            )
            return

        # 当前无活跃任务，尝试恢复同名任务
        resumed = state.resume_task(command.flow)
        if resumed:
            # 没事做，用户要A（之前做过一半），A在暂停栈 → 恢复A
            self._activate_resumed_system_flow(
                state, flows,
                resumed_flow_id=command.flow,
                resumed_flow_name=self._readable_flow_name(command.flow, flows),
            )
            return

        # 没事做，用户要A（从没做过），A不在暂停栈 → 创建A
        state.start_task(TaskContext(
            flow_id=command.flow,
            step_id=start_step.id
        ))
        self._activate_started_system_flow(
            state, flows,
            started_flow_id=command.flow,
            started_flow_name=self._readable_flow_name(command.flow, flows),
        )

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
        target_flow = flows.get_flow_by_id(command.flow)
        if target_flow is None:
            raise ValueError(f"Unknown flow '{command.flow}'.")

        active_task = state.active_task
        if active_task is not None:
            if active_task.flow_id == target_flow.id:
                return
            # 暂停当前任务，恢复目标任务
            interrupted_flow_id = active_task.flow_id
            interrupted_flow_name = self._readable_flow_name(active_task.flow_id, flows)
            state.interrupt_active_task()
            if not state.resume_task(target_flow.id):
                state.resume_task()  # 回退：恢复刚才中断的任务
                return
            self._activate_interruption_system_flow(
                state, flows,
                interrupted_flow_id=interrupted_flow_id,
                interrupted_flow_name=interrupted_flow_name,
                started_flow_id=target_flow.id,
                started_flow_name=target_flow.name,
            )
        else:
            if not state.resume_task(target_flow.id):
                return
            self._activate_resumed_system_flow(
                state, flows,
                resumed_flow_id=target_flow.id,
                resumed_flow_name=target_flow.name,
            )

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _readable_flow_name(flow_id: str, flows: FlowsList) -> str:
        flow = flows.get_flow_by_id(flow_id)
        return flow.name if flow else flow_id

    def _activate_started_system_flow(
            self,
            state: DialogueState,
            flows: FlowsList,
            started_flow_id: str,
            started_flow_name: str,
    ) -> None:
        flow = flows.get_flow_by_id("system_task_started")
        state.start_system_task(StartedSystemContext(
            flow_id="system_task_started",
            step_id=flow.start_step().id,
            started_flow_id=started_flow_id,
            started_flow_name=started_flow_name,
        ))

    def _activate_resumed_system_flow(
            self,
            state: DialogueState,
            flows: FlowsList,
            resumed_flow_id: str,
            resumed_flow_name: str,
    ) -> None:
        flow = flows.get_flow_by_id("system_task_resumed")
        state.start_system_task(ResumedSystemContext(
            flow_id="system_task_resumed",
            step_id=flow.start_step().id,
            resumed_flow_id=resumed_flow_id,
            resumed_flow_name=resumed_flow_name,
        ))

    def _activate_interruption_system_flow(
            self,
            state: DialogueState,
            flows: FlowsList,
            interrupted_flow_id: str,
            interrupted_flow_name: str,
            started_flow_id: str,
            started_flow_name: str,
    ) -> None:
        flow = flows.get_flow_by_id("system_task_interrupted")
        state.start_system_task(InterruptedSystemContext(
            flow_id="system_task_interrupted",
            step_id=flow.start_step().id,
            interrupted_flow_id=interrupted_flow_id,
            interrupted_flow_name=interrupted_flow_name,
            started_flow_id=started_flow_id,
            started_flow_name=started_flow_name,
        ))

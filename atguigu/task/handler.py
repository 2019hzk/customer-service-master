from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.runner import ActionRunner
from atguigu.task.command.models import Command
from atguigu.task.command.processor import CommandProcessor
from atguigu.task.flow.executor import FlowExecutor
from atguigu.task.flow.models import FlowsList


class TaskHandler:
    def __init__(self,
                 command_processor: CommandProcessor,
                 flows: FlowsList,
                 flow_executor: FlowExecutor,
                 action_runner: ActionRunner
                 ):
        self.command_processor: CommandProcessor = command_processor
        self.flows: FlowsList = flows
        self.flow_executor: FlowExecutor = flow_executor
        self.action_runner: ActionRunner = action_runner

    async def handle(self, commands: list[Command], state: DialogueState) -> list[BotMessage]:
        self.command_processor.run(commands, state, self.flows)
        messages: list[BotMessage] = await self.flow_executor.run_task(state, self.flows, self.action_runner)
        return messages

from atguigu.domain.messages import UserMessage, ProcessResult
from atguigu.domain.state import DialogueState
from atguigu.engine.dialogue_engine import DialogueEngine
from atguigu.repository.dialogue_state_repository import DialogueStateRepository


class DialogueService:
    def __init__(self,
                 dialogue_state_repository: DialogueStateRepository,
                 dialogue_engine: DialogueEngine):
        self.dialogue_state_repository = dialogue_state_repository
        self.dialogue_engine = dialogue_engine

    async def process_message(self, user_message: UserMessage) -> ProcessResult:
        # 1.通过dialogue_state_repository根据sender_id 加载对话状态
        state: DialogueState = await self.dialogue_state_repository.load_state(user_message.sender_id)
        # 2. 使用dialogue_engine根据对话状态去处理最新消息
        process_result: ProcessResult = await self.dialogue_engine.process_message(state, user_message)
        # 3. 通过dialogue_state_repository保存最新的对话状态
        await self.dialogue_state_repository.save_state(state)
        # 4. 返回本轮处理结果
        return process_result

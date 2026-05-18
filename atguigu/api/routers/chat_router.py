import uuid

from fastapi import APIRouter
from fastapi.params import Depends

from atguigu.api.dependencies import get_dialogue_service
from atguigu.api.schemas import ChatRequest, ChatResponse, HistoryResponse, ChatBotMessage, HistoryMessage, ChatObject
from atguigu.domain.messages import UserMessage, ProcessResult, MessageType, MessageObject
from atguigu.service.dialogue_service import DialogueService

chat_router = APIRouter()


@chat_router.post('/api/chat')
async def chat(
        chat_request: ChatRequest,
        dialogue_service: DialogueService = Depends(get_dialogue_service)
) -> ChatResponse:
    process_result: ProcessResult = await dialogue_service.process_message(_build_user_message(chat_request))
    return _build_chat_response(process_result)


@chat_router.get('/api/chat/history')
async def history(sender_id: str) -> HistoryResponse:
    return HistoryResponse(
        sender_id=sender_id,
        messages=[
            HistoryMessage(
                role='user',
                text='你好'
            ),
            HistoryMessage(
                role='bot',
                text='我不好'
            )
        ]
    )


def _build_user_message(chat_request: ChatRequest) -> UserMessage:
    return UserMessage(
        sender_id=chat_request.sender_id,
        message_id=chat_request.message_id or str(uuid.uuid4()),
        type=MessageType.TEXT if chat_request.text else MessageType.OBJECT,
        text=chat_request.text,
        object=MessageObject(type=chat_request.object.type,
                             id=chat_request.object.id,
                             title=chat_request.object.title,
                             attributes=chat_request.object.attributes
                             ) if chat_request.object else None
    )


def _build_chat_response(process_result: ProcessResult) -> ChatResponse:
    return ChatResponse(
        sender_id=process_result.sender_id,
        message_id=process_result.message_id,
        messages=[ChatBotMessage(
            text=message.text,
            object=ChatObject(type=message.object.type,
                              id=message.object.id,
                              title=message.object.title,
                              attributes=message.object.attributes
                              ) if message.object else None
        ) for message in process_result.messages]
    )

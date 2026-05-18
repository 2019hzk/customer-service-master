import asyncio

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.domain.messages import UserMessage, BotMessage, MessageType
from atguigu.domain.state import Turn
from atguigu.infrastructure.llm import llm
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.prompt_loader import load_prompt


class ChitchatResponder:

    async def respond(
            self,
            user_message: UserMessage,
            recent_turns: list[Turn],
    ) -> list[BotMessage]:
        user_message = HistoryBuilder._render_user_message(user_message)
        history = HistoryBuilder.build(recent_turns)

        prompt_text = load_prompt("chitchat_respond")
        prompt = PromptTemplate.from_template(
            prompt_text,
            template_format="jinja2"
        )
        chain = prompt | llm | StrOutputParser()
        response = await chain.ainvoke({
            "user_message": user_message,
            "history": history,
        })
        return [BotMessage(text=response)]


if __name__ == '__main__':
    chitchat_responder = ChitchatResponder()


    async def test():
        response = await chitchat_responder.respond(
            user_message=UserMessage(
                sender_id="u1001",
                message_id="m1001",
                type=MessageType.TEXT,
                text="你好"
            ),
            recent_turns=[]
        )
        print(response)


    asyncio.run(test())

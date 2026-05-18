from langchain.chat_models import init_chat_model

from atguigu.conf.config import settings

llm = init_chat_model(
    model=settings.llm_model,
    model_provider='openai',
    api_key=settings.llm_api_key,
    temperature=0,
    base_url=settings.llm_base_url
)

if __name__ == '__main__':
    print(llm.invoke("你好").content)

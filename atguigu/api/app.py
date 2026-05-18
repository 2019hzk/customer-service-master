from contextlib import asynccontextmanager

from fastapi import FastAPI

from atguigu.api.dependencies import init_dialogue_engine
from atguigu.api.routers.chat_router import chat_router
from atguigu.infrastructure.database import init_db_engine, close_db_engine
from atguigu.infrastructure.http_client import init_http_client, close_http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_http_client()
    init_dialogue_engine()
    init_db_engine()
    yield
    await close_db_engine()
    await close_http_client()


app = FastAPI(lifespan=lifespan)
app.include_router(chat_router)

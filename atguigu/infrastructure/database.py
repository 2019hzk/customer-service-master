import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession, create_async_engine

from atguigu.conf.config import settings

engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db_engine():
    global engine, session_factory
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def close_db_engine():
    await engine.dispose()


if __name__ == '__main__':
    async def test():
        init_db_engine()
        async with session_factory() as session:
            result = await session.execute(text("select 1"))
            data = result.fetchall()
            print(data)
            print(type(data))
            print(type(data[0]))

        await close_db_engine()


    asyncio.run(test())

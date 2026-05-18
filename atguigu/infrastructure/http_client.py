import asyncio

from httpx import AsyncClient

http_client: AsyncClient | None = None


def init_http_client():
    global http_client
    http_client = AsyncClient()


async def close_http_client():
    await http_client.aclose()


if __name__ == '__main__':
    async def test():
        init_http_client()
        result = await http_client.get('http://localhost:18081/users/u1001/orders')
        print(result.json()['data']['orders'])

        await close_http_client()


    asyncio.run(test())

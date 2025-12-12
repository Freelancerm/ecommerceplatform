import redis.asyncio as redis
from ..core.config import settings


class RedisClient:
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.client = None

    async def connect(self):
        self.client = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)

    async def disconnect(self):
        if self.client:
            await self.client.close()

    async def set_value(self, key: str, value: str, ttl: int = None):
        await self.client.set(key, value, ex=ttl)

    async def get_value(self, key: str) -> str | None:
        return await self.client.get(key)

    async def publish(self, channel: str, message: str):
        await self.client.publish(channel, message)


redis_client = RedisClient()

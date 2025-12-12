import redis.asyncio as redis
from ..core.config import settings


class RedisClient:
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.client: redis.Redis | None = None

    async def connect(self):
        if self.redis_url:
            self.client = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)

    async def close(self):
        if self.client:
            await self.client.close()

    async def add_online_user(self, user_id: str):
        if self.client:
            await self.client.sadd("online_users", user_id)

    async def remove_online_user(self, user_id: str):
        if self.client:
            await self.client.srem("online_users", user_id)

    async def get_chat_id(self, phone: str) -> str | None:
        """
        Direct lookup of user:{phone}:chat_id which is set by Service D.
        Shared Redis allows this pattern for MVP.
        """
        if self.client:
            return await self.client.get(f"user:{phone}:chat_id")
        return None


redis_client = RedisClient()

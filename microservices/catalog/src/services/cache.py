import redis.asyncio as redis
import json
from ..core.config import settings
from typing import Any


class CacheService:
    def __init__(self):
        self.redis: redis.Redis | None = None

    async def connect(self):
        if settings.REDIS_URL:
            self.redis = await redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

    async def close(self):
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Any | None:
        if not self.redis:
            return None
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set(self, key: str, value: Any, ttl: int = 300):
        if not self.redis:
            return
        await self.redis.set(key, json.dumps(value), ex=ttl)


cache_service = CacheService()

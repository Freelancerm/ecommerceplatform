from fastapi import FastAPI
from .core.config import settings

from contextlib import asynccontextmanager
import asyncio
from .services.telegram_bot import dp, bot
from .services.consumer import notification_consumer
from .api import ws
from .core.redis_client import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect Redis
    await redis_client.connect()

    # Start Redis Consumer
    consumer_task = asyncio.create_task(notification_consumer())

    # Start Bot Polling (only if token is set)
    # Note: dp.start_polling is blocking, so we wrap it or use start_polling in a task?
    # Aiogram 3 start_polling is blocking. We need to run it in a task.
    bot_task = None
    if bot:
        bot_task = asyncio.create_task(dp.start_polling(bot))

    yield

    # Cleanup
    consumer_task.cancel()
    if bot_task:
        bot_task.cancel()  # Or better stop polling gracefully
    if bot:
        await bot.session.close()
    await redis_client.close()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.include_router(ws.router, prefix="/notifications", tags=["Notifications"])


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "notification(E)"
    }

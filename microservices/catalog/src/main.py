from fastapi import FastAPI
from .core.config import settings

from contextlib import asynccontextmanager
from .api.routers import products
from .core.es_client import es_client
from .services.consumer import inventory_update_consumer
from .services.cache import cache_service
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    await es_client.connect()
    await es_client.create_index()
    await cache_service.connect()

    # Start Redis Consumer for Inventory Updates
    consumer_task = asyncio.create_task(inventory_update_consumer())

    yield

    consumer_task.cancel()
    await cache_service.close()
    await es_client.close()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.include_router(products.router, prefix="/products", tags=["Products"])


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "catalog(A)"
    }

from fastapi import FastAPI
from contextlib import asynccontextmanager
from .core.config import  settings

from .api.routers import order_routers
from .core.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.include_router(order_routers.router, prefix="/orders", tags=["Orders"])
from .api.routers import admin_routers
app.include_router(admin_routers.router, prefix="/orders/admin", tags=["Admin"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}!"}

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "order(C)"
    }

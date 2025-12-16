from fastapi import FastAPI
from contextlib import asynccontextmanager
from .core.config import settings
from .api.routers import inventory_routes
from .core.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.include_router(inventory_routes.router, prefix="/inventory", tags=["Inventory"])

from .api.routers import admin_routes

app.include_router(admin_routes.router, prefix="/admin", tags=["Admin"])


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "inventory(B)"
    }

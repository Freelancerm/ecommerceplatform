from fastapi import FastAPI
from .core.config import settings
from contextlib import asynccontextmanager
from .api import auth_routes, internal_routes
from .core.redis_client import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.connect()
    yield
    await redis_client.disconnect()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)


@app.middleware("http")
async def log_requests(request, call_next):
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("middleware")
    logger.info(f"Incoming Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response Status: {response.status_code}")
    return response


app.include_router(auth_routes.router, prefix="/auth", tags=["Auth"])
app.include_router(internal_routes.router, prefix="/internal", tags=["Internal"])


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}!"}


@app.get("/health")
async def health_check():
    return {"status": "ok",
            "service": "auth"
            }

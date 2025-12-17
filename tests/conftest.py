import asyncio
import os
from dataclasses import dataclass
from typing import Dict

import httpx
import importlib
import pytest
import pytest_asyncio
import redis.asyncio as redis
from dotenv import dotenv_values


def _load_secret() -> str:
    """
    Load JWT secret from env or known .env files to align with running services.
    """
    if os.getenv("JWT_SECRET"):
        return os.environ["JWT_SECRET"]
    for path in (
        "microservices/order/.env",
        "microservices/auth/.env",
        ".env",
    ):
        if os.path.exists(path):
            data = dotenv_values(path)
            if data.get("JWT_SECRET"):
                return data["JWT_SECRET"]
    return "441926da9555464ac711125e47f44562"


DEFAULT_SECRET = _load_secret()


@dataclass(frozen=True)
class ServiceURLs:
    catalog: str
    inventory: str
    orders: str
    notification: str
    auth: str
    redis_url: str
    elasticsearch: str


@pytest.fixture(scope="session")
def service_urls() -> ServiceURLs:
    """
    Resolve service endpoints based on running docker-compose ports.
    """
    es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    if not es_url.startswith("http"):
        es_url = f"http://{es_url}"

    return ServiceURLs(
        catalog=os.getenv("CATALOG_BASE_URL", "http://127.0.0.1:81"),
        inventory=os.getenv("INVENTORY_BASE_URL", "http://127.0.0.1:82"),
        orders=os.getenv("ORDERS_BASE_URL", "http://127.0.0.1:83"),
        notification=os.getenv("NOTIFICATION_BASE_URL", "http://127.0.0.1:84"),
        auth=os.getenv("AUTH_BASE_URL", "http://127.0.0.1:80"),
        redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        elasticsearch=es_url,
    )


@pytest.fixture(scope="session")
def tokens() -> Dict[str, str]:
    """
    Generate access tokens for user and admin using shared JWT secret.
    """
    # Ensure secret is present before importing utils
    if not os.getenv("JWT_SECRET"):
        os.environ["JWT_SECRET"] = DEFAULT_SECRET

    import jwt_core_lib.utils as utils

    # Update runtime secret in case module was imported earlier
    utils.SECRET_KEY = os.environ["JWT_SECRET"]
    utils.ACCESS_TOKEN_EXPIRE_MINUTES = 60

    user_token = utils.create_access_token({"sub": "380001111111"}, role="user")
    admin_token = utils.create_access_token({"sub": "380009999999"}, role="admin")
    return {"user": user_token, "admin": admin_token}


@pytest_asyncio.fixture
async def http_client():
    """
    Shared HTTPX async client for integration calls.
    """
    async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
        yield client


class _DummyRedis:
    """Lightweight stand-in so unit tests don't need a live Redis."""

    async def flushdb(self):
        return None

    async def aclose(self):
        return None


@pytest_asyncio.fixture
async def redis_client(service_urls: ServiceURLs, request):
    """
    Redis client for pub/sub checks during tests.
    Returns a dummy client for non-integration tests to avoid connection hangs.
    """
    if "integration" not in request.node.nodeid:
        yield _DummyRedis()
        return

    client = redis.from_url(
        service_urls.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=1.0,
    )
    yield client
    await client.aclose()


@pytest_asyncio.fixture(autouse=True)
async def clear_redis(redis_client):
    """
    Clear Redis between tests to avoid stale cache/interference.
    """
    try:
        await redis_client.flushdb()
    except Exception:
        pass


async def _wait_for_http(url: str, http_client, attempts: int = 10, delay: float = 1.0):
    for _ in range(attempts):
        try:
            resp = await http_client.get(url, timeout=5.0)
            if resp.status_code < 500:
                return
        except Exception:
            await asyncio.sleep(delay)
    raise TimeoutError(f"Service at {url} not reachable after {attempts} attempts")


async def _wait_for_redis(url: str, attempts: int = 10, delay: float = 1.0):
    client = redis.from_url(url, encoding="utf-8", decode_responses=True, socket_connect_timeout=1.0)
    try:
        for _ in range(attempts):
            try:
                await client.ping()
                return
            except Exception:
                await asyncio.sleep(delay)
    finally:
        await client.aclose()
    raise TimeoutError(f"Redis at {url} not reachable")


@pytest_asyncio.fixture(autouse=True)
async def ensure_services_up(service_urls: ServiceURLs, http_client, request):
    """
    Wait for core services to be reachable before running integration tests.
    Unit-style tests in this repo don't need live services, so we only check
    connectivity for modules that look like integration tests.
    """
    # Skip connectivity checks for non-integration tests to avoid unnecessary waits.
    if "integration" not in request.node.nodeid:
        return

    if os.getenv("SKIP_INTEGRATION_TESTS") == "1":
        pytest.skip("Integration tests disabled via SKIP_INTEGRATION_TESTS.")

    if getattr(ensure_services_up, "_failed", False):
        pytest.skip("Skipping integration tests; services not reachable.")

    if not getattr(ensure_services_up, "_ready", False):
        attempts = int(os.getenv("SERVICE_WAIT_ATTEMPTS", "3"))
        delay = float(os.getenv("SERVICE_WAIT_DELAY", "0.5"))
        try:
            await _wait_for_http(f"{service_urls.catalog}/health", http_client, attempts=attempts, delay=delay)
            await _wait_for_http(f"{service_urls.inventory}/health", http_client, attempts=attempts, delay=delay)
            await _wait_for_http(f"{service_urls.orders}/health", http_client, attempts=attempts, delay=delay)
            await _wait_for_http(f"{service_urls.notification}/health", http_client, attempts=attempts, delay=delay)
            await _wait_for_http(f"{service_urls.auth}/health", http_client, attempts=attempts, delay=delay)
            await _wait_for_http(service_urls.elasticsearch, http_client, attempts=attempts, delay=delay)
            await _wait_for_redis(service_urls.redis_url, attempts=attempts, delay=delay)
            ensure_services_up._ready = True
        except TimeoutError as exc:
            ensure_services_up._failed = True
            pytest.skip(f"Skipping integration tests; services not reachable: {exc}")


async def wait_for_pubsub_message(pubsub, timeout: float = 5.0):
    """
    Await a pubsub message ignoring subscription acks.
    """
    end_time = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < end_time:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if message:
            return message
    raise TimeoutError("Did not receive pubsub message in time")

import os
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

def _clear_src_modules():
    """Remove any cached src.* modules to avoid cross-service package collisions."""
    for key in list(sys.modules.keys()):
        if key == "src" or key.startswith("src."):
            sys.modules.pop(key, None)

# Minimal env to satisfy settings parsing
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("ELASTICSEARCH_URL", "http://localhost:9200")
os.environ.setdefault("INVENTORY_SERVICE_URL", "http://localhost:82")
os.environ.setdefault("PAYMENT_SERVICE_URL", "http://localhost:9999/mock")
os.environ.setdefault("JWT_SECRET", "secret")
os.environ.setdefault("SECRET_KEY", "secret")

# Ensure service path is importable (add package root containing src/)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "microservices/order"))
_clear_src_modules()

from src.services.saga import SagaOrchestrator, OrderStatus  # noqa: E402


class DummyResponse:
    def __init__(self, status_code=200, text="ok"):
        self.status_code = status_code
        self.text = text


class DummyAsyncClient:
    def __init__(self, responses=None):
        self.responses = responses or []
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def post(self, url, json):
        self.calls.append((url, json))
        if self.responses:
            return self.responses.pop(0)
        return DummyResponse()


class DummySession:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_saga_success(monkeypatch):
    """Payment step runs and order is marked paid on success."""
    order = SimpleNamespace(id=1, items=[{"product_id": "p1", "quantity": 1}], status=None)
    session = DummySession()

    client = DummyAsyncClient()
    from src.services import saga
    monkeypatch.setattr(saga.httpx, "AsyncClient", lambda: client)

    orchestrator = SagaOrchestrator(session, order)
    await orchestrator.execute()

    assert order.status == OrderStatus.PAID
    assert session.commits == 1
    assert orchestrator.reserved_items == [{"product_id": "p1", "quantity": 1}]


@pytest.mark.asyncio
async def test_saga_payment_failure_triggers_rollback(monkeypatch):
    """Simulated payment failure rolls back stock and cancels order."""
    order = SimpleNamespace(id=2, items=[{"product_id": "p2", "quantity": 3}], status=None)
    session = DummySession()

    client = DummyAsyncClient()
    from src.services import saga
    monkeypatch.setattr(saga.httpx, "AsyncClient", lambda: client)

    orchestrator = SagaOrchestrator(session, order)
    with pytest.raises(Exception):
        await orchestrator.execute(simulate_failure=True)

    assert order.status == OrderStatus.CANCELED
    # One commit during rollback
    assert session.commits == 1
    # Two HTTP calls: reserve + release
    assert len(client.calls) == 2

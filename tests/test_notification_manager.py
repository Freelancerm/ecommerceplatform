import os
import sys
from pathlib import Path
import importlib

import pytest

def _clear_src_modules():
    """Remove cached src.* modules to isolate microservice packages."""
    for key in list(sys.modules.keys()):
        if key == "src" or key.startswith("src."):
            sys.modules.pop(key, None)

# Minimal env to satisfy settings parsing
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("ELASTICSEARCH_URL", "http://localhost:9200")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "dummy")
os.environ.setdefault("AUTH_SERVICE_URL", "http://localhost:80")

# Make notification source importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "microservices/notification"))
_clear_src_modules()

from src.webosckets.manager import ConnectionManager  # noqa: E402
manager_module = importlib.import_module("src.webosckets.manager")


class DummyWebSocket:
    def __init__(self):
        self.accepted = False
        self.sent = []

    async def accept(self):
        self.accepted = True

    async def send_text(self, message: str):
        self.sent.append(message)


class DummyRedis:
    def __init__(self):
        self.added = []
        self.removed = []

    async def add_online_user(self, user_id: str):
        self.added.append(user_id)

    async def remove_online_user(self, user_id: str):
        self.removed.append(user_id)


@pytest.mark.asyncio
async def test_disconnect_handles_missing_user(monkeypatch):
    """disconnect should be safe even if user not tracked."""
    dummy_redis = DummyRedis()
    manager = ConnectionManager()
    monkeypatch.setattr(manager, "_ConnectionManager__redis_client", dummy_redis, raising=False)
    # Monkeypatch module-level redis_client used in methods
    monkeypatch.setattr(manager_module, "redis_client", dummy_redis)

    ws = DummyWebSocket()
    await manager.disconnect(ws, "absent")
    assert dummy_redis.removed == []


@pytest.mark.asyncio
async def test_disconnect_removes_last_connection(monkeypatch):
    """disconnect removes user entry and calls redis cleanup."""
    dummy_redis = DummyRedis()
    manager = ConnectionManager()
    monkeypatch.setattr(manager_module, "redis_client", dummy_redis)

    ws = DummyWebSocket()
    await manager.connect(ws, "user1")
    await manager.disconnect(ws, "user1")

    assert "user1" not in manager.active_connections
    assert dummy_redis.removed == ["user1"]

import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

def _clear_src_modules():
    """Remove cached src.* modules to isolate microservice packages."""
    for key in list(sys.modules.keys()):
        if key == "src" or key.startswith("src."):
            sys.modules.pop(key, None)

# Minimal env to satisfy settings parsing
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("ELASTICSEARCH_URL", "http://localhost:9200")

# Make catalog source importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "microservices/catalog"))
_clear_src_modules()

from src.api.routers import products  # noqa: E402


class DummyES:
    def __init__(self, result):
        self._result = result
        self.calls = 0

    async def get(self, doc_id: str):
        self.calls += 1
        return self._result


@pytest.mark.asyncio
async def test_get_product_success(monkeypatch):
    """Ensures get_product returns Product when ES finds document."""
    dummy_source = {"title": "Shoes", "description": "Running", "price": 10, "available": True}
    dummy = DummyES({"found": True, "_id": "p1", "_source": dummy_source})
    monkeypatch.setattr(products, "es_client", dummy)

    product = await products.get_product("p1")
    assert product.id == "p1"
    assert product.title == "Shoes"
    assert dummy.calls == 1


@pytest.mark.asyncio
async def test_get_product_missing(monkeypatch):
    """get_product raises 404 when document absent."""
    dummy = DummyES({"found": False})
    monkeypatch.setattr(products, "es_client", dummy)

    with pytest.raises(HTTPException) as exc:
        await products.get_product("p2")
    assert exc.value.status_code == 404

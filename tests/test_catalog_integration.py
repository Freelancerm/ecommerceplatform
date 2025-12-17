import asyncio
import uuid

import pytest


pytestmark = pytest.mark.asyncio


async def index_product(es_url: str, http_client, product_id: str):
    """
    Index a test product directly into Elasticsearch.
    """
    title = f"Test Product {product_id}"
    body = {
        "title": title,
        "description": "Fast runner",
        "price": 123.45,
        "available": True,
    }
    await http_client.put(f"{es_url}/products/_doc/{product_id}", json=body)
    await http_client.post(f"{es_url}/products/_refresh")
    return body


async def test_catalog_get_and_search(service_urls, http_client):
    product_id = f"test-{uuid.uuid4().hex[:8]}"
    source = await index_product(service_urls.elasticsearch, http_client, product_id)

    # Get by id
    resp = await http_client.get(f"{service_urls.catalog}/products/{product_id}")
    resp.raise_for_status()
    data = resp.json()
    assert data["id"] == product_id
    assert data["title"] == source["title"]

    # Search
    resp = await http_client.get(
        f"{service_urls.catalog}/products/search",
        params={"q": product_id, "skip": 0, "limit": 10},
    )
    resp.raise_for_status()
    payload = resp.json()
    assert any(hit["id"] == product_id for hit in payload["hits"])
    assert payload["total"] >= 1

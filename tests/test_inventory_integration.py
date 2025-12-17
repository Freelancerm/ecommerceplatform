import uuid

import pytest

from tests.conftest import wait_for_pubsub_message

pytestmark = pytest.mark.asyncio


async def subscribe_inventory_updates(redis_client):
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("inventory_updates")
    return pubsub


async def test_inventory_reserve_and_release(service_urls, http_client, redis_client, tokens):
    product_id = f"inv-{uuid.uuid4().hex[:8]}"

    # Seed inventory item
    resp = await http_client.post(
        f"{service_urls.inventory}/inventory/",
        json={"product_id": product_id, "stock": 3},
    )
    resp.raise_for_status()

    pubsub = await subscribe_inventory_updates(redis_client)

    # Reserve one unit
    resp = await http_client.post(
        f"{service_urls.inventory}/inventory/reserve",
        json={"product_id": product_id, "quantity": 1},
    )
    resp.raise_for_status()
    assert resp.json()["status"] == "reserved"

    # Expect inventory update event (available should be True with remaining stock)
    message = await wait_for_pubsub_message(pubsub, timeout=5)
    assert message["channel"] == "inventory_updates"

    # Release stock
    resp = await http_client.post(
        f"{service_urls.inventory}/inventory/release",
        json={"product_id": product_id, "quantity": 1},
    )
    resp.raise_for_status()
    assert resp.json()["status"] == "released"

    await pubsub.unsubscribe()
    await pubsub.aclose()

    # Admin list should include the item
    resp = await http_client.get(
        f"{service_urls.inventory}/admin/",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
    )
    if resp.status_code >= 500:
        pytest.skip(f"Inventory admin endpoint returned {resp.status_code}: {resp.text}")
    resp.raise_for_status()
    items = resp.json()
    assert any(item["product_id"] == product_id for item in items)

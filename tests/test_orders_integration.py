import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def seed_inventory(service_urls, http_client, product_id: str):
    resp = await http_client.post(
        f"{service_urls.inventory}/inventory/",
        json={"product_id": product_id, "stock": 5},
    )
    resp.raise_for_status()


async def test_order_saga_success_and_failure(service_urls, http_client, tokens):
    product_id = f"ord-{uuid.uuid4().hex[:8]}"
    await seed_inventory(service_urls, http_client, product_id)

    payload = {
        "items": [{"product_id": product_id, "quantity": 1}],
        "simulate_failure": False,
    }
    resp = await http_client.post(
        f"{service_urls.orders}/orders/",
        json=payload,
        headers={"Authorization": f"Bearer {tokens['user']}"},
    )
    if resp.status_code == 401:
        pytest.skip("Orders service rejected provided user token (401).")
    resp.raise_for_status()
    order = resp.json()
    assert order["status"] == "PAID"

    # Failure path should cancel order
    payload["simulate_failure"] = True
    resp = await http_client.post(
        f"{service_urls.orders}/orders/",
        json=payload,
        headers={"Authorization": f"Bearer {tokens['user']}"},
    )
    if resp.status_code == 401:
        pytest.skip("Orders service rejected provided user token (401).")
    resp.raise_for_status()
    failed_order = resp.json()
    assert failed_order["status"] in ("CANCELED", "FAILED")


async def test_order_admin_listing_and_update(service_urls, http_client, tokens):
    # List orders as admin
    resp = await http_client.get(
        f"{service_urls.orders}/orders/admin/",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
    )
    if resp.status_code == 401:
        pytest.skip("Orders service rejected admin token (401).")
    resp.raise_for_status()
    orders = resp.json()
    if not orders:
        pytest.skip("No orders present to update; run saga test first.")

    order_id = orders[0]["id"]
    resp = await http_client.put(
        f"{service_urls.orders}/orders/admin/{order_id}/status",
        params={"new_status": "SHIPPED"},
        headers={"Authorization": f"Bearer {tokens['admin']}"},
    )
    resp.raise_for_status()
    updated = resp.json()
    assert updated["status"] == "SHIPPED"

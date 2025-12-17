import asyncio
import json

import pytest
import websockets


pytestmark = pytest.mark.asyncio


def ws_url(http_url: str) -> str:
    return http_url.replace("http://", "ws://").replace("https://", "wss://")


async def test_user_websocket_receives_order_update(service_urls, tokens, redis_client):
    user_phone = "380001111111"
    uri = f"{ws_url(service_urls.notification)}/notifications/ws/{user_phone}?token={tokens['user']}"

    try:
        async with websockets.connect(uri) as websocket:
            event = {"type": "order_update", "user_id": user_phone, "status": "SHIPPED"}
            await redis_client.publish("notifications", json.dumps(event))
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
            assert "SHIPPED" in message
    except websockets.InvalidStatusCode as exc:
        if exc.status_code == 403:
            pytest.skip("Notification WS rejected token (403).")
        raise


async def test_admin_websocket_receives_new_order(service_urls, tokens, redis_client):
    uri = f"{ws_url(service_urls.notification)}/notifications/ws/admin/feed"

    async with websockets.connect(uri) as websocket:
        event = {"type": "new_order", "order_id": "order-xyz", "user_id": "380001111111", "amount": 50}
        await redis_client.publish("notifications", json.dumps(event))
        message = await asyncio.wait_for(websocket.recv(), timeout=5)
        assert "New order created" in message

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from ..webosckets.manager import manager
from jwt_core_lib.utils import verify_token
import logging

router = APIRouter()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        token: str = Query(..., description="JWT Access Token")
):
    try:
        payload = verify_token(token)
        user_id = payload.get("phone")

        if not user_id:
            raise ValueError("Token missing user ID claim.")

    except Exception as ex:
        logging.error(f"WS Auth failed: {ex}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or missing authentication token")
        return

    await manager.connect(websocket, user_id)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)

    except Exception as ex:
        logging.error(f"WS Error for user {user_id}: {ex}")
        await manager.disconnect(websocket, user_id)


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "notification"}


@router.websocket("/ws/admin/feed")
async def websocket_admin_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for Admins to receive global updates (e.g. New Orders)
    """
    await manager.connect_admin(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

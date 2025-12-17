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
    """
    Establishes a dedicated WebSocket connection for an authenticated user.

    The endpoint performs authentication by validating the provided JWT access token.
    Upon successful validation, the user_id (extracted from the 'phone' claim) is
    registered with the connection manager. This connection remains open until
    explicitly closed by the client or interrupted by an error.

    Arguments:
     websocket (WebSocket): The active connection object managed by FastAPI.
     token (str): The JWT access token provided as a query parameter for authentication.

    Authentication Flow:
    1. Verify JWT validity and expiration.
    2. Extract 'phone' claim as user_id.
    3. Register connection with manager.

    Raises:
     WebSocketDisconnect: Triggered when the client gracefully closes the connection.
     Exception: If JWT verification fails (e.g., token invalid/expired), the
      connection is closed with status WS_1008_POLICY_VIOLATION.
    """
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
    """
    Simple health check endpoint to confirm the service is operational.

    Returns:
     dict: Status confirmation {"status": "ok", "service": "notification"}.
    """
    return {"status": "ok", "service": "notification"}


@router.websocket("/ws/admin/feed")
async def websocket_admin_endpoint(websocket: WebSocket):
    """
    Establishes an unauthenticated, persistent WebSocket connection for the Admin Feed.

    This connection is intended for broadcasting global, read-only administrative
    updates (e.g., "New Order Received"). It registers the connection with the
    manager's administrative group.

    Arguments:
     websocket (WebSocket): The active connection object.

    Raises:
     WebSocketDisconnect: Triggered when the admin client closes the connection.    """
    await manager.connect_admin(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect_admin(websocket)

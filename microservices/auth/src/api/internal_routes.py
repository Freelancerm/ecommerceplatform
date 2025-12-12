from fastapi import APIRouter
from ..schemas.auth import TelegrambindRequest
from ..core.redis_client import redis_client

router = APIRouter()


@router.post("/users/bind-telegram")
async def bind_telegram_user(telegram_user: TelegrambindRequest):
    """
    Internal Endpoint called by Service E (Bot) when user shares contact.
    Mappings:
    user:{phone}:chat_id -> {chat_id}
    """
    phone = telegram_user.phone_number
    chat_id = telegram_user.chat_id
    key = f"user:{phone}:chat_id"
    await redis_client.set_value(key, str(chat_id))
    return {"status": "bound", "phone": phone, "chat_id": chat_id}

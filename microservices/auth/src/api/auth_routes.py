import secrets
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import timedelta
from ..core.config import settings
from ..schemas.auth import OtpRequest, OtpResponse, TokePair
from ..core.redis_client import redis_client
from jwt_core_lib.utils import create_access_token, create_refresh_token, TokenPair

router = APIRouter()


@router.post("/otp/send/", response_model=OtpResponse)
async def send_otp(request: OtpRequest):
    """
    Generates OTP and requests Service E to send it via Telegram.
    Fails if user hasn't started the bot (no chat_id mapping).
    """
    phone = request.phone_number
    chat_id_key = f"user:{phone}:chat_id"

    chat_id = await redis_client.get_value(chat_id_key)

    if not chat_id:
        raise HTTPException(
            status_code=400,
            detail="TELEGRAM BOT NOT STARTED",
            headers={"X-ERROR-CODE": "BOT_REQUIRED"},
        )

    # Generate 6 digit code
    otp_code = "".join([str(secrets.randbelow(10)) for _ in range(6)])

    # SAVE OTP to Redis with 5 min TTL
    otp_key = f"otp:{phone}"
    await redis_client.set_value(otp_key, otp_code, ttl=300)

    # Publish event for Service E
    event = {
        "type": "otp_send",
        "phone": phone,
        "otp_code": otp_code,
    }
    await redis_client.publish("notifications", json.dumps(event))

    return OtpResponse(message="OTP sent to Telegram", debug_info=None)


class OtpVerifyRequest(BaseModel):
    phone_number: str
    code: str


@router.post("/otp/verify/", response_model=TokePair)
async def verify_otp(request: OtpVerifyRequest):
    """
    Verifies OTP and issues JWT tokens.
    """
    phone = request.phone_number
    otp_key = f"otp:{phone}"

    stored_code = await redis_client.get_value(otp_key)

    if not stored_code:
        raise HTTPException(status_code=400, detail="OTP expired or not found")

    if stored_code != request.code:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Prevent reuse, delete token
    await redis_client.set_value(otp_key, "", ttl=1)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

    # Generate tokens
    access_token = create_access_token(
        data={"sub": request.phone_number, "type": "access"},
        expires_delta=access_token_expires
    )

    refresh_token = create_refresh_token(
        data={"sub": request.phone_number, "type": "refresh"},
        expires_delta=refresh_token_expires
    )

    return TokenPair(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

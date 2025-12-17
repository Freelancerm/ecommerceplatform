import secrets
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import timedelta
from ..core.config import settings
from ..schemas.auth import OtpRequest, OtpResponse, TokePair
from ..core.redis_client import redis_client
from jwt_core_lib.utils import create_access_token, create_refresh_token, TokenPair
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()


@router.post("/otp/send/", response_model=OtpResponse)
async def send_otp(request: OtpRequest):
    """
    Initiates the OTP delivery process via Telegram.

    This function checks if the user's phone number is mapped to a Telegram chat ID in Redis.
    If found, it generates a cryptographically secure 6-digit code, saves it to Redis
    with a 5-minute TTL, and publishes an event to a notification worker.

    Arguments:
     `request` (OtpRequest): A Pydantic model containing the user's `phone_number`.

    Returns:
     `OtpResponse`: A success message indicating the OTP was dispatched.

    Raises:
     `HTTPException (400)`: Raised with detail "TELEGRAM BOT NOT STARTED" if no `chat_id`
        is found for the provided phone number.
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
    Validates the provided OTP and issues a JWT token pair.

    This function retrieves the stored OTP from Redis using the phone number as a key.
    If the code matches, it immediately deletes or invalidates the OTP to prevent
    reuse and generates both Access and Refresh tokens.

    Arguments:
     request (OtpVerifyRequest): Contains phone_number and the 6-digit code submitted by the user.

    Returns:
     TokenPair: An object containing the access_token, refresh_token, and token_type ("bearer").

    Raises:
     HTTPException (400): If the OTP is expired, not found, or if the submitted code
        does not match the stored code ("Invalid OTP").
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


@router.post("/token", response_model=TokePair)
async def get_token_for_swagger(
    form_data: OAuth2PasswordRequestForm = Depends() # Очікує дані форми: username, password
):
    """
    Standard OAuth2 compatible token endpoint used primarily for Swagger UI.

    This endpoint mimics the token generation logic of verify_otp but accepts standard
    OAuth2 form data (username and password) instead of a JSON body.
    It maps the fields as follows:
    - username is treated as the phone_number.
    - password is treated as the OTP code.

    Arguments:
     form_data (OAuth2PasswordRequestForm): Standard dependency that extracts
        username and password from the request body, typically used by interactive
        documentation systems like Swagger.

    Returns:
     TokenPair: JWT tokens for the authenticated session.

    Raises:
     HTTPException (400): If the credentials (Phone/OTP) are invalid or expired.
    """
    phone = form_data.username # Swagger передає телефон як username
    otp_code = form_data.password # Swagger передає OTP як password
    otp_key = f"otp:{phone}"

    stored_code = await redis_client.get_value(otp_key)

    if not stored_code:
        raise HTTPException(status_code=400, detail="OTP expired or not found")

    if stored_code != otp_code: # Порівнюємо переданий OTP з формою
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Успішна верифікація, генеруємо токени (логіка з verify_otp)
    await redis_client.set_value(otp_key, "", ttl=1)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": phone, "type": "access"},
        expires_delta=access_token_expires
    )

    refresh_token = create_refresh_token(
        data={"sub": phone, "type": "refresh"},
        expires_delta=refresh_token_expires
    )

    return TokenPair(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

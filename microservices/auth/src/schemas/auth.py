from pydantic import BaseModel, Field


class TelegrambindRequest(BaseModel):
    phone_number: str = Field(..., description="Telegram phone number in international format (e. g. +380....")
    chat_id: int = Field(..., description="Telegram Chat ID")


class OtpRequest(BaseModel):
    phone_number: str = Field(..., description="User phone number")


class OtpResponse(BaseModel):
    message: str
    debug_info: str | None = None  # For testing(MVP) only


class TokePair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'Bearer'

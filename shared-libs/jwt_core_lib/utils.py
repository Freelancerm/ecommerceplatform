from datetime import datetime, UTC, timedelta
from jose import jwt, JWTError
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class TokenData(BaseModel):
    phone: str | None = None
    role: str = "user"  # Default Role


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(data: dict, expires_delta: timedelta | None = None, role: str = "user"):
    to_encode = data.copy()
    to_encode.update({"type": "access"})

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "role": role})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        phone: str = payload.get("sub")
        role: str = payload.get("role", "user")

        if phone is None:
            raise ValueError("Token missing required 'sub' (phone number) claim.")

        token_type = payload.get("type")
        if token_type != "access":
            raise ValueError("Invalid token type. Only 'access' tokens are accepted here.")

        return {"phone": phone, "role": role}

    except JWTError as ex:
        raise ex
    except Exception as ex:
        raise ex

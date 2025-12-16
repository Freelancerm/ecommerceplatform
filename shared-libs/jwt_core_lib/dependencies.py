from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .utils import verify_token, TokenData
from jose import JWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost/auth/token")  # URL generic here


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_token(token)
        phone: str = payload.get("phone")
        role: str = payload.get("role", "user")
        if not phone:
            raise credentials_exception

        token_data = TokenData(phone=phone, role=role)

    except (JWTError, ValueError):
        raise credentials_exception

    return token_data


async def get_current_admin(current_user: TokenData = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user

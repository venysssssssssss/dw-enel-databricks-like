"""JWT authentication helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.api.config import get_api_settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/admin/token")

USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin"),
        "role": "admin",
    },
    "analyst": {
        "username": "analyst",
        "hashed_password": pwd_context.hash("analyst"),
        "role": "analyst",
    },
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str) -> dict[str, str] | None:
    user = USERS.get(username)
    if user is None or not verify_password(password, user["hashed_password"]):
        return None
    return {"username": user["username"], "role": user["role"]}


def create_access_token(data: dict[str, str], expires_delta: timedelta | None = None) -> str:
    settings = get_api_settings()
    expire_at = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.token_expire_minutes)
    )
    payload = {**data, "exp": expire_at}
    return str(jwt.encode(payload, settings.secret_key, algorithm="HS256"))


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict[str, str]:
    settings = get_api_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    username = payload.get("sub")
    role = payload.get("role")
    if username is None or role is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {"username": str(username), "role": str(role)}

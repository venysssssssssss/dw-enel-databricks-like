"""Role-based access control."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, HTTPException, status

from src.api.auth.jwt import get_current_user


class Role(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


def require_role(allowed_roles: list[Role]) -> Callable[[dict[str, str]], dict[str, str]]:
    async def checker(
        user: Annotated[dict[str, str], Depends(get_current_user)],
    ) -> dict[str, str]:
        if user["role"] not in {role.value for role in allowed_roles}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker

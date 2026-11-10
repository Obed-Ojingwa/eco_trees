from collections.abc import Callable
from typing import Any
from uuid import UUID

from jwt import InvalidTokenError
from fastapi import Depends, Request

from app.core.config import settings
from app.core.errors import ApiError
from app.core.security import decode_token
from app.db.pool import connection


def get_current_user(request: Request) -> dict[str, Any]:
    token = request.cookies.get(settings.jwt_cookie_name)
    if not token:
        raise ApiError(401, "AUTH_REQUIRED", "Please sign in to continue.")
    try:
        claims = decode_token(token)
        user_id = UUID(claims["sub"])
    except (ValueError, KeyError, TypeError, InvalidTokenError):
        raise ApiError(401, "INVALID_SESSION", "Your session is invalid or expired.")

    with connection() as conn:
        user = conn.execute(
            """
            SELECT id, role, display_name, phone, email, kyc_verified
            FROM users
            WHERE id = %s AND disabled_at IS NULL
            """,
            (user_id,),
        ).fetchone()
    if not user:
        raise ApiError(401, "INVALID_SESSION", "Your session is invalid or expired.")
    return user


def require_roles(*roles: str) -> Callable[..., dict[str, Any]]:
    def dependency(
        user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if user["role"] not in roles:
            raise ApiError(403, "FORBIDDEN", "You do not have permission to do this.")
        return user

    return dependency

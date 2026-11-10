from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings


_hasher = PasswordHasher()
_dummy_password_hash = _hasher.hash("not-a-real-user-credential")


def hash_secret(secret: str) -> str:
    return _hasher.hash(secret)


def verify_secret(secret: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, secret)
    except (InvalidHashError, VerifyMismatchError):
        return False


def issue_token(user_id: UUID, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expiry_minutes
    )
    return jwt.encode(
        {"sub": str(user_id), "role": role, "exp": expires_at},
        settings.jwt_secret,
        algorithm="HS256",
    )


def decode_token(token: str) -> dict[str, str]:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def verify_dummy(secret: str) -> None:
    verify_secret(secret, _dummy_password_hash)

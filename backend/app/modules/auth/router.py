from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Response
from psycopg.errors import UniqueViolation

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.errors import ApiError
from app.core.security import hash_secret, issue_token, verify_dummy, verify_secret
from app.db.pool import connection
from app.modules.auth.schemas import (
    FarmerRegistration,
    LoginRequest,
    LoginResponse,
    UserResponse,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_response(user: dict) -> UserResponse:
    return UserResponse(
        id=str(user["id"]),
        role=user["role"],
        display_name=user["display_name"],
        phone=user["phone"],
        email=user["email"],
        kyc_verified=user["kyc_verified"],
    )


def _set_session(response: Response, user: dict) -> LoginResponse:
    response.set_cookie(
        settings.jwt_cookie_name,
        issue_token(user["id"], user["role"]),
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.jwt_expiry_minutes * 60,
        path="/",
    )
    return LoginResponse(
        user=_user_response(user),
        expires_in_seconds=settings.jwt_expiry_minutes * 60,
    )


@router.post("/register", response_model=LoginResponse, status_code=201)
def register_farmer(payload: FarmerRegistration, response: Response) -> LoginResponse:
    user_id = uuid4()
    try:
        with connection() as conn, conn.transaction():
            user = conn.execute(
                """
                INSERT INTO users (id, role, display_name, phone, password_hash)
                VALUES (%s, 'farmer', %s, %s, %s)
                RETURNING id, role, display_name, phone, email, kyc_verified
                """,
                (
                    user_id,
                    payload.display_name,
                    payload.phone,
                    hash_secret(payload.pin),
                ),
            ).fetchone()
    except UniqueViolation:
        raise ApiError(409, "PHONE_ALREADY_REGISTERED", "This phone number is already registered.")
    return _set_session(response, user)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response) -> LoginResponse:
    user: dict | None = None
    failure: ApiError | None = None
    now = datetime.now(timezone.utc)

    with connection() as conn, conn.transaction():
        user = conn.execute(
            """
            SELECT id, role, display_name, phone, email, password_hash,
                   kyc_verified, failed_logins, locked_until, disabled_at
            FROM users
            WHERE phone = %s OR email = %s
            FOR UPDATE
            """,
            (payload.identifier, payload.identifier.lower()),
        ).fetchone()

        if not user:
            verify_dummy(payload.secret)
            failure = ApiError(401, "INVALID_CREDENTIALS", "Phone/email or PIN/password is incorrect.")
        elif user["disabled_at"] is not None:
            verify_secret(payload.secret, user["password_hash"])
            failure = ApiError(401, "INVALID_CREDENTIALS", "Phone/email or PIN/password is incorrect.")
        elif user["locked_until"] and user["locked_until"] > now:
            verify_secret(payload.secret, user["password_hash"])
            failure = ApiError(
                423,
                "ACCOUNT_LOCKED",
                "Sign-in is temporarily locked. Try again after the lock expires.",
                {"locked_until": user["locked_until"].isoformat()},
            )
        elif not verify_secret(payload.secret, user["password_hash"]):
            failed_logins = user["failed_logins"] + 1
            locked_until = now + timedelta(minutes=15) if failed_logins >= 5 else None
            conn.execute(
                """
                UPDATE users
                SET failed_logins = %s, locked_until = %s, updated_at = now()
                WHERE id = %s
                """,
                (failed_logins, locked_until, user["id"]),
            )
            failure = ApiError(
                401,
                "INVALID_CREDENTIALS",
                "Phone/email or PIN/password is incorrect.",
            )
        else:
            user = conn.execute(
                """
                UPDATE users
                SET failed_logins = 0, locked_until = NULL, updated_at = now()
                WHERE id = %s
                RETURNING id, role, display_name, phone, email, kyc_verified
                """,
                (user["id"],),
            ).fetchone()

    if failure:
        raise failure
    if not user:
        raise ApiError(401, "INVALID_CREDENTIALS", "Phone/email or PIN/password is incorrect.")
    return _set_session(response, user)


@router.post("/logout", status_code=204)
def logout(response: Response) -> Response:
    response.delete_cookie(
        settings.jwt_cookie_name,
        path="/",
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
    )
    response.status_code = 204
    return response


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(get_current_user)) -> UserResponse:
    return _user_response(user)

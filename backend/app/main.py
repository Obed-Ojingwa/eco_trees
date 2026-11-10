import logging
import re
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.errors import ApiError
from app.core.logging import configure_logging, request_id_var
from app.db.pool import close_pool, connection, open_pool
from app.modules.auth.router import router as auth_router
from app.modules.auth.schemas import ProfileUpdate
from app.modules.monitoring.router import router as monitoring_router
from app.modules.plots.router import router as plots_router
from app.modules.notifications.router import router as notifications_router


logger = logging.getLogger(__name__)
_request_id_pattern = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
_mutating_methods = {"POST", "PUT", "PATCH", "DELETE"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    open_pool()
    yield
    close_pool()


app = FastAPI(
    title="EcoTrees API",
    version="0.1.0",
    docs_url=None if settings.environment.lower() in {"production", "prod"} else "/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-EcoTrees", "X-Ingest-Token", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    supplied_id = request.headers.get("X-Request-ID", "")
    request_id = supplied_id if _request_id_pattern.fullmatch(supplied_id) else str(uuid4())
    context_token = request_id_var.set(request_id)
    started = time.monotonic()
    try:
        if (
            request.url.path.startswith("/api/")
            and request.method in _mutating_methods
            and request.headers.get("X-EcoTrees") != "1"
        ):
            response = JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "CLIENT_HEADER_REQUIRED",
                        "message": "Mutating API requests must include X-EcoTrees: 1.",
                        "details": None,
                    },
                    "request_id": request_id,
                },
            )
        else:
            response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "HTTP request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "request_id": request_id,
            },
        )
        return response
    finally:
        request_id_var.reset(context_token)


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
            "request_id": request_id_var.get(),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(part) for part in item["loc"] if part != "body"),
            "message": item["msg"],
            "type": item["type"],
        }
        for item in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "One or more request fields are invalid.",
                "details": {"fields": errors},
            },
            "request_id": request_id_var.get(),
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    logger.info("HTTP error response", extra={"path": request.url.path, "status_code": exc.status_code})
    messages = {
        404: ("NOT_FOUND", "The requested resource was not found."),
        405: ("METHOD_NOT_ALLOWED", "This method is not allowed for the requested resource."),
    }
    code, message = messages.get(exc.status_code, ("HTTP_ERROR", str(exc.detail)))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {"code": code, "message": message, "details": None},
            "request_id": request_id_var.get(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled API error for %s: %s",
        request.url.path,
        exc,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "The request could not be completed.",
                "details": None,
            },
            "request_id": request_id_var.get(),
        },
    )


@app.get("/healthz")
@app.get("/api/healthz")
def health() -> dict[str, str]:
    with connection() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/api/data")
def legacy_demo_data() -> dict[str, str]:
    return {"message": "Hello from the FastAPI backend!", "status": "success"}


@app.get("/api/me")
def current_user_alias(user: dict = Depends(get_current_user)) -> dict:
    return {
        "id": str(user["id"]),
        "role": user["role"],
        "display_name": user["display_name"],
        "phone": user["phone"],
        "email": user["email"],
        "kyc_verified": user["kyc_verified"],
    }


@app.patch("/api/me")
def update_current_user(
    payload: ProfileUpdate,
    user: dict = Depends(get_current_user),
) -> dict:
    with connection() as conn:
        updated = conn.execute(
            """
            UPDATE users
            SET display_name = %s, updated_at = now()
            WHERE id = %s AND disabled_at IS NULL
            RETURNING id, role, display_name, phone, email, kyc_verified
            """,
            (payload.display_name, user["id"]),
        ).fetchone()
    if not updated:
        raise ApiError(401, "INVALID_SESSION", "Your session is invalid or expired.")
    return {
        "id": str(updated["id"]),
        "role": updated["role"],
        "display_name": updated["display_name"],
        "phone": updated["phone"],
        "email": updated["email"],
        "kyc_verified": updated["kyc_verified"],
    }


app.include_router(auth_router)
app.include_router(plots_router)
app.include_router(monitoring_router)
app.include_router(notifications_router)

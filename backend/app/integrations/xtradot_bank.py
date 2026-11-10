import logging
import random
import re
import time
from uuid import uuid4

import httpx

from app.core.config import settings
from app.core.errors import ApiError
from app.core.logging import request_id_var
from app.db.pool import connection


logger = logging.getLogger(__name__)
_sensitive_path_segment = re.compile(r"(?<!\d)\d{6,}(?!\d)")


class DatabaseTokenBucket:
    def __init__(self, budget_per_minute: int) -> None:
        if budget_per_minute < 1:
            raise ValueError("The bank request budget must be positive.")
        self.rate_per_second = budget_per_minute / 60
        self.capacity = float(budget_per_minute)

    def acquire(self) -> None:
        while True:
            with connection() as conn, conn.transaction():
                row = conn.execute(
                    """
                    SELECT tokens, updated_at
                    FROM bank_rate_limiter
                    WHERE id = 1
                    FOR UPDATE
                    """
                ).fetchone()
                if not row:
                    raise RuntimeError("The shared bank rate limiter has not been migrated.")
                now = conn.execute("SELECT clock_timestamp() AS now").fetchone()["now"]
                elapsed = max(0.0, (now - row["updated_at"]).total_seconds())
                tokens = min(self.capacity, row["tokens"] + elapsed * self.rate_per_second)
                if tokens >= 1:
                    tokens -= 1
                    wait_seconds = 0.0
                else:
                    wait_seconds = (1 - tokens) / self.rate_per_second
                conn.execute(
                    """
                    UPDATE bank_rate_limiter
                    SET tokens = %s, updated_at = %s
                    WHERE id = 1
                    """,
                    (tokens, now),
                )
            if wait_seconds <= 0:
                return
            time.sleep(wait_seconds)


class XtradotBankClient:
    def __init__(self) -> None:
        self._limiter = DatabaseTokenBucket(settings.bank_rpm_budget)
        self._client = httpx.Client(timeout=httpx.Timeout(15.0))

    def close(self) -> None:
        self._client.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        idempotency_key: str | None = None,
    ) -> httpx.Response:
        if not settings.gateway_key:
            raise ApiError(503, "BANK_NOT_CONFIGURED", "The bank integration is not configured.")
        method = method.upper()
        url = f"{settings.bank_api_base.rstrip('/')}/{path.lstrip('/')}"
        headers = {"x-api-key": settings.gateway_key}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        safe_path = _sensitive_path_segment.sub("[redacted]", "/" + path.lstrip("/"))
        request_id = request_id_var.get()
        max_attempts = settings.bank_get_retries + 1 if method == "GET" else 1
        started = time.monotonic()
        response: httpx.Response | None = None

        for attempt in range(max_attempts):
            self._limiter.acquire()
            try:
                response = self._client.request(
                    method,
                    url,
                    headers=headers,
                    json=json_body,
                )
            except httpx.RequestError as exc:
                self._write_log(request_id, method, safe_path, None, started)
                logger.error(
                    "Bank request failed with %s",
                    type(exc).__name__,
                    extra={
                        "method": method,
                        "path": safe_path,
                        "request_id": request_id,
                    },
                )
                raise

            if (
                method == "GET"
                and response.status_code in {429, 503}
                and attempt + 1 < max_attempts
            ):
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = min(5.0, max(0.0, float(retry_after))) if retry_after else 0
                except ValueError:
                    delay = 0
                if delay == 0:
                    delay = min(2.0, 0.2 * (2**attempt))
                delay = min(5.0, delay * random.uniform(0.75, 1.25))
                time.sleep(delay)
                continue
            break

        if response is None:
            raise RuntimeError("Bank client completed without a response.")
        self._write_log(request_id, method, safe_path, response.status_code, started)
        logger.info(
            "Bank request completed",
            extra={
                "method": method,
                "path": safe_path,
                "status_code": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "bank_request_id": response.headers.get("x-request-id"),
                "request_id": request_id,
            },
        )
        return response

    @staticmethod
    def _write_log(
        request_id: str,
        method: str,
        path: str,
        status_code: int | None,
        started: float,
    ) -> None:
        duration_ms = max(0, round((time.monotonic() - started) * 1000))
        with connection() as conn:
            conn.execute(
                """
                INSERT INTO bank_api_log (id, request_id, method, path, status_code, duration_ms)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (uuid4(), request_id, method, path, status_code, duration_ms),
            )


client = XtradotBankClient()

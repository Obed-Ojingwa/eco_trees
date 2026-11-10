from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import ApiError
from app.integrations.xtradot_bank import client as bank_client


def bank_request(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    if settings.payment_backend != "mock":
        raise ApiError(
            503,
            "BANK_SCHEMA_UNCONFIRMED",
            "Payment, transfer, and beneficiary schemas are not verified for the live bank.",
        )
    try:
        response = bank_client.request(
            method,
            path,
            json_body=body,
            idempotency_key=idempotency_key,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ApiError(
            502,
            "BANK_REQUEST_REJECTED",
            "The bank rejected the request.",
            {"bank_status": exc.response.status_code},
        ) from exc
    except httpx.RequestError as exc:
        raise ApiError(
            502,
            "BANK_UNAVAILABLE",
            "The bank request did not complete; its outcome may be unknown.",
        ) from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise ApiError(502, "BANK_INVALID_RESPONSE", "The bank returned invalid JSON.") from exc
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise ApiError(502, "BANK_INVALID_RESPONSE", "The bank response has an invalid shape.")
    return data

import hashlib
import hmac
import json
import time
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from pydantic import BaseModel, Field, field_validator
from psycopg.types.json import Jsonb

from app.core.config import settings
from app.core.dependencies import require_roles
from app.core.errors import ApiError
from app.db.pool import connection
from app.integrations.bank_flows import bank_request
from app.modules.finance import validate_ledger_entries


router = APIRouter(tags=["marketplace and payments"])


class OrderCreateRequest(BaseModel):
    credit_serials: list[str] = Field(min_length=1, max_length=500)

    @field_validator("credit_serials")
    @classmethod
    def unique_credit_serials(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("credit_serials cannot contain duplicates.")
        return value


class PaymentDrillRequest(BaseModel):
    outcome: Literal["paid", "partial", "overpaid", "failed", "pending", "timeout"]


def _order_response(
    order: dict[str, Any],
    items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result = {
        "id": str(order["id"]),
        "status": order["status"],
        "escrow_state": order["escrow_state"],
        "payment_status": order["payment_status"],
        "subtotal_kobo": order["subtotal_kobo"],
        "buyer_fee_kobo": order["buyer_fee_kobo"],
        "total_kobo": order["total_kobo"],
        "payment_reference": order["payment_reference"],
        "payment_url": order["payment_url"],
        "expires_at": order["expires_at"],
        "paid_at": order["paid_at"],
        "created_at": order["created_at"],
    }
    if items is not None:
        result["credits"] = items
    return result


def _order_items(conn, order_id: UUID) -> list[dict[str, Any]]:
    return conn.execute(
        """
        SELECT c.serial, oi.price_per_tonne_kobo
        FROM order_items oi JOIN credits c ON c.id = oi.credit_id
        WHERE oi.order_id = %s ORDER BY c.serial
        """,
        (order_id,),
    ).fetchall()


def _post_ledger_txn(
    conn,
    *,
    idempotency_key: str,
    source_type: str,
    source_id: UUID,
    description: str,
    entries: list[tuple[str, UUID | None, str, int]],
) -> UUID:
    try:
        validate_ledger_entries([(side, amount) for _, _, side, amount in entries])
    except ValueError as exc:
        raise ApiError(422, "UNBALANCED_LEDGER_TRANSACTION", str(exc)) from exc
    request_hash = hashlib.sha256(
        json.dumps(
            sorted((account, str(owner) if owner else None, side, amount)
                   for account, owner, side, amount in entries),
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    existing = conn.execute(
        "SELECT id, request_sha256 FROM ledger_transactions WHERE idempotency_key = %s",
        (idempotency_key,),
    ).fetchone()
    if existing:
        if existing["request_sha256"] != request_hash:
            raise ApiError(
                409,
                "LEDGER_IDEMPOTENCY_CONFLICT",
                "This ledger idempotency key was already used for a different transaction.",
            )
        return existing["id"]
    transaction_id = uuid4()
    conn.execute(
        """
        INSERT INTO ledger_transactions
            (id, idempotency_key, source_type, source_id, description, request_sha256)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (transaction_id, idempotency_key, source_type, source_id, description, request_hash),
    )
    conn.executemany(
        """
        INSERT INTO ledger_entries
            (id, transaction_id, account_code, owner_id, side, amount_kobo)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        [
            (uuid4(), transaction_id, account, owner, side, amount)
            for account, owner, side, amount in entries
            if amount > 0
        ],
    )
    return transaction_id


def _release_order_credits(conn, order_id: UUID) -> None:
    conn.execute(
        """
        UPDATE credits
        SET status = 'listed', reserved_order_id = NULL
        WHERE reserved_order_id = %s AND status = 'reserved'
        """,
        (order_id,),
    )


def confirm_payment(conn, order_id: UUID, payment: dict[str, Any]) -> dict[str, Any]:
    order = conn.execute(
        "SELECT * FROM orders WHERE id = %s FOR UPDATE",
        (order_id,),
    ).fetchone()
    if not order:
        raise ApiError(404, "ORDER_NOT_FOUND", "Order not found.")
    if payment.get("reference") != order["payment_reference"]:
        raise ApiError(502, "BANK_REFERENCE_MISMATCH", "The verified payment reference does not match the order.")

    provider_status = payment.get("status")
    if provider_status in {"pending", "unknown", "timeout"}:
        conn.execute(
            "UPDATE orders SET payment_status = 'unknown', updated_at = now() WHERE id = %s",
            (order_id,),
        )
        return {"status": order["status"], "payment_status": "unknown"}
    if provider_status == "failed":
        if order["status"] in {"created", "checkout_pending"}:
            conn.execute(
                """
                UPDATE orders
                SET status = 'failed', payment_status = 'failed', updated_at = now()
                WHERE id = %s
                """,
                (order_id,),
            )
            _release_order_credits(conn, order_id)
        return {"status": "failed", "payment_status": "failed"}
    if provider_status != "paid":
        raise ApiError(502, "BANK_INVALID_RESPONSE", "The bank returned an unsupported payment status.")

    amount = payment.get("amount_kobo")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        raise ApiError(502, "BANK_INVALID_RESPONSE", "The bank returned an invalid payment amount.")
    if order["status"] == "paid":
        if amount != order["total_kobo"]:
            raise ApiError(409, "PAID_ORDER_AMOUNT_CHANGED", "The bank's paid amount changed after confirmation.")
        return {"status": "paid", "payment_status": "paid"}

    if amount != order["total_kobo"] or order["status"] not in {"created", "checkout_pending"}:
        if amount:
            _post_ledger_txn(
                conn,
                idempotency_key=f"payment-suspense:{order_id}",
                source_type="payment_suspense",
                source_id=order_id,
                description="Unmatched, late, partial, or overpaid bank collection",
                entries=[
                    ("bank_cash", None, "debit", amount),
                    ("payment_suspense", None, "credit", amount),
                ],
            )
        conn.execute(
            """
            UPDATE orders
            SET status = 'failed', payment_status = 'amount_mismatch', updated_at = now()
            WHERE id = %s AND status <> 'paid'
            """,
            (order_id,),
        )
        _release_order_credits(conn, order_id)
        return {"status": "failed", "payment_status": "amount_mismatch"}

    _post_ledger_txn(
        conn,
        idempotency_key=f"payment:{order_id}",
        source_type="order_payment",
        source_id=order_id,
        description="Verified buyer collection held in escrow",
        entries=[
            ("bank_cash", None, "debit", order["total_kobo"]),
            ("marketplace_escrow", None, "credit", order["subtotal_kobo"]),
            ("buyer_fee_revenue", None, "credit", order["buyer_fee_kobo"]),
        ],
    )
    conn.execute(
        """
        UPDATE orders
        SET status = 'paid', escrow_state = 'held', payment_status = 'paid',
            paid_at = now(), updated_at = now()
        WHERE id = %s
        """,
        (order_id,),
    )
    conn.execute(
        """
        UPDATE credits
        SET status = 'sold', reserved_order_id = NULL
        WHERE reserved_order_id = %s AND status = 'reserved'
        """,
        (order_id,),
    )
    conn.execute(
        """
        INSERT INTO credit_ownership (credit_id, owner_id, order_id)
        SELECT oi.credit_id, o.buyer_id, o.id
        FROM order_items oi JOIN orders o ON o.id = oi.order_id
        WHERE o.id = %s
        ON CONFLICT (credit_id) DO NOTHING
        """,
        (order_id,),
    )
    conn.execute(
        """
        UPDATE carbon_batches b
        SET status = 'sold_out', updated_at = now()
        WHERE b.status = 'listed'
          AND b.id IN (
              SELECT c.batch_id
              FROM order_items oi JOIN credits c ON c.id = oi.credit_id
              WHERE oi.order_id = %s
          )
          AND NOT EXISTS (
              SELECT 1 FROM credits c
              WHERE c.batch_id = b.id AND c.status IN ('listed', 'reserved')
          )
        """,
        (order_id,),
    )
    return {"status": "paid", "payment_status": "paid"}


def _get_order(order_id: UUID, buyer_id: UUID | None = None) -> dict[str, Any]:
    with connection() as conn:
        order = conn.execute(
            """
            SELECT * FROM orders
            WHERE id = %s AND (%s::uuid IS NULL OR buyer_id = %s)
            """,
            (order_id, buyer_id, buyer_id),
        ).fetchone()
        items = _order_items(conn, order_id) if order else []
    if not order:
        raise ApiError(404, "ORDER_NOT_FOUND", "Order not found.")
    return _order_response(order, items)


@router.get("/api/marketplace/credits")
def browse_marketplace(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT c.serial, c.registry_source, b.batch_number, b.vintage,
                   b.price_per_tonne_kobo, b.package_sha256
            FROM credits c JOIN carbon_batches b ON b.id = c.batch_id
            WHERE c.status = 'listed'
            ORDER BY b.vintage DESC, c.serial
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        ).fetchall()
    return {"items": rows, "limit": limit, "offset": offset}


@router.post("/api/orders", status_code=201)
def create_order(
    payload: OrderCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    buyer: dict = Depends(require_roles("buyer")),
) -> dict:
    with connection() as conn, conn.transaction():
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (f"{buyer['id']}:{idempotency_key}",),
        )
        existing = conn.execute(
            """
            SELECT * FROM orders WHERE buyer_id = %s AND idempotency_key = %s
            """,
            (buyer["id"], idempotency_key),
        ).fetchone()
        if existing:
            previous_serials = conn.execute(
                """
                SELECT c.serial FROM order_items oi JOIN credits c ON c.id = oi.credit_id
                WHERE oi.order_id = %s ORDER BY c.serial
                """,
                (existing["id"],),
            ).fetchall()
            if sorted(item["serial"] for item in previous_serials) != sorted(payload.credit_serials):
                raise ApiError(
                    409,
                    "IDEMPOTENCY_KEY_REUSED",
                    "This idempotency key was already used for another credit selection.",
                )
            return _order_response(existing, _order_items(conn, existing["id"]))

        credits = conn.execute(
            """
            SELECT c.id, c.serial, c.status, c.batch_id, b.price_per_tonne_kobo
            FROM credits c
            JOIN carbon_batches b ON b.id = c.batch_id
            WHERE c.serial = ANY(%s)
            ORDER BY c.id
            FOR UPDATE OF c
            """,
            (payload.credit_serials,),
        ).fetchall()
        if len(credits) != len(payload.credit_serials):
            raise ApiError(404, "CREDIT_NOT_FOUND", "One or more selected credits were not found.")
        unavailable = [item["serial"] for item in credits if item["status"] != "listed"]
        if unavailable:
            raise ApiError(
                409,
                "CREDIT_UNAVAILABLE",
                "One or more selected credits are no longer available.",
                {"serials": unavailable},
            )
        subtotal = sum(item["price_per_tonne_kobo"] for item in credits)
        buyer_fee = (subtotal * settings.checkout_fee_bps) // 10_000
        order_id = uuid4()
        order = conn.execute(
            """
            INSERT INTO orders
                (id, buyer_id, idempotency_key, subtotal_kobo, buyer_fee_kobo,
                 total_kobo, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s,
                    now() + make_interval(mins => %s))
            RETURNING *
            """,
            (
                order_id,
                buyer["id"],
                idempotency_key,
                subtotal,
                buyer_fee,
                subtotal + buyer_fee,
                settings.order_expiry_minutes,
            ),
        ).fetchone()
        conn.executemany(
            """
            INSERT INTO order_items (order_id, credit_id, price_per_tonne_kobo)
            VALUES (%s, %s, %s)
            """,
            [(order_id, item["id"], item["price_per_tonne_kobo"]) for item in credits],
        )
        updated = conn.execute(
            """
            UPDATE credits SET status = 'reserved', reserved_order_id = %s
            WHERE id = ANY(%s) AND status = 'listed'
            """,
            (order_id, [item["id"] for item in credits]),
        )
        if updated.rowcount != len(credits):
            raise ApiError(409, "CREDIT_RESERVATION_FAILED", "Some credits could not be reserved.")
        item_rows = _order_items(conn, order_id)
    return _order_response(order, item_rows)


@router.get("/api/orders")
def list_orders(
    buyer: dict = Depends(require_roles("buyer")),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM orders WHERE buyer_id = %s
            ORDER BY created_at DESC LIMIT %s
            """,
            (buyer["id"], limit),
        ).fetchall()
    return {"items": [_order_response(item) for item in rows]}


@router.get("/api/orders/{order_id}")
def get_order(order_id: UUID, buyer: dict = Depends(require_roles("buyer"))) -> dict:
    return _get_order(order_id, buyer["id"])


@router.post("/api/orders/{order_id}/checkout")
def start_checkout(order_id: UUID, buyer: dict = Depends(require_roles("buyer"))) -> dict:
    if settings.payment_backend != "mock":
        raise ApiError(
            503,
            "BANK_SCHEMA_UNCONFIRMED",
            "Hosted checkout is disabled until the live bank payment schema is verified.",
        )
    expired = False
    with connection() as conn, conn.transaction():
        order = conn.execute(
            "SELECT * FROM orders WHERE id = %s AND buyer_id = %s FOR UPDATE",
            (order_id, buyer["id"]),
        ).fetchone()
        if not order:
            raise ApiError(404, "ORDER_NOT_FOUND", "Order not found.")
        if order["status"] == "paid":
            return _order_response(order)
        if order["status"] != "created":
            return _order_response(order)
        if order["expires_at"] <= conn.execute("SELECT now() AS now").fetchone()["now"]:
            conn.execute(
                "UPDATE orders SET status = 'expired', updated_at = now() WHERE id = %s",
                (order_id,),
            )
            _release_order_credits(conn, order_id)
            expired = True
        else:
            payment_reference = str(order_id)
            conn.execute(
                """
                UPDATE orders
                SET status = 'checkout_pending', payment_status = 'pending',
                    payment_reference = %s, payment_request_started_at = now(),
                    updated_at = now()
                WHERE id = %s
                """,
                (payment_reference, order_id),
            )
    if expired:
        raise ApiError(409, "ORDER_EXPIRED", "This order has expired.")

    callback_url = f"{settings.public_base_url.rstrip('/')}/api/payments/{payment_reference}/verify"
    try:
        payment = bank_request(
            "POST",
            "/payments/checkout",
            body={
                "reference": payment_reference,
                "amount_kobo": order["total_kobo"],
                "callback_url": callback_url,
                "webhook_url": settings.webhook_url,
            },
            idempotency_key=f"checkout:{order_id}",
        )
    except ApiError:
        with connection() as conn:
            conn.execute(
                "UPDATE orders SET payment_status = 'unknown', updated_at = now() WHERE id = %s",
                (order_id,),
            )
        raise
    payment_url = payment.get("payment_url")
    if (
        payment.get("reference") != payment_reference
        or payment.get("amount_kobo") != order["total_kobo"]
        or not isinstance(payment_url, str)
        or not payment_url.startswith(("https://", "http://"))
    ):
        with connection() as conn:
            conn.execute(
                "UPDATE orders SET payment_status = 'unknown', updated_at = now() WHERE id = %s",
                (order_id,),
            )
        raise ApiError(502, "BANK_INVALID_RESPONSE", "The checkout response did not match the order.")
    with connection() as conn:
        updated = conn.execute(
            """
            UPDATE orders
            SET payment_url = %s, provider_reference = %s, updated_at = now()
            WHERE id = %s AND status = 'checkout_pending'
            RETURNING *
            """,
            (payment_url, payment_reference, order_id),
        ).fetchone()
    return _order_response(updated)


def _verify_and_confirm(order: dict[str, Any]) -> dict[str, Any]:
    reference = order["payment_reference"]
    if not reference:
        raise ApiError(409, "CHECKOUT_NOT_STARTED", "Checkout has not been started for this order.")
    payment = bank_request("GET", f"/payments/{reference}/verify")
    with connection() as conn, conn.transaction():
        result = confirm_payment(conn, order["id"], payment)
    return {"order": _get_order(order["id"]), "verification": result}


@router.get("/api/payments/{reference}/verify")
def verify_payment(reference: UUID, buyer: dict = Depends(require_roles("buyer"))) -> dict:
    with connection() as conn:
        order = conn.execute(
            "SELECT * FROM orders WHERE payment_reference = %s AND buyer_id = %s",
            (str(reference), buyer["id"]),
        ).fetchone()
    if not order:
        raise ApiError(404, "ORDER_NOT_FOUND", "Payment reference not found.")
    return _verify_and_confirm(order)


@router.post("/hooks/forge", status_code=202)
async def receive_forge_webhook(
    request: Request,
    response: Response,
    x_forge_timestamp: str = Header(alias="x-forge-timestamp"),
    x_forge_signature: str = Header(alias="x-forge-signature"),
) -> dict:
    if not settings.forge_webhook_secret:
        raise ApiError(503, "WEBHOOK_NOT_CONFIGURED", "Webhook signature verification is not configured.")
    if not x_forge_timestamp.isascii() or not x_forge_timestamp.isdigit() or len(x_forge_timestamp) > 12:
        raise ApiError(401, "INVALID_WEBHOOK_SIGNATURE", "Webhook timestamp is invalid.")
    timestamp = int(x_forge_timestamp)
    if abs(int(time.time()) - timestamp) > 300:
        raise ApiError(401, "WEBHOOK_TIMESTAMP_EXPIRED", "Webhook timestamp is outside the allowed window.")
    raw_body = await request.body()
    if len(raw_body) > 1_048_576:
        raise ApiError(413, "WEBHOOK_TOO_LARGE", "Webhook payload exceeds the 1 MiB limit.")
    expected_signature = hmac.new(
        settings.forge_webhook_secret.encode("utf-8"),
        x_forge_timestamp.encode("ascii") + b"." + raw_body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, x_forge_signature):
        raise ApiError(401, "INVALID_WEBHOOK_SIGNATURE", "Webhook signature is invalid.")
    try:
        event = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApiError(400, "INVALID_WEBHOOK_BODY", "Webhook body must be valid JSON.") from exc
    event_id = event.get("event_id") if isinstance(event, dict) else None
    event_type = event.get("event_type") if isinstance(event, dict) else None
    if (
        not isinstance(event_id, str)
        or not 1 <= len(event_id) <= 200
        or not isinstance(event_type, str)
        or not 1 <= len(event_type) <= 100
        or not isinstance(event.get("data"), dict)
    ):
        raise ApiError(422, "INVALID_WEBHOOK_BODY", "Webhook event is missing required fields.")
    if event_type not in {
        "payment.succeeded",
        "payment.failed",
        "transfer.completed",
        "transfer.failed",
        "transfer.reversed",
    }:
        raise ApiError(422, "UNSUPPORTED_WEBHOOK_EVENT", "Webhook event type is not supported.")
    with connection() as conn:
        previous = conn.execute(
            "SELECT payload FROM payment_webhook_events WHERE event_id = %s",
            (event_id,),
        ).fetchone()
        if previous:
            if previous["payload"] != event:
                raise ApiError(409, "WEBHOOK_EVENT_ID_REUSED", "Webhook event ID was reused with a different payload.")
            response.status_code = 200
            return {"received": True, "duplicate": True}
        conn.execute(
            """
            INSERT INTO payment_webhook_events (event_id, event_type, payload)
            VALUES (%s, %s, %s)
            """,
            (event_id, event_type, Jsonb(event)),
        )
    return {"received": True, "duplicate": False}


@router.post("/api/admin/drills/payments/{order_id}")
def run_payment_drill(
    order_id: UUID,
    payload: PaymentDrillRequest,
    _admin: dict = Depends(require_roles("admin")),
) -> dict:
    if settings.payment_backend != "mock":
        raise ApiError(503, "DRILLS_MOCK_ONLY", "Payment failure drills are available only with the mock bank.")
    with connection() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id = %s", (order_id,)).fetchone()
    if not order or not order["payment_reference"]:
        raise ApiError(404, "CHECKOUT_NOT_FOUND", "A started checkout for this order was not found.")
    bank_request(
        "POST",
        f"/payments/{order['payment_reference']}/simulate",
        body={"outcome": payload.outcome},
    )
    with connection() as conn:
        refreshed = conn.execute("SELECT * FROM orders WHERE id = %s", (order_id,)).fetchone()
    return _verify_and_confirm(refreshed)


def ensure_webhook() -> dict[str, Any]:
    return bank_request("POST", "/webhooks/register", body={"url": settings.webhook_url})


@router.post("/api/admin/bank-reset")
def reset_mock_bank(_admin: dict = Depends(require_roles("admin"))) -> dict:
    if settings.payment_backend != "mock":
        raise ApiError(503, "BANK_RESET_MOCK_ONLY", "Bank reset is available only with the mock bank.")
    with connection() as conn:
        active = conn.execute(
            """
            SELECT
                (SELECT count(*) FROM orders
                  WHERE status IN ('created', 'checkout_pending')
                     OR (status = 'paid' AND escrow_state = 'held')) +
                (SELECT count(*) FROM payouts WHERE status IN ('submitted', 'processing', 'unknown')) AS total
            """
        ).fetchone()["total"]
    if active:
        raise ApiError(409, "BANK_RESET_HAS_ACTIVE_FLOWS", "Resolve open orders and payouts before resetting the mock bank.")
    result = bank_request("POST", "/mock/reset", body={})
    registration = ensure_webhook()
    return {"bank": result, "webhook": registration}

import logging
import time

from app.core.errors import ApiError
from app.core.logging import configure_logging
from app.db.pool import close_pool, connection, open_pool
from app.integrations.bank_flows import bank_request
from app.modules.payments import confirm_payment, ensure_webhook
from app.modules.payouts import release_paid_orders, requery_payout, submit_payout
from psycopg import Error as PsycopgError


logger = logging.getLogger(__name__)


def process_webhook_events(limit: int = 50) -> int:
    with connection() as conn, conn.transaction():
        conn.execute(
            """
            UPDATE payment_webhook_events SET status = 'pending'
            WHERE status = 'processing' AND received_at < now() - interval '5 minutes'
            """
        )
        events = conn.execute(
            """
            SELECT event_id, event_type, payload
            FROM payment_webhook_events
            WHERE status = 'pending'
            ORDER BY received_at
            LIMIT %s
            FOR UPDATE SKIP LOCKED
            """,
            (limit,),
        ).fetchall()
        for event in events:
            conn.execute(
                """
                UPDATE payment_webhook_events
                SET status = 'processing', attempts = attempts + 1
                WHERE event_id = %s
                """,
                (event["event_id"],),
            )

    processed = 0
    for event in events:
        try:
            data = event["payload"]["data"]
            reference = data.get("reference")
            if not isinstance(reference, str) or not reference:
                raise ValueError("Webhook data must include a reference.")
            if event["event_type"].startswith("payment."):
                with connection() as conn:
                    order = conn.execute(
                        "SELECT id FROM orders WHERE payment_reference = %s",
                        (reference,),
                    ).fetchone()
                if not order:
                    raise ValueError("Webhook payment reference does not match an order.")
                payment = bank_request("GET", f"/payments/{reference}/verify")
                with connection() as conn, conn.transaction():
                    confirm_payment(conn, order["id"], payment)
            elif event["event_type"].startswith("transfer."):
                with connection() as conn:
                    payout = conn.execute(
                        "SELECT id FROM payouts WHERE reference = %s",
                        (reference,),
                    ).fetchone()
                if not payout:
                    raise ValueError("Webhook transfer reference does not match a payout.")
                requery_payout(payout["id"])
            else:
                raise ValueError("Unsupported payment webhook event type.")
        except ValueError as exc:
            logger.warning(
                "Payment webhook event is invalid",
                extra={"event_id": event["event_id"], "reason": str(exc)},
            )
            with connection() as conn:
                conn.execute(
                    """
                    UPDATE payment_webhook_events
                    SET status = 'failed', last_error = %s
                    WHERE event_id = %s
                    """,
                    (str(exc)[:500], event["event_id"]),
                )
            continue
        except (ApiError, PsycopgError) as exc:
            logger.error(
                "Payment webhook processing failed",
                extra={"event_id": event["event_id"], "error": str(exc)},
                exc_info=(type(exc), exc, exc.__traceback__),
            )
            with connection() as conn:
                conn.execute(
                    """
                    UPDATE payment_webhook_events
                    SET status = CASE WHEN attempts >= 10 THEN 'failed' ELSE 'pending' END,
                        last_error = %s
                    WHERE event_id = %s
                    """,
                    (str(exc)[:500], event["event_id"]),
                )
            continue
        with connection() as conn:
            conn.execute(
                """
                UPDATE payment_webhook_events
                SET status = 'processed', processed_at = now(), last_error = NULL
                WHERE event_id = %s
                """,
                (event["event_id"],),
            )
        processed += 1
    return processed


def expire_orders(limit: int = 50) -> int:
    with connection() as conn:
        orders = conn.execute(
            """
            SELECT id, payment_reference
            FROM orders
            WHERE status IN ('created', 'checkout_pending') AND expires_at <= now()
            ORDER BY expires_at
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    expired = 0
    for item in orders:
        payment = None
        if item["payment_reference"]:
            try:
                payment = bank_request(
                    "GET",
                    f"/payments/{item['payment_reference']}/verify",
                )
            except ApiError:
                logger.warning(
                    "Unable to verify an expired order; reservation retained for recheck",
                    extra={"order_id": str(item["id"])},
                    exc_info=True,
                )
                continue
        with connection() as conn, conn.transaction():
            order = conn.execute("SELECT * FROM orders WHERE id = %s FOR UPDATE", (item["id"],)).fetchone()
            if not order or order["status"] not in {"created", "checkout_pending"}:
                continue
            if payment is not None:
                if payment.get("status") in {"unknown", "timeout"}:
                    continue
                result = confirm_payment(conn, item["id"], payment)
                if result["status"] == "paid":
                    continue
                if result["payment_status"] in {"failed", "amount_mismatch"}:
                    expired += 1
                    continue
            conn.execute(
                """
                UPDATE orders SET status = 'expired', updated_at = now()
                WHERE id = %s AND status IN ('created', 'checkout_pending')
                """,
                (item["id"],),
            )
            conn.execute(
                """
                UPDATE credits SET status = 'listed', reserved_order_id = NULL
                WHERE reserved_order_id = %s AND status = 'reserved'
                """,
                (item["id"],),
            )
            expired += 1
    return expired


def process_payouts(limit: int = 50) -> int:
    release_paid_orders(limit)
    with connection() as conn:
        pending = conn.execute(
            """
            SELECT id FROM payouts WHERE status = 'pending'
            ORDER BY created_at LIMIT %s
            """,
            (limit,),
        ).fetchall()
        to_requery = conn.execute(
            """
            SELECT id FROM payouts WHERE status IN ('submitted', 'unknown', 'processing')
            ORDER BY updated_at LIMIT %s
            """,
            (limit,),
        ).fetchall()
    processed = 0
    for payout in pending:
        submit_payout(payout["id"])
        processed += 1
    for payout in to_requery:
        requery_payout(payout["id"])
        processed += 1
    return processed


def run_once() -> dict[str, int]:
    return {
        "webhooks": process_webhook_events(),
        "expired_orders": expire_orders(),
        "payouts": process_payouts(),
    }


def run() -> None:
    configure_logging()
    open_pool()
    last_webhook_check = 0.0
    try:
        while True:
            now = time.monotonic()
            if now - last_webhook_check >= 300:
                try:
                    ensure_webhook()
                except ApiError:
                    logger.exception("Could not ensure the payment webhook registration.")
                last_webhook_check = now
            try:
                run_once()
            except (ApiError, PsycopgError):
                logger.exception("Finance worker cycle failed.")
            time.sleep(5)
    finally:
        close_pool()


if __name__ == "__main__":
    run()

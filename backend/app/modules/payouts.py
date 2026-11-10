from collections import defaultdict
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.dependencies import require_roles
from app.core.errors import ApiError
from app.db.pool import connection
from app.integrations.bank_flows import bank_request
from app.modules.finance import allocate_payouts
from app.modules.payments import _post_ledger_txn


router = APIRouter(tags=["farmer payouts"])


class PayoutAccountRequest(BaseModel):
    bank_code: str = Field(min_length=3, max_length=10, pattern=r"^[A-Za-z0-9]+$")
    account_number: str = Field(pattern=r"^\d{10}$")


class ConfirmPayoutAccountRequest(BaseModel):
    account_name: str = Field(min_length=2, max_length=160)


def _allocate_remainders(amount_kobo: int, claims: dict[str, Decimal]) -> dict[str, int]:
    if amount_kobo < 0 or not claims:
        raise ValueError("A non-negative amount and payout claims are required.")
    total = sum(claims.values(), Decimal(0))
    amounts: dict[str, int] = {}
    remainders: list[tuple[Decimal, str]] = []
    for key, claim in claims.items():
        exact = Decimal(amount_kobo) * claim / total
        amount = int(exact)
        amounts[key] = amount
        remainders.append((exact - amount, key))
    left = amount_kobo - sum(amounts.values())
    remainders.sort(key=lambda item: (-item[0], item[1]))
    for _, key in remainders[:left]:
        amounts[key] += 1
    return amounts


def release_paid_orders(limit: int = 50) -> int:
    released = 0
    with connection() as conn, conn.transaction():
        orders = conn.execute(
            """
            SELECT * FROM orders
            WHERE status = 'paid' AND escrow_state = 'held'
            ORDER BY paid_at, id
            LIMIT %s
            FOR UPDATE SKIP LOCKED
            """,
            (limit,),
        ).fetchall()
        for order in orders:
            batch_rows = conn.execute(
                """
                SELECT b.id AS batch_id, b.units,
                       count(*)::integer AS purchased_units,
                       sum(oi.price_per_tonne_kobo)::bigint AS proceeds_kobo
                FROM order_items oi
                JOIN credits c ON c.id = oi.credit_id
                JOIN carbon_batches b ON b.id = c.batch_id
                WHERE oi.order_id = %s
                GROUP BY b.id, b.units
                ORDER BY b.id
                """,
                (order["id"],),
            ).fetchall()
            if not batch_rows:
                raise ApiError(409, "ORDER_HAS_NO_CREDITS", "A paid order has no credit items to release.")
            seller_claims: dict[UUID, Decimal] = defaultdict(Decimal)
            for batch in batch_rows:
                attributed = conn.execute(
                    """
                    SELECT be.plot_id, p.farmer_id, be.tonnes_attributed
                    FROM batch_estimates be
                    JOIN plots p ON p.id = be.plot_id
                    WHERE be.batch_id = %s
                    ORDER BY p.farmer_id, be.plot_id
                    """,
                    (batch["batch_id"],),
                ).fetchall()
                if batch["units"] <= 0 or not attributed:
                    raise ApiError(409, "BATCH_ATTRIBUTION_INVALID", "Credit batch payout attribution is unavailable.")
                attributed_total = sum(
                    (item["tonnes_attributed"] for item in attributed),
                    Decimal(0),
                )
                if attributed_total != Decimal(batch["units"]):
                    raise ApiError(
                        409,
                        "BATCH_ATTRIBUTION_INVALID",
                        "Farmer attribution does not sum to the batch's issued units.",
                        {
                            "batch_id": str(batch["batch_id"]),
                            "attributed_tonnes": str(attributed_total),
                            "units": batch["units"],
                        },
                    )
                for item in attributed:
                    seller_claims[item["farmer_id"]] += (
                        Decimal(batch["proceeds_kobo"])
                        * item["tonnes_attributed"]
                        / Decimal(batch["units"])
                    )

            fee = order["subtotal_kobo"] * settings.payout_fee_bps // 10_000
            distributable_kobo = (order["subtotal_kobo"] - fee) // 100 * 100
            farmer_payouts = allocate_payouts(distributable_kobo, seller_claims)
            farmer_batch_payouts: dict[UUID, dict[UUID, Decimal]] = defaultdict(dict)
            for batch in batch_rows:
                for item in conn.execute(
                    """
                    SELECT p.farmer_id, be.tonnes_attributed
                    FROM batch_estimates be
                    JOIN plots p ON p.id = be.plot_id
                    WHERE be.batch_id = %s
                    ORDER BY p.farmer_id, be.plot_id
                    """,
                    (batch["batch_id"],),
                ).fetchall():
                    farmer_batch_payouts[item["farmer_id"]][batch["batch_id"]] = (
                        farmer_batch_payouts[item["farmer_id"]].get(batch["batch_id"], Decimal(0))
                        + Decimal(batch["proceeds_kobo"])
                        * item["tonnes_attributed"]
                        / Decimal(batch["units"])
                    )

            ledger_entries = [
                ("marketplace_escrow", None, "debit", order["subtotal_kobo"]),
            ]
            for farmer_id, amount in farmer_payouts.items():
                if amount:
                    ledger_entries.append(("farmer_payable", farmer_id, "credit", amount))
            retained_fee = order["subtotal_kobo"] - distributable_kobo
            if retained_fee:
                ledger_entries.append(("seller_fee_revenue", None, "credit", retained_fee))
            _post_ledger_txn(
                conn,
                idempotency_key=f"escrow-release:{order['id']}",
                source_type="escrow_release",
                source_id=order["id"],
                description="Escrow released to farmer payables",
                entries=ledger_entries,
            )

            accounts = conn.execute(
                """
                SELECT farmer_id, account_number_last4, confirmed_at
                FROM farmer_payout_accounts
                WHERE farmer_id = ANY(%s)
                """,
                (list(farmer_payouts),),
            ).fetchall()
            accounts_by_farmer = {item["farmer_id"]: item for item in accounts}
            for farmer_id, amount in farmer_payouts.items():
                if amount <= 0:
                    continue
                payout_id = uuid4()
                reference = f"ETP-{order['created_at']:%Y%m%d}-{payout_id.hex[:16].upper()}"
                account = accounts_by_farmer.get(farmer_id)
                status = "pending" if account and account["confirmed_at"] else "blocked"
                failure_code = None if status == "pending" else "PAYOUT_ACCOUNT_UNCONFIRMED"
                conn.execute(
                    """
                    INSERT INTO payouts
                        (id, order_id, farmer_id, reference, idempotency_key,
                         amount_kobo, status, account_last4, failure_code)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        payout_id,
                        order["id"],
                        farmer_id,
                        reference,
                        f"payout:{payout_id}",
                        amount,
                        status,
                        account["account_number_last4"] if account else None,
                        failure_code,
                    ),
                )
                allocations = _allocate_remainders(amount, farmer_batch_payouts[farmer_id])
                conn.executemany(
                    """
                    INSERT INTO payout_allocations (payout_id, batch_id, amount_kobo)
                    VALUES (%s, %s, %s)
                    """,
                    [
                        (payout_id, batch_id, allocation)
                        for batch_id, allocation in allocations.items()
                        if allocation > 0
                    ],
                )
                conn.execute(
                    """
                    INSERT INTO notifications
                        (id, farmer_id, kind, ref_id, message, points, celebrate)
                    VALUES (%s, %s, 'payout_pending', %s, %s, 0, false)
                    ON CONFLICT (farmer_id, kind, ref_id) DO NOTHING
                    """,
                    (
                        uuid4(),
                        farmer_id,
                        payout_id,
                        "A carbon-credit sale is ready for payout." if status == "pending"
                        else "A payout is waiting for a confirmed payout account.",
                    ),
                )
            conn.execute(
                "UPDATE orders SET escrow_state = 'released', updated_at = now() WHERE id = %s",
                (order["id"],),
            )
            released += 1
    return released


def _finalize_transfer(conn, payout: dict[str, Any], status: str, bank_reference: str | None) -> str:
    current_status = payout["status"]
    if current_status == "reversed":
        return "reversed"
    if current_status == "successful" and status not in {"successful", "reversed"}:
        return "successful"
    if status == "successful":
        if current_status != "successful":
            _post_ledger_txn(
                conn,
                idempotency_key=f"payout-settlement:{payout['id']}",
                source_type="payout",
                source_id=payout["id"],
                description="Successful farmer bank transfer",
                entries=[
                    ("farmer_payable", payout["farmer_id"], "debit", payout["amount_kobo"]),
                    ("bank_cash", None, "credit", payout["amount_kobo"]),
                ],
            )
            conn.execute(
                """
                INSERT INTO notifications
                    (id, farmer_id, kind, ref_id, message, points, celebrate)
                VALUES (%s, %s, 'payout_successful', %s, %s, 0, true)
                ON CONFLICT (farmer_id, kind, ref_id) DO NOTHING
                """,
                (uuid4(), payout["farmer_id"], payout["id"], "Your carbon-credit payout has arrived."),
            )
        conn.execute(
            """
            UPDATE payouts SET status = 'successful', bank_reference = COALESCE(%s, bank_reference),
                completed_at = COALESCE(completed_at, now()), updated_at = now()
            WHERE id = %s
            """,
            (bank_reference, payout["id"]),
        )
        return "successful"
    if status == "reversed":
        if current_status == "successful":
            _post_ledger_txn(
                conn,
                idempotency_key=f"payout-reversal:{payout['id']}",
                source_type="payout_reversal",
                source_id=payout["id"],
                description="Compensating entry for reversed bank transfer",
                entries=[
                    ("bank_cash", None, "debit", payout["amount_kobo"]),
                    ("farmer_payable", payout["farmer_id"], "credit", payout["amount_kobo"]),
                ],
            )
        conn.execute(
            """
            UPDATE payouts SET status = 'reversed', bank_reference = COALESCE(%s, bank_reference),
                completed_at = now(), updated_at = now()
            WHERE id = %s
            """,
            (bank_reference, payout["id"]),
        )
        conn.execute(
            """
            INSERT INTO notifications
                (id, farmer_id, kind, ref_id, message, points, celebrate)
            VALUES (%s, %s, 'payout_reversed', %s, %s, 0, false)
            ON CONFLICT (farmer_id, kind, ref_id) DO NOTHING
            """,
            (
                uuid4(),
                payout["farmer_id"],
                payout["id"],
                "A payout was reversed by the bank; the amount remains payable.",
            ),
        )
        return "reversed"
    if status in {"pending", "processing"}:
        next_status = "processing"
    elif status in {"unknown", "timeout"}:
        next_status = "unknown"
    elif status in {"blocked", "beneficiary_blocked"}:
        next_status = "blocked"
    elif status == "failed":
        next_status = "failed"
    else:
        raise ApiError(502, "BANK_INVALID_RESPONSE", "The bank returned an unsupported transfer status.")
    conn.execute(
        """
        UPDATE payouts SET status = %s, bank_reference = COALESCE(%s, bank_reference),
            failure_code = CASE WHEN %s IN ('failed', 'blocked') THEN %s ELSE failure_code END,
            updated_at = now()
        WHERE id = %s
        """,
        (
            next_status,
            bank_reference,
            next_status,
            next_status.upper(),
            payout["id"],
        ),
    )
    return next_status


def submit_payout(payout_id: UUID, *, test_outcome: str = "successful") -> dict[str, Any]:
    with connection() as conn, conn.transaction():
        payout = conn.execute(
            """
            SELECT p.*, a.bank_code, a.account_number_last4, a.account_name, a.confirmed_at,
                   pgp_sym_decrypt(a.account_number_ciphertext, %s) AS account_number
            FROM payouts p
            LEFT JOIN farmer_payout_accounts a ON a.farmer_id = p.farmer_id
            WHERE p.id = %s FOR UPDATE OF p
            """,
            (settings.payout_encryption_key, payout_id),
        ).fetchone()
        if not payout:
            raise ApiError(404, "PAYOUT_NOT_FOUND", "Payout not found.")
        if payout["status"] != "pending":
            return {"id": str(payout_id), "status": payout["status"]}
        if not payout["confirmed_at"] or not payout["account_number"]:
            conn.execute(
                """
                UPDATE payouts SET status = 'blocked', failure_code = 'PAYOUT_ACCOUNT_UNCONFIRMED',
                    updated_at = now() WHERE id = %s
                """,
                (payout_id,),
            )
            return {"id": str(payout_id), "status": "blocked"}
        account_number = payout["account_number"]

    if not settings.treasury_account:
        raise ApiError(503, "TREASURY_ACCOUNT_NOT_CONFIGURED", "The treasury account is not configured.")
    balance = bank_request("GET", f"/accounts/{settings.treasury_account}/balance")
    available = balance.get("available_balance_kobo")
    if not isinstance(available, int) or isinstance(available, bool) or available < 0:
        raise ApiError(502, "BANK_INVALID_RESPONSE", "The bank returned an invalid treasury balance.")
    if available < payout["amount_kobo"]:
        with connection() as conn:
            conn.execute(
                """
                UPDATE payouts SET failure_code = 'TREASURY_PREFLIGHT_INSUFFICIENT', updated_at = now()
                WHERE id = %s AND status = 'pending'
                """,
                (payout_id,),
            )
        return {"id": str(payout_id), "status": "pending", "reason": "treasury_insufficient"}

    with connection() as conn, conn.transaction():
        current = conn.execute("SELECT status FROM payouts WHERE id = %s FOR UPDATE", (payout_id,)).fetchone()
        if not current:
            raise ApiError(404, "PAYOUT_NOT_FOUND", "Payout not found.")
        if current["status"] != "pending":
            return {"id": str(payout_id), "status": current["status"]}
        conn.execute(
            """
            UPDATE payouts SET status = 'submitted', submitted_at = now(), updated_at = now()
            WHERE id = %s AND status = 'pending'
            """,
            (payout_id,),
        )
    try:
        transfer = bank_request(
            "POST",
            "/transfers",
            body={
                "reference": payout["reference"],
                "amount_kobo": payout["amount_kobo"],
                "bank_code": payout["bank_code"],
                "account_number": account_number,
                "account_name": payout["account_name"],
                "test_outcome": test_outcome if settings.payment_backend == "mock" else "successful",
            },
            idempotency_key=payout["idempotency_key"],
        )
    except (ApiError, httpx.RequestError):
        with connection() as conn:
            conn.execute(
                "UPDATE payouts SET status = 'unknown', failure_code = 'TRANSFER_OUTCOME_UNKNOWN', updated_at = now() WHERE id = %s AND status = 'submitted'",
                (payout_id,),
            )
        return {"id": str(payout_id), "status": "unknown"}
    if (
        transfer.get("reference") != payout["reference"]
        or transfer.get("amount_kobo") != payout["amount_kobo"]
        or transfer.get("status") not in {"successful", "processing", "unknown", "failed", "blocked", "reversed"}
    ):
        with connection() as conn:
            conn.execute(
                "UPDATE payouts SET status = 'unknown', failure_code = 'TRANSFER_RESPONSE_MISMATCH', updated_at = now() WHERE id = %s AND status = 'submitted'",
                (payout_id,),
            )
        return {"id": str(payout_id), "status": "unknown"}
    with connection() as conn, conn.transaction():
        current = conn.execute("SELECT * FROM payouts WHERE id = %s FOR UPDATE", (payout_id,)).fetchone()
        status = _finalize_transfer(conn, current, transfer["status"], transfer.get("bank_reference"))
    return {"id": str(payout_id), "status": status}


def requery_payout(payout_id: UUID) -> dict[str, Any]:
    with connection() as conn:
        payout = conn.execute("SELECT * FROM payouts WHERE id = %s", (payout_id,)).fetchone()
    if not payout:
        raise ApiError(404, "PAYOUT_NOT_FOUND", "Payout not found.")
    if payout["status"] not in {"submitted", "unknown", "processing", "successful"}:
        return {"id": str(payout_id), "status": payout["status"]}
    transfer = bank_request("GET", f"/transfers/{payout['reference']}")
    if transfer.get("reference") != payout["reference"] or transfer.get("amount_kobo") != payout["amount_kobo"]:
        raise ApiError(502, "BANK_REFERENCE_MISMATCH", "The queried bank transfer does not match the payout.")
    with connection() as conn, conn.transaction():
        current = conn.execute("SELECT * FROM payouts WHERE id = %s FOR UPDATE", (payout_id,)).fetchone()
        status = _finalize_transfer(conn, current, transfer["status"], transfer.get("bank_reference"))
    return {"id": str(payout_id), "status": status}


@router.put("/api/farmer/payout-account")
def set_payout_account(
    payload: PayoutAccountRequest,
    farmer: dict = Depends(require_roles("farmer")),
) -> dict:
    if len(settings.payout_encryption_key.encode()) < 32:
        raise ApiError(503, "PAYOUT_ENCRYPTION_UNAVAILABLE", "Payout account encryption is not configured.")
    result = bank_request(
        "POST",
        "/accounts/name-enquiry",
        body={"bank_code": payload.bank_code, "account_number": payload.account_number},
    )
    account_name = result.get("account_name")
    if (
        result.get("bank_code") != payload.bank_code
        or result.get("account_number") != payload.account_number
        or not isinstance(account_name, str)
        or not account_name.strip()
    ):
        raise ApiError(502, "BANK_INVALID_RESPONSE", "The name enquiry did not match the submitted account.")
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO farmer_payout_accounts
                (farmer_id, bank_code, account_number_ciphertext, account_number_last4,
                 account_name, name_enquiry_reference, verified_at, confirmed_at, updated_at)
            VALUES (%s, %s, pgp_sym_encrypt(%s, %s), %s, %s, %s, now(), NULL, now())
            ON CONFLICT (farmer_id) DO UPDATE SET
                bank_code = EXCLUDED.bank_code,
                account_number_ciphertext = EXCLUDED.account_number_ciphertext,
                account_number_last4 = EXCLUDED.account_number_last4,
                account_name = EXCLUDED.account_name,
                name_enquiry_reference = EXCLUDED.name_enquiry_reference,
                verified_at = now(), confirmed_at = NULL, updated_at = now()
            """,
            (
                farmer["id"],
                payload.bank_code,
                payload.account_number,
                settings.payout_encryption_key,
                payload.account_number[-4:],
                account_name.strip(),
                result.get("reference"),
            ),
        )
    return {
        "bank_code": payload.bank_code,
        "account_number_masked": f"******{payload.account_number[-4:]}",
        "resolved_account_name": account_name.strip(),
        "confirmed": False,
    }


@router.get("/api/farmer/payout-account")
def get_payout_account(farmer: dict = Depends(require_roles("farmer"))) -> dict:
    with connection() as conn:
        account = conn.execute(
            """
            SELECT bank_code, account_number_last4, account_name, verified_at, confirmed_at
            FROM farmer_payout_accounts WHERE farmer_id = %s
            """,
            (farmer["id"],),
        ).fetchone()
    if not account:
        return {"configured": False}
    return {
        "configured": True,
        "bank_code": account["bank_code"],
        "account_number_masked": f"******{account['account_number_last4']}",
        "resolved_account_name": account["account_name"],
        "verified_at": account["verified_at"],
        "confirmed_at": account["confirmed_at"],
        "confirmed": account["confirmed_at"] is not None,
    }


@router.post("/api/farmer/payout-account/confirm")
def confirm_payout_account(
    payload: ConfirmPayoutAccountRequest,
    farmer: dict = Depends(require_roles("farmer")),
) -> dict:
    with connection() as conn, conn.transaction():
        account = conn.execute(
            """
            UPDATE farmer_payout_accounts
            SET confirmed_at = now(), updated_at = now()
            WHERE farmer_id = %s AND account_name = %s AND verified_at > now() - interval '24 hours'
            RETURNING bank_code, account_number_last4, account_name, confirmed_at
            """,
            (farmer["id"], payload.account_name.strip()),
        ).fetchone()
        if account:
            conn.execute(
                """
                UPDATE payouts p
                SET status = 'pending', account_last4 = a.account_number_last4,
                    failure_code = NULL, updated_at = now()
                FROM farmer_payout_accounts a
                WHERE p.farmer_id = %s AND a.farmer_id = p.farmer_id
                  AND p.status = 'blocked'
                  AND p.failure_code = 'PAYOUT_ACCOUNT_UNCONFIRMED'
                """,
                (farmer["id"],),
            )
            conn.execute(
                """
                UPDATE payouts p
                SET account_last4 = a.account_number_last4, updated_at = now()
                FROM farmer_payout_accounts a
                WHERE p.farmer_id = %s AND a.farmer_id = p.farmer_id
                  AND p.status = 'pending'
                """,
                (farmer["id"],),
            )
    if not account:
        raise ApiError(409, "PAYOUT_ACCOUNT_CONFIRMATION_FAILED", "Confirm the recently resolved account name exactly.")
    return {
        "bank_code": account["bank_code"],
        "account_number_masked": f"******{account['account_number_last4']}",
        "account_name": account["account_name"],
        "confirmed_at": account["confirmed_at"],
    }


@router.get("/api/admin/payouts")
def list_payouts(
    _admin: dict = Depends(require_roles("admin")),
    status: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    allowed = {"pending", "submitted", "processing", "unknown", "successful", "failed", "blocked", "reversed"}
    if status and status not in allowed:
        raise ApiError(422, "INVALID_PAYOUT_STATUS", "The requested payout status is invalid.")
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT id, order_id, farmer_id, reference, amount_kobo, status,
                   account_last4, bank_reference, failure_code, submitted_at,
                   completed_at, created_at, updated_at
            FROM payouts
            WHERE (%s::text IS NULL OR status = %s)
            ORDER BY created_at DESC LIMIT %s
            """,
            (status, status, limit),
        ).fetchall()
    return {"items": rows}


@router.post("/api/admin/payouts/release")
def release_payouts(_admin: dict = Depends(require_roles("admin"))) -> dict:
    return {"released_orders": release_paid_orders()}


@router.post("/api/admin/payouts/{payout_id}/requery")
def admin_requery_payout(
    payout_id: UUID,
    _admin: dict = Depends(require_roles("admin")),
) -> dict:
    return requery_payout(payout_id)


@router.post("/api/admin/payouts/{payout_id}/submit")
def admin_submit_payout(
    payout_id: UUID,
    x_test_outcome: str = Header(default="successful", alias="X-Test-Outcome"),
    _admin: dict = Depends(require_roles("admin")),
) -> dict:
    allowed = {"successful", "processing", "unknown", "failed", "blocked"}
    if x_test_outcome not in allowed:
        raise ApiError(422, "INVALID_TEST_OUTCOME", "The requested payout test outcome is invalid.")
    if settings.payment_backend != "mock" and x_test_outcome != "successful":
        raise ApiError(400, "TEST_OUTCOME_MOCK_ONLY", "Forced transfer outcomes require the mock bank.")
    return submit_payout(payout_id, test_outcome=x_test_outcome)

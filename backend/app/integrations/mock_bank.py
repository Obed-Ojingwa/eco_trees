import hmac
import os
from threading import RLock
from uuid import uuid4

from fastapi import FastAPI
from fastapi import Request
from fastapi import Header
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse


app = FastAPI(title="EcoTrees Mock Bank", docs_url=None, redoc_url=None)
_lock = RLock()
_payments: dict[str, dict] = {}
_payment_idempotency: dict[str, str] = {}
_transfers: dict[str, dict] = {}
_transfer_idempotency: dict[str, str] = {}
_webhooks: dict[str, dict] = {}
_treasury_balance_kobo = 10_000_000_000


class CheckoutRequest(BaseModel):
    reference: str
    amount_kobo: int = Field(gt=0)
    callback_url: str
    webhook_url: str


class SimulatePaymentRequest(BaseModel):
    outcome: str = Field(pattern="^(paid|partial|overpaid|failed|pending|timeout)$")


class NameEnquiryRequest(BaseModel):
    bank_code: str
    account_number: str = Field(pattern=r"^\d{10}$")


class TransferRequest(BaseModel):
    reference: str
    amount_kobo: int = Field(gt=0)
    bank_code: str
    account_number: str = Field(pattern=r"^\d{10}$")
    account_name: str
    test_outcome: str = Field(
        default="successful",
        pattern="^(successful|processing|unknown|failed|blocked)$",
    )


class SimulateTransferRequest(BaseModel):
    outcome: str = Field(pattern="^(successful|processing|unknown|failed|blocked|reversed)$")


@app.middleware("http")
async def require_mock_api_key(request: Request, call_next):
    if request.url.path.startswith("/v1/"):
        expected = os.getenv("GATEWAY_KEY", "")
        supplied = request.headers.get("x-api-key", "")
        if not expected or not hmac.compare_digest(expected, supplied):
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "INVALID_API_KEY",
                        "message": "A valid x-api-key is required.",
                    }
                },
            )
    return await call_next(request)


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/banks")
def list_banks() -> dict:
    return {
        "data": [
            {"code": "001", "name": "Demo Commercial Bank"},
            {"code": "002", "name": "Demo Community Bank"},
        ]
    }


@app.get("/v1/tariff")
def tariff() -> dict:
    return {"data": [], "message": "Configure mock tariffs for the integration test."}


@app.post("/v1/payments/checkout")
def create_checkout(
    payload: CheckoutRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> dict:
    with _lock:
        existing_ref = _payment_idempotency.get(idempotency_key)
        if existing_ref:
            return {"data": _payments[existing_ref]}
        payment = {
            "reference": payload.reference,
            "amount_kobo": payload.amount_kobo,
            "status": "pending",
            "payment_url": f"http://mock-bank/pay/{payload.reference}",
        }
        _payments[payload.reference] = payment
        _payment_idempotency[idempotency_key] = payload.reference
        return {"data": payment}


@app.get("/v1/payments/{reference}/verify")
def verify_checkout(reference: str) -> dict:
    with _lock:
        payment = _payments.get(reference)
        if not payment:
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "PAYMENT_NOT_FOUND", "message": "Payment not found."}},
            )
        return {"data": dict(payment)}


@app.post("/v1/payments/{reference}/simulate")
def simulate_payment(reference: str, payload: SimulatePaymentRequest) -> dict:
    with _lock:
        payment = _payments.get(reference)
        if not payment:
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "PAYMENT_NOT_FOUND", "message": "Payment not found."}},
            )
        amount = payment["amount_kobo"]
        if payload.outcome == "paid":
            payment.update(status="paid", amount_kobo=amount)
        elif payload.outcome == "partial":
            payment.update(status="paid", amount_kobo=max(1, amount - 100))
        elif payload.outcome == "overpaid":
            payment.update(status="paid", amount_kobo=amount + 100)
        else:
            payment["status"] = payload.outcome
        return {"data": dict(payment)}


@app.post("/v1/webhooks/register")
def register_webhook(payload: dict) -> dict:
    url = payload.get("url")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "INVALID_WEBHOOK_URL", "message": "A valid URL is required."}},
        )
    with _lock:
        webhook = _webhooks.setdefault(url, {"id": str(uuid4()), "url": url})
        return {"data": dict(webhook)}


@app.post("/v1/accounts/name-enquiry")
def name_enquiry(payload: NameEnquiryRequest) -> dict:
    return {
        "data": {
            "bank_code": payload.bank_code,
            "account_number": payload.account_number,
            "account_name": f"Demo Beneficiary {payload.account_number[-4:]}",
            "reference": f"NAME-{uuid4()}",
        }
    }


@app.get("/v1/accounts/{account_number}/balance")
def account_balance(account_number: str) -> dict:
    if not account_number.isdigit():
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "INVALID_ACCOUNT", "message": "Invalid account number."}},
        )
    with _lock:
        return {"data": {"account_number": account_number, "available_balance_kobo": _treasury_balance_kobo}}


@app.post("/v1/transfers")
def create_transfer(
    payload: TransferRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> dict:
    global _treasury_balance_kobo
    with _lock:
        existing_ref = _transfer_idempotency.get(idempotency_key)
        if existing_ref:
            return {"data": dict(_transfers[existing_ref])}
        transfer = {
            "reference": payload.reference,
            "amount_kobo": payload.amount_kobo,
            "status": payload.test_outcome,
            "bank_reference": f"MOCK-{uuid4()}",
            "settled_status": "successful" if payload.test_outcome == "unknown" else payload.test_outcome,
            "debited": False,
        }
        if transfer["settled_status"] == "successful":
            _treasury_balance_kobo -= payload.amount_kobo
            transfer["debited"] = True
        _transfers[payload.reference] = transfer
        _transfer_idempotency[idempotency_key] = payload.reference
        return {"data": dict(transfer)}


@app.get("/v1/transfers/{reference}")
def get_transfer(reference: str) -> dict:
    global _treasury_balance_kobo
    with _lock:
        transfer = _transfers.get(reference)
        if not transfer:
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "TRANSFER_NOT_FOUND", "message": "Transfer not found."}},
            )
        if transfer["status"] == "unknown":
            transfer["status"] = transfer["settled_status"]
        return {"data": dict(transfer)}


@app.post("/v1/transfers/{reference}/simulate")
def simulate_transfer(reference: str, payload: SimulateTransferRequest) -> dict:
    global _treasury_balance_kobo
    with _lock:
        transfer = _transfers.get(reference)
        if not transfer:
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "TRANSFER_NOT_FOUND", "message": "Transfer not found."}},
            )
        was_debited = transfer["debited"]
        now_debited = was_debited
        if payload.outcome == "reversed":
            if was_debited:
                _treasury_balance_kobo += transfer["amount_kobo"]
            now_debited = False
        elif payload.outcome == "successful" and not was_debited:
            _treasury_balance_kobo -= transfer["amount_kobo"]
            now_debited = True
        elif payload.outcome in {"failed", "blocked"} and was_debited:
            _treasury_balance_kobo += transfer["amount_kobo"]
            now_debited = False
        transfer["debited"] = now_debited
        transfer["status"] = payload.outcome
        transfer["settled_status"] = payload.outcome
        return {"data": dict(transfer)}


@app.post("/v1/mock/reset")
def reset_mock_bank() -> dict:
    global _treasury_balance_kobo
    with _lock:
        _payments.clear()
        _payment_idempotency.clear()
        _transfers.clear()
        _transfer_idempotency.clear()
        _webhooks.clear()
        _treasury_balance_kobo = 10_000_000_000
    return {"data": {"status": "reset"}}

from uuid import uuid4

from fastapi.testclient import TestClient

from app.integrations.mock_bank import app


client = TestClient(app)
headers = {"x-api-key": "local-test-key"}


def _reset(monkeypatch) -> None:
    monkeypatch.setenv("GATEWAY_KEY", "local-test-key")
    response = client.post("/v1/mock/reset", headers=headers)
    assert response.status_code == 200


def test_checkout_idempotency_returns_one_payment(monkeypatch) -> None:
    _reset(monkeypatch)
    reference = str(uuid4())
    payload = {
        "reference": reference,
        "amount_kobo": 250_000,
        "callback_url": "https://example.test/return",
        "webhook_url": "https://example.test/hooks/forge",
    }

    first = client.post(
        "/v1/payments/checkout",
        headers={**headers, "Idempotency-Key": f"checkout:{reference}"},
        json=payload,
    )
    second = client.post(
        "/v1/payments/checkout",
        headers={**headers, "Idempotency-Key": f"checkout:{reference}"},
        json=payload,
    )

    assert first.status_code == second.status_code == 200
    assert first.json()["data"] == second.json()["data"]


def test_unknown_transfer_is_requeried_without_a_second_debit(monkeypatch) -> None:
    _reset(monkeypatch)
    account_number = "0123456789"
    initial_balance = client.get(
        f"/v1/accounts/{account_number}/balance",
        headers=headers,
    ).json()["data"]["available_balance_kobo"]
    reference = str(uuid4())
    transfer_request = {
        "reference": reference,
        "amount_kobo": 142_500_00,
        "bank_code": "001",
        "account_number": account_number,
        "account_name": "Demo Beneficiary 6789",
        "test_outcome": "unknown",
    }
    request_headers = {**headers, "Idempotency-Key": f"payout:{reference}"}

    first = client.post("/v1/transfers", headers=request_headers, json=transfer_request)
    after_submit = client.get(
        f"/v1/accounts/{account_number}/balance",
        headers=headers,
    ).json()["data"]["available_balance_kobo"]
    queried = client.get(f"/v1/transfers/{reference}", headers=headers)
    after_requery = client.get(
        f"/v1/accounts/{account_number}/balance",
        headers=headers,
    ).json()["data"]["available_balance_kobo"]
    retried = client.post("/v1/transfers", headers=request_headers, json=transfer_request)

    assert first.json()["data"]["status"] == "unknown"
    assert queried.json()["data"]["status"] == "successful"
    assert after_submit == initial_balance - transfer_request["amount_kobo"]
    assert after_requery == after_submit
    assert retried.json()["data"]["status"] == "successful"
    assert after_requery == initial_balance - transfer_request["amount_kobo"]

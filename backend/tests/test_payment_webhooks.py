import hashlib
import hmac
import json
import time
from dataclasses import replace

from fastapi.testclient import TestClient

from app.main import app
from app.modules import payments


client = TestClient(app)


def _signature(secret: str, timestamp: str, body: bytes) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        timestamp.encode("ascii") + b"." + body,
        hashlib.sha256,
    ).hexdigest()


def test_forge_webhook_rejects_bad_signature_before_queueing(monkeypatch) -> None:
    secret = "local-webhook-secret-that-is-long-enough"
    monkeypatch.setattr(
        payments,
        "settings",
        replace(payments.settings, forge_webhook_secret=secret),
    )
    timestamp = str(int(time.time()))
    body = json.dumps(
        {
            "event_id": "event-1",
            "event_type": "payment.succeeded",
            "data": {"reference": "order-reference"},
        },
        separators=(",", ":"),
    ).encode()

    response = client.post(
        "/hooks/forge",
        content=body,
        headers={
            "x-forge-timestamp": timestamp,
            "x-forge-signature": "0" * 64,
            "content-type": "application/json",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_WEBHOOK_SIGNATURE"


def test_forge_webhook_rejects_stale_timestamp_even_with_valid_signature(monkeypatch) -> None:
    secret = "local-webhook-secret-that-is-long-enough"
    monkeypatch.setattr(
        payments,
        "settings",
        replace(payments.settings, forge_webhook_secret=secret),
    )
    timestamp = str(int(time.time()) - 301)
    body = b'{"event_id":"event-2","event_type":"payment.succeeded","data":{"reference":"order"}}'

    response = client.post(
        "/hooks/forge",
        content=body,
        headers={
            "x-forge-timestamp": timestamp,
            "x-forge-signature": _signature(secret, timestamp, body),
            "content-type": "application/json",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "WEBHOOK_TIMESTAMP_EXPIRED"

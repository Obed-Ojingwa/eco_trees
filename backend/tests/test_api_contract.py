from fastapi.testclient import TestClient

from app.main import app
from app.integrations.mock_bank import app as mock_bank_app


client = TestClient(app)
mock_bank_client = TestClient(mock_bank_app)


def test_legacy_endpoint_remains_available() -> None:
    response = client.get("/api/data")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Hello from the FastAPI backend!",
        "status": "success",
    }


def test_mutating_api_requires_ecotrees_header() -> None:
    response = client.post("/api/auth/login", json={})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CLIENT_HEADER_REQUIRED"
    assert response.headers["X-Request-ID"]


def test_validation_errors_use_the_api_error_envelope() -> None:
    response = client.post(
        "/api/auth/login",
        headers={"X-EcoTrees": "1"},
        json={},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"]["fields"]


def test_carbon_phase_routes_are_registered() -> None:
    paths = app.openapi()["paths"]

    assert "/api/carbon/parameters" in paths
    assert "/api/admin/estimates/run" in paths
    assert "/api/admin/batches/{batch_id}/submit" in paths
    assert "/api/auditor/batches/{batch_id}/decision" in paths
    assert "/api/auditor/plots/{plot_id}/verification" in paths
    assert "/api/public/credits/{serial}" in paths
    assert "/api/marketplace/credits" in paths
    assert "/api/orders" in paths
    assert "/api/orders/{order_id}/checkout" in paths
    assert "/api/payments/{reference}/verify" in paths
    assert "/hooks/forge" in paths
    assert "/api/buyer/credits/retire" in paths
    assert "/api/farmer/payout-account" in paths
    assert "/api/farmer/home" in paths
    assert "/api/public/impact" in paths


def test_mock_bank_rejects_missing_api_key(monkeypatch) -> None:
    monkeypatch.setenv("GATEWAY_KEY", "local-test-key")

    response = mock_bank_client.get("/v1/banks")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_API_KEY"


def test_mock_bank_accepts_configured_api_key(monkeypatch) -> None:
    monkeypatch.setenv("GATEWAY_KEY", "local-test-key")

    response = mock_bank_client.get(
        "/v1/banks",
        headers={"x-api-key": "local-test-key"},
    )

    assert response.status_code == 200
    assert response.json()["data"]

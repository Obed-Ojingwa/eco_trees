from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


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

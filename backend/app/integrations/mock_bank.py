import hmac
import os

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse


app = FastAPI(title="EcoTrees Mock Bank", docs_url=None, redoc_url=None)


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

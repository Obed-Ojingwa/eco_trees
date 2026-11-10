from fastapi import FastAPI


app = FastAPI(title="EcoTrees Mock Bank", docs_url=None, redoc_url=None)


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

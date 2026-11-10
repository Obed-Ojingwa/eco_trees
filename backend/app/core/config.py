import os
from dataclasses import dataclass
from pathlib import Path


def _csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _default_cors_origins(environment: str) -> tuple[str, ...]:
    if environment.lower() in {"development", "local", "test"}:
        return ("http://localhost:5173", "http://127.0.0.1:5173")
    return ()


def _level_thresholds(value: str) -> tuple[tuple[int, str], ...]:
    try:
        thresholds = tuple(
            (int(threshold.strip()), label.strip())
            for entry in value.split(",")
            for threshold, label in [entry.split(":", 1)]
        )
    except (ValueError, TypeError) as exc:
        raise RuntimeError(
            "FARMER_LEVEL_THRESHOLDS must use 'points:label' comma-separated values."
        ) from exc
    if (
        not thresholds
        or thresholds[0][0] != 0
        or any(points < 0 or not label for points, label in thresholds)
        or any(left[0] >= right[0] for left, right in zip(thresholds, thresholds[1:]))
    ):
        raise RuntimeError(
            "FARMER_LEVEL_THRESHOLDS must start at zero and use non-empty labels with increasing points."
        )
    return thresholds


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = os.getenv("DB_URL", "")
    migration_database_url: str = os.getenv("DB_MIGRATION_URL", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "development-only-change-me")
    jwt_expiry_minutes: int = int(os.getenv("JWT_EXPIRY_MINUTES", "60"))
    jwt_cookie_name: str = os.getenv("JWT_COOKIE_NAME", "ecotrees_session")
    cors_origins: tuple[str, ...] = _csv(
        os.getenv(
            "CORS_ORIGINS",
            ",".join(_default_cors_origins(os.getenv("ENVIRONMENT", "development"))),
        )
    )
    ingest_token: str = os.getenv("INGEST_TOKEN", "")
    bank_api_base: str = os.getenv("BANK_API_BASE", "http://localhost:9000/v1")
    gateway_key: str = os.getenv("GATEWAY_KEY", "")
    bank_rpm_budget: int = int(os.getenv("BANK_RPM_BUDGET", "45"))
    bank_get_retries: int = int(os.getenv("BANK_GET_RETRIES", "3"))
    payment_backend: str = os.getenv("PAYMENT_BACKEND", "mock").lower()
    allow_mock_payments: bool = (
        os.getenv("ALLOW_MOCK_PAYMENTS", "false").strip().lower() == "true"
    )
    forge_webhook_secret: str = os.getenv("FORGE_WEBHOOK_SECRET", "")
    payout_encryption_key: str = os.getenv("PAYOUT_ENCRYPTION_KEY", "")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
    webhook_url: str = os.getenv(
        "WEBHOOK_URL",
        "http://127.0.0.1:8000/hooks/forge",
    )
    treasury_account: str = os.getenv("TREASURY_ACCOUNT", "")
    checkout_fee_bps: int = int(os.getenv("CHECKOUT_FEE_BPS", "0"))
    payout_fee_bps: int = int(os.getenv("PAYOUT_FEE_BPS", "0"))
    order_expiry_minutes: int = int(os.getenv("ORDER_EXPIRY_MINUTES", "30"))
    farmer_level_thresholds: tuple[tuple[int, str], ...] = _level_thresholds(
        os.getenv(
            "FARMER_LEVEL_THRESHOLDS",
            "0:Seedling,500:Sapling,1500:Canopy,5000:Forest Guardian",
        )
    )
    max_photo_bytes: int = int(os.getenv("MAX_PHOTO_BYTES", str(8 * 1024 * 1024)))
    photo_gps_tolerance_m: float = float(os.getenv("PHOTO_GPS_TOLERANCE_M", "50"))
    photo_accuracy_limit_m: float = float(os.getenv("PHOTO_ACCURACY_LIMIT_M", "50"))
    photo_points_weekly_cap: int = int(os.getenv("PHOTO_POINTS_WEEKLY_CAP", "500"))
    min_plot_area_ha: float = float(os.getenv("MIN_PLOT_AREA_HA", "0.01"))
    max_plot_area_ha: float = float(os.getenv("MAX_PLOT_AREA_HA", "1000"))
    density_min_per_ha: float = float(os.getenv("DENSITY_MIN_PER_HA", "50"))
    density_max_per_ha: float = float(os.getenv("DENSITY_MAX_PER_HA", "2500"))
    monitoring_min_observations: int = int(os.getenv("MONITORING_MIN_OBSERVATIONS", "4"))
    monitoring_rolling_n: int = int(os.getenv("MONITORING_ROLLING_N", "3"))
    monitoring_reference_window_days: int = int(
        os.getenv("MONITORING_REFERENCE_WINDOW_DAYS", "365")
    )
    monitoring_watch_drop: float = float(os.getenv("MONITORING_WATCH_DROP", "0.15"))
    monitoring_freeze_drop: float = float(os.getenv("MONITORING_FREEZE_DROP", "0.30"))
    monitoring_freeze_consecutive: int = int(
        os.getenv("MONITORING_FREEZE_CONSECUTIVE", "2")
    )
    monitoring_recover_consecutive: int = int(
        os.getenv("MONITORING_RECOVER_CONSECUTIVE", "3")
    )
    monitoring_min_valid_pixels: int = int(
        os.getenv("MONITORING_MIN_VALID_PIXELS", "1")
    )
    existing_forest_ndvi: float = float(os.getenv("EXISTING_FOREST_NDVI", "0.7"))
    carbon_min_valid_pixels: int = int(os.getenv("CARBON_MIN_VALID_PIXELS", "5"))
    carbon_batch_min_tonnes: str = os.getenv("CARBON_BATCH_MIN_TONNES", "1")
    carbon_param_version: str = os.getenv("CARBON_PARAM_VERSION", "illustrative-v1")
    carbon_signing_key: str = os.getenv("CARBON_SIGNING_KEY", "")
    carbon_signing_key_id: str = os.getenv("CARBON_SIGNING_KEY_ID", "local-placeholder")
    registry_backend: str = os.getenv("REGISTRY_BACKEND", "mock").lower()
    registry_xtradot_enabled: bool = (
        os.getenv("REGISTRY_XTRADOT_ENABLED", "false").strip().lower() == "true"
    )
    migration_dir: Path = Path(__file__).resolve().parents[1] / "db" / "migrations"

    @property
    def secure_cookies(self) -> bool:
        return self.environment.lower() not in {"development", "local", "test"}


settings = Settings()

if settings.environment.lower() in {"production", "prod", "staging", "stage"}:
    if not settings.database_url:
        raise RuntimeError("DB_URL is required outside local development.")
    if len(settings.jwt_secret.encode()) < 32 or settings.jwt_secret == "development-only-change-me":
        raise RuntimeError("JWT_SECRET must be at least 32 bytes outside local development.")
    if not settings.ingest_token:
        raise RuntimeError("INGEST_TOKEN is required outside local development.")
    if not settings.carbon_signing_key:
        raise RuntimeError("CARBON_SIGNING_KEY is required outside local development.")
    if len(settings.carbon_signing_key.encode()) < 32:
        raise RuntimeError("CARBON_SIGNING_KEY must be at least 32 bytes outside local development.")
    if settings.registry_backend not in {"mock", "xtradot"}:
        raise RuntimeError("REGISTRY_BACKEND must be 'mock' or 'xtradot'.")
    if not os.getenv("PAYMENT_BACKEND"):
        raise RuntimeError("PAYMENT_BACKEND must be explicitly configured outside local development.")
    if settings.payment_backend == "mock" and not settings.allow_mock_payments:
        raise RuntimeError("Mock payments require ALLOW_MOCK_PAYMENTS=true outside local development.")
    if settings.payment_backend not in {"mock", "xtradot"}:
        raise RuntimeError("PAYMENT_BACKEND must be 'mock' or 'xtradot'.")
    if not settings.forge_webhook_secret or len(settings.forge_webhook_secret.encode()) < 32:
        raise RuntimeError("FORGE_WEBHOOK_SECRET must be at least 32 bytes outside local development.")
    if len(settings.payout_encryption_key.encode()) < 32:
        raise RuntimeError("PAYOUT_ENCRYPTION_KEY must be at least 32 bytes outside local development.")
    if not settings.treasury_account:
        raise RuntimeError("TREASURY_ACCOUNT is required outside local development.")

if not 0 <= settings.checkout_fee_bps <= 10_000:
    raise RuntimeError("CHECKOUT_FEE_BPS must be between 0 and 10000.")
if not 0 <= settings.payout_fee_bps <= 10_000:
    raise RuntimeError("PAYOUT_FEE_BPS must be between 0 and 10000.")
if settings.order_expiry_minutes < 1:
    raise RuntimeError("ORDER_EXPIRY_MINUTES must be positive.")

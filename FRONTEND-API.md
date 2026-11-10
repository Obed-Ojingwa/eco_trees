# EcoTrees Backend API for Frontend

This contract describes the backend implemented for phases B0–B3. The API prefix is `/api`. In production, the browser should call the same-origin web proxy; local Vite development may call `http://127.0.0.1:8000`.

All mutating `/api/*` requests must include `X-EcoTrees: 1`. JSON requests use `Content-Type: application/json`. Send browser requests with credentials enabled so the session cookie is included. The backend sets an `HttpOnly`, `SameSite=Lax` session cookie; it does not return a JWT for JavaScript to store.

## Common responses

Errors use this envelope:

```json
{
  "error": {
    "code": "PLOT_OVERLAP",
    "message": "This plot overlaps an existing registered plot.",
    "details": null
  },
  "request_id": "..."
}
```

Validation errors return `422` and `details.fields`, an array containing `field`, `message`, and `type`. The `X-Request-ID` response header can be included when reporting a problem.

## Authentication and current user

### `POST /api/auth/register`

Creates a farmer account and signs the farmer in. Farmer phone numbers and PINs are accepted here; other roles are provisioned by an administrator and cannot self-register.

```json
{
  "display_name": "Demo Farmer",
  "phone": "+2348000000001",
  "pin": "2468"
}
```

Success: `201`

```json
{
  "user": {
    "id": "uuid",
    "role": "farmer",
    "display_name": "Demo Farmer",
    "phone": "+2348000000001",
    "email": null,
    "kyc_verified": false
  },
  "expires_in_seconds": 3600
}
```

Relevant errors: `PHONE_ALREADY_REGISTERED` (`409`), `VALIDATION_ERROR` (`422`).

### `POST /api/auth/login`

Accepts a phone + PIN for farmers or an email + password for provisioned roles.

```json
{
  "identifier": "+2348000000001",
  "secret": "2468"
}
```

Success: `200`, same response shape as registration. The response sets the session cookie.

Relevant errors: `INVALID_CREDENTIALS` (`401`), `ACCOUNT_LOCKED` (`423`). Five consecutive failed attempts lock an account for 15 minutes.

### `POST /api/auth/logout`

Clears the session cookie. Success: `204`.

### `GET /api/me` and `GET /api/auth/me`

Returns the signed-in user's `id`, `role`, `display_name`, `phone`, `email`, and `kyc_verified`.

### `PATCH /api/me`

Updates the signed-in user's display name:

```json
{"display_name": "Updated Demo Name"}
```

Returns the current-user response shape.

### `GET /healthz` and `GET /api/healthz`

Returns `{"status":"ok"}` when the API can query PostgreSQL. These are readiness checks, not database-free liveness checks.

## Species and plots

### `GET /api/species`

Returns the species values currently offered by the backend:

```json
{
  "items": [
    {
      "code": "GMELINA",
      "common_name": "Gmelina",
      "scientific_name": "Gmelina arborea"
    }
  ]
}
```

### `POST /api/plots/preflight`

Checks geometry, geodesic area, and overlap before submission. This is advisory only; the database repeats the validation atomically when the plot is created. Farmer and admin roles may call it.

```json
{
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[3.4, 6.5], [3.401, 6.5], [3.401, 6.501], [3.4, 6.5]]]
  }
}
```

Success:

```json
{
  "ok": true,
  "area_ha": 0.62,
  "overlap_area_m2": 0,
  "overlap_percent": 0,
  "warnings": []
}
```

`ok: false` means the backend found an overlap. No other farmer's identity is returned. Errors include `INVALID_GEOMETRY` or `AREA_OUT_OF_RANGE` (`422`).

### `POST /api/plots`

Creates a draft plot and planting records in one transaction. Only farmers can create plots.

```json
{
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[3.4, 6.5], [3.401, 6.5], [3.401, 6.501], [3.4, 6.5]]]
  },
  "plantings": [
    {
      "species_code": "GMELINA",
      "trees_planted": 250,
      "planted_on": "2025-01-15"
    }
  ]
}
```

Success: `201`. The response includes authoritative `area_ha`, `geometry`, `status: "draft"`, `monitoring_state`, planting records, any density `flags`, and `points_awarded` (normally 100 for the first map event). Density thresholds are configurable warning bands, not carbon eligibility decisions.

Important errors:

| Code | HTTP | Meaning |
|---|---:|---|
| `PLOT_OVERLAP` | 409 | The database found positive-area overlap. Touching edges are allowed. |
| `INVALID_GEOMETRY` | 422 | The polygon is invalid or cannot be parsed. |
| `AREA_OUT_OF_RANGE` | 422 | Area is outside configured bounds. |
| `PLANTING_ALREADY_EXISTS` | 409 | Duplicate species/date planting record. |

### `GET /api/plots` and `GET /api/plots/{plot_id}`

Returns plot geometry as GeoJSON, area, status, monitoring state, flags, planting records, and photo metadata. Farmers only see their own plots; auditors and admins can read all plots. Unauthorized plot IDs are returned as `PLOT_NOT_FOUND`.

### `POST /api/plots/{plot_id}/photos`

Uploads one JPEG, PNG, or WebP photo as `multipart/form-data`:

| Field | Type | Required |
|---|---|---|
| `file` | image file, max 8 MiB by default | yes |
| `latitude` | decimal degrees, -90 to 90 | yes |
| `longitude` | decimal degrees, -180 to 180 | yes |
| `accuracy_m` | non-negative metres | yes |

Success: `201` with `gps_match`, distance in metres, `flags`, points awarded (100 per photo, capped at 500 points per farmer per calendar week), and `content_url`. GPS mismatch and poor accuracy are flags, not upload failures.

Relevant errors: `PHOTO_TOO_LARGE` (`413`), `UNSUPPORTED_PHOTO_TYPE` (`415`), `PHOTO_REUSED` (`409`), `PLOT_NOT_FOUND` (`404`).

### `GET /api/plots/{plot_id}/photos`

Returns photo metadata. `GET /api/plots/{plot_id}/photos/{photo_id}` returns the image bytes and is authentication-gated; the browser should not cache the response.

### `POST /api/plots/{plot_id}/submit`

Moves a farmer-owned draft to `submitted`. Requires at least one planting and one photo. Success includes `plot_id`, `status`, and `submitted_at`.

## Farmer points and notifications

### `GET /api/farmer/points?limit=50`

Farmer-only. Returns `total_points` and the most recent point events (`reason`, `ref_id`, `points`, `created_at`). `limit` is 1–100.

### `GET /api/notifications?unseen_only=true&limit=50`

Farmer-only. Returns notification `items` with `kind`, `message`, points, `celebrate`, `seen_at`, and `created_at`.

### `POST /api/farmer/seen`

Farmer-only. Marks all unseen notifications as seen. To mark selected notifications, send:

```json
{"notification_ids": ["uuid", "uuid"]}
```

Success: `{"marked_seen": 2}`.

## Satellite ingestion and monitoring

The internal ingestion routes are for the offline NDVI tool or trusted ingestion service—not browser use. They require `X-Ingest-Token` and `X-EcoTrees: 1` for POST. A missing server-side token disables ingestion with `INGEST_DISABLED`.

### `GET /api/internal/plots`

Returns plot IDs, GeoJSON, and earliest `planted_on` for plots available to monitor. Requires `X-Ingest-Token`.

### `POST /api/internal/ndvi`

Inserts or updates one observation, idempotent on `(plot_id, scene_id)`. A repeat with identical data does not create another assessment.

```json
{
  "plot_id": "uuid",
  "scene_id": "sentinel-item-id",
  "observed_on": "2026-03-01",
  "ndvi_plot": 0.62,
  "ndvi_control": 0.41,
  "valid_px_plot": 18,
  "valid_px_control": 42,
  "source": "sentinel-2",
  "metadata": {"eo_cloud_cover": 8.4}
}
```

`source` is `sentinel-2`, `synthetic_demo`, or `manual`. The response includes the stored observation ID, whether it was inserted/updated, and the resulting assessment (or `null` for an unchanged duplicate).

The assessment compares plot NDVI minus control-ring NDVI, uses a rolling mean against a preceding reference window, and applies configurable watch/freeze/recovery thresholds. It never estimates carbon tonnes. Fewer than the configured minimum number of valid observations, or no usable reference period, yields `pending`. Baseline imagery in the 12 months before planting can add `POSSIBLE_EXISTING_FOREST`; it is not proof of prior forest.

### `GET /api/plots/{plot_id}/monitoring`

Farmer (own plot), auditor, and admin access. Returns current `monitoring_state`, flags, NDVI observations including `relative_ndvi`, and the latest 50 human-readable assessments.

## Local development and implementation boundary

1. From `backend/`, copy `.env.example` to `.env` and set distinct local `DB_ADMIN_PASSWORD` and `DB_APP_PASSWORD` values.
2. With Docker Compose installed, from `backend/` run `docker compose up -d db mock_bank`.
3. Create and activate a Python 3.12 virtual environment, then install dependencies with `pip install -r requirements.txt`.
4. Export the environment in the API shell with `set -a; . ./.env; set +a`, then run `python -m app.db.migrate`.
5. Start the API from `backend/` with `uvicorn main:app --reload`.
6. To run tests, install `requirements-dev.txt` and run `python -m pytest`.
7. To seed synthetic non-farmer roles, set `DEMO_USERS_JSON` to a JSON array and run `python -m app.db.seed_users`. Farmer accounts register through the API.
8. For Sentinel-2 ingestion, install `requirements-ndvi.txt` on an internet-connected machine, export the same API URL and ingest token, then run `python -m app.tools.ndvi_ingest --dry-run` before uploading observations.

The Kubernetes manifests are in `backend/k8s/`. Create secrets outside source control: `ecotrees-db-admin` (`DB_ADMIN_PASSWORD`, `DB_APP_PASSWORD`), `ecotrees-secrets` (`DB_URL`, `JWT_SECRET`, `INGEST_TOKEN`), and `ecotrees-migration` (`DB_MIGRATION_URL`). The pre-provisioned `huawei-gateway` secret supplies `GATEWAY_KEY`. Build the API image for `linux/amd64`, apply `db.yaml`, wait for the database, run `migrate-job.yaml`, then apply `api.yaml`. The API service is internal; the frontend's public service proxies requests to it.

`GET /api/farmer/home`, account setup, carbon estimates, batches, marketplace, payments, and payouts belong to later backend phases and are not implemented by this B0–B3 contract.

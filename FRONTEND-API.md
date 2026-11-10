# EcoTrees Backend API for Frontend

This contract describes the backend implemented for phases B0–B5. The API prefix is `/api`. In production, the browser should call the same-origin web proxy; local Vite development may call `http://127.0.0.1:8000`.

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

## Carbon estimates, batches, and credits (B4–B5)

Carbon tonnes are illustrative while the active parameter response reports
`is_placeholder: true`; this status must remain visible in the UI. NDVI only
corroborates survival/loss and does not produce tonnes. `PLACEHOLDER_PARAMS`
is informational and does not block approval; every other estimate flag
requires an explicit auditor override with a note before approval. A prototype
credit serial is not a Verra, Gold Standard, or national-registry serial.
Only the newest estimate per plot can be batched. If credits were issued after
an estimate was calculated, rerun estimates before forming another batch.

### Public carbon parameters

#### `GET /api/carbon/parameters`

Returns the active parameter version, placeholder status, satellite
multipliers, and per-species assumptions. Fields that represent Decimal
values are strings. Carbon tonnes and hectare values in estimate, batch, and
auditor responses are also fixed-point strings, preserving their stored
precision without JSON floating-point conversion.

### Auditor plot review

#### `POST /api/auditor/plots/{plot_id}/verification`

Auditor-only. Moves a `submitted` or `flagged` plot to `verified` or `rejected`.
This is the review path required before a verified plot can be estimated.

```json
{"decision": "verified", "note": "Planting and evidence reviewed."}
```

#### `PUT /api/auditor/plots/{plot_id}/survival-override`

Auditor-only. Records an audited survival estimate; the note is required.

```json
{"survival": "0.82", "note": "Field review found 82% survival."}
```

### Estimates and batch formation

#### `POST /api/admin/estimates/run`

Admin-only. Writes a replayable snapshot for eligible planted plots. `plot_ids`
is optional and `as_of` defaults to today.

```json
{"as_of": "2026-03-01", "plot_ids": ["plot-uuid"]}
```

Returns `count` and estimate `items`, including gross/net tonnes, incremental
`issuable_t`, flags, and each estimate ID. Estimates with unverified plots
calculate to zero.

#### `GET /api/admin/estimates?plot_id={uuid}&limit=100`

Admin-only, with optional plot filter. Returns persisted estimate snapshots.

#### `POST /api/admin/batches`

Admin-only; creates a forming batch from the newest unbatched estimate per
eligible plot when `estimate_ids` is omitted. To select estimates explicitly:

```json
{"estimate_ids": ["estimate-uuid"]}
```

Only verified plots in `ok` or `watch` monitoring state with positive
incremental tonnes can be included. An estimate can belong to only one batch,
and a batch can contain at most one estimate per plot.

#### `GET /api/admin/batches?limit=100`

Admin-only. Lists batches and their status, tonnes, units, registry source, and
timestamps.

#### `POST /api/admin/batches/{batch_id}/submit`

Admin-only. Submits a forming batch once its total reaches the configured
minimum and contains at least one full tonne. Units are floored to whole
credits. Per-plot attribution is apportioned to four decimals and sums exactly
to the issued unit count without exceeding any plot claim.

### Auditor batch review

#### `GET /api/auditor/batches?limit=100`

Auditor-only queue of submitted batches, including plot and blocking-flag
counts.

#### `GET /api/auditor/batches/{batch_id}`

Auditor-only detail with plot geometry, estimate inputs, tonnes, flags, and any
recorded review.

#### `POST /api/auditor/batches/{batch_id}/decision`

Auditor-only. The note is required. Approval requires an override entry for
each plot with blocking flags; each entry must cover exactly that plot's
blocking flags and include a note. Placeholder parameters never require an
override.

```json
{
  "decision": "approved",
  "note": "Reviewed source evidence and estimates.",
  "overrides": [
    {
      "plot_id": "plot-uuid",
      "flags": ["FEW_VALID_PIXELS"],
      "note": "Field photos corroborate the planting."
    }
  ]
}
```

An approval stores the canonical package, SHA-256 hash, signing-key ID, and
HMAC-SHA256 signature, then issues credits through the configured registry
adapter. Repeating the same decision is idempotent. A rejected or approved
review is final.

### Credit listing and lookup

#### `POST /api/admin/batches/{batch_id}/listing`

Admin-only. Lists every issued credit in an issued batch at the given
`price_per_tonne_kobo`:

```json
{"price_per_tonne_kobo": 250000}
```

#### `GET /api/public/credits?limit=100&offset=0`

Lists publicly available listed, sold, and retired serials.

#### `GET /api/public/credits/{serial}`

Returns the serial, batch/vintage, registry source and reference, current
status, listing price (if any), and retirement details (if any).

Common workflow errors include `PLOT_NOT_REVIEWABLE`, `PLOT_NOT_VERIFIED`,
`ESTIMATES_NOT_BATCHABLE`, `BATCH_BELOW_MINIMUM`,
`BLOCKING_FLAGS_REQUIRE_OVERRIDE`, and `BATCH_NOT_ISSUED`. All endpoints use
the common error envelope above. Mutating requests still require
`X-EcoTrees: 1` and browser credentials.

The internal mock registry produces prototype `EC-NG-...` serials. The
Xtradot adapter remains disabled until its sandbox request/response schemas
are verified; setting the backend to Xtradot does not enable an unverified
integration.

## Marketplace, orders, checkout, and retirement (B6)

#### `GET /api/marketplace/credits`

Lists available `listed` credits with serial, registry source, batch/vintage,
and `price_per_tonne_kobo`.

#### `POST /api/orders`

Buyer-only. Select one or more listed serials. Send a unique
`Idempotency-Key` header (8–128 characters); reusing the key with a different
selection returns `409 IDEMPOTENCY_KEY_REUSED`. The server reserves all
selected credits atomically or reserves none.

```json
{"credit_serials": ["EC-NG-2026-000001-000001"]}
```

The order response includes the itemized credits and fixed kobo amounts:
`subtotal_kobo`, `buyer_fee_kobo`, and `total_kobo`. The optional buyer fee is
configured by `CHECKOUT_FEE_BPS`. Reservations expire after
`ORDER_EXPIRY_MINUTES` unless verified payment has completed.

#### `POST /api/orders/{order_id}/checkout`

Buyer-only. Starts a hosted checkout once and returns `payment_url` and
`payment_reference`. The server never retries a checkout POST after an
ambiguous response; use the verify endpoint to reconcile it.

#### `GET /api/payments/{reference}/verify`

Buyer-only. Queries the bank and confirms payment only when the returned
reference, `paid` status, and exact kobo amount match the order. Repeated
verification is idempotent. Partial, overpaid, late, or mismatched collections
are recorded in the suspense ledger and do not transfer credit ownership.

#### `GET /api/orders` and `GET /api/orders/{order_id}`

Buyer-only order history/detail. A buyer can only see their own orders.

#### `POST /hooks/forge`

Server-to-server webhook receiver. Verifies
`x-forge-signature = HMAC-SHA256(secret, timestamp + "." + raw_body)` and
`x-forge-timestamp` within five minutes before de-duplicating by `event_id`
and queueing supported payment/transfer events. Workers re-query the bank;
webhook contents alone never grant payment or payout value.

#### Buyer-owned credits and retirement

- `GET /api/buyer/credits` lists credits that belong to the authenticated buyer.
- `POST /api/buyer/credits/retire` retires owned, unretired credits from one
  batch/registry. Requires `Idempotency-Key` and
  `{"serials": ["..."], "beneficiary": "..."}`.
- `GET /api/buyer/retirements/{reference}/certificate` returns the certificate
  for the authenticated buyer's retirement, including serials, registry
  source, batch and auditor package hash.

## Escrow, ledger, payouts, and dashboard (B7–B8)

The ledger stores integer kobo debit/credit entries and rejects unbalanced
transactions both in the service and with a deferred database constraint.
Payment creates a held escrow liability; a worker releases it to per-farmer
payables and records the applicable platform fee. Payout shares use attributed
batch tonnes and largest-remainder allocation to whole naira, preserving the
exact distributable total.

- `PUT /api/farmer/payout-account` submits bank code/account number for name
  enquiry. The response exposes only a masked number and the resolved name.
  The account number is encrypted at rest using PostgreSQL `pgcrypto`.
- `GET /api/farmer/payout-account` returns the saved masked account/name and
  confirmation state.
- `POST /api/farmer/payout-account/confirm` confirms the recently resolved
  name exactly before payouts are eligible.
- `GET /api/admin/payouts` lists payout state and masked account details.
- `POST /api/admin/payouts/release` releases paid orders held in escrow.
- `POST /api/admin/payouts/{payout_id}/submit` is an admin/manual test path;
  `X-Test-Outcome` only has effect with the mock bank.
- `POST /api/admin/payouts/{payout_id}/requery` queries an existing transfer.
  `unknown` and `processing` transfers are only requeried, never POSTed again.
- `POST /api/admin/drills/payments/{order_id}` exercises mock outcomes
  (`paid`, `partial`, `overpaid`, `failed`, `pending`, `timeout`).
- `POST /api/admin/bank-reset` resets the mock bank only when no active order,
  held escrow, or in-flight payout remains, then re-registers the webhook.
- `GET /api/farmer/home` returns points/level, new notifications since
  `POST /api/farmer/seen`, plot/greenness summary, estimate-only potential
  value, successful payouts, and suggested next actions. Level thresholds are
  configured with `FARMER_LEVEL_THRESHOLDS` (`points:label` pairs).
- `GET /api/public/impact` returns aggregate, non-identifying impact counters.
- `GET /api/admin/batches/{batch_id}/impact-pack` exports geometries,
  attribution, monitoring history, auditor package hash, and payout totals.

The asynchronous worker is `python -m app.workers.run`; it processes webhook
events, expires orders only after verification, releases escrow, submits
eligible payouts once, polls unknown/processing payouts, and ensures the
webhook registration.

## Bank integration boundary

The checked-in mock bank provides deterministic local checkout, verification,
name-enquiry, treasury-balance, transfer, and reset routes for backend tests.
Its state is in-memory and is for development/demo use only. The live
Xtradot payment, transfer, identity/BVN, and webhook schemas are not present
in the repository. Therefore `PAYMENT_BACKEND=xtradot` fails finance calls
with `BANK_SCHEMA_UNCONFIRMED`; the code deliberately does not guess live
request/response formats or send money. BVN verification remains blocked until
the identity schema is confirmed. Production must explicitly configure
`PAYMENT_BACKEND`, `FORGE_WEBHOOK_SECRET`, `PAYOUT_ENCRYPTION_KEY`, and
`TREASURY_ACCOUNT`; use a mock backend in production only for an explicitly
approved demo with `ALLOW_MOCK_PAYMENTS=true`.

1. From `backend/`, copy `.env.example` to `.env` and set distinct local `DB_ADMIN_PASSWORD` and `DB_APP_PASSWORD` values.
2. With Docker Compose installed, from `backend/` run `docker compose up -d db mock_bank`.
3. Create and activate a Python 3.12 virtual environment, then install dependencies with `pip install -r requirements.txt`.
4. Export the environment in the API shell with `set -a; . ./.env; set +a`, then run `python -m app.db.migrate`.
5. Start the API from `backend/` with `uvicorn main:app --reload`.
6. To run tests, install `requirements-dev.txt` and run `python -m pytest`.
7. To seed synthetic non-farmer roles, set `DEMO_USERS_JSON` to a JSON array and run `python -m app.db.seed_users`. Farmer accounts register through the API.
8. For Sentinel-2 ingestion, install `requirements-ndvi.txt` on an internet-connected machine, export the same API URL and ingest token, then run `python -m app.tools.ndvi_ingest --dry-run` before uploading observations.

The Kubernetes manifests are in `backend/k8s/`. Create secrets outside source control: `ecotrees-db-admin` (`DB_ADMIN_PASSWORD`, `DB_APP_PASSWORD`), `ecotrees-secrets` (`DB_URL`, `JWT_SECRET`, `INGEST_TOKEN`, `CARBON_SIGNING_KEY`, `FORGE_WEBHOOK_SECRET`, `PAYOUT_ENCRYPTION_KEY`, `TREASURY_ACCOUNT`), and `ecotrees-migration` (`DB_MIGRATION_URL`). Use separate random signing/encryption keys of at least 32 bytes; `CARBON_SIGNING_KEY_ID` is configured in the manifests. The pre-provisioned `huawei-gateway` secret supplies `GATEWAY_KEY`. Build the API image for `linux/amd64`, apply `db.yaml`, wait for the database, run `migrate-job.yaml`, then apply `api.yaml` and `worker.yaml`. The API service is internal; the frontend's public service proxies requests to it.

For local development, set `PAYMENT_BACKEND=mock`, `ALLOW_MOCK_PAYMENTS=true`,
`GATEWAY_KEY`, and the local webhook/encryption keys in `.env`. Run the mock
bank and API with the same `GATEWAY_KEY`. The mock bank is not a payment
processor or a source of production settlement evidence.

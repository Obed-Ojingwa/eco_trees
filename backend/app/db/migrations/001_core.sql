CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE users (
    id uuid PRIMARY KEY,
    role text NOT NULL CHECK (role IN ('farmer', 'auditor', 'buyer', 'bank_viewer', 'admin')),
    display_name text NOT NULL CHECK (length(trim(display_name)) BETWEEN 1 AND 120),
    phone text UNIQUE,
    email text UNIQUE,
    password_hash text NOT NULL,
    failed_logins integer NOT NULL DEFAULT 0 CHECK (failed_logins >= 0),
    locked_until timestamptz,
    kyc_verified boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    disabled_at timestamptz,
    CHECK ((role = 'farmer' AND phone IS NOT NULL AND email IS NULL)
        OR (role <> 'farmer' AND email IS NOT NULL AND phone IS NULL))
);

CREATE TABLE plots (
    id uuid PRIMARY KEY,
    farmer_id uuid NOT NULL REFERENCES users(id),
    geom geometry(Geometry, 4326) NOT NULL,
    area_ha numeric(14, 6) NOT NULL DEFAULT 0 CHECK (area_ha >= 0),
    status text NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'submitted', 'monitoring', 'eligible', 'in_batch', 'verified', 'flagged', 'frozen', 'rejected')),
    monitoring_state text NOT NULL DEFAULT 'pending'
        CHECK (monitoring_state IN ('pending', 'ok', 'watch', 'frozen')),
    flags text[] NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE plantings (
    id uuid PRIMARY KEY,
    plot_id uuid NOT NULL REFERENCES plots(id) ON DELETE CASCADE,
    species_code text NOT NULL,
    trees_planted integer NOT NULL CHECK (trees_planted > 0),
    planted_on date NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (plot_id, species_code, planted_on)
);

CREATE TABLE plot_photos (
    id uuid PRIMARY KEY,
    plot_id uuid NOT NULL REFERENCES plots(id) ON DELETE CASCADE,
    farmer_id uuid NOT NULL REFERENCES users(id),
    content_type text NOT NULL CHECK (content_type IN ('image/jpeg', 'image/png', 'image/webp')),
    content bytea NOT NULL,
    sha256 text NOT NULL UNIQUE,
    captured_at timestamptz NOT NULL DEFAULT now(),
    gps geometry(Point, 4326) NOT NULL,
    accuracy_m numeric(10, 2) NOT NULL CHECK (accuracy_m >= 0),
    distance_m numeric(12, 2) NOT NULL CHECK (distance_m >= 0),
    gps_match boolean NOT NULL,
    flags text[] NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE xp_events (
    id uuid PRIMARY KEY,
    farmer_id uuid NOT NULL REFERENCES users(id),
    reason text NOT NULL,
    ref_id uuid NOT NULL,
    points integer NOT NULL CHECK (points > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (farmer_id, reason, ref_id)
);

CREATE TABLE notifications (
    id uuid PRIMARY KEY,
    farmer_id uuid NOT NULL REFERENCES users(id),
    kind text NOT NULL,
    ref_id uuid NOT NULL,
    message text NOT NULL,
    points integer NOT NULL DEFAULT 0 CHECK (points >= 0),
    celebrate boolean NOT NULL DEFAULT false,
    seen_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (farmer_id, kind, ref_id)
);

CREATE TABLE ndvi_observations (
    id uuid PRIMARY KEY,
    plot_id uuid NOT NULL REFERENCES plots(id) ON DELETE CASCADE,
    scene_id text NOT NULL,
    observed_on date NOT NULL,
    ndvi_plot double precision NOT NULL CHECK (ndvi_plot BETWEEN -1 AND 1),
    ndvi_control double precision NOT NULL CHECK (ndvi_control BETWEEN -1 AND 1),
    valid_px_plot integer NOT NULL CHECK (valid_px_plot >= 0),
    valid_px_control integer NOT NULL CHECK (valid_px_control >= 0),
    source text NOT NULL DEFAULT 'sentinel-2'
        CHECK (source IN ('sentinel-2', 'synthetic_demo', 'manual')),
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (plot_id, scene_id)
);

CREATE TABLE monitoring_assessments (
    id uuid PRIMARY KEY,
    plot_id uuid NOT NULL REFERENCES plots(id) ON DELETE CASCADE,
    state text NOT NULL CHECK (state IN ('pending', 'ok', 'watch', 'frozen')),
    previous_state text NOT NULL CHECK (previous_state IN ('pending', 'ok', 'watch', 'frozen')),
    reason text NOT NULL,
    reference_delta double precision,
    latest_delta double precision,
    drop_value double precision,
    observation_count integer NOT NULL CHECK (observation_count >= 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE bank_api_log (
    id uuid PRIMARY KEY,
    request_id text NOT NULL,
    method text NOT NULL,
    path text NOT NULL,
    status_code integer,
    duration_ms integer NOT NULL CHECK (duration_ms >= 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE bank_rate_limiter (
    id smallint PRIMARY KEY CHECK (id = 1),
    tokens double precision NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO bank_rate_limiter (id, tokens) VALUES (1, 45)
ON CONFLICT (id) DO NOTHING;

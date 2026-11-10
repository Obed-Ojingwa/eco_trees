CREATE SEQUENCE carbon_batch_number_seq;

CREATE TABLE carbon_param_sets (
    id uuid PRIMARY KEY,
    version text NOT NULL UNIQUE,
    is_placeholder boolean NOT NULL DEFAULT true,
    buffer_pct numeric(8, 6) NOT NULL CHECK (buffer_pct BETWEEN 0 AND 1),
    satellite_multipliers jsonb NOT NULL,
    source_citation text,
    notes text NOT NULL DEFAULT '',
    active boolean NOT NULL DEFAULT false,
    created_by uuid REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (is_placeholder OR length(trim(COALESCE(source_citation, notes))) > 0)
);

CREATE UNIQUE INDEX carbon_param_sets_one_active
    ON carbon_param_sets (active)
    WHERE active;

CREATE TABLE species_params (
    id uuid PRIMARY KEY,
    param_set_id uuid NOT NULL REFERENCES carbon_param_sets(id),
    species_code text NOT NULL,
    growth_curve jsonb NOT NULL,
    root_shoot_ratio numeric(12, 8) NOT NULL CHECK (root_shoot_ratio >= 0),
    carbon_fraction numeric(12, 8) NOT NULL CHECK (carbon_fraction BETWEEN 0 AND 1),
    target_density_per_ha numeric(12, 4) NOT NULL CHECK (target_density_per_ha > 0),
    min_density_per_ha numeric(12, 4) NOT NULL CHECK (min_density_per_ha >= 0),
    max_density_per_ha numeric(12, 4) NOT NULL CHECK (max_density_per_ha >= min_density_per_ha),
    default_survival numeric(12, 8) NOT NULL CHECK (default_survival BETWEEN 0 AND 1),
    source_citation text,
    notes text NOT NULL DEFAULT '',
    UNIQUE (param_set_id, species_code),
    CHECK (length(trim(COALESCE(source_citation, notes))) > 0)
);

CREATE TABLE plot_survival_overrides (
    plot_id uuid PRIMARY KEY REFERENCES plots(id),
    auditor_id uuid NOT NULL REFERENCES users(id),
    survival numeric(12, 8) NOT NULL CHECK (survival BETWEEN 0 AND 1),
    note text NOT NULL CHECK (length(trim(note)) > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE carbon_batches (
    id uuid PRIMARY KEY,
    batch_number bigint NOT NULL UNIQUE DEFAULT nextval('carbon_batch_number_seq'),
    vintage integer NOT NULL,
    status text NOT NULL DEFAULT 'forming'
        CHECK (status IN ('forming', 'submitted', 'approved', 'rejected', 'issued', 'listed', 'sold_out')),
    registry_source text NOT NULL DEFAULT 'mock'
        CHECK (registry_source IN ('mock', 'xtradot')),
    total_claimed_tonnes numeric(18, 4) NOT NULL DEFAULT 0 CHECK (total_claimed_tonnes >= 0),
    units integer NOT NULL DEFAULT 0 CHECK (units >= 0),
    price_per_tonne_kobo bigint CHECK (price_per_tonne_kobo > 0),
    registry_project_ref text,
    registry_mrv_ref text,
    package_sha256 text,
    created_by uuid NOT NULL REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    submitted_at timestamptz,
    decided_at timestamptz,
    issued_at timestamptz,
    listed_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE carbon_estimates (
    id uuid PRIMARY KEY,
    plot_id uuid NOT NULL REFERENCES plots(id),
    param_set_id uuid NOT NULL REFERENCES carbon_param_sets(id),
    as_of date NOT NULL,
    inputs jsonb NOT NULL,
    area_ha numeric(18, 6) NOT NULL CHECK (area_ha > 0),
    co2e_gross_t numeric(18, 4) NOT NULL CHECK (co2e_gross_t >= 0),
    buffer_t numeric(18, 4) NOT NULL CHECK (buffer_t >= 0),
    co2e_net_cum_t numeric(18, 4) NOT NULL CHECK (co2e_net_cum_t >= 0),
    already_issued_t numeric(18, 4) NOT NULL DEFAULT 0 CHECK (already_issued_t >= 0),
    issuable_t numeric(18, 4) NOT NULL CHECK (issuable_t >= 0),
    flags text[] NOT NULL DEFAULT '{}',
    batch_id uuid REFERENCES carbon_batches(id),
    created_by uuid NOT NULL REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE batch_estimates (
    batch_id uuid NOT NULL REFERENCES carbon_batches(id),
    estimate_id uuid NOT NULL UNIQUE REFERENCES carbon_estimates(id),
    plot_id uuid NOT NULL REFERENCES plots(id),
    tonnes_claimed numeric(18, 4) NOT NULL CHECK (tonnes_claimed > 0),
    tonnes_attributed numeric(18, 4) NOT NULL DEFAULT 0 CHECK (tonnes_attributed >= 0),
    PRIMARY KEY (batch_id, estimate_id)
);

CREATE TABLE audit_reviews (
    id uuid PRIMARY KEY,
    batch_id uuid NOT NULL REFERENCES carbon_batches(id),
    auditor_id uuid NOT NULL REFERENCES users(id),
    decision text NOT NULL CHECK (decision IN ('approved', 'rejected')),
    note text NOT NULL,
    overrides jsonb NOT NULL DEFAULT '[]',
    package jsonb NOT NULL,
    package_sha256 text NOT NULL CHECK (length(package_sha256) = 64),
    signature text NOT NULL CHECK (length(signature) = 64),
    signing_key_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (batch_id)
);

CREATE TABLE audit_log (
    id uuid PRIMARY KEY,
    actor_id uuid NOT NULL REFERENCES users(id),
    action text NOT NULL,
    entity_type text NOT NULL,
    entity_id uuid NOT NULL,
    details jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE credits (
    id uuid PRIMARY KEY,
    batch_id uuid NOT NULL REFERENCES carbon_batches(id),
    unit_index integer NOT NULL CHECK (unit_index > 0),
    serial text NOT NULL UNIQUE,
    registry_source text NOT NULL CHECK (registry_source IN ('mock', 'xtradot')),
    registry_credit_ref text,
    status text NOT NULL DEFAULT 'issued'
        CHECK (status IN ('issued', 'listed', 'reserved', 'sold', 'retired')),
    retirement_ref text,
    retired_for text,
    retired_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (batch_id, unit_index),
    CHECK (
        (status = 'retired' AND retirement_ref IS NOT NULL AND retired_at IS NOT NULL)
        OR status <> 'retired'
    )
);

CREATE TABLE registry_operations (
    id uuid PRIMARY KEY,
    batch_id uuid NOT NULL REFERENCES carbon_batches(id),
    operation text NOT NULL CHECK (operation IN ('issue', 'retire')),
    idempotency_key text NOT NULL UNIQUE,
    request jsonb NOT NULL,
    response jsonb,
    status text NOT NULL CHECK (status IN ('pending', 'succeeded', 'failed')),
    error_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz
);

CREATE INDEX carbon_estimates_plot_created_idx
    ON carbon_estimates (plot_id, created_at DESC);
CREATE INDEX carbon_estimates_unbatched_idx
    ON carbon_estimates (created_at DESC)
    WHERE batch_id IS NULL;
CREATE INDEX carbon_batches_status_created_idx
    ON carbon_batches (status, created_at DESC);
CREATE INDEX batch_estimates_plot_idx
    ON batch_estimates (plot_id);
CREATE INDEX credits_batch_status_idx
    ON credits (batch_id, status);
CREATE INDEX audit_log_entity_idx
    ON audit_log (entity_type, entity_id, created_at DESC);

INSERT INTO carbon_param_sets (
    id, version, is_placeholder, buffer_pct, satellite_multipliers,
    source_citation, notes, active
) VALUES (
    '00000000-0000-4000-8000-000000000001',
    'illustrative-v1',
    true,
    0.20,
    '{"pending":0,"ok":1,"watch":0.8,"frozen":0}'::jsonb,
    NULL,
    'Illustrative demonstration parameters only. Replace every species value with sourced data before non-demo use.',
    true
);

INSERT INTO species_params (
    id, param_set_id, species_code, growth_curve, root_shoot_ratio,
    carbon_fraction, target_density_per_ha, min_density_per_ha,
    max_density_per_ha, default_survival, source_citation, notes
) VALUES
(
    '00000000-0000-4000-8000-000000000101',
    '00000000-0000-4000-8000-000000000001',
    'GMELINA', '[[0,0],[1,10]]'::jsonb, 0.25, 0.47, 500, 50, 2500, 0.90,
    NULL, 'Illustrative placeholder values; not suitable for real credit issuance.'
),
(
    '00000000-0000-4000-8000-000000000102',
    '00000000-0000-4000-8000-000000000001',
    'CASHEW', '[[0,0],[1,10]]'::jsonb, 0.25, 0.47, 500, 50, 2500, 0.90,
    NULL, 'Illustrative placeholder values; not suitable for real credit issuance.'
),
(
    '00000000-0000-4000-8000-000000000103',
    '00000000-0000-4000-8000-000000000001',
    'NEEM', '[[0,0],[1,10]]'::jsonb, 0.25, 0.47, 500, 50, 2500, 0.90,
    NULL, 'Illustrative placeholder values; not suitable for real credit issuance.'
),
(
    '00000000-0000-4000-8000-000000000104',
    '00000000-0000-4000-8000-000000000001',
    'MANGROVE', '[[0,0],[1,10]]'::jsonb, 0.25, 0.47, 500, 50, 2500, 0.90,
    NULL, 'Illustrative placeholder values; not suitable for real credit issuance.'
);

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ecotrees;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ecotrees;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ecotrees;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO ecotrees;
REVOKE UPDATE, DELETE ON audit_log FROM ecotrees;

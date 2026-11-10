CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE orders (
    id uuid PRIMARY KEY,
    buyer_id uuid NOT NULL REFERENCES users(id),
    idempotency_key text NOT NULL,
    status text NOT NULL DEFAULT 'created'
        CHECK (status IN ('created', 'checkout_pending', 'paid', 'failed', 'expired', 'cancelled')),
    escrow_state text NOT NULL DEFAULT 'none'
        CHECK (escrow_state IN ('none', 'held', 'released')),
    payment_status text NOT NULL DEFAULT 'not_started'
        CHECK (payment_status IN ('not_started', 'pending', 'paid', 'failed', 'amount_mismatch', 'unknown')),
    subtotal_kobo bigint NOT NULL CHECK (subtotal_kobo > 0),
    buyer_fee_kobo bigint NOT NULL CHECK (buyer_fee_kobo >= 0),
    total_kobo bigint NOT NULL CHECK (total_kobo = subtotal_kobo + buyer_fee_kobo),
    payment_reference text UNIQUE,
    provider_reference text,
    payment_url text,
    payment_request_started_at timestamptz,
    expires_at timestamptz NOT NULL,
    paid_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (buyer_id, idempotency_key)
);

ALTER TABLE credits
    ADD COLUMN reserved_order_id uuid REFERENCES orders(id);

CREATE TABLE order_items (
    order_id uuid NOT NULL REFERENCES orders(id),
    credit_id uuid NOT NULL UNIQUE REFERENCES credits(id),
    price_per_tonne_kobo bigint NOT NULL CHECK (price_per_tonne_kobo > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (order_id, credit_id)
);

CREATE TABLE credit_ownership (
    credit_id uuid PRIMARY KEY REFERENCES credits(id),
    owner_id uuid NOT NULL REFERENCES users(id),
    order_id uuid NOT NULL REFERENCES orders(id),
    acquired_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE credit_retirements (
    id uuid PRIMARY KEY,
    batch_id uuid NOT NULL REFERENCES carbon_batches(id),
    buyer_id uuid NOT NULL REFERENCES users(id),
    idempotency_key text NOT NULL,
    retirement_reference text NOT NULL UNIQUE,
    beneficiary text NOT NULL,
    serials jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (buyer_id, idempotency_key)
);

CREATE TABLE ledger_transactions (
    id uuid PRIMARY KEY,
    idempotency_key text NOT NULL UNIQUE,
    source_type text NOT NULL,
    source_id uuid NOT NULL,
    description text NOT NULL,
    request_sha256 text NOT NULL CHECK (length(request_sha256) = 64),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ledger_entries (
    id uuid PRIMARY KEY,
    transaction_id uuid NOT NULL REFERENCES ledger_transactions(id),
    account_code text NOT NULL,
    owner_id uuid REFERENCES users(id),
    side text NOT NULL CHECK (side IN ('debit', 'credit')),
    amount_kobo bigint NOT NULL CHECK (amount_kobo > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION check_ledger_transaction_balanced() RETURNS trigger AS $$
DECLARE
    transaction_uuid uuid;
    debit_total bigint;
    credit_total bigint;
    entry_count integer;
BEGIN
    transaction_uuid := COALESCE(NEW.transaction_id, OLD.transaction_id);
    SELECT count(*),
           COALESCE(sum(amount_kobo) FILTER (WHERE side = 'debit'), 0),
           COALESCE(sum(amount_kobo) FILTER (WHERE side = 'credit'), 0)
      INTO entry_count, debit_total, credit_total
      FROM ledger_entries
     WHERE transaction_id = transaction_uuid;
    IF entry_count = 0 OR debit_total <> credit_total THEN
        RAISE EXCEPTION 'Unbalanced ledger transaction %: debits %, credits %',
            transaction_uuid, debit_total, credit_total
            USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER ledger_entries_must_balance
AFTER INSERT OR UPDATE OR DELETE ON ledger_entries
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION check_ledger_transaction_balanced();

CREATE TABLE payment_webhook_events (
    event_id text PRIMARY KEY,
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'processed', 'failed')),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error text,
    received_at timestamptz NOT NULL DEFAULT now(),
    processed_at timestamptz
);

CREATE TABLE farmer_payout_accounts (
    farmer_id uuid PRIMARY KEY REFERENCES users(id),
    bank_code text NOT NULL,
    account_number_ciphertext bytea NOT NULL,
    account_number_last4 text NOT NULL CHECK (length(account_number_last4) = 4),
    account_name text NOT NULL,
    name_enquiry_reference text,
    verified_at timestamptz NOT NULL,
    confirmed_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE payouts (
    id uuid PRIMARY KEY,
    order_id uuid NOT NULL REFERENCES orders(id),
    farmer_id uuid NOT NULL REFERENCES users(id),
    reference text NOT NULL UNIQUE,
    idempotency_key text NOT NULL UNIQUE,
    amount_kobo bigint NOT NULL CHECK (amount_kobo > 0 AND amount_kobo % 100 = 0),
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'submitted', 'processing', 'unknown', 'successful', 'failed', 'blocked', 'reversed')),
    account_last4 text,
    bank_reference text,
    failure_code text,
    submitted_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (order_id, farmer_id)
);

CREATE TABLE payout_allocations (
    payout_id uuid NOT NULL REFERENCES payouts(id),
    batch_id uuid NOT NULL REFERENCES carbon_batches(id),
    amount_kobo bigint NOT NULL CHECK (amount_kobo > 0),
    PRIMARY KEY (payout_id, batch_id)
);

CREATE TABLE farmer_dashboard_visits (
    farmer_id uuid PRIMARY KEY REFERENCES users(id),
    last_seen_at timestamptz NOT NULL
);

CREATE INDEX orders_buyer_created_idx ON orders (buyer_id, created_at DESC);
CREATE INDEX orders_expiry_idx ON orders (expires_at) WHERE status IN ('created', 'checkout_pending');
CREATE INDEX orders_release_idx ON orders (created_at) WHERE status = 'paid' AND escrow_state = 'held';
CREATE INDEX credit_ownership_buyer_idx ON credit_ownership (owner_id, acquired_at DESC);
CREATE INDEX ledger_entries_account_created_idx ON ledger_entries (account_code, owner_id, created_at DESC);
CREATE INDEX payment_webhook_pending_idx ON payment_webhook_events (received_at) WHERE status = 'pending';
CREATE INDEX payouts_status_created_idx ON payouts (status, created_at);
CREATE INDEX payout_allocations_batch_idx ON payout_allocations (batch_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ecotrees;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ecotrees;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ecotrees;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO ecotrees;
REVOKE UPDATE, DELETE ON audit_log FROM ecotrees;

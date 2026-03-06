-- Hackathon v1: CPS settlement fields for Arbitrum escrow integration.
-- Adapt table names if your CPS schema differs.

ALTER TABLE execution_units
    ADD COLUMN settlement_chain TEXT NOT NULL DEFAULT 'ARBITRUM_SEPOLIA',
    ADD COLUMN escrow_job_id BIGINT,
    ADD COLUMN escrow_contract_address TEXT,
    ADD COLUMN escrow_status TEXT NOT NULL DEFAULT 'NONE',
    ADD COLUMN result_hash TEXT,
    ADD COLUMN attestation_digest TEXT,
    ADD COLUMN attestor_address TEXT,
    ADD COLUMN submit_result_tx_hash TEXT,
    ADD COLUMN release_payment_tx_hash TEXT,
    ADD COLUMN chain_last_error TEXT,
    ADD COLUMN escrow_value_wei NUMERIC(78, 0),
    ADD COLUMN challenge_window_sec INTEGER,
    ADD COLUMN submitted_onchain_at TIMESTAMPTZ,
    ADD COLUMN released_onchain_at TIMESTAMPTZ;

ALTER TABLE execution_units
    ADD CONSTRAINT execution_units_escrow_status_check
        CHECK (
            escrow_status IN (
                'NONE',
                'CREATED',
                'RESULT_SUBMITTED',
                'DISPUTED',
                'PAYMENT_RELEASED',
                'REFUNDED'
            )
        );

CREATE INDEX idx_execution_units_escrow_status
    ON execution_units (escrow_status);

CREATE INDEX idx_execution_units_escrow_job_id
    ON execution_units (escrow_job_id);

CREATE INDEX idx_execution_units_submit_result_tx_hash
    ON execution_units (submit_result_tx_hash);

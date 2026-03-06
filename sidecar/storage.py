from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from cps_settlement.models import ComputeState, EscrowStatus, SettlementRecord


class SettlementRepository:
    """SQLite persistence for sidecar settlement records."""

    def __init__(self, db_path: str = "sidecar.sqlite3") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settlement_records (
                    task_id TEXT NOT NULL,
                    execution_unit_id TEXT,
                    settlement_chain TEXT NOT NULL,
                    escrow_job_id INTEGER,
                    escrow_contract_address TEXT,
                    escrow_status TEXT NOT NULL,
                    result_hash TEXT,
                    attestation_digest TEXT,
                    attestor_address TEXT,
                    submit_result_tx_hash TEXT,
                    release_payment_tx_hash TEXT,
                    chain_last_error TEXT,
                    escrow_value_wei INTEGER,
                    challenge_window_sec INTEGER,
                    submitted_onchain_at TEXT,
                    released_onchain_at TEXT,
                    compute_state TEXT NOT NULL,
                    PRIMARY KEY (task_id, execution_unit_id)
                )
                """
            )

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path.as_posix())
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save(self, record: SettlementRecord) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO settlement_records (
                    task_id,
                    execution_unit_id,
                    settlement_chain,
                    escrow_job_id,
                    escrow_contract_address,
                    escrow_status,
                    result_hash,
                    attestation_digest,
                    attestor_address,
                    submit_result_tx_hash,
                    release_payment_tx_hash,
                    chain_last_error,
                    escrow_value_wei,
                    challenge_window_sec,
                    submitted_onchain_at,
                    released_onchain_at,
                    compute_state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id, execution_unit_id) DO UPDATE SET
                    settlement_chain=excluded.settlement_chain,
                    escrow_job_id=excluded.escrow_job_id,
                    escrow_contract_address=excluded.escrow_contract_address,
                    escrow_status=excluded.escrow_status,
                    result_hash=excluded.result_hash,
                    attestation_digest=excluded.attestation_digest,
                    attestor_address=excluded.attestor_address,
                    submit_result_tx_hash=excluded.submit_result_tx_hash,
                    release_payment_tx_hash=excluded.release_payment_tx_hash,
                    chain_last_error=excluded.chain_last_error,
                    escrow_value_wei=excluded.escrow_value_wei,
                    challenge_window_sec=excluded.challenge_window_sec,
                    submitted_onchain_at=excluded.submitted_onchain_at,
                    released_onchain_at=excluded.released_onchain_at,
                    compute_state=excluded.compute_state
                """,
                (
                    record.task_id,
                    record.execution_unit_id,
                    record.settlement_chain,
                    record.escrow_job_id,
                    record.escrow_contract_address,
                    record.escrow_status.value,
                    record.result_hash,
                    record.attestation_digest,
                    record.attestor_address,
                    record.submit_result_tx_hash,
                    record.release_payment_tx_hash,
                    record.chain_last_error,
                    record.escrow_value_wei,
                    record.challenge_window_sec,
                    self._to_iso(record.submitted_onchain_at),
                    self._to_iso(record.released_onchain_at),
                    record.compute_state.value,
                ),
            )

    def get(self, task_id: str, execution_unit_id: str | None) -> SettlementRecord | None:
        with self._conn() as conn:
            base_query = """
                SELECT
                    task_id,
                    execution_unit_id,
                    settlement_chain,
                    escrow_job_id,
                    escrow_contract_address,
                    escrow_status,
                    result_hash,
                    attestation_digest,
                    attestor_address,
                    submit_result_tx_hash,
                    release_payment_tx_hash,
                    chain_last_error,
                    escrow_value_wei,
                    challenge_window_sec,
                    submitted_onchain_at,
                    released_onchain_at,
                    compute_state
                FROM settlement_records
                WHERE task_id = ?
            """
            if execution_unit_id is None:
                row = conn.execute(
                    base_query + " AND execution_unit_id IS NULL",
                    (task_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    base_query + " AND execution_unit_id = ?",
                    (task_id, execution_unit_id),
                ).fetchone()

        if row is None:
            return None

        return SettlementRecord(
            task_id=row[0],
            execution_unit_id=row[1],
            settlement_chain=row[2],
            escrow_job_id=row[3],
            escrow_contract_address=row[4],
            escrow_status=EscrowStatus(row[5]),
            result_hash=row[6],
            attestation_digest=row[7],
            attestor_address=row[8],
            submit_result_tx_hash=row[9],
            release_payment_tx_hash=row[10],
            chain_last_error=row[11],
            escrow_value_wei=row[12],
            challenge_window_sec=row[13],
            submitted_onchain_at=self._from_iso(row[14]),
            released_onchain_at=self._from_iso(row[15]),
            compute_state=ComputeState(row[16]),
        )

    @staticmethod
    def _to_iso(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()

    @staticmethod
    def _from_iso(value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value)

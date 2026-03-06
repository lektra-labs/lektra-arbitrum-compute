from __future__ import annotations

import hashlib

from cps_settlement import (
    ComputeState,
    SettlementRecord,
    SettlementStateMachine,
)

from .arbitrum_client import ArbitrumEscrowClient
from .storage import SettlementRepository


class SettlementOrchestrator:
    """Coordinates sidecar settlement lifecycle around an existing backend."""

    def __init__(
        self,
        *,
        repository: SettlementRepository,
        chain_client: ArbitrumEscrowClient,
    ) -> None:
        self.repository = repository
        self.chain_client = chain_client

    def ensure_record(
        self,
        *,
        task_id: str,
        execution_unit_id: str | None,
    ) -> SettlementRecord:
        existing = self.repository.get(task_id, execution_unit_id)
        if existing:
            return existing
        record = SettlementRecord(task_id=task_id, execution_unit_id=execution_unit_id)
        self.repository.save(record)
        return record

    def create_job(
        self,
        *,
        task_id: str,
        execution_unit_id: str | None,
        escrow_value_wei: int,
        challenge_window_sec: int,
        input_spec_hash: str,
    ) -> SettlementRecord:
        record = self.ensure_record(task_id=task_id, execution_unit_id=execution_unit_id)
        if record.escrow_job_id:
            return record

        tx = self.chain_client.create_job(
            task_id=task_id,
            execution_unit_id=execution_unit_id or "",
            escrow_value_wei=escrow_value_wei,
            input_spec_hash=input_spec_hash,
            challenge_window_sec=challenge_window_sec,
        )

        SettlementStateMachine.mark_escrow_created(
            record,
            escrow_job_id=tx.escrow_job_id or 0,
            contract_address=self.chain_client.contract_address,
            escrow_value_wei=escrow_value_wei,
            challenge_window_sec=challenge_window_sec,
        )
        self.repository.save(record)
        return record

    def mark_backend_completed(
        self,
        *,
        task_id: str,
        execution_unit_id: str | None,
    ) -> SettlementRecord:
        record = self.ensure_record(task_id=task_id, execution_unit_id=execution_unit_id)
        SettlementStateMachine.set_compute_state(record, ComputeState.COMPLETED)
        self.repository.save(record)
        return record

    def submit_result(
        self,
        *,
        task_id: str,
        execution_unit_id: str | None,
        result_payload: bytes,
        attestation_digest: str,
        attestor_address: str,
        energy_micro_kwh: int,
        signature: str,
    ) -> SettlementRecord:
        record = self.ensure_record(task_id=task_id, execution_unit_id=execution_unit_id)

        result_hash = "0x" + hashlib.sha256(result_payload).hexdigest()
        tx = self.chain_client.submit_result(
            escrow_job_id=record.escrow_job_id or 0,
            result_hash=result_hash,
            attestation_digest=attestation_digest,
            energy_micro_kwh=energy_micro_kwh,
            signature=signature,
        )

        SettlementStateMachine.mark_result_submitted(
            record,
            result_hash=result_hash,
            attestation_digest=attestation_digest,
            attestor_address=attestor_address,
            submit_result_tx_hash=tx.tx_hash,
        )
        self.repository.save(record)
        return record

    def release_payment(
        self,
        *,
        task_id: str,
        execution_unit_id: str | None,
    ) -> SettlementRecord:
        record = self.ensure_record(task_id=task_id, execution_unit_id=execution_unit_id)
        tx = self.chain_client.release_payment(escrow_job_id=record.escrow_job_id or 0)
        SettlementStateMachine.mark_payment_released(
            record,
            release_payment_tx_hash=tx.tx_hash,
        )
        self.repository.save(record)
        return record

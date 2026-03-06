from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ComputeState(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    OFFERED = "OFFERED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EscrowStatus(str, Enum):
    NONE = "NONE"
    CREATED = "CREATED"
    RESULT_SUBMITTED = "RESULT_SUBMITTED"
    DISPUTED = "DISPUTED"
    PAYMENT_RELEASED = "PAYMENT_RELEASED"
    REFUNDED = "REFUNDED"


@dataclass
class SettlementRecord:
    task_id: str
    execution_unit_id: Optional[str] = None

    settlement_chain: str = "ARBITRUM_SEPOLIA"
    escrow_job_id: Optional[int] = None
    escrow_contract_address: Optional[str] = None
    escrow_status: EscrowStatus = EscrowStatus.NONE

    result_hash: Optional[str] = None
    attestation_digest: Optional[str] = None
    attestor_address: Optional[str] = None

    submit_result_tx_hash: Optional[str] = None
    release_payment_tx_hash: Optional[str] = None
    chain_last_error: Optional[str] = None

    escrow_value_wei: Optional[int] = None
    challenge_window_sec: Optional[int] = None
    submitted_onchain_at: Optional[datetime] = None
    released_onchain_at: Optional[datetime] = None

    compute_state: ComputeState = ComputeState.PENDING

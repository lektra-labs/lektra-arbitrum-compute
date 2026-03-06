from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from .models import ComputeState, EscrowStatus, SettlementRecord


class InvalidTransition(ValueError):
    """Raised when a settlement state transition is not allowed."""


class ValidationError(ValueError):
    """Raised when a settlement payload is malformed."""


class SettlementStateMachine:
    """Hackathon v1 settlement transitions for CPS records."""

    @staticmethod
    def set_compute_state(record: SettlementRecord, state: ComputeState) -> None:
        record.compute_state = state

    @staticmethod
    def idempotency_key(
        *,
        chain: str,
        contract_address: str,
        escrow_job_id: int,
        action: Literal["submit", "release"],
    ) -> str:
        SettlementStateMachine._validate_address("contract_address", contract_address)
        if escrow_job_id <= 0:
            raise ValidationError("escrow_job_id must be > 0")
        if action not in ("submit", "release"):
            raise ValidationError("action must be 'submit' or 'release'")
        return f"{chain}:{contract_address.lower()}:{escrow_job_id}:{action}"

    @staticmethod
    def mark_escrow_created(
        record: SettlementRecord,
        *,
        escrow_job_id: int,
        contract_address: str,
        escrow_value_wei: int,
        challenge_window_sec: int,
    ) -> None:
        if escrow_job_id <= 0:
            raise ValidationError("escrow_job_id must be > 0")
        SettlementStateMachine._validate_address("contract_address", contract_address)
        if escrow_value_wei <= 0:
            raise ValidationError("escrow_value_wei must be > 0")
        if challenge_window_sec < 0:
            raise ValidationError("challenge_window_sec must be >= 0")

        # Idempotent re-apply for the same escrow job.
        if (
            record.escrow_status == EscrowStatus.CREATED
            and record.escrow_job_id == escrow_job_id
        ):
            return

        if record.escrow_status != EscrowStatus.NONE:
            raise InvalidTransition(
                f"cannot move from {record.escrow_status} to {EscrowStatus.CREATED}"
            )

        record.escrow_job_id = escrow_job_id
        record.escrow_contract_address = contract_address.lower()
        record.escrow_value_wei = escrow_value_wei
        record.challenge_window_sec = challenge_window_sec
        record.escrow_status = EscrowStatus.CREATED
        record.chain_last_error = None

    @staticmethod
    def mark_result_submitted(
        record: SettlementRecord,
        *,
        result_hash: str,
        attestation_digest: str,
        attestor_address: str,
        submit_result_tx_hash: str,
        submitted_onchain_at: datetime | None = None,
    ) -> None:
        SettlementStateMachine._validate_bytes32("result_hash", result_hash)
        SettlementStateMachine._validate_bytes32("attestation_digest", attestation_digest)
        SettlementStateMachine._validate_address("attestor_address", attestor_address)
        SettlementStateMachine._validate_tx_hash(
            "submit_result_tx_hash", submit_result_tx_hash
        )

        if record.compute_state != ComputeState.COMPLETED:
            raise InvalidTransition(
                "compute state must be COMPLETED before result submission"
            )

        if record.escrow_status == EscrowStatus.RESULT_SUBMITTED:
            # Idempotent re-apply for the same transaction.
            if record.submit_result_tx_hash == submit_result_tx_hash.lower():
                return
            raise InvalidTransition(
                "result already submitted with a different transaction hash"
            )

        if record.escrow_status != EscrowStatus.CREATED:
            raise InvalidTransition(
                f"cannot move from {record.escrow_status} to {EscrowStatus.RESULT_SUBMITTED}"
            )

        record.result_hash = result_hash.lower()
        record.attestation_digest = attestation_digest.lower()
        record.attestor_address = attestor_address.lower()
        record.submit_result_tx_hash = submit_result_tx_hash.lower()
        record.submitted_onchain_at = submitted_onchain_at or datetime.now(timezone.utc)
        record.escrow_status = EscrowStatus.RESULT_SUBMITTED
        record.chain_last_error = None

    @staticmethod
    def mark_payment_released(
        record: SettlementRecord,
        *,
        release_payment_tx_hash: str,
        released_onchain_at: datetime | None = None,
    ) -> None:
        SettlementStateMachine._validate_tx_hash(
            "release_payment_tx_hash", release_payment_tx_hash
        )

        if record.escrow_status == EscrowStatus.PAYMENT_RELEASED:
            # Idempotent re-apply for the same transaction.
            if record.release_payment_tx_hash == release_payment_tx_hash.lower():
                return
            raise InvalidTransition("payment already released with a different tx hash")

        if record.escrow_status != EscrowStatus.RESULT_SUBMITTED:
            raise InvalidTransition(
                f"cannot move from {record.escrow_status} to {EscrowStatus.PAYMENT_RELEASED}"
            )

        record.release_payment_tx_hash = release_payment_tx_hash.lower()
        record.released_onchain_at = released_onchain_at or datetime.now(timezone.utc)
        record.escrow_status = EscrowStatus.PAYMENT_RELEASED
        record.chain_last_error = None

    @staticmethod
    def mark_disputed(record: SettlementRecord) -> None:
        if record.escrow_status != EscrowStatus.RESULT_SUBMITTED:
            raise InvalidTransition(
                f"cannot move from {record.escrow_status} to {EscrowStatus.DISPUTED}"
            )
        record.escrow_status = EscrowStatus.DISPUTED
        record.chain_last_error = None

    @staticmethod
    def mark_refunded(record: SettlementRecord) -> None:
        if record.escrow_status not in (EscrowStatus.CREATED, EscrowStatus.DISPUTED):
            raise InvalidTransition(
                f"cannot move from {record.escrow_status} to {EscrowStatus.REFUNDED}"
            )
        record.escrow_status = EscrowStatus.REFUNDED
        record.chain_last_error = None

    @staticmethod
    def record_chain_error(record: SettlementRecord, error_message: str) -> None:
        record.chain_last_error = error_message[:512] if error_message else "unknown error"

    @staticmethod
    def _validate_bytes32(field_name: str, value: str) -> None:
        if not SettlementStateMachine._is_fixed_hex(value, 32):
            raise ValidationError(f"{field_name} must be a 32-byte 0x-prefixed hex string")

    @staticmethod
    def _validate_tx_hash(field_name: str, value: str) -> None:
        if not SettlementStateMachine._is_fixed_hex(value, 32):
            raise ValidationError(f"{field_name} must be a tx hash (32-byte hex)")

    @staticmethod
    def _validate_address(field_name: str, value: str) -> None:
        if not SettlementStateMachine._is_fixed_hex(value, 20):
            raise ValidationError(f"{field_name} must be a 20-byte 0x-prefixed hex address")

    @staticmethod
    def _is_fixed_hex(value: str, byte_length: int) -> bool:
        if not isinstance(value, str):
            return False
        if not value.startswith("0x"):
            return False
        expected_length = 2 + byte_length * 2
        if len(value) != expected_length:
            return False
        hex_body = value[2:]
        try:
            int(hex_body, 16)
        except ValueError:
            return False
        return True

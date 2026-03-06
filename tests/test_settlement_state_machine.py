import unittest

from cps_settlement import (
    ComputeState,
    EscrowStatus,
    InvalidTransition,
    SettlementRecord,
    SettlementStateMachine,
    ValidationError,
)


def fixed_hex(byte_len: int, nibble: str) -> str:
    return "0x" + nibble * (byte_len * 2)


CONTRACT = fixed_hex(20, "1")
ATTESTOR = fixed_hex(20, "2")
RESULT_HASH = fixed_hex(32, "a")
ATTESTATION_DIGEST = fixed_hex(32, "b")
SUBMIT_TX = fixed_hex(32, "c")
RELEASE_TX = fixed_hex(32, "d")


class SettlementStateMachineTest(unittest.TestCase):
    def test_create_and_happy_path_transitions(self) -> None:
        record = SettlementRecord(task_id="task-1")

        SettlementStateMachine.mark_escrow_created(
            record,
            escrow_job_id=17,
            contract_address=CONTRACT,
            escrow_value_wei=10**15,
            challenge_window_sec=3600,
        )
        SettlementStateMachine.set_compute_state(record, ComputeState.COMPLETED)
        SettlementStateMachine.mark_result_submitted(
            record,
            result_hash=RESULT_HASH,
            attestation_digest=ATTESTATION_DIGEST,
            attestor_address=ATTESTOR,
            submit_result_tx_hash=SUBMIT_TX,
        )
        SettlementStateMachine.mark_payment_released(
            record, release_payment_tx_hash=RELEASE_TX
        )

        self.assertEqual(record.escrow_status, EscrowStatus.PAYMENT_RELEASED)
        self.assertEqual(record.submit_result_tx_hash, SUBMIT_TX)
        self.assertEqual(record.release_payment_tx_hash, RELEASE_TX)

    def test_result_submit_requires_completed_compute(self) -> None:
        record = SettlementRecord(task_id="task-2")
        SettlementStateMachine.mark_escrow_created(
            record,
            escrow_job_id=21,
            contract_address=CONTRACT,
            escrow_value_wei=10**15,
            challenge_window_sec=0,
        )

        with self.assertRaises(InvalidTransition):
            SettlementStateMachine.mark_result_submitted(
                record,
                result_hash=RESULT_HASH,
                attestation_digest=ATTESTATION_DIGEST,
                attestor_address=ATTESTOR,
                submit_result_tx_hash=SUBMIT_TX,
            )

    def test_submit_is_idempotent_for_same_tx(self) -> None:
        record = SettlementRecord(task_id="task-3")
        SettlementStateMachine.mark_escrow_created(
            record,
            escrow_job_id=22,
            contract_address=CONTRACT,
            escrow_value_wei=10**15,
            challenge_window_sec=0,
        )
        SettlementStateMachine.set_compute_state(record, ComputeState.COMPLETED)

        SettlementStateMachine.mark_result_submitted(
            record,
            result_hash=RESULT_HASH,
            attestation_digest=ATTESTATION_DIGEST,
            attestor_address=ATTESTOR,
            submit_result_tx_hash=SUBMIT_TX,
        )
        SettlementStateMachine.mark_result_submitted(
            record,
            result_hash=RESULT_HASH,
            attestation_digest=ATTESTATION_DIGEST,
            attestor_address=ATTESTOR,
            submit_result_tx_hash=SUBMIT_TX,
        )

        self.assertEqual(record.escrow_status, EscrowStatus.RESULT_SUBMITTED)

    def test_submit_with_different_tx_after_success_fails(self) -> None:
        record = SettlementRecord(task_id="task-4")
        SettlementStateMachine.mark_escrow_created(
            record,
            escrow_job_id=23,
            contract_address=CONTRACT,
            escrow_value_wei=10**15,
            challenge_window_sec=0,
        )
        SettlementStateMachine.set_compute_state(record, ComputeState.COMPLETED)
        SettlementStateMachine.mark_result_submitted(
            record,
            result_hash=RESULT_HASH,
            attestation_digest=ATTESTATION_DIGEST,
            attestor_address=ATTESTOR,
            submit_result_tx_hash=SUBMIT_TX,
        )

        with self.assertRaises(InvalidTransition):
            SettlementStateMachine.mark_result_submitted(
                record,
                result_hash=RESULT_HASH,
                attestation_digest=ATTESTATION_DIGEST,
                attestor_address=ATTESTOR,
                submit_result_tx_hash=fixed_hex(32, "e"),
            )

    def test_release_requires_result_submitted(self) -> None:
        record = SettlementRecord(task_id="task-5")
        SettlementStateMachine.mark_escrow_created(
            record,
            escrow_job_id=24,
            contract_address=CONTRACT,
            escrow_value_wei=10**15,
            challenge_window_sec=0,
        )

        with self.assertRaises(InvalidTransition):
            SettlementStateMachine.mark_payment_released(
                record, release_payment_tx_hash=RELEASE_TX
            )

    def test_idempotency_key_format(self) -> None:
        key = SettlementStateMachine.idempotency_key(
            chain="ARBITRUM_SEPOLIA",
            contract_address="0x" + CONTRACT[2:].upper(),
            escrow_job_id=99,
            action="submit",
        )
        self.assertEqual(key, "ARBITRUM_SEPOLIA:" + CONTRACT + ":99:submit")

    def test_validation_rejects_bad_hash(self) -> None:
        record = SettlementRecord(task_id="task-6")
        SettlementStateMachine.mark_escrow_created(
            record,
            escrow_job_id=25,
            contract_address=CONTRACT,
            escrow_value_wei=10**15,
            challenge_window_sec=0,
        )
        SettlementStateMachine.set_compute_state(record, ComputeState.COMPLETED)

        with self.assertRaises(ValidationError):
            SettlementStateMachine.mark_result_submitted(
                record,
                result_hash="0x1234",
                attestation_digest=ATTESTATION_DIGEST,
                attestor_address=ATTESTOR,
                submit_result_tx_hash=SUBMIT_TX,
            )


if __name__ == "__main__":
    unittest.main()

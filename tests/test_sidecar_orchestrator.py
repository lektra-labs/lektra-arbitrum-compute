import tempfile
import unittest
from pathlib import Path

from cps_settlement import EscrowStatus, InvalidTransition
from sidecar import ArbitrumEscrowClient, SettlementOrchestrator, SettlementRepository


def fixed_hex(byte_len: int, nibble: str) -> str:
    return "0x" + nibble * (byte_len * 2)


class SidecarOrchestratorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self.tmpdir.name) / "sidecar.sqlite3"
        self.repo = SettlementRepository(db_path.as_posix())
        self.chain = ArbitrumEscrowClient(
            contract_address=fixed_hex(20, "1"),
            dry_run=True,
        )
        self.orchestrator = SettlementOrchestrator(
            repository=self.repo,
            chain_client=self.chain,
        )

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_happy_path(self) -> None:
        self.orchestrator.create_job(
            task_id="task-1",
            execution_unit_id="unit-1",
            escrow_value_wei=10**15,
            challenge_window_sec=300,
            input_spec_hash=fixed_hex(32, "a"),
        )
        self.orchestrator.mark_backend_completed(
            task_id="task-1", execution_unit_id="unit-1"
        )
        self.orchestrator.submit_result(
            task_id="task-1",
            execution_unit_id="unit-1",
            result_payload=b"result",
            attestation_digest=fixed_hex(32, "b"),
            attestor_address=fixed_hex(20, "2"),
            energy_micro_kwh=123,
            signature="sig",
        )
        final_record = self.orchestrator.release_payment(
            task_id="task-1", execution_unit_id="unit-1"
        )

        self.assertEqual(final_record.escrow_status, EscrowStatus.PAYMENT_RELEASED)
        self.assertIsNotNone(final_record.submit_result_tx_hash)
        self.assertIsNotNone(final_record.release_payment_tx_hash)

    def test_submit_result_requires_completed_backend_state(self) -> None:
        self.orchestrator.create_job(
            task_id="task-2",
            execution_unit_id="unit-2",
            escrow_value_wei=10**15,
            challenge_window_sec=300,
            input_spec_hash=fixed_hex(32, "a"),
        )

        with self.assertRaises(InvalidTransition):
            self.orchestrator.submit_result(
                task_id="task-2",
                execution_unit_id="unit-2",
                result_payload=b"result",
                attestation_digest=fixed_hex(32, "b"),
                attestor_address=fixed_hex(20, "2"),
                energy_micro_kwh=123,
                signature="sig",
            )

    def test_repeated_create_job_is_idempotent(self) -> None:
        first = self.orchestrator.create_job(
            task_id="task-3",
            execution_unit_id="unit-3",
            escrow_value_wei=10**15,
            challenge_window_sec=300,
            input_spec_hash=fixed_hex(32, "a"),
        )
        second = self.orchestrator.create_job(
            task_id="task-3",
            execution_unit_id="unit-3",
            escrow_value_wei=10**15,
            challenge_window_sec=300,
            input_spec_hash=fixed_hex(32, "a"),
        )

        self.assertEqual(first.escrow_job_id, second.escrow_job_id)
        self.assertEqual(second.escrow_status, EscrowStatus.CREATED)


if __name__ == "__main__":
    unittest.main()

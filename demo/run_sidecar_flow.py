from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sidecar import ArbitrumEscrowClient, SettlementOrchestrator, SettlementRepository


def fixed_hex(byte_len: int, nibble: str) -> str:
    return "0x" + nibble * (byte_len * 2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a dry-run sidecar settlement flow")
    parser.add_argument("--task-id", default="demo-task-1")
    parser.add_argument("--execution-unit-id", default="unit-1")
    parser.add_argument("--db-path", default="demo/sidecar-demo.sqlite3")
    parser.add_argument(
        "--contract-address",
        default=fixed_hex(20, "1"),
        help="0x-prefixed escrow contract address",
    )
    parser.add_argument("--escrow-value-wei", type=int, default=10**15)
    parser.add_argument("--challenge-window-sec", type=int, default=300)
    parser.add_argument(
        "--reuse-db",
        action="store_true",
        help="Reuse existing DB file instead of resetting it for the demo run",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists() and not args.reuse_db:
        db_path.unlink()

    repo = SettlementRepository(db_path.as_posix())
    chain = ArbitrumEscrowClient(
        contract_address=args.contract_address,
        dry_run=True,
    )
    orchestrator = SettlementOrchestrator(repository=repo, chain_client=chain)

    attestor = fixed_hex(20, "2")
    attestation_digest = fixed_hex(32, "b")
    signature = "demo-signature"
    input_spec_hash = fixed_hex(32, "a")

    record = orchestrator.create_job(
        task_id=args.task_id,
        execution_unit_id=args.execution_unit_id,
        escrow_value_wei=args.escrow_value_wei,
        challenge_window_sec=args.challenge_window_sec,
        input_spec_hash=input_spec_hash,
    )
    record = orchestrator.mark_backend_completed(
        task_id=args.task_id,
        execution_unit_id=args.execution_unit_id,
    )
    record = orchestrator.submit_result(
        task_id=args.task_id,
        execution_unit_id=args.execution_unit_id,
        result_payload=b"demo-result-payload",
        attestation_digest=attestation_digest,
        attestor_address=attestor,
        energy_micro_kwh=123456,
        signature=signature,
    )
    record = orchestrator.release_payment(
        task_id=args.task_id,
        execution_unit_id=args.execution_unit_id,
    )

    print(
        json.dumps(
            {
                "task_id": record.task_id,
                "execution_unit_id": record.execution_unit_id,
                "escrow_job_id": record.escrow_job_id,
                "escrow_status": record.escrow_status.value,
                "result_hash": record.result_hash,
                "submit_result_tx_hash": record.submit_result_tx_hash,
                "release_payment_tx_hash": record.release_payment_tx_hash,
                "db_path": db_path.as_posix(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sidecar import ArbitrumEscrowClient, SettlementOrchestrator, SettlementRepository
from sidecar.backend_client import BackendApiClient


def fixed_hex(byte_len: int, nibble: str) -> str:
    return "0x" + nibble * (byte_len * 2)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


def poll_until_completed(
    backend: BackendApiClient,
    *,
    task_id: str,
    execution_unit_id: str,
    poll_interval_seconds: int,
    poll_timeout_seconds: int,
) -> dict[str, Any]:
    deadline = time.time() + poll_timeout_seconds
    while time.time() < deadline:
        snap = backend.get_execution_unit_snapshot(task_id, execution_unit_id)
        if snap and snap.status.upper() == "COMPLETED":
            return {
                "task_id": snap.task_id,
                "execution_unit_id": snap.execution_unit_id,
                "status": snap.status,
                "artifact_urls": list(snap.artifact_urls),
            }
        time.sleep(poll_interval_seconds)
    raise TimeoutError(
        f"Timeout waiting for unit completion: task_id={task_id}, "
        f"execution_unit_id={execution_unit_id}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run real sidecar settlement flow against backend + Arbitrum"
    )
    parser.add_argument("--env-file", default=".env", help="Optional env file path")
    parser.add_argument("--task-id", help="Existing backend task id")
    parser.add_argument("--execution-unit-id", help="Existing backend execution unit id")
    parser.add_argument(
        "--result-payload",
        default="demo-result",
        help="Fallback payload for hash anchoring when artifact fetch is not wired",
    )
    parser.add_argument(
        "--auto-release",
        action="store_true",
        help="Call releasePayment after submitResult",
    )
    parser.add_argument(
        "--reuse-db",
        action="store_true",
        help="Reuse existing sidecar DB file (default resets DB before run)",
    )
    parser.add_argument(
        "--skip-backend-poll",
        action="store_true",
        help="Skip CPS polling and assume the execution unit is already completed",
    )
    args = parser.parse_args()

    load_env_file(Path(args.env_file))

    backend_api_url = env("BACKEND_API_URL", default="")
    backend_bearer = env("BACKEND_BEARER_TOKEN", default="")
    escrow_contract = env("ESCROW_CONTRACT_ADDRESS", required=True)
    rpc_url = env("ARBITRUM_RPC_URL", required=True)
    chain_id = int(env("ARBITRUM_CHAIN_ID", default="421614"))
    private_key = env("TX_SENDER_PRIVATE_KEY", required=True)
    provider_address = env("PROVIDER_ADDRESS", required=True)
    requester_address = env("JOB_REQUESTER_ADDRESS", required=True)
    attestor_address = env("ATTESTOR_ADDRESS", default=fixed_hex(20, "2"))

    db_path = Path(env("SIDECAR_DB_PATH", default="demo/sidecar-real.sqlite3"))
    poll_interval_seconds = int(env("POLL_INTERVAL_SECONDS", default="5"))
    poll_timeout_seconds = int(env("POLL_TIMEOUT_SECONDS", default="600"))
    escrow_value_wei = int(env("ESCROW_VALUE_WEI", default=str(10**15)))
    challenge_window_sec = int(env("CHALLENGE_WINDOW_SEC", default="300"))

    task_id = args.task_id or env("TASK_ID", default="")
    execution_unit_id = args.execution_unit_id or env("EXECUTION_UNIT_ID", default="")
    if not task_id or not execution_unit_id:
        raise RuntimeError(
            "Provide --task-id and --execution-unit-id or set TASK_ID/EXECUTION_UNIT_ID"
        )

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists() and not args.reuse_db:
        db_path.unlink()

    skip_backend_poll = args.skip_backend_poll or not backend_bearer
    if not skip_backend_poll and not backend_api_url:
        raise RuntimeError(
            "BACKEND_API_URL is required unless backend polling is skipped"
        )

    backend = (
        None
        if skip_backend_poll
        else BackendApiClient(base_url=backend_api_url, bearer_token=backend_bearer)
    )
    repository = SettlementRepository(db_path.as_posix())
    chain = ArbitrumEscrowClient(
        contract_address=escrow_contract,
        dry_run=False,
        rpc_url=rpc_url,
        private_key=private_key,
        chain_id=chain_id,
        worker_address=provider_address,
        requester_address=requester_address,
    )
    orchestrator = SettlementOrchestrator(repository=repository, chain_client=chain)

    input_spec_hash = fixed_hex(32, "a")
    attestation_digest = fixed_hex(32, "b")
    signature = "0x1234"

    record = orchestrator.create_job(
        task_id=task_id,
        execution_unit_id=execution_unit_id,
        escrow_value_wei=escrow_value_wei,
        challenge_window_sec=challenge_window_sec,
        input_spec_hash=input_spec_hash,
    )

    if skip_backend_poll:
        completion = {
            "task_id": task_id,
            "execution_unit_id": execution_unit_id,
            "status": "COMPLETED",
            "artifact_urls": [],
        }
    else:
        completion = poll_until_completed(
            backend,
            task_id=task_id,
            execution_unit_id=execution_unit_id,
            poll_interval_seconds=poll_interval_seconds,
            poll_timeout_seconds=poll_timeout_seconds,
        )

    orchestrator.mark_backend_completed(task_id=task_id, execution_unit_id=execution_unit_id)

    # Artifact download/hash can be wired here later. For now we anchor provided payload bytes.
    result_payload = args.result_payload.encode("utf-8")
    record = orchestrator.submit_result(
        task_id=task_id,
        execution_unit_id=execution_unit_id,
        result_payload=result_payload,
        attestation_digest=attestation_digest,
        attestor_address=attestor_address,
        energy_micro_kwh=123456,
        signature=signature,
    )

    if args.auto_release:
        record = orchestrator.release_payment(
            task_id=task_id,
            execution_unit_id=execution_unit_id,
        )

    print(
        json.dumps(
            {
                "task_id": task_id,
                "execution_unit_id": execution_unit_id,
                "backend_mode": "skipped_demo" if skip_backend_poll else "polled",
                "backend_status": completion["status"],
                "artifact_urls": completion["artifact_urls"],
                "escrow_job_id": record.escrow_job_id,
                "escrow_status": record.escrow_status.value,
                "provider_address": provider_address,
                "job_requester_address": requester_address,
                "attestor_address": attestor_address,
                "submit_result_tx_hash": record.submit_result_tx_hash,
                "release_payment_tx_hash": record.release_payment_tx_hash,
                "db_path": db_path.as_posix(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

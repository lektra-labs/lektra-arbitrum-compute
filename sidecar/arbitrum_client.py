from __future__ import annotations

import hashlib
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ArbitrumTxResult:
    tx_hash: str
    escrow_job_id: int | None = None


class ArbitrumEscrowClient:
    """Thin chain client abstraction.

    In hackathon dry-run mode this generates deterministic synthetic tx hashes.
    """

    def __init__(
        self,
        *,
        contract_address: str,
        dry_run: bool = True,
        rpc_url: str | None = None,
        private_key: str | None = None,
        chain_id: int = 421614,
        contract_abi: Sequence[dict[str, Any]] | None = None,
        worker_address: str | None = None,
        requester_address: str | None = None,
        default_deadline_seconds: int = 3600,
        tx_timeout_seconds: int = 120,
    ) -> None:
        self.contract_address = contract_address.lower()
        self.dry_run = dry_run
        self.chain_id = chain_id
        self._next_job_id = 1
        self._default_deadline_seconds = default_deadline_seconds
        self._tx_timeout_seconds = tx_timeout_seconds

        self._web3 = None
        self._account = None
        self._contract = None
        self._worker_address = worker_address
        self._requester_address = requester_address.lower() if requester_address else None

        if not self.dry_run:
            self._init_real_mode(
                rpc_url=rpc_url,
                private_key=private_key,
                contract_abi=contract_abi,
                worker_address=worker_address,
                requester_address=requester_address,
            )

    def create_job(
        self,
        *,
        task_id: str,
        execution_unit_id: str,
        escrow_value_wei: int,
        input_spec_hash: str,
        challenge_window_sec: int,
    ) -> ArbitrumTxResult:
        if not self.dry_run:
            return self._create_job_real(
                task_id=task_id,
                execution_unit_id=execution_unit_id,
                escrow_value_wei=escrow_value_wei,
                input_spec_hash=input_spec_hash,
                challenge_window_sec=challenge_window_sec,
            )

        escrow_job_id = self._next_job_id
        self._next_job_id += 1

        tx_hash = self._fake_tx_hash(
            "createJob",
            str(escrow_job_id),
            task_id,
            execution_unit_id,
            str(escrow_value_wei),
            input_spec_hash,
            str(challenge_window_sec),
        )
        return ArbitrumTxResult(tx_hash=tx_hash, escrow_job_id=escrow_job_id)

    def submit_result(
        self,
        *,
        escrow_job_id: int,
        result_hash: str,
        attestation_digest: str,
        energy_micro_kwh: int,
        signature: str,
    ) -> ArbitrumTxResult:
        if not self.dry_run:
            return self._submit_result_real(
                escrow_job_id=escrow_job_id,
                result_hash=result_hash,
                attestation_digest=attestation_digest,
                energy_micro_kwh=energy_micro_kwh,
                signature=signature,
            )

        tx_hash = self._fake_tx_hash(
            "submitResult",
            str(escrow_job_id),
            result_hash,
            attestation_digest,
            str(energy_micro_kwh),
            signature,
        )
        return ArbitrumTxResult(tx_hash=tx_hash)

    def release_payment(self, *, escrow_job_id: int) -> ArbitrumTxResult:
        if not self.dry_run:
            fn = self._contract_call("releasePayment(uint256)", escrow_job_id)
            tx_hash = self._send_function_tx(fn, value=0)
            self._wait_for_receipt(tx_hash)
            return ArbitrumTxResult(tx_hash=tx_hash)
        tx_hash = self._fake_tx_hash("releasePayment", str(escrow_job_id))
        return ArbitrumTxResult(tx_hash=tx_hash)

    def _fake_tx_hash(self, *parts: str) -> str:
        digest = hashlib.sha256(
            "|".join((self.contract_address, *parts)).encode("utf-8")
        ).hexdigest()
        return "0x" + digest

    def _create_job_real(
        self,
        *,
        task_id: str,
        execution_unit_id: str,
        escrow_value_wei: int,
        input_spec_hash: str,
        challenge_window_sec: int,
    ) -> ArbitrumTxResult:
        before_job_id = self._read_next_job_id()
        deadline = int(time.time()) + self._default_deadline_seconds
        worker = self._worker_address or self._account.address

        if self._has_function("createJob(address,uint64,uint64,bytes32)"):
            fn = self._contract_call(
                "createJob(address,uint64,uint64,bytes32)",
                worker,
                deadline,
                challenge_window_sec,
                input_spec_hash,
            )
        elif self._has_function("createJob(address,uint64,bytes32)"):
            fn = self._contract_call(
                "createJob(address,uint64,bytes32)",
                worker,
                deadline,
                input_spec_hash,
            )
        elif self._has_function("createJob(bytes32,uint64)"):
            fn = self._contract_call(
                "createJob(bytes32,uint64)",
                input_spec_hash,
                challenge_window_sec,
            )
        elif self._has_function("createJob(bytes32)"):
            fn = self._contract_call("createJob(bytes32)", input_spec_hash)
        else:
            raise RuntimeError("contract ABI does not expose a supported createJob signature")

        tx_hash = self._send_function_tx(fn, value=escrow_value_wei)
        receipt = self._wait_for_receipt(tx_hash)
        created_job_id = self._extract_job_id_from_receipt(receipt) or before_job_id

        if created_job_id is None:
            raise RuntimeError(
                "createJob succeeded but escrow_job_id could not be resolved"
            )

        return ArbitrumTxResult(tx_hash=tx_hash, escrow_job_id=created_job_id)

    def _submit_result_real(
        self,
        *,
        escrow_job_id: int,
        result_hash: str,
        attestation_digest: str,
        energy_micro_kwh: int,
        signature: str,
    ) -> ArbitrumTxResult:
        signature_bytes = self._to_bytes(signature)

        if self._has_function("submitResult(uint256,bytes32,uint64,bytes32,bytes)"):
            fn = self._contract_call(
                "submitResult(uint256,bytes32,uint64,bytes32,bytes)",
                escrow_job_id,
                result_hash,
                energy_micro_kwh,
                attestation_digest,
                signature_bytes,
            )
        elif self._has_function(
            "submitResult(uint256,bytes32,uint64,uint64,uint64,uint64,bytes)"
        ):
            now_ts = int(time.time())
            fn = self._contract_call(
                "submitResult(uint256,bytes32,uint64,uint64,uint64,uint64,bytes)",
                escrow_job_id,
                result_hash,
                energy_micro_kwh,
                now_ts - 60,
                now_ts,
                now_ts,
                signature_bytes,
            )
        else:
            raise RuntimeError(
                "contract ABI does not expose a supported submitResult signature"
            )

        tx_hash = self._send_function_tx(fn, value=0)
        self._wait_for_receipt(tx_hash)
        return ArbitrumTxResult(tx_hash=tx_hash)

    def _init_real_mode(
        self,
        *,
        rpc_url: str | None,
        private_key: str | None,
        contract_abi: Sequence[dict[str, Any]] | None,
        worker_address: str | None,
        requester_address: str | None,
    ) -> None:
        try:
            from web3 import Web3
        except ImportError as exc:
            raise RuntimeError(
                "web3 is required for dry_run=False. Install with: pip install web3"
            ) from exc

        if not rpc_url:
            raise ValueError("rpc_url is required when dry_run=False")
        if not private_key:
            raise ValueError("private_key is required when dry_run=False")

        web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}))
        if not web3.is_connected():
            raise RuntimeError(f"cannot connect to RPC endpoint: {rpc_url}")

        account = web3.eth.account.from_key(private_key)
        abi = list(contract_abi) if contract_abi is not None else self._default_abi()
        contract = web3.eth.contract(
            address=Web3.to_checksum_address(self.contract_address),
            abi=abi,
        )

        if requester_address:
            requester_checksum = Web3.to_checksum_address(requester_address)
            if requester_checksum != account.address:
                raise ValueError(
                    "private_key account does not match requester_address: "
                    f"{account.address} != {requester_checksum}"
                )

        if worker_address:
            worker_address = Web3.to_checksum_address(worker_address)
        else:
            worker_address = account.address

        self._web3 = web3
        self._account = account
        self._contract = contract
        self._worker_address = worker_address

    def _send_function_tx(self, fn: Any, *, value: int) -> str:
        tx = self._build_transaction(fn, value=value)
        signed = self._account.sign_transaction(tx)
        raw = getattr(signed, "rawTransaction", None) or getattr(
            signed, "raw_transaction"
        )
        tx_hash_bytes = self._web3.eth.send_raw_transaction(raw)
        return self._web3.to_hex(tx_hash_bytes)

    def _build_transaction(self, fn: Any, *, value: int) -> dict[str, Any]:
        nonce = self._web3.eth.get_transaction_count(self._account.address)
        tx_params: dict[str, Any] = {
            "from": self._account.address,
            "nonce": nonce,
            "chainId": self.chain_id,
            "value": value,
        }

        gas_estimate = fn.estimate_gas({"from": self._account.address, "value": value})
        tx_params["gas"] = int(gas_estimate * 1.2) + 50_000

        latest_block = self._web3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas")
        if base_fee is not None:
            priority = self._web3.to_wei(0.1, "gwei")
            tx_params["maxPriorityFeePerGas"] = priority
            tx_params["maxFeePerGas"] = int(base_fee * 2 + priority)
        else:
            tx_params["gasPrice"] = self._web3.eth.gas_price

        return fn.build_transaction(tx_params)

    def _wait_for_receipt(self, tx_hash: str) -> Any:
        receipt = self._web3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=self._tx_timeout_seconds,
            poll_latency=2,
        )
        if int(receipt.get("status", 0)) != 1:
            raise RuntimeError(f"transaction failed: {tx_hash}")
        return receipt

    def _read_next_job_id(self) -> int | None:
        if not self._has_function("nextJobId()"):
            return None
        value = self._contract_call("nextJobId()").call()
        return int(value)

    def _extract_job_id_from_receipt(self, receipt: Any) -> int | None:
        try:
            events = self._contract.events.JobCreated().process_receipt(receipt)
        except Exception:
            return None
        if not events:
            return None
        job_id = events[0].get("args", {}).get("jobId")
        return int(job_id) if job_id is not None else None

    def _has_function(self, signature: str) -> bool:
        try:
            self._contract.get_function_by_signature(signature)
            return True
        except ValueError:
            return False

    def _contract_call(self, signature: str, *args: Any) -> Any:
        fn = self._contract.get_function_by_signature(signature)
        return fn(*args)

    @staticmethod
    def _to_bytes(value: str) -> bytes:
        if value.startswith("0x"):
            hex_body = value[2:]
            if len(hex_body) % 2 == 1:
                hex_body = "0" + hex_body
            try:
                return bytes.fromhex(hex_body)
            except ValueError:
                return value.encode("utf-8")
        return value.encode("utf-8")

    @staticmethod
    def _default_abi() -> list[dict[str, Any]]:
        # Minimal ABI for the expected escrow lifecycle.
        return [
            {
                "inputs": [
                    {"internalType": "address", "name": "worker", "type": "address"},
                    {"internalType": "uint64", "name": "deadline", "type": "uint64"},
                    {
                        "internalType": "uint64",
                        "name": "challengeWindow",
                        "type": "uint64",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "inputSpecHash",
                        "type": "bytes32",
                    },
                ],
                "name": "createJob",
                "outputs": [{"internalType": "uint256", "name": "jobId", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "jobId", "type": "uint256"},
                    {
                        "internalType": "bytes32",
                        "name": "resultHash",
                        "type": "bytes32",
                    },
                    {
                        "internalType": "uint64",
                        "name": "energyMicroKWh",
                        "type": "uint64",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "attestationDigest",
                        "type": "bytes32",
                    },
                    {"internalType": "bytes", "name": "signature", "type": "bytes"},
                ],
                "name": "submitResult",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "uint256", "name": "jobId", "type": "uint256"}],
                "name": "releasePayment",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [],
                "name": "nextJobId",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "anonymous": False,
                "inputs": [
                    {
                        "indexed": False,
                        "internalType": "uint256",
                        "name": "jobId",
                        "type": "uint256",
                    }
                ],
                "name": "JobCreated",
                "type": "event",
            },
        ]

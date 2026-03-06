Solar-powered AI compute settlement layer using Arbitrum and Ray clusters.

## Purpose
This repository contains a public-safe hackathon sidecar implementation that adds on-chain escrow settlement to an existing compute backend without modifying production repositories.

## What's here
- `cps_settlement/`: settlement state model and transition rules.
- `sidecar/`: sidecar clients, orchestration, and SQLite persistence.
- `demo/`: runnable dry-run flow.
- `migrations/`: SQL template for settlement fields.
- `tests/`: unit tests.

## Quick start
Run tests:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

Run demo flow:

```bash
python3 demo/run_sidecar_flow.py
```

Default demo addresses:
- Provider: `0x58FBf65233eFbFFE36Aa3e83DCd7a8813fC65bB9`
- Job requester: `0x66c18AC12b1D4790939e84AA3476ADfCd8284180`

## Real chain mode (step 1)
The sidecar chain client now supports real transactions when `dry_run=False`.

Requirements:
- `web3` Python package
- Arbitrum RPC URL
- escrow tx sender private key
- deployed escrow contract address

Example construction (from your own runner code):

```python
from sidecar import ArbitrumEscrowClient

client = ArbitrumEscrowClient(
    contract_address="0x1111111111111111111111111111111111111111",
    dry_run=False,
    rpc_url="https://sepolia-rollup.arbitrum.io/rpc",
    private_key="0x...",
    chain_id=421614,
    worker_address="0x58FBf65233eFbFFE36Aa3e83DCd7a8813fC65bB9",
    requester_address="0x66c18AC12b1D4790939e84AA3476ADfCd8284180",
)
```

`requester_address` is validated against the address derived from `private_key` in real mode.

## Run real flow
1. Copy env template:

```bash
cp .env.example .env
```

2. Fill required values in `.env`:
- `BACKEND_API_URL`
- `ARBITRUM_RPC_URL`
- `ESCROW_CONTRACT_ADDRESS`
- `TX_SENDER_PRIVATE_KEY`
- `PROVIDER_ADDRESS`
- `JOB_REQUESTER_ADDRESS`
- `TASK_ID`
- `EXECUTION_UNIT_ID`

3. Run:

```bash
python3 demo/run_real_flow.py --auto-release
```

Or pass IDs directly:

```bash
python3 demo/run_real_flow.py \
  --task-id <task_id> \
  --execution-unit-id <execution_unit_id> \
  --auto-release
```

## Public-safe policy
- Keep secrets out of git (`.env`, keys, internal endpoints).
- Use generic architecture wording in docs.
- Keep production backend/frontend repositories read-only for hackathon development.

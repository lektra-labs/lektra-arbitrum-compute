Solar-powered AI compute settlement layer using Arbitrum and Ray clusters.

## Purpose
This repository contains the hackathon implementation of Lektra's on-chain settlement capability on Arbitrum. It integrates with the existing compute backend through a sidecar execution pattern so core production repositories remain unchanged.

## What's here
- `cps_settlement/`: settlement state model and transition rules.
- `sidecar/`: sidecar clients, orchestration, and SQLite persistence.
- `demo/`: runnable dry-run flow.
- `migrations/`: SQL template for settlement fields.
- `tests/`: unit tests.

## Lektra Arbitrum Hackathon deployment
- Contract: `InferenceEscrow`
- Network: `Arbitrum Sepolia (421614)`
- Contract address: `0x6f8C4F2df574239312D06810786f943131d5e6c8`
- Explorer link: [sepolia.arbiscan.io/address/0x6f8C4F2df574239312D06810786f943131d5e6c8](https://sepolia.arbiscan.io/address/0x6f8C4F2df574239312D06810786f943131d5e6c8)
- Example `submitResult` tx: [0x77a190ea99f4da7389d9df9832b5a2a8ce7221ac7bbe9c38b6505974c2d04399](https://sepolia.arbiscan.io/tx/0x77a190ea99f4da7389d9df9832b5a2a8ce7221ac7bbe9c38b6505974c2d04399)
- Repository: [github.com/lektra-labs/lektra-arbitrum-compute](https://github.com/lektra-labs/lektra-arbitrum-compute)

Demo roles used:
- Provider: `0x58FBf65233eFbFFE36Aa3e83DCd7a8813fC65bB9`
- Job requester: `0xFEF9E3e1571004F0C6f7d219108A48ef1171c021`

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
- Job requester: `0xFEF9E3e1571004F0C6f7d219108A48ef1171c021`

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

## Real flow config
1. Copy env template:

```bash
cp .env.example .env
```

2. Fill required values in `.env`:
- `BACKEND_API_URL`
- `BACKEND_BEARER_TOKEN` (optional for demo mode; required for live CPS polling)
- `ARBITRUM_RPC_URL`
- `ESCROW_CONTRACT_ADDRESS`
- `TX_SENDER_PRIVATE_KEY`
- `PROVIDER_ADDRESS`
- `JOB_REQUESTER_ADDRESS`
- `TASK_ID`
- `EXECUTION_UNIT_ID`

## Escrow contract deployment (Arbitrum Sepolia)
This repo now includes a minimal Foundry contract/deploy setup in `contracts/`.

### 1. Install Foundry
```bash
curl -L https://foundry.paradigm.xyz | bash
source ~/.zshrc
foundryup
```

### 2. Build contract
```bash
cd contracts
forge install foundry-rs/forge-std
forge build
```

### 3. Deploy to Arbitrum Sepolia
```bash
export ARBITRUM_RPC_URL="https://arb-sepolia.g.alchemy.com/v2/<ALCHEMY_KEY>"
export DEPLOYER_PRIVATE_KEY="0x<DEPLOYER_PRIVATE_KEY>"
forge script script/Deploy.s.sol:Deploy --rpc-url "$ARBITRUM_RPC_URL" --broadcast
```

Copy the contract address from output and set:
- `ESCROW_CONTRACT_ADDRESS=0x...`

## Real flow prerequisites (local dev)
Before running `demo/run_real_flow.py`, ensure:

1. `compute-platform-services` is running and reachable:
```bash
curl http://localhost:8000/health
```
2. DB has a valid `TASK_ID` and matching `EXECUTION_UNIT_ID`.
3. `.env` is configured as shown in the `Real flow config` section above.

Important:
- `JOB_REQUESTER_ADDRESS` must match the address derived from `TX_SENDER_PRIVATE_KEY` in real mode.

## Run real flow
Default (uses `TASK_ID` and `EXECUTION_UNIT_ID` from `.env`):
```bash
python3 demo/run_real_flow.py --auto-release
```

If `BACKEND_BEARER_TOKEN` is not set, the script skips CPS polling and assumes the selected execution unit is already completed. This is intended for local demos.

Or pass IDs directly:
```bash
python3 demo/run_real_flow.py \
  --task-id <task_id> \
  --execution-unit-id <execution_unit_id> \
  --auto-release
```

Force demo mode even when a bearer token is present:
```bash
python3 demo/run_real_flow.py --skip-backend-poll --auto-release
```

## Troubleshooting
- `ModuleNotFoundError: No module named 'web3'`:
```bash
python3 -m pip install web3
```
- `private_key account does not match requester_address`:
  Set `JOB_REQUESTER_ADDRESS` to the address derived from `TX_SENDER_PRIVATE_KEY`.
- `backend API error 403 ... Not authenticated`:
  Provide `BACKEND_BEARER_TOKEN`, use `--skip-backend-poll` for demo mode, or use a local auth-bypass configuration for development.
- `execution reverted: bad msg.value`:
  Ensure you are using the latest deployed escrow contract address that matches current sidecar expectations.
- If secrets were shared during testing:
  Rotate API keys and private keys immediately.

## Public-safe policy
- Keep secrets out of git (`.env`, keys, internal endpoints).
- Use generic architecture wording in docs.
- Keep production backend/frontend repositories read-only for hackathon development.

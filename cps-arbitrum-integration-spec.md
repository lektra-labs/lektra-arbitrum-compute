# CPS-Arbitrum Integration Card (Hackathon v1, No-Touch Repos)

## 1) What We Are Building
Add Arbitrum escrow settlement as a sidecar around existing Lektra systems.

Keep unchanged (read-only):
- `compute-platform-services`
- `compute-platform-console`

Observed execution path for v1:
- `Console -> CPS Backend -> CPS Worker -> Lektra Agent -> Ray -> Artifact Store`

Added sidecar responsibilities:
- `createJob` (escrow created)
- `submitResult` (result + energy attestation anchored)
- `releasePayment` (post-challenge payout)

## 2) Fixed Decisions (No More Debate for v1)
- Chain: Arbitrum Sepolia (`421614`)
- Currency: ETH escrow
- Attestor: single allowlisted key
- Disputes: centralized operator decision
- Control transport: direct CPS-to-Agent behavior remains as-is; NATS later
- Repo boundary: no commits to CPS/Console repos during hackathon

## 3) Single Source of Truth
- Compute lifecycle stays in CPS (read-only for sidecar).
- Settlement lifecycle is tracked in sidecar storage as `escrow_status`.

`escrow_status` enum:
- `NONE`
- `CREATED`
- `RESULT_SUBMITTED`
- `DISPUTED`
- `PAYMENT_RELEASED`
- `REFUNDED`

Rule:
- Sidecar mirrors CPS status; it does not mutate CPS compute state.

## 4) Minimal Sidecar Data Contract
Store these fields in sidecar DB (keyed by `task_id` + `execution_unit_id`):

- `task_id`
- `execution_unit_id`
- `settlement_chain` (`ARBITRUM_SEPOLIA`)
- `escrow_job_id`
- `escrow_contract_address`
- `escrow_status`
- `result_hash`
- `attestation_digest`
- `attestor_address`
- `submit_result_tx_hash`
- `release_payment_tx_hash`
- `chain_last_error`

Recommended:
- `escrow_value_wei`
- `challenge_window_sec`
- `submitted_onchain_at`
- `released_onchain_at`

## 5) Triggers (Only 3)
### A) `createJob`
When:
- Demo run starts via sidecar command/API.

Do:
- Sidecar creates CPS task (or receives task id if user created from Console).
- Sidecar sends `createJob` on Arbitrum.
- Persist `escrow_job_id`, set `escrow_status=CREATED`.

### B) `submitResult`
When:
- Sidecar polling detects CPS execution unit completion and artifact availability.

Preconditions:
- Artifact exists and is retrievable.
- `result_hash` computed deterministically.
- EIP-712 attestation is signed.

Do:
- Call `submitResult`.
- Persist `submit_result_tx_hash`.
- Set `escrow_status=RESULT_SUBMITTED`.

### C) `releasePayment`
When:
- Manual sidecar action after challenge window.

Do:
- Call `releasePayment`.
- Persist `release_payment_tx_hash`.
- Set `escrow_status=PAYMENT_RELEASED`.

## 6) External Inputs (Read-Only)
From CPS APIs:
- task creation response (`task_id`, unit ids)
- unit status and completion state
- artifact/resource references for hash verification

From energy path:
- EOS/Kepler-derived measurement if available
- fallback: clearly labeled demo estimate/simulation

From chain:
- tx receipts and final status for submit/release

## 7) Reliability Rules (Short Version)
- Idempotency key format: `<chain>:<contract>:<escrow_job_id>:<action>`
- One successful tx per action (`submit`, `release`)
- Duplicate CPS completion detections become no-op after first successful `submitResult`
- Retry transient RPC/mempool errors with backoff, same logical idempotency key

## 8) Security Rules (Must-Have)
- Tx sender key and attestor key stored in sidecar secret manager (or K8s secret)
- Keys never placed in Ray worker runtime
- Attestor key and tx sender key are separate
- Signature domain includes chain ID + contract address

## 9) Done Definition
1. One real CPS task is linked to one Arbitrum `escrow_job_id` in sidecar storage.
2. Sidecar submits `submitResult` with persisted tx hash and status `RESULT_SUBMITTED`.
3. Sidecar submits `releasePayment` and status becomes `PAYMENT_RELEASED`.
4. Reprocessing the same completion event does not create duplicate on-chain submissions.

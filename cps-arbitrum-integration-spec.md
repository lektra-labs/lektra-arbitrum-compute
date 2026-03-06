# CPS-Arbitrum Integration Card (Hackathon v1)

## 1) What We Are Building
Add Arbitrum escrow settlement to the existing Lektra compute pipeline.

Keep this unchanged:
- `Console -> CPS Backend -> CPS Worker -> Lektra Agent -> Ray -> Artifact Store`

Add this:
- `createJob` (escrow created)
- `submitResult` (result + energy attestation anchored)
- `releasePayment` (post-challenge payout)

Control-plane note:
- NATS is not implemented yet. Hackathon v1 uses direct CPS Worker -> Lektra Agent dispatch.
- Keep a transport adapter boundary so NATS can replace direct dispatch later.

## 2) Fixed Decisions (No More Debate for v1)
- Chain: Arbitrum Sepolia (`421614`)
- Currency: ETH escrow
- Attestor: single allowlisted key
- Disputes: centralized operator decision
- Existing Base payout flow: untouched
- Control transport: direct CPS-to-Agent dispatch for v1, NATS later

## 3) Single Source of Truth
Compute lifecycle stays in CPS.  
Settlement lifecycle is tracked separately as `escrow_status`.

`escrow_status` enum:
- `NONE`
- `CREATED`
- `RESULT_SUBMITTED`
- `DISPUTED`
- `PAYMENT_RELEASED`
- `REFUNDED`

Rule:
- Never let on-chain state replace CPS compute states (`PENDING...COMPLETED`).

## 4) Minimal Data Contract
Store these fields per task/execution (or in a linked settlement record):

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
- Job accepted in CPS and escrow amount known.

Do:
- Send chain tx.
- Persist `escrow_job_id` and set `escrow_status=CREATED`.

### B) `submitResult`
When:
- CPS receives final completion from Agent/Ray.

Preconditions:
- Artifact is stored.
- `result_hash` is deterministic.
- EIP-712 attestation is signed.

Do:
- Call `submitResult`.
- Persist `submit_result_tx_hash`.
- Set `escrow_status=RESULT_SUBMITTED`.

### C) `releasePayment`
When:
- User triggers release after challenge window.

Do:
- Call `releasePayment`.
- Persist `release_payment_tx_hash`.
- Set `escrow_status=PAYMENT_RELEASED`.

## 6) Payload Additions
Agent -> CPS completion payload:
- `result_hash`
- `artifact_uri`
- `energy_micro_kwh`
- `energy_window_start_ts`
- `energy_window_end_ts`

CPS Worker -> Lektra Agent dispatch payload (direct transport for v1):
- existing task/execution payload
- `escrow_job_id` (if already created)
- `input_spec_hash`

CPS -> Web3 gateway `submitResult` payload:
- `chain_id`
- `contract_address`
- `escrow_job_id`
- `result_hash`
- `input_spec_hash`
- `energy_micro_kwh`
- `window_start`
- `window_end`
- `attestation_digest`
- `attestation_signature`
- `idempotency_key`

Console task response additions:
- `escrow_status`
- `escrow_job_id`
- `result_hash`
- `attestation_digest`
- tx hashes (with explorer links)

## 7) Reliability Rules (Short Version)
- Idempotency key format: `<chain>:<contract>:<escrow_job_id>:<action>`
- One successful tx per action (`submit`, `release`)
- Duplicate completion events must become no-op after first successful `submitResult`
- Retry transient failures with backoff; keep same logical idempotency key

## 8) Security Rules (Must-Have)
- Tx sender key and attestor key in Infisical/Kubernetes Secrets
- Keys never in Ray worker pods
- Attestor key and tx key are separate
- Signature domain includes chain ID + contract address

## 9) Done Definition
1. One real job reaches `RESULT_SUBMITTED` on Arbitrum Sepolia with persisted tx hash.
2. Console shows escrow status and both digests/hashes.
3. `releasePayment` succeeds and status becomes `PAYMENT_RELEASED`.
4. Duplicate completion events do not create duplicate on-chain submissions.

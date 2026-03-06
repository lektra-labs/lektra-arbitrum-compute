# Arbitrum Hackathon Action Brief (One Page)

## 1) Project Thesis (What v1 Is and Is Not)
Build a working v1 of a solar-powered AI inference marketplace on Arbitrum where payment is escrowed on-chain, outputs are anchored on-chain by hash, and energy usage is signed off-chain and referenced on-chain.

What v1 is:
- A settlement and auditability layer for compute jobs.
- An end-to-end demo that proves job creation, result delivery, and payout flow.
- A practical trust model with bounded dispute handling.

What v1 is not:
- Trustless on-chain inference verification.
- A fully decentralized arbitration system.
- A token/DAO launch.

## 2) MVP Scope (On-Chain vs Off-Chain)
On-chain (Arbitrum Sepolia for demo):
- Escrow and payout rules.
- Job state transitions (`createJob`, `submitResult`, `releasePayment`, optional `dispute`).
- Immutable anchors: `resultHash` and `attestationDigest`.
- Optional allowlist for trusted attestor keys.

Off-chain:
- Inference execution (Ray worker).
- Artifact storage and result retrieval.
- Energy measurement and EIP-712 signature creation.
- Event watching, retries, nonce handling, and operational reliability.

Principle: keep calldata/storage small; anchor hashes on-chain and keep heavy payloads off-chain.

## 3) Must-Build Components for the Demo
Contracts:
- `InferenceEscrow.sol` on Arbitrum Sepolia.
- Embedded attestor allowlist or separate `AttestorRegistry`.

Backend:
- Event watcher for `JobCreated`.
- Dispatcher + worker runner.
- Transaction sender for `submitResult` with retry logic.

Compute:
- Ray-backed inference path (GPU if available, deterministic fallback if needed).
- Output artifact + manifest + `resultHash`.

UI:
- Create Job view: prompt/input, model profile, escrow amount, submit.
- Job Detail view: status, hash, energy, attestor, download, verify hash, release/dispute controls.

Attestation:
- EIP-712 energy attestation signed by an allowlisted attestor key.
- On-chain verification for demo simplicity or digest-first strategy with full payload off-chain.

## 4) Critical Risks and Mitigations
Risk: inference correctness is not objectively verifiable on-chain in v1.
- Mitigation: explicitly position chain as settlement/audit layer; support dispute window and freeze payout on dispute.

Risk: weak dispute adjudication undermines trust.
- Mitigation: use transparent centralized arbiter for hackathon, document as interim model, and include worker bond/slashing policy.

Risk: fee bloat from large calldata.
- Mitigation: store fixed-size hashes on-chain; keep outputs, logs, and full attestation payload off-chain.

Risk: reliability issues (dropped tx/nonces/duplicate processing).
- Mitigation: idempotency keys (`jobId`, `txHash+logIndex`), dedicated tx sender, at-least-once submission with fee bumping.

## 5) Cost and Time Constraints
Transaction footprint per job lifecycle:
- Baseline 3 calls: `createJob`, `submitResult`, `releasePayment`.
- Optional 1-2 calls for dispute/resolve.
- Treat Sepolia measurements as tuning input; keep payloads compact to control fee variability.

Compute budget:
- Single GPU instance is enough for demo workload.
- Expected hackathon run cost remains modest for 24-36 active hours.
- If Lektra hardware is used, cloud spend drops and product narrative improves.

Delivery window:
- Planning assumes a 3-day build sprint from March 6-8, 2026, with architecture frozen up front and demo script finalized on submission day.

## 6) Prioritized Execution Plan
Today (design lock + skeletons):
- Freeze data model and trust boundaries (on-chain vs off-chain).
- Finalize contract interface and deploy first version to Arbitrum Sepolia.
- Stand up storage format + event watcher + tx sender skeleton.

Day 1 (first full loop):
- Wire UI `createJob` to contract.
- Execute full backend path: event -> inference -> artifact -> hash -> `submitResult`.
- Confirm job status transitions from Created to Submitted.

Day 2 (hardening + trust signals):
- Add EIP-712 energy attestation end-to-end.
- Implement challenge window logic + payout release path.
- Stabilize retries, dedupe, and operational logs.

Submission Day (packaging + pitch):
- Run rehearsed `demo.sh` for deterministic flow.
- Capture proof points (tx hashes, hashes matched, attestation data).
- Finalize 60-second pitch and architecture slide.

## 7) Immediate Decisions to Lock (Defaults Chosen)
Worker model:
- Default: one dedicated worker per job class with queue-based dispatch (simplest reliable control).

Attestor model:
- Default: single allowlisted attestor key in v1 (managed in secure secret store), rotate post-hackathon.

Dispute policy:
- Default: centralized operator arbitration with explicit disclosure, bounded challenge window, and worker bond/slashing hooks.

## Top 5 Actions in Next 24 Hours
1. Ship and deploy `InferenceEscrow` on Arbitrum Sepolia with final event/function signatures.
2. Stand up watcher -> dispatcher -> tx sender pipeline and prove one successful `submitResult`.
3. Lock artifact manifest format and client-side hash verification flow.
4. Implement EIP-712 attestation signing path and bind it to `jobId` + `resultHash`.
5. Record one complete dry-run script (`create -> submit -> verify -> release`) and use it as demo baseline.

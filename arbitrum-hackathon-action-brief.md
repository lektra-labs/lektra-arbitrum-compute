# Arbitrum Hackathon Action Brief (Aligned to Existing Lektra Architecture)

## 1) Project Thesis (What v1 Is and Is Not)
Build the Arbitrum hackathon demo as an extension of Lektra’s existing cloud-edge platform, not a new stack. Keep current CPS -> NATS -> Lektra Agent -> Ray -> artifact pipeline, and add an Arbitrum settlement layer for escrow, result anchoring, and signed energy claims.

What v1 is:
- A blockchain settlement add-on for existing Lektra compute flows.
- A working proof that completed inference can trigger verifiable on-chain settlement.
- A practical trust model with bounded disputes for demo conditions.

What v1 is not:
- A replacement for CPS/Ray/NATS architecture.
- Trustless on-chain inference correctness verification.
- A production-grade decentralized court/arbitration system.

## 2) MVP Scope (On-Chain vs Off-Chain)
On-chain (Arbitrum Sepolia):
- Escrow and payout lifecycle: `createJob`, `submitResult`, `releasePayment`, optional `dispute`.
- Immutable anchors: `resultHash`, `attestationDigest`, and minimal job metadata.
- Allowlisted attestor verification (single key in v1).

Off-chain (reuse existing Lektra components):
- **CPS Backend + Console**: job intake and status UI.
- **CPS Worker + NATS JetStream**: routing and node assignment (existing offer/accept/commit path).
- **Lektra Agent + Ray on edge K3s nodes**: execution on current GPU fleet.
- **Existing artifact flow (GCS/presigned URLs)**: output storage and retrieval.
- **EOS/Kepler metrics path**: energy measurement source for attestation payload.
- **Web3 gateway service**: submit on-chain settlement transactions from completion events.

Principle: add the minimum blockchain delta while preserving current control and data planes.

## 3) Must-Build Components for the Demo
Net-new components:
- `InferenceEscrow.sol` (Arbitrum Sepolia) with escrow + result anchor + challenge window.
- EIP-712 attestation schema for `jobId`, `resultHash`, `energyMicroKWh`, time window, nonce.

Extensions to existing Lektra services:
- CPS task/job model: add `escrowJobId`, `resultHash`, `attestationDigest`, on-chain status fields.
- Web3 gateway: add Arbitrum provider + escrow contract client (keep existing Base payout path unchanged).
- Lektra Agent completion payload: include deterministic output hash and energy metrics reference.
- Console: add blockchain panel (escrow status, tx links, attestor, verify-hash action).

Keep unchanged for hackathon:
- NATS offer/accept/commit protocol.
- Ray workload deployment model.
- Tailscale-based network topology and cluster ops model (RKE2 cloud + K3s edge).

## 4) Critical Risks and Mitigations
Risk: integration drift between existing CPS task states and new escrow states.
- Mitigation: define explicit state mapping (`PENDING/QUEUED/OFFERED/RUNNING/COMPLETED` <-> on-chain statuses) and enforce idempotent transition handlers.

Risk: chain fragmentation (existing Web3 flow is Base-oriented, new flow is Arbitrum).
- Mitigation: isolate hackathon chain config in gateway module; avoid touching existing Base payout code path.

Risk: weak correctness guarantees for inference and energy claims.
- Mitigation: present claims accurately: integrity anchor + signed attestation, with centralized dispute resolution in v1.

Risk: secret/key exposure across distributed services.
- Mitigation: store attestor and tx-sender keys in existing secret management path (Infisical/Kubernetes Secrets), not in worker pods.

## 5) Cost and Time Constraints
Transaction footprint per lifecycle:
- Baseline 3 Arbitrum calls: `createJob`, `submitResult`, `releasePayment`.
- Optional dispute path for demo narrative.
- Keep calldata compact; pass hashes and pointers only.

Infrastructure cost:
- Reuse existing Lektra edge GPUs and cloud control plane to avoid spinning new infra.
- If overflow needed, add one temporary GPU node only.

Delivery window:
- 3-day sprint (March 6-8, 2026) assumes reuse-first integration, no platform rewrites.
- Any change that touches core NATS protocol, Fleet topology, or Ray orchestration is out of scope.

## 6) Prioritized Execution Plan
Today (design + wiring lock):
- Freeze integration contract: where escrow IDs live in CPS records and what event triggers on-chain submission.
- Deploy `InferenceEscrow` to Arbitrum Sepolia.
- Add Arbitrum client module to web3 gateway and wire a mocked `submitResult`.

Day 1 (end-to-end happy path):
- Complete one real flow through existing pipeline:
  Console/CPS job -> NATS -> Agent/Ray -> artifact hash -> gateway `submitResult`.
- Persist and surface `escrowJobId`, tx hash, and `resultHash` in CPS/Console.

Day 2 (energy + release + hardening):
- Add EIP-712 attestation from EOS/Kepler-derived metrics.
- Enable `releasePayment` path with challenge window gating.
- Add dedupe and retry logic for event-driven chain submission.

Submission Day:
- Run deterministic demo script with one successful paid job.
- Show proof points: output hash match, attestation digest, on-chain escrow release.
- Deliver concise architecture slide: “existing Lektra stack + Arbitrum settlement extension.”

## 7) Immediate Decisions to Lock (Defaults Chosen)
Worker model:
- Default: keep current CPS worker + Lektra Agent scheduling model; do not introduce a separate blockchain worker fleet.

Attestor model:
- Default: single centralized attestor service backed by EOS/Kepler metrics, key managed via existing secrets pipeline.

Dispute policy:
- Default: centralized operator adjudication with bounded challenge window and explicit disclosure in demo.

Network and chain policy:
- Default: Arbitrum Sepolia for hackathon escrow; existing Base-related payout services remain untouched unless explicitly required.

## Top 5 Actions in Next 24 Hours
1. Finalize CPS-to-escrow data contract (`escrowJobId`, `resultHash`, `attestationDigest`, tx status fields).
2. Deploy `InferenceEscrow` on Arbitrum Sepolia and integrate contract client into the web3 gateway.
3. Emit deterministic `resultHash` from Lektra Agent completion and persist it through CPS.
4. Implement first EIP-712 energy attestation using EOS/Kepler-derived metrics.
5. Execute and record one full pipeline run using existing NATS/Ray/GCS architecture plus on-chain settlement.

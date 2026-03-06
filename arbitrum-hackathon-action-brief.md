# Arbitrum Hackathon Action Brief (Public-Safe)

## 1) Project Thesis (What v1 Is and Is Not)
Build the Arbitrum hackathon demo as a sidecar extension around an existing compute platform. For hackathon v1, keep the existing backend and frontend unchanged, use current job execution behavior as-is, and add Arbitrum settlement in a separate repo/service.

What v1 is:
- A blockchain settlement add-on for existing compute flows.
- A working proof that completed inference can trigger verifiable on-chain settlement.
- A practical trust model with bounded disputes for demo conditions.

What v1 is not:
- A replacement for the existing backend/runtime architecture.
- Trustless on-chain inference correctness verification.
- A production-grade decentralized court/arbitration system.
- Any commit to core production repositories.

## 2) MVP Scope (On-Chain vs Off-Chain)
On-chain (Arbitrum Sepolia):
- Escrow and payout lifecycle: `createJob`, `submitResult`, `releasePayment`, optional `dispute`.
- Immutable anchors: `resultHash`, `attestationDigest`, and minimal job metadata.
- Allowlisted attestor verification (single key in v1).

Off-chain (reuse existing platform components):
- **Existing backend + frontend**: consumed as-is through existing APIs/UI.
- **Existing worker dispatch**: behavior remains unchanged for v1.
- **Existing inference runtime (Ray-based)**: execution on current GPU fleet.
- **Existing artifact storage flow**: output storage and retrieval.
- **Existing energy telemetry path**: measurement source for attestation payload.
- **Hackathon sidecar service (new repo)**: polls/consumes task status and submits on-chain settlement transactions.

Principle: add the minimum blockchain delta without editing existing production codebases.

## 3) Must-Build Components for the Demo
Net-new components:
- `InferenceEscrow.sol` (Arbitrum Sepolia) with escrow + result anchor + challenge window.
- EIP-712 attestation schema for `jobId`, `resultHash`, `energyMicroKWh`, time window, nonce.

Hackathon sidecar components (new repo only):
- Sidecar orchestrator that:
  - creates escrow jobs on Arbitrum,
  - tracks task/unit completion via existing read APIs,
  - computes/stores settlement metadata (`resultHash`, `attestationDigest`),
  - submits `submitResult` and `releasePayment`.
- Sidecar persistence (small DB/table) keyed by backend `task_id`/`execution_unit_id`.
- Optional minimal sidecar UI/CLI for blockchain proof display (tx hash, status, attestation digest).

Keep unchanged for hackathon:
- Existing workload deployment model.
- Existing network and cluster operations model.
- Existing task queue and dispatch mechanics (no control-plane bus rollout during hackathon).
- Existing production backend/frontend repositories (read-only during hackathon).

## 4) Critical Risks and Mitigations
Risk: integration drift between existing backend task states and new escrow states.
- Mitigation: define explicit mapping in sidecar storage (`backend state` <-> `escrow_status`) and enforce idempotent sidecar handlers.

Risk: introducing a new message bus now would increase delivery risk.
- Mitigation: keep a thin dispatch adapter interface; implement direct dispatch now and switch transport later without changing settlement logic.

Risk: chain fragmentation (existing payment flows use another chain, new flow uses Arbitrum).
- Mitigation: isolate Arbitrum logic in sidecar; avoid touching existing payment code paths.

Risk: weak correctness guarantees for inference and energy claims.
- Mitigation: present claims accurately: integrity anchor + signed attestation, with centralized dispute resolution in v1.

Risk: secret/key exposure across distributed services.
- Mitigation: store attestor and tx-sender keys in a dedicated secret manager, not in worker pods.

## 5) Cost and Time Constraints
Transaction footprint per lifecycle:
- Baseline 3 Arbitrum calls: `createJob`, `submitResult`, `releasePayment`.
- Optional dispute path for demo narrative.
- Keep calldata compact; pass hashes and pointers only.

Infrastructure cost:
- Reuse existing GPUs and control plane to avoid spinning new infra.
- If overflow needed, add one temporary GPU node only.

Delivery window:
- 3-day sprint (March 6-8, 2026) assumes sidecar-only integration and no platform rewrites.
- Message bus migration is out of scope for hackathon v1; major topology/runtime rewrites are also out of scope.

## 6) Prioritized Execution Plan
Today (design + wiring lock):
- Freeze sidecar mapping contract: how `task_id/execution_unit_id` map to `escrow_job_id` in sidecar storage.
- Deploy `InferenceEscrow` to Arbitrum Sepolia.
- Build sidecar Arbitrum client and wire mocked `submitResult`.

Day 1 (end-to-end happy path):
- Complete one real flow through existing pipeline:
  UI/backend job -> direct dispatch -> runtime -> sidecar -> `submitResult`.
- Persist and surface `escrowJobId`, tx hash, and `resultHash` in sidecar dashboard/CLI.

Day 2 (energy + release + hardening):
- Add EIP-712 attestation from available energy telemetry.
- Enable `releasePayment` path with challenge window gating.
- Add dedupe and retry logic for event-driven chain submission.

Submission Day:
- Run deterministic demo script with one successful paid job.
- Show proof points: output hash match, attestation digest, on-chain escrow release.
- Deliver concise architecture slide: “existing stack + Arbitrum settlement extension.”

## 7) Immediate Decisions to Lock (Defaults Chosen)
Worker model:
- Default: keep current worker scheduling model; sidecar handles blockchain actions.

Attestor model:
- Default: single centralized attestor service backed by available energy telemetry, key managed via a secure secret pipeline.

Dispute policy:
- Default: centralized operator adjudication with bounded challenge window and explicit disclosure in demo.

Network and chain policy:
- Default: Arbitrum Sepolia for hackathon escrow; existing payment flows remain untouched unless explicitly required.

Control-plane policy:
- Default: direct dispatch for v1 hackathon; message-bus migration planned post-hackathon.

Repo boundary policy:
- Default: no commits to core production repos; all hackathon code lives in a separate repo.

## Top 5 Actions in Next 24 Hours
1. Finalize sidecar mapping contract (`task_id`, `execution_unit_id`, `escrowJobId`, `resultHash`, `attestationDigest`, tx status fields).
2. Deploy `InferenceEscrow` on Arbitrum Sepolia and integrate contract client into sidecar.
3. Pull deterministic completion/result artifacts from existing backend APIs and persist settlement state in sidecar.
4. Implement first EIP-712 energy attestation using available energy telemetry.
5. Execute and record one full pipeline run using existing runtime/storage plus sidecar on-chain settlement.

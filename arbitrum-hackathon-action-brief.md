# Arbitrum Hackathon Action Brief (Aligned to Existing Lektra Architecture)

## 1) Project Thesis (What v1 Is and Is Not)
Build the Arbitrum hackathon demo as a sidecar extension around Lektra’s existing cloud-edge platform. For hackathon v1, keep CPS and Console unchanged, use existing CPS -> Lektra Agent -> Ray -> artifact behavior as-is, and add Arbitrum settlement in a separate repo/service.

What v1 is:
- A blockchain settlement add-on for existing Lektra compute flows.
- A working proof that completed inference can trigger verifiable on-chain settlement.
- A practical trust model with bounded disputes for demo conditions.

What v1 is not:
- A replacement for CPS/Ray architecture.
- Trustless on-chain inference correctness verification.
- A production-grade decentralized court/arbitration system.
- Any commit to `compute-platform-services` or `compute-platform-console`.

## 2) MVP Scope (On-Chain vs Off-Chain)
On-chain (Arbitrum Sepolia):
- Escrow and payout lifecycle: `createJob`, `submitResult`, `releasePayment`, optional `dispute`.
- Immutable anchors: `resultHash`, `attestationDigest`, and minimal job metadata.
- Allowlisted attestor verification (single key in v1).

Off-chain (reuse existing Lektra components):
- **CPS Backend + Console**: consumed as-is through existing APIs/UI.
- **CPS Worker + direct agent dispatch**: existing behavior remains unchanged for v1.
- **Lektra Agent + Ray on edge K3s nodes**: execution on current GPU fleet.
- **Existing artifact flow (GCS/presigned URLs)**: output storage and retrieval.
- **EOS/Kepler metrics path**: energy measurement source for attestation payload.
- **Hackathon sidecar service (new repo)**: polls/consumes CPS task status and submits on-chain settlement transactions.

Principle: add the minimum blockchain delta without editing existing CPS/Console codebases.

## 3) Must-Build Components for the Demo
Net-new components:
- `InferenceEscrow.sol` (Arbitrum Sepolia) with escrow + result anchor + challenge window.
- EIP-712 attestation schema for `jobId`, `resultHash`, `energyMicroKWh`, time window, nonce.

Hackathon sidecar components (new repo only):
- Sidecar orchestrator that:
  - creates escrow jobs on Arbitrum,
  - tracks CPS task/unit completion via existing read APIs,
  - computes/stores settlement metadata (`resultHash`, `attestationDigest`),
  - submits `submitResult` and `releasePayment`.
- Sidecar persistence (small DB/table) keyed by CPS `task_id`/`execution_unit_id`.
- Optional minimal sidecar UI/CLI for blockchain proof display (tx hash, status, attestation digest).

Keep unchanged for hackathon:
- Ray workload deployment model.
- Tailscale-based network topology and cluster ops model (RKE2 cloud + K3s edge).
- Existing CPS task queue and direct dispatch mechanics (no new control-plane bus rollout during hackathon).
- Existing CPS and Console repositories (read-only during hackathon).

## 4) Critical Risks and Mitigations
Risk: integration drift between existing CPS task states and new escrow states.
- Mitigation: define explicit mapping in sidecar storage (`CPS state` <-> `escrow_status`) and enforce idempotent sidecar handlers.

Risk: introducing NATS now would increase delivery risk.
- Mitigation: keep a thin dispatch adapter interface in CPS; implement direct dispatch now and switch transport to NATS later without changing settlement logic.

Risk: chain fragmentation (existing Web3 flow is Base-oriented, new flow is Arbitrum).
- Mitigation: isolate Arbitrum logic in sidecar; avoid touching existing Base payout code path.

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
- 3-day sprint (March 6-8, 2026) assumes sidecar-only integration and no platform rewrites.
- NATS implementation itself is out of scope for hackathon v1; Fleet topology and Ray orchestration rewrites are also out of scope.

## 6) Prioritized Execution Plan
Today (design + wiring lock):
- Freeze sidecar mapping contract: how `task_id/execution_unit_id` map to `escrow_job_id` in sidecar storage.
- Deploy `InferenceEscrow` to Arbitrum Sepolia.
- Build sidecar Arbitrum client and wire mocked `submitResult`.

Day 1 (end-to-end happy path):
- Complete one real flow through existing pipeline:
  Console/CPS job -> direct dispatch -> Agent/Ray -> sidecar -> `submitResult`.
- Persist and surface `escrowJobId`, tx hash, and `resultHash` in sidecar dashboard/CLI.

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
- Default: keep current CPS worker + Lektra Agent scheduling model; sidecar handles blockchain actions.

Attestor model:
- Default: single centralized attestor service backed by EOS/Kepler metrics, key managed via existing secrets pipeline.

Dispute policy:
- Default: centralized operator adjudication with bounded challenge window and explicit disclosure in demo.

Network and chain policy:
- Default: Arbitrum Sepolia for hackathon escrow; existing Base-related payout services remain untouched unless explicitly required.

Control-plane policy:
- Default: direct CPS-to-Agent dispatch for v1 hackathon; NATS migration planned post-hackathon.

Repo boundary policy:
- Default: no commits to `compute-platform-services` and `compute-platform-console`; all hackathon code lives in a separate repo.

## Top 5 Actions in Next 24 Hours
1. Finalize sidecar mapping contract (`task_id`, `execution_unit_id`, `escrowJobId`, `resultHash`, `attestationDigest`, tx status fields).
2. Deploy `InferenceEscrow` on Arbitrum Sepolia and integrate contract client into sidecar.
3. Pull deterministic completion/result artifacts from CPS APIs and persist settlement state in sidecar.
4. Implement first EIP-712 energy attestation using EOS/Kepler-derived metrics.
5. Execute and record one full pipeline run using existing CPS/Ray/GCS plus sidecar on-chain settlement.

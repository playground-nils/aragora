# Next Steps (Canonical)

Last updated: 2026-03-18

This is the single source of truth for short-horizon execution priorities.
`docs/CANONICAL_GOALS.md` defines what Aragora is and why.
`docs/plans/ARAGORA_EVOLUTION_ROADMAP.md` defines the long-range architecture and moat.
`docs/FEATURE_GAP_LIST.md` is the current capability/backlog truth.
`ACTIVE_EXECUTION_ISSUES.md` links this execution order to the live GitHub issue backlog.
This file defines execution order.

## Current Reality

- The full vision remains the goal; the near-term requirement is sequencing, not scope reduction.
- The moat is the receipt-gated decision kernel: prompt/spec/debate/consensus/cryptographic receipt/policy-gated action.
- GitHub issues now carry active execution status, owners, and acceptance criteria. Docs should summarize context and order, not act as the only operational backlog.
- Truthfulness and backlog canonicalization are complete on `main` through [#809](https://github.com/synaptent/aragora/issues/809), and the first Decision Integrity Kernel bridge tranche [#810](https://github.com/synaptent/aragora/issues/810) is also complete.
- The core kernel base is now on `main` through [#811](https://github.com/synaptent/aragora/issues/811) and [#812](https://github.com/synaptent/aragora/issues/812); provider-routing integration has also landed in part on `main`, while the remaining runtime/accountability scale-out continues in [#813](https://github.com/synaptent/aragora/issues/813) through [#816](https://github.com/synaptent/aragora/issues/816).
- Recent swarm-control-plane hardening on `main` closed file-scope ownership ([#840](https://github.com/synaptent/aragora/issues/840)) and PR supersession ([#841](https://github.com/synaptent/aragora/issues/841)), but the task claim protocol, universal run receipts, and integrator view are still open across [#836](https://github.com/synaptent/aragora/issues/836), [#837](https://github.com/synaptent/aragora/issues/837), [#842](https://github.com/synaptent/aragora/issues/842), and [#843](https://github.com/synaptent/aragora/issues/843).
- Long unattended self-improvement is now an explicit product/engineering goal. The assessment compiler ([#1037](https://github.com/synaptent/aragora/issues/1037)) and pause-refresh shift contract ([#1038](https://github.com/synaptent/aragora/issues/1038)) are on `main`; the remaining gap is making task ownership, receipts, and operator visibility truthful enough to dogfood the loop via [#990](https://github.com/synaptent/aragora/issues/990).
- Surface area should be productized sequentially, not hidden or allowed to drift.
- **Ralph autonomous loop hardened (March 18):** LLM-powered scope validation and blocker classification shipped (PR #1020). File-scope propagation fix (#884), vague-goal LLM expansion (#888), and observability dashboard (#1007) all landed. Ralph V14 benchmark validated autonomous spec→PR→merge.
- **Swarm control plane work next:** #837 (task queue + claim protocol), #842 (universal run receipts), and #843 (integrator view) are the natural continuation of the Ralph hardening track.
- **Epistemic hygiene goals added (March 18):** Anti-sycophancy detection, calibration tracking, adversarial protocol red-teaming, and epistemic hygiene debate mode added to CANONICAL_GOALS.md (P4 #39-43) and Evolution Roadmap (Phase 2D). Derived from multi-model analysis sessions.

## Execution Order

### 1) Truthfulness And Backlog Canonicalization
- Tracking: [#804](https://github.com/synaptent/aragora/issues/804), [#807](https://github.com/synaptent/aragora/issues/807), [#808](https://github.com/synaptent/aragora/issues/808), [#809](https://github.com/synaptent/aragora/issues/809)
- Goal: `main` and current-source docs should stay truthful, and the active backlog should live in GitHub instead of only in Markdown.
- Current status: complete on `main`; keep the gates blocking and maintain the issue map/doc linkage.
- Acceptance:
  - Launch/readiness claims match what works on `main`.
  - Self-host/readiness docs and gates are evidence-backed.
  - Current execution lanes are tracked in GitHub with owners, priorities, and acceptance criteria.
  - Canonical planning docs link to the issue map instead of carrying operational status alone.

### 2) Decision Integrity Kernel Unification
- Tracking: [#805](https://github.com/synaptent/aragora/issues/805), [#810](https://github.com/synaptent/aragora/issues/810), [#811](https://github.com/synaptent/aragora/issues/811), [#812](https://github.com/synaptent/aragora/issues/812), [#813](https://github.com/synaptent/aragora/issues/813), [#814](https://github.com/synaptent/aragora/issues/814), [#815](https://github.com/synaptent/aragora/issues/815), [#816](https://github.com/synaptent/aragora/issues/816)
- Goal: unify `prompt -> specification -> adversarial debate -> consensus/dissent -> cryptographic decision receipt -> policy gate -> execution` as one canonical runtime.
- Current tranche: the kernel base landed through [#811](https://github.com/synaptent/aragora/issues/811) and [#812](https://github.com/synaptent/aragora/issues/812); the remaining scale-out is [#813](https://github.com/synaptent/aragora/issues/813) through [#816](https://github.com/synaptent/aragora/issues/816).
- Why now:
  - This is the architectural center of Aragora's differentiation.
  - Provider routing, OpenClaw, 10+ agent scale, and ERC-8004 only matter if they plug into the same receipt-gated kernel.

### 3) Developer Swarm Control Plane And Autonomous Self-Improvement Cadence
- Tracking: [#836](https://github.com/synaptent/aragora/issues/836), [#837](https://github.com/synaptent/aragora/issues/837), [#840](https://github.com/synaptent/aragora/issues/840), [#841](https://github.com/synaptent/aragora/issues/841), [#842](https://github.com/synaptent/aragora/issues/842), [#843](https://github.com/synaptent/aragora/issues/843), [#871](https://github.com/synaptent/aragora/issues/871), [#989](https://github.com/synaptent/aragora/issues/989), [#990](https://github.com/synaptent/aragora/issues/990), [#1036](https://github.com/synaptent/aragora/issues/1036), [#1037](https://github.com/synaptent/aragora/issues/1037), [#1038](https://github.com/synaptent/aragora/issues/1038)
- Goal: make long unattended repo improvement truthful by keeping lane ownership, receipts, worktree hygiene, assessment, and pause-refresh cadence canonical.
- Why now:
  - Recent high-churn sessions proved Aragora can generate and land useful autonomous work, but they also exposed drift, duplicate lanes, stale assumptions, and repo hygiene gaps.
  - The codebase now contains the assessment compiler and shift controller; what remains is the task/receipt/operator control plane that makes long runs defensible.

### 4) Sequential Surface Productization
- Tracking: [#806](https://github.com/synaptent/aragora/issues/806), [#817](https://github.com/synaptent/aragora/issues/817), [#818](https://github.com/synaptent/aragora/issues/818), [#819](https://github.com/synaptent/aragora/issues/819), [#820](https://github.com/synaptent/aragora/issues/820)
- Goal: productize every exposed surface in waves, starting from the inbox trust wedge and public proof surfaces.
- Rules:
  - The wedge proves the kernel; it does not replace the whole vision.
  - Keep partial surfaces visible, but label and harden them honestly.
  - Prefer one surface wave at a time over broad parallel productization.

### 5) Assurance And GTM Closeout (Kept Warm, Not Main Product Lane)
- Tracking: [#273](https://github.com/synaptent/aragora/issues/273), [#274](https://github.com/synaptent/aragora/issues/274), [#509](https://github.com/synaptent/aragora/issues/509)
- Goal: keep enterprise assurance truthfulness real without turning pentest/GTM work into the primary execution lane before the core kernel is unified.
- Acceptance:
  - Open assurance work remains visible, owned, and sequenced.
  - Docs do not overclaim GA or launch readiness while these items remain open.

### Operational Incidents (Interrupt-Driven)
- Tracking: [#829](https://github.com/synaptent/aragora/issues/829) and any future incident tickets
- Rule: incidents can preempt the planned order, but they do not replace the canonical program; once mitigated, execution returns to the issue order above.

## Operating Rules
- GitHub issues are the live execution backlog; docs summarize context, order, and capability posture.
- `ACTIVE_EXECUTION_ISSUES.md` must stay aligned with the current issue set.
- `docs/FEATURE_GAP_LIST.md` is the capability/backlog truth for planned and partial features; execution status lives in GitHub.
- `ROADMAP.md` and other summary docs must reconcile to `NEXT_STEPS_CANONICAL.md`, `docs/FEATURE_GAP_LIST.md`, and the issue map.
- No document should claim "only one blocker remains" unless `main` CI/CD and deployment signals support that claim.
- Productize exposed surface area sequentially; do not broaden active implementation lanes faster than the kernel can support.
- If priorities change, update the GitHub issues first, then update this file and the linked summaries.

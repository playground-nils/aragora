# Aragora Founder Proof-Points Library

Last updated: 2026-03-25

This is the founder-facing source of truth for what Aragora can claim today.
The rule is simple: lead with the smallest set of claims that can be repeated on
current `main`, tied to durable artifacts, with an explicit boundary when the
proof is CLI-only, benchmark-only, or still awaiting live dogfood.

## Standard For A Claim To Be Founder-Safe

A claim is founder-safe only if all of the following are true:

- it can be rerun on current `main` without narrative hand-waving
- it produces a durable artifact a prospect can inspect
- the artifact explains why the system advanced or stopped
- the boundary is explicit when the proof is not yet a live external workflow

If one of those is missing, downgrade the statement to "wired", "benchmark
proof", or "not yet for founder use."

## Core Claims To Lead With

### 1. Live decision review is repeatable on current `main`

Use this claim:

> Aragora can run a live multi-agent decision review and produce a stored
> receipt on current `main`.

Minimum proof packet required:

- one live run on current `main`
- resulting receipt ID or share link
- proof that the receipt is visible on operator surfaces
- if you mention repeatability or speed, the March 24, 2026 baseline:
  5/5 consecutive founder-loop runs, 35-62 seconds, all 7 acceptance items pass

Current repo anchors:

- `ROADMAP.md` -- live founder loop proven repeatable, receipt-store visibility
- `docs/FEATURE_GAP_LIST.md` -- repeatability baseline and acceptance summary
- `docs/status/DESIGN_PARTNER_PROGRAM.md` -- default partner surface and live path

Do not say:

- "every onboarding path is live-proven"
- "provider routing quality is already live-proven"
- "KM read/write visibility is already proven in live partner runs"

### 2. Aragora can show why the system advanced or stopped

Use this claim:

> Aragora does not just return an answer; it returns a receipt that shows the
> consensus, dissent, provenance, and next human action.

Minimum proof packet required:

- one exported or stored receipt artifact
- one verification surface, such as `aragora receipt verify` or a receipt API
- evidence that the receipt records outcome shape: approved, blocked, or needs human
- one example where dissent, provenance, or blocker handling is visible

Current repo anchors:

- `docs/integration/decision-receipts.md` -- receipt model and storage/verification path
- `aragora-debate/src/aragora_debate/receipt.py` -- receipt construction and integrity hashing
- `README.md` -- product path from debate to receipt

Do not say:

- "the system is always correct"
- "the receipt replaces human judgment"
- "cryptographic receipt" unless you can show the actual receipt artifact or verification step

### 3. Aragora can gate bounded actions on persisted receipts and explicit policy

Use this claim:

> Aragora keeps automation bounded: receipt first, then explicit approval policy.

Minimum proof packet required:

- one action path with a narrow allowed-action set
- proof that a receipt is persisted before the action gate opens
- one policy surface, such as CLI approval mode, dry-run, or merge gate behavior
- if using the inbox wedge, show the current CLI path:
  `aragora triage auth` and `aragora triage run --dry-run`

Current repo anchors:

- `ROADMAP.md` -- inbox trust wedge CLI ready on March 24, 2026
- `docs/status/DESIGN_PARTNER_PROGRAM.md` -- receipt-before-action path and allowed inbox actions
- `tests/trust_wedge/test_attestation.py` -- receipt persisted before execution gate runs

Do not say:

- "broad autonomous actioning is proven"
- "the inbox wedge is already proven on a live customer inbox"
- "no human approval is needed"

## Reserve Claims, Not Default Openers

These are real, but they should stay secondary until the prospect asks for them
or the matching artifact pack is already in hand.

### EU AI Act artifact generation

Safe claim:

> Aragora can generate EU AI Act artifact bundles from real decision receipts.

Proof required:

- compliance export generated from a real receipt
- bundle artifact or screenshots
- explicit boundary that this is artifact generation, not a certification claim

Current anchors:

- `ROADMAP.md` -- compliance bundle verified end-to-end with real quickstart receipts
- `docs/compliance/COMPLIANCE_BUNDLE.md`
- `docs/compliance/EU_AI_ACT_CUSTOMER_PLAYBOOK.md`

### Ralph autonomous benchmark

Safe claim:

> Aragora has benchmark evidence that it can complete bounded repo work under
> explicit merge policy.

Proof required:

- benchmark artifact or result log
- exact policy boundary for the run
- resulting PR or merge metadata

Current anchors:

- `docs/FEATURE_GAP_LIST.md` -- Ralph V14 benchmark summary
- `docs/status/DESIGN_PARTNER_PROGRAM.md` -- how to pitch the benchmark truthfully

Boundary:

Use this as bounded autonomy evidence, not as proof of unrestricted external
autonomy.

## Facts That Support Claims But Should Not Be The Claim

These are supporting facts. They should appear after the proof point, not as the
opening line:

- 43 agent types
- 42 adapter counts
- SDK namespace counts
- broad connector breadth
- generic "multi-model" or "orchestration" language
- prompt-to-spec timing
- Prover-Estimator and truth-ratio internals

They help explain the system. They do not prove the wedge by themselves.

## Claims To Avoid Until New Proof Exists

- "Smart provider routing is live-proven in production workflows."
- "Knowledge Mound read/write is visibly proven in the live loop."
- "10+ agent coordination is proven at enterprise operating scale."
- "Aragora is already pentested / SOC 2 audited."
- "Aragora delivers broad autonomous execution without human gates."

## Founder Talk Track

Use this sequence:

1. We can run a live review and produce a stored receipt.
2. The receipt shows why the system advanced or stopped.
3. We can put bounded actions behind that receipt and an explicit approval policy.

Everything else is support, extension, or future proof.

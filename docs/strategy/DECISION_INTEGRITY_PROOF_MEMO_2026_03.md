# Aragora Decision-Integrity Proof Memo — March 2026

## Purpose

This memo defines the strongest defensible claim Aragora can make today against a
single-model workflow, and the places where the proof is still incomplete.

The goal is claim discipline. Aragora should only claim superiority where the
repo contains evidence, repeatable live runs, or clearly structural advantages.

## Core Thesis

Aragora does **not** yet prove that a multi-model workflow is always more
correct than the best single-model workflow.

Aragora **does** already prove a stronger decision process on consequential
work:

- disagreement is surfaced instead of hidden
- receipts preserve who said what, why the system advanced, and why it stopped
- bounded execution can fail closed instead of bluffing past uncertainty
- review and action gates can require more than one model's unchecked judgment

That is the current decision-integrity wedge.

## What Aragora Proves Better Than A Single-Model Workflow

### 1. Better auditability and replayability

Single-model workflows usually leave chat logs and tool traces. Aragora produces
decision receipts with consensus state, dissent, provenance, and integrity
metadata, and those receipts are now visible on API and dashboard surfaces.

What is materially proven on `main`:

- receipt generation and storage are part of the live product loop
- quickstart receipts persist to the receipt store and are visible via
  API/dashboard/share-link
- the live founder loop passed 5/5 consecutive runs on March 24, 2026, with
  receipts visible on product surfaces

This is stronger than "the model said X." It gives operators an artifact they
can inspect, export, and compare across runs.

### 2. Better visibility into disagreement and uncertainty

A single-model workflow collapses proposal, critique, and judgment into one
voice. Aragora separates those steps and records dissent as a first-class output.

What is defensible today:

- the debate engine is explicitly adversarial, not only cooperative
- dissent trails and unresolved tensions can survive into the receipt
- hollow-consensus detection, cross-verification, and truth-ratio scoring are
  wired into the debate path
- debate output quality has internal benchmark support: the March 5 diverse
  10-domain benchmark passed 100% with 0.938 average composite quality

External literature strengthens the direction of the claim. The
`aragora-debate` package cites multi-agent debate work reporting a `+13.8`
percentage-point accuracy gain over single-model baselines. That supports the
mechanism, but it is not yet the product's own live partner proof.

### 3. Better truthful stopping behavior on bounded execution

Single-model workflows often optimize for producing an answer. Aragora is built
to preserve blocker truth and stop explicitly when evidence is insufficient.

What is already proven:

- the live founder loop is repeatable and truthful enough to pass 5/5 runs
- bounded execution paths preserve receipts and explicit blocker handling
- the inbox trust wedge is receipt-before-action by design
- quickstart behavior has fail-closed handling instead of silently continuing on
  broken setup

This is the most practical current proof: Aragora behaves more like a governed
control plane than a persuasive assistant.

### 4. Better resilience to one model's blind spot or compromise

A single model can be wrong, sycophantic, injected, or compromised with no
internal challenge. Aragora's architecture gives one model's output multiple
opportunities to be challenged by heterogeneous peers before action is allowed.

The structural defense is real:

- provider and model-family diversity are part of the execution-gate logic
- consensus proof plus dissent recording make unilateral model action harder
- security docs already frame this as protection against prompt injection,
  hollow consensus, and some refusal-ablation scenarios

This is a structural advantage over a single-model workflow even where the live
product proof is still partial.

## What Aragora Only Partially Proves Today

### 1. Quality improvement over the strongest single-model baseline

This is the biggest remaining commercial proof gap.

Aragora has:

- internal debate-quality benchmarks
- external literature supporting adversarial debate
- real dogfood proof that the founder loop is repeatable

Aragora does **not** yet have:

- a published bug/finding catch-rate delta versus a strong single-model review
  workflow on real engineering tasks
- a measured decision-quality delta on partner inbox, spec-review, or merge-gate
  workflows

The repo's own competitive positioning document already names this missing proof:
measure single-model versus multi-model quality deltas on real work and publish
case studies with findings and receipts.

### 2. Full end-to-end proof across all user-facing surfaces

The repo now proves several important slices, but not yet a continuous external
user journey.

Still explicitly open in the feature gap list:

- smart provider routing is shipped, but live proof is pending
- one complete working user journey has mocked proof but still needs repeatable
  live proof
- Knowledge Mound read/write enrichment is shipped, but live visibility and
  trustworthiness in the founder loop remain open
- developer onboarding is improved, but the sub-10-minute live proof is still
  required

So the right claim is "the proof surfaces are real and getting truthful," not
"the entire platform is already proven end to end for external operators."

### 3. Security completeness for high-impact decisions

Aragora proves that multi-model governance is harder to subvert than a
single-model workflow. It does **not** yet prove that the ensemble is secure
against every high-impact failure mode.

The threat model is explicit about remaining gaps:

- coordinated multi-provider compromise is not addressed with a hard proof
- correlated failure across all models is still possible
- there is no mandatory external verification gate for high-impact decisions
- runtime model attestation remains incomplete for endpoint substitution or
  refusal-ablation scenarios
- receipt-signing key custody is not enforced as an execution prerequisite

For high-impact decisions, Aragora currently proves better process integrity,
not guaranteed truth.

## What Aragora Should Claim Right Now

Aragora should say:

> We prove a better governed AI decision process than a single-model workflow:
> multi-model challenge, explicit dissent, signed receipts, and truthful stopping
> behavior on bounded execution.

Aragora should **not** yet say:

- multi-model is always more correct than single-model
- routing is fully proven in live production conditions
- every user-facing path is already partner-ready
- consensus alone eliminates correlated failure

## The Remaining Proof Agenda

### Proofs to earn next

1. Publish measured single-model vs Aragora catch-rate deltas on real review
   tasks.
2. Prove one repeatable external user journey with routing, KM, receipt, and UI
   continuity visible end to end.
3. Turn the inbox and repo-review wedges into partner case studies with before /
   after operator outcomes.
4. Add stricter high-impact policy gates: external verification, stronger model
   attestation, and key-custody enforcement.

### Metrics that matter

- bug and finding catch-rate delta vs strong single-model baseline
- override rate after receipt review
- blocked-for-good-reason rate vs false-positive blocker rate
- receipt generation coverage on consequential actions
- partner workflow repetition count with stable outcomes
- outcome-labeled calibration samples by domain

## Bottom Line

Aragora's current proof is strongest on **decision integrity**, not universal
decision correctness.

Today Aragora can credibly prove that consequential AI-assisted work is more
auditable, more challengeable, and more truthfully gated than in a single-model
workflow.

The missing proof is the hardest and most valuable one: quantified real-world
quality lift over the strongest single-model alternative, plus stronger defenses
against correlated ensemble failure on high-impact decisions.

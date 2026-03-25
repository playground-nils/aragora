# PMF Evidence Ladder

**Date:** March 25, 2026
**Purpose:** Sequence Aragora's go-to-market motion by proof, not optimism.

This document defines the evidence ladder from internal dogfood to repeatable
design partner proof to paid expansion. Each rung exists to answer a different
question. The next rung should stay locked until the current one has receipt-
backed evidence.

## Current Position

As of March 25, 2026, Aragora has already proven the founder loop:

- 5/5 consecutive live founder-loop runs
- 35-62s runtime range
- receipts visible on API/dashboard/share-link surfaces
- `aragora spec` working end-to-end
- inbox trust wedge CLI wired, but not yet proven on a real internal inbox

That is enough to justify internal dogfood. It is not yet enough to claim
repeatable external proof.

## The Ladder

| Rung | Core question | Evidence that unlocks the next rung | What becomes allowed |
|------|---------------|-------------------------------------|----------------------|
| 1. Internal dogfood | Can Aragora run consequential internal work on two real workflows without founder magic? | Founder loop and inbox wedge both have exact commands, receipts, and visible result surfaces. The inbox wedge completes 10 consecutive live runs over at least 5 business days on a real internal inbox. At least 2 internal operators other than the primary builder can run the workflow from the written runbook and reach first useful result in 10 minutes or less. Over a 2-week window, at least 70% of internal runs end in an accepted action, and every remaining run stops truthfully with a blocker class and next action. Zero false-success incidents. | Start a bounded design partner program, use a repeatable live demo, and package proof assets around the actual workflow. |
| 2. Repeatable design partner proof | Does the wedge transfer to external teams and create measurable value without founder-operated rescue? | 3-5 design partners each complete at least 2 real tasks with receipt bundles. At least 2 partners repeat weekly usage for 4 consecutive weeks without the founder driving the keyboard. Each partner starts with a pre-agreed KPI, and at least 2 partners show a measurable delta of 20% or better on cycle time, finding catch-rate, or manual coordination load. At least 1 publishable case study or 2 private reference packs exist. At least 2 partners ask for a paid next step. | Sell a paid pilot in the same wedge, standardize onboarding and proof-pack collateral, and treat design partner proof as the basis for the first commercial motion. |
| 3. Paid expansion | Is there a repeatable paid land-and-expand motion in one wedge? | At least 2 design partners convert to paid. At least 1 additional paid logo closes in the same wedge from the same proof pack. At least 1 paid customer expands to a second workflow or team within 60 days. The paid cohort shows 8 consecutive weeks of active, receipt-backed usage without founder-operated rescue on the normal path. Procurement objections are stable enough to fit a standard security/compliance checklist. | Pull forward pentest and audit work, invest in procurement packaging, and expand into adjacent teams or workflows from a proven wedge. |

## Evidence Categories

Every rung should be judged across the same four categories:

| Category | What it means | Minimum bar |
|----------|---------------|-------------|
| Repeatability | The same workflow works more than once under realistic conditions | Consecutive live runs with receipts and visible result surfaces |
| Transferability | Someone other than the builder can get the same result | Internal operators first, then partner champions |
| Value | The workflow produces an accepted result, not just a demo | Pre-agreed KPI delta or accepted action rate |
| Truthfulness | The system either succeeds or stops with a direct reason | Zero false-success incidents and explicit blocker capture |

If a candidate proof artifact is missing one of these categories, it does not
unlock the next rung.

## What Does Not Count As Unlock Evidence

The following are supportive, but none of them substitute for rung-closing
proof:

- a single heroic founder demo
- generic waitlist demand or positive calls
- raw receipt counts without repeated useful outcomes
- more provider breadth, more agents, or more orchestration complexity
- pentest, SOC 2, or EU AI Act packaging before paid expansion proof
- unpublished anecdotes without command transcripts, receipts, or KPIs

## Required Proof Artifacts Per Rung

Each rung should leave behind a compact proof pack:

- exact command or workflow transcript
- receipt bundle and visible product-surface evidence
- KPI definition used for that rung
- blocker taxonomy with linked fixes or stop reasons
- short narrative: what changed, what still fails, what the next rung needs

Without this pack, the rung is not auditable and should be treated as
incomplete.

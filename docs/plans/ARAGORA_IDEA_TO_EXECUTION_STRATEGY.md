# Aragora Idea-to-Execution Strategy

*Converted from `Aragora Idea-to-Execution Strategy.docx` and updated for the March 22, 2026 repo state.*

## Executive Summary

Aragora is evolving from a multi-agent debate engine into a local-first idea-to-execution system: a person starts with rough ideas, Aragora turns them into goals and executable specs, and heterogeneous agent lanes carry the work through review, receipts, PR creation, and merge gates.

The strategic thesis from the original document still holds:

- the four-stage idea-to-execution pipeline is differentiated
- the codebase already contains most of the backend substrate
- the missing moat layer is a unified interactive canvas and stage-transition UX
- heterogeneous model diversity plus audit receipts remain the product advantage

What changed during the March 19-22 tranche/live-proof work is the backend maturity and the product wedge. The repo is no longer only proving a single Ralph lane. It now has a real tranche queue, design review, watch/review/integrate flow, authoritative integrator views, KM-backed debate recall, a truthful public proof surface, and a growing body of evidence about what unattended execution can and cannot yet do truthfully.

## Five Strategic Goals

### 1. Reliable Spec-to-Merge Engine

Make Aragora a real autonomous engineering loop, not a demo. The loop is:

`plan -> dispatch -> implement -> review -> classify blockers -> repair -> PR creation -> merge gate`

Every handoff in that loop must behave truthfully under unattended execution.

### 2. Idea-to-Execution for Non-Engineers

Turn vague human intent into executable plans without forcing the user to become a project manager or spec writer.

### 3. Unified DAG Visual Language

Ideas, goals, tasks, and agent orchestration are all DAGs with provenance. They should share one visual language and one canvas instead of fragmenting across tools.

### 4. Heterogeneous Model Diversity as Product Advantage

Claude plans. Codex implements. Cross-model review catches real issues. Aragora's moat is not "many models talking," but routing the right model strengths to the right stage and preserving the dissent trail.

### 5. Benchmarked Evidence, Not Anecdotes

Each autonomy cycle should end with an explicit contract: what the system can do unattended, where it truthfully stops, and what evidence supports that claim.

## The Four-Stage Pipeline

| Stage | Name | Input | Output | AI Role |
|---|---|---|---|---|
| 1 | Ideas | Freeform notes, thoughts, sketches | Structured idea graph | Cluster, link, surface gaps |
| 2 | Goals | Idea graph plus clarifying Q&A | Goal and principle DAG | Synthesize goals, extract constraints, score confidence |
| 3 | Actions | Goal DAG plus domain context | Task and spec DAG | Decompose goals, assign effort, generate specs |
| 4 | Orchestration | Task DAG plus agent pool | Executed, reviewed, merged code with receipts | Assign agents, run debate review, coordinate repair |

### Why DAGs, Not Trees

DAGs model the real structure of work better than trees. One idea can support multiple goals, one goal can influence multiple tasks, and one task can depend on several upstream conditions.

### Provenance and Stage Gates

Every stage transition should preserve provenance. Aragora's debate receipts and pipeline provenance model already establish the foundation. The missing piece is a high-quality interface that makes those transitions legible and editable.

## Market Landscape

The original research remains directionally correct:

- Stage 1 idea organization is crowded
- Stage 2 goal derivation is still the emptiest part of the market
- Stage 3 project management is mature but mostly proprietary
- Stage 4 agent orchestration is rich in open source, but starts too late in the pipeline

No serious competitor spans all four stages with one visual abstraction, auditable stage transitions, heterogeneous review, and provenance from idea to merged artifact.

## What Is Genuinely Novel

The core differentiators are still the same six gaps identified in the source document:

1. AI-driven goal derivation from structured idea graphs remains mostly unserved.
2. Existing tools still do not close the loop bidirectionally from execution back to planning.
3. No existing product exposes one DAG abstraction across ideas, goals, tasks, and orchestration.
4. No existing product offers one unified visual canvas across all four stages.
5. Open-source tooling is still rich at stages 1 and 4 and weak in the middle.
6. "Idea-rich, execution-poor" remains a distinct and underserved user profile.

## Capability Audit

The codebase is still best understood as "audit, unify, and finish," not "build from scratch."

| Stage | Current Assets | Repo Reality | Main Gap |
|---|---|---|---|
| Ideas | `aragora/canvas/*`, `idea_store.py`, `idea_canvas.py`, `/ideas` page | Strong local-first graph model and CRUD surface | Better user onboarding and graph generation UX |
| Goals | `aragora/goals/extractor.py`, goal store, goal canvas types | Good backend substrate and structural extraction | Higher-quality interactive transition UX |
| Actions | Workflow engine, pipeline planning, action graph models | Strong decomposition substrate | Better task-quality heuristics and richer review loops |
| Orchestration | Ralph, swarm supervisor, tranche submit/review/integrate/watch, queue compiler/runner | Now materially stronger after March 19-20 hardening | Truthful unattended completion and publish edge cases |
| Cross-stage | provenance links, receipts, pipeline abstractions | Strong backend pattern exists | Unified canvas and stage transition product surface |

## Recommended Open Source Stack

The recommended stack from the original document is still reasonable:

| Layer | Recommendation | Why |
|---|---|---|
| Canvas UI | React Flow / Xyflow | Strong node-and-edge interaction model |
| Whiteboard / freeform capture | Excalidraw | Useful early-stage ideation affordance |
| Layout / graph helpers | dagre, Mermaid | Good DAG layout and export utilities |
| Orchestration patterns | LangGraph, Temporal, Hatchet | Durable execution and workflow references |
| Multi-agent coordination | Aragora native plus targeted external patterns | Aragora's differentiation is the debate/receipt layer, not generic workflow wiring |

Avoid introducing new dependencies that weaken embedding or self-hosting economics when the current stack already covers the core need.

## March 22, 2026 Addendum

The source document's "Immediate - Finish the Clean Ralph Rerun" recommendation is now historically stale. The backend frontier moved forward first during the March 19-20 tranche/overnight autonomy sprint, then again during the March 21-22 proof-surface closure on `main`.

### What Landed On `main`

Recent merged work materially expanded both the autonomous execution substrate and the user-visible proof surfaces:

- sequential tranche queue execution and curated queue compilation
- low-risk auto-merge policy for suitable single-lane work
- dead-worker reconciliation and deliverable recovery
- single-lane queue behavior for broad issue sources
- verification-command propagation through queue compile
- explicit single work-order emission for single-lane tranche specs
- supervisor-to-artifact deliverable sync
- stale fleet-claim reaping before conflict checks
- truthful queue-state persistence before long watch loops
- live receipts page backed by real data
- truthful integrations status/edit flow instead of optimistic placeholders
- preserved detached verification evidence and truthful terminal tranche reconciliation
- authoritative lane/integrator view plus completed-lane publish after watch exit
- Knowledge Mound retrieval in debate context, default enablement, writeback, and settlement-hook outcome wiring
- real OpenClaw action dispatch on `main`, not just scaffolding
- truthful public proof surface and live pipeline state in the UI
- remote-head PR review loop so merge decisions are grounded in the real review target

### What The Merged Autonomy Proofs Now Show

The current proof set is broader than a single overnight PR:

- Ralph V14 already validated the bounded repo-improvement loop under explicit merge policy: `spec -> deliverable -> review -> blocker classification -> repair -> PR -> merge`
- `#1108` proved that the tranche queue can recover, publish, and merge a real output
- `#1110` turned the first user-journey/API-key slice into merged code on `main`
- `#1111`, `#1131`, `#1132`, and `#1134` proved that debate results can retrieve from KM, write back to KM, and fire settlement hooks on the canonical outcome path
- `#1119` and `#1136` proved that public- and integrations-facing surfaces can be made truthful instead of demo-shaped
- `#1124`, `#1126`, `#1127`, `#1133`, and `#1138` proved the operator contract is getting real: evidence survives detach, tranche terminal states reconcile truthfully, lane state is authoritative, completed deliverables publish after watch exit, and review can inspect the actual remote PR head
- `#1135` proved the OpenClaw execution path is now real enough to count as part of the wedge, not just a future promise

The key bugs uncovered through dogfooding were:

1. multi-lane planner overlap blocking queue preflight
2. dead workers not terminalizing truthfully
3. single-lane specs being re-decomposed inside the supervisor
4. verification commands being dropped before the merge gate
5. stale fleet claims permanently blocking fresh work
6. queue resume losing `manifest_path` and resubmitting duplicate tranches

### Current Frontier

As of the latest durable March 22 state:

- `queue-v4b` is still the reduced proof lane for `#1047` and `#819`, but the meaning of that proof changed
- `#1047` has already reached a truthful `needs_human` / review-blocked state in the queue
- `#819` now has a merged truthful status/edit slice on `main`, but the broader integrations surface still needs to become trustworthy by default

The main remaining questions are now narrower:

- can the default product loop feel continuous from credentials and provider routing through visible result and receipt
- can every bounded execution lane emit authoritative provenance, preserve blocker reasons, and support remote review without operator guesswork
- can the user-facing proof surfaces stay truthful under partial/live states instead of falling back to shell behavior
- can the merged proof slices become repeatable partner workflows rather than one-off dogfood wins

That is a much better place to be than the original March 2026 strategy assumed.

## Visible Result Contract

Aragora should define a **visible result** more strictly than "the loop ran" or
"a receipt was written somewhere."

A run counts as a visible result only when the user can open Aragora and see a
first-class outcome for that exact run without reading raw terminal output. The
surface must make four things legible:

1. the outcome: answer, artifact, proposed action, PR-ready summary, or
   truthful blocked state
2. the why: evidence, model debate, KM context, and verification linked to the
   result
3. the state: whether the run is complete, partial, failed, or `needs_human`
4. the next action: what the operator should do next when the loop stops short
   of completion

What does **not** count as a visible result:

- a shell transcript or `/tmp` artifact that never becomes product-visible
- a receipt row that exists in storage but is not attached to a readable result
- a status chip without the underlying answer, artifact, or blocker explanation
- a side effect outside Aragora that cannot be inspected from Aragora's own
  surfaces
- an optimistic placeholder that hides partial or missing live state

The practical standard is: if a design partner asks "what did Aragora actually
do here?" the answer must be visible in-product, with provenance one click
away.

## Minimum User-Facing Surfaces Before The Loop Is Production-Worthy

Aragora can reasonably claim the loop is production-worthy only after one
default journey has all of these surfaces working together on the same run:

### 1. Start / setup surface

The user can:

- enter or select the task
- see credential/provider readiness
- understand whether the run is advisory, approval-gated, or live
- know which bounded workflow is about to execute

This is the start of the trust contract. If routing or auth state is hidden,
the rest of the loop will feel like operator folklore instead of product.

### 2. Live-state surface

The user can watch the run move through real stages with truthful partial
state:

- queued
- running
- waiting on approval
- `needs_human`
- failed
- completed

This surface should cover debate/pipeline progress, not just a generic spinner.
If the run is stuck or partially complete, the UI/CLI/API should say that
plainly.

### 3. Result surface

The loop must culminate in a readable outcome:

- a debate synthesis
- a spec or plan artifact
- an inbox action recommendation
- a PR or execution summary
- or an explicit blocked result with the missing decision called out

This is the core answer to "what did Aragora produce?" A receipt ID alone is
not enough.

### 4. Receipt and provenance surface

From the result, the user must be able to inspect:

- evidence and citations
- model participation / dissent
- verification status
- generated artifacts
- settlement or follow-on links where relevant

This is where Aragora differentiates from a generic agent shell. The result has
to be inspectable, not just asserted.

### 5. Review / intervention surface

When the loop cannot finish unattended, the user needs a first-class place to:

- inspect the blocker
- review the latest artifact or PR head
- approve, edit, retry, or hold
- see the exact next manual step

Without this surface, `needs_human` is only a failure code, not a truthful handoff.

### 6. Durable history / share surface

The outcome must remain retrievable after the original session through a durable
surface such as dashboard history, API lookup, or share link. Production-worthy
claims require that the result survive beyond the terminal session and be easy
to reference in sales, review, or audit contexts.

## Implication For The Current Wedge

The current wedge is still the right one, but the bar is now clearer:

- receipt-gated inbox actioning must end in a visible triage result, not just a
  successful backend auth flow
- truthful public/default debate surfaces must show both the synthesis and the
  receipt trail
- bounded swarm/OpenClaw execution must end in a reviewable execution result or
  explicit `needs_human` handoff

If those surfaces do not exist on the same default journey, Aragora has
autonomy proof but not a production-worthy loop.

## Updated Strategy And Best Next Steps

### Immediate

1. Close the default product loop on current `main`.
   The immediate job is no longer "generate candidate PRs." It is "make one truthful path work end to end": credentials and provider routing -> debate -> KM-enriched context -> receipt -> visible result.
2. Establish the provider-path truth contract before widening live-default usage.
   Saved credentials, env vars, or a green settings form are only `config_present`, not proof that the live route works. Missing keys, rejected keys, provider-selection gaps, and transport failures before the first verified provider response must end as blocked/failed states with explicit next action, not as "live" success.
2. Make the proof surfaces truthful by default.
   `/demo`, integrations status/edit, receipts, and pipeline live state should reflect actual live or partial state, not optimistic UI theater.
3. Finish the operator contract for bounded repo execution.
   Every lane should preserve verification evidence, publish completed deliverables after watch exit, review remote PR heads, and end with canonical provenance plus an explicit next manual step when blocked.
4. Treat the wedge as three bounded proof surfaces, not one generic starter pack.
   The real wedge on `main` is receipt-gated inbox actioning, truthful public/default debate surfaces, and bounded swarm/OpenClaw execution under operator control.

In practice, that means only two classes of non-live output are acceptable: explicitly requested demo/offline output, and visibly labeled fallback output when the operator allowed fallback. Everything else must stop truthfully.

### Near Term

1. Expand the workbench from one truthful stage-transition slice into a cohesive shell.
   The highest-value moat work is still the stage-transition UX, but it should now be built on top of truthful live state, not ahead of it.
2. Make execution results revise upstream plans automatically.
   Provenance should not stop at auditability; it should power KM writeback, settlement, replanning, and idea/goal revision.
3. Turn autonomy evidence into PMF proof.
   Use the merged proof surfaces and measured partner workflows as sales proof, not just engineering validation.

### Medium Term

1. Turn the pipeline into the default local-first product shell for non-engineers.
2. Preserve local-first speed and durability as a feature, not a compromise.
3. Scale beyond the bounded wedges only after the operator and product truth contracts are routine.

## MVP Vertical Slice

The original MVP slice is still right:

| Step | Human Action | AI Action |
|---|---|---|
| Idea capture | Add and connect ideas on a local canvas | Cluster and structure them |
| Stage 1 -> 2 | Answer clarifying questions | Derive a goal and principle DAG |
| Goal review | Edit, split, or remove goals | Re-derive dependent structure |
| Stage 2 -> 3 | Approve task breakdown | Produce fully specified tasks with acceptance criteria |
| Stage 3 -> 4 | Approve orchestration plan | Assign agents and launch execution |
| Execution | Watch or intervene | Run the spec-to-merge loop |
| Merge gate | Approve or request changes | Hold, surface findings, and prepare repair work |

### Success Criteria

- A non-engineer can move from 10 rough ideas to a merged PR in under 30 minutes.
- Every merged action can be traced back to goals and source ideas.
- The human makes minimal edits to machine-generated content.
- The orchestration layer requires zero hidden manual rescue between dispatch and the merge gate.

## Competitive Positioning

If Aragora finishes this system, its distinct position is:

- one pipeline spanning ideas, goals, actions, and orchestration
- adversarial debate and review, not just "AI suggestions"
- provenance from originating idea to merged artifact
- heterogeneous model diversity as a reliability mechanism
- local-first execution for people who have many ideas but weak execution bandwidth

## Summary

The original Word document was directionally right: Aragora's biggest opportunity is not another backend substrate, but finishing the product surface that lets people move from ideas to execution with confidence.

What changed after the March 19-22 work is that the orchestration backend and proof surfaces are substantially more real than they were when the document was drafted. The strategic center is now:

- close one truthful default product loop,
- make the existing proof surfaces operator-grade and partner-repeatable,
- and then package the full system behind a unified idea-to-execution interface.

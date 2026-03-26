# Precision And Terms

Consolidated from:
- `docs/strategy/TERMINOLOGY_GLOSSARY.md`
- `docs/strategy/FOUNDER_RUN_FAILURE_TAXONOMY.md`

Last updated: 2026-03-25

---

## Part 1: Terminology And Phrase Glossary

This glossary standardizes the core terms that recur across Aragora's README,
strategy docs, outreach, and product copy. Use these meanings unless a document
explicitly defines a narrower technical variant.

### Debate

**Canonical meaning:** Aragora's structured adversarial validation loop where
multiple agents propose, critique, revise, and either converge or leave
explicit dissent before a decision or action advances.

**Use it for:**

- the core validation engine
- propose / critique / revise workflows
- disagreement that sharpens confidence or surfaces uncertainty

**Do not use it for:**

- any generic chat thread
- a loose brainstorming session
- "many agents did something" without adversarial review

### Receipt

**Canonical meaning:** A durable decision artifact produced from a debate or
execution step that records the inputs, evidence, participants, dissent,
confidence, and the reason the system advanced, stopped, or asked for review.

**Use it for:**

- auditability and provenance
- verification and export
- receipt-before-action gates on consequential work

**Do not use it for:**

- raw logs
- a chat transcript
- a loose summary with no verification or state transition meaning

### Trust Wedge

**Canonical meaning:** The narrow initial workflow where Aragora earns trust
because receipt-gated adversarial review is materially better than unguided AI
execution.

**Current example:** inbox triage (`Gmail -> debate -> receipt -> approval/action`).

**Use it for:**

- the first beachhead workflow
- the adoption surface where trust is won earliest
- a workflow where receipt-before-action changes behavior

**Do not use it for:**

- the whole product
- generic brand trust
- broad enterprise positioning with no concrete workflow

### Founder Loop

**Canonical meaning:** The shortest repeatable live workflow the founder can run
on real work to prove Aragora is truthful, useful, and worth using again.

It must end with a visible result such as a verified receipt, a gated action,
or an explicit truthful stop.

**Use it for:**

- daily dogfooding
- PMF proof on current `main`
- the smallest loop that proves real product value

**Do not use it for:**

- any internal roadmap item
- the entire self-improvement system
- vague references to "working on Aragora"

### Control Plane

**Canonical meaning:** The governance layer above worker runtimes and
connectors that frames work, routes it, applies policy, preserves receipts,
manages review and approval gates, and stops truthfully when evidence is
insufficient.

**Use it for:**

- Aragora's category and moat
- the layer that governs consequential execution
- the system that coordinates policy, routing, review, and provenance

**Do not use it for:**

- a single agent
- a model router by itself
- the UI alone
- generic backend infrastructure with no governance role

### Phrase Rules

- Prefer `decision receipt` when the artifact matters; use bare `receipt` only
  when context is already clear.
- Prefer `structured debate` or `adversarial debate` for the core engine; avoid
  implying that debate means argument for its own sake.
- Prefer `receipt-before-action` for risky automation flows.
- Prefer `trust wedge` for the first narrow adoption surface, not the whole
  product strategy.
- Prefer `control plane` when distinguishing Aragora from agent shells, IDE
  copilots, and execution substrates.

### One-Sentence Synthesis

Aragora is an auditable execution control plane that uses structured debate to
produce decision receipts, earns adoption through a trust wedge, and proves its
truthfulness through a repeatable founder loop.

---

## Part 2: Founder Run Failure Taxonomy

Aragora should not show founders raw internal errors when a run cannot safely
complete. It should reduce every non-success outcome to one primary, truthful
label with a plain-English explanation, visible evidence, and an exact next
action.

This taxonomy is the founder-facing contract for quickstart, inbox, review,
and other Aragora-run surfaces.

### Surface Contract

Every non-successful run should emit:

- one canonical label
- one sentence that explains what happened in founder language
- the evidence Aragora checked before stopping
- what Aragora did **not** do because the stop condition fired
- one exact next action

Do not show multiple top-level failure labels to the founder. Keep secondary
diagnostics in the receipt, logs, or operator view.

### Canonical States

| State | Founder meaning | Use when | Founder next action |
|---|---|---|---|
| `auth_failure` | Aragora could not access a required account, provider, or workspace. | Missing, expired, revoked, or unauthorized credentials block the run before grounded work can proceed. | Reconnect the account, refresh the secret, or grant the missing permission. |
| `no_evidence` | Aragora looked, but it could not find enough grounded evidence to support an answer or action. | Retrieval is empty, the needed files/threads/artifacts do not exist, or the evidence surface is unavailable in a way that yields no usable proof. | Point Aragora at the right source or provide the missing context/artifact. |
| `low_confidence` | Aragora found some evidence, but not enough to act safely. | Evidence is thin, partial, stale, weakly corroborated, or below the action threshold even after verification attempts. | Narrow the question, gather stronger evidence, or ask for a more bounded run. |
| `conflicting_models` | Credible model lanes disagree on the important conclusion. | Material disagreement remains after critique/challenge, and the dissent changes the decision or risk profile. | Review the disagreement, choose the tie-break criterion, or request a decisive external check. |
| `blocked_integration` | Aragora knows the next step, but the external system blocked execution. | Auth succeeded, but the side effect failed because of API outage, schema drift, unsupported capability, rate limit, transport failure, or downstream system error. | Fix the integration, retry later, or perform the blocked step manually. |
| `truthful_stop` | Aragora reached the correct boundary and stopped instead of pretending completion. | A human approval, policy boundary, unresolved strategic choice, or explicit scope limit remains after the run has done the grounded work it safely can. | Do the named handoff step, then rerun or continue from that boundary. |

### Classification Rules

Use the earliest blocking reason that best explains why the run did not safely
complete.

1. If Aragora cannot legally or technically access the required system, use
   `auth_failure`.
2. If access is valid but the external side effect is blocked, use
   `blocked_integration`.
3. If Aragora cannot gather grounded proof from the reachable sources, use
   `no_evidence`.
4. If disagreement between credible lanes is the main reason the run cannot
   advance, use `conflicting_models`.
5. If the evidence is weak without a decisive disagreement story, use
   `low_confidence`.
6. Use `truthful_stop` only when the system is behaving correctly by stopping
   at a named human or policy boundary. It is not a catch-all bucket.

### Founder Copy Guidance

The user-facing sentence should say:

- what Aragora attempted
- why it stopped
- what it did not do
- what the founder should do next

Good examples:

- `auth_failure`: "Aragora could not access Gmail because OAuth is not
  connected. No messages were acted on."
- `no_evidence`: "Aragora checked the selected sources and found no grounded
  evidence for this conclusion. It did not guess."
- `low_confidence`: "Aragora found partial evidence, but not enough to act with
  confidence. It stopped before making a weak recommendation."
- `conflicting_models`: "Aragora found real disagreement between credible model
  lanes. It did not hide that conflict behind a single answer."
- `blocked_integration`: "Aragora knew the next action, but GitHub blocked the
  publish step. No partial publish was performed."
- `truthful_stop`: "Aragora completed the bounded run and stopped at the human
  approval boundary. It did not continue past that gate."

### Why This Matters

The founder should be able to tell the difference between:

- "the system could not get in"
- "the system got in but found nothing trustworthy"
- "the system found something but not enough"
- "the system found real disagreement"
- "the system knew what to do but an integration blocked it"
- "the system stopped honestly at the right human boundary"

That distinction is part of Aragora's product wedge. Truthful failure handling
is not support copy; it is the governance surface.

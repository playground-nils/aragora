# Aragora Terminology And Phrase Glossary

This glossary standardizes the core terms that recur across Aragora's README,
strategy docs, outreach, and product copy. Use these meanings unless a document
explicitly defines a narrower technical variant.

## Debate

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

## Receipt

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

## Trust Wedge

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

## Founder Loop

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

## Control Plane

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

## Phrase Rules

- Prefer `decision receipt` when the artifact matters; use bare `receipt` only
  when context is already clear.
- Prefer `structured debate` or `adversarial debate` for the core engine; avoid
  implying that debate means argument for its own sake.
- Prefer `receipt-before-action` for risky automation flows.
- Prefer `trust wedge` for the first narrow adoption surface, not the whole
  product strategy.
- Prefer `control plane` when distinguishing Aragora from agent shells, IDE
  copilots, and execution substrates.

## One-Sentence Synthesis

Aragora is an auditable execution control plane that uses structured debate to
produce decision receipts, earns adoption through a trust wedge, and proves its
truthfulness through a repeatable founder loop.

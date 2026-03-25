# Human-In-The-Loop Boundaries

Aragora is allowed to automate work, not to erase accountable human judgment.
The system should always be in one of three states:

- `propose`: generate drafts, plans, critiques, patches, and bounded actions
- `must ask`: pause for an explicit human decision before continuing
- `must stop`: terminate the lane truthfully and emit the blocker / next action

The purpose of this boundary is simple: keep automation useful on reversible
work, keep approval explicit on consequential transitions, and keep failure
truthful instead of silently improvising.

## Default Rule

Use the lowest-autonomy mode that preserves truthfulness.

- If the work is reversible, bounded, and inside an explicit contract, Aragora
  can propose.
- If the next step changes authority, risk, spend, publication state, or scope,
  Aragora must ask.
- If the system cannot proceed safely or truthfully, Aragora must stop.

## 1. When Aragora Can Propose

Aragora can act without an approval pause when all of the following are true:

- the task is inside an explicit scope, lease, issue, or validation contract
- the output is reversible or low-cost to discard
- the action does not publish, merge, send, purchase, or bind the organization
- the system has enough evidence to explain why it chose the next step
- a human can still review, override, or reject the result before a
  consequential transition

Typical `propose` work:

- write or revise docs, specs, plans, and internal analysis
- generate code patches in a bounded file scope
- run local validation, tests, linting, and review flows
- decompose a vague request into candidate tasks and assumptions
- prepare drafts of PRs, issues, receipts, runbooks, or operator summaries

`Propose` means "draft or stage the next move," not "silently finalize the
decision."

## 2. When Aragora Must Ask

Aragora must ask for explicit human approval before continuing when any of the
following become true:

- the next step creates an irreversible or externally visible effect
- the system needs to merge, publish, deploy, send messages, or trigger
  real-world execution
- the task requires choosing among materially different strategies, priorities,
  or tradeoffs not already settled in the contract
- scope needs to widen beyond the leased files, stated issue, or accepted plan
- money, legal exposure, compliance posture, vendor commitments, or customer
  promises are involved
- the system is about to touch production data, secrets, credentials, access
  controls, or user accounts
- the system sees meaningful disagreement, ambiguous evidence, or multiple
  reasonable interpretations that affect the outcome
- a human role with authority is required by policy, governance, or law

Typical `must ask` gates:

- "merge this PR or keep iterating?"
- "deploy this change to a live environment?"
- "send this message to a customer or regulator?"
- "expand from `docs/**` into application code?"
- "treat this recommendation as the final organizational decision?"

When Aragora asks, it should present:

- the exact pending action
- why approval is required
- the evidence and dissent that matter
- the lowest-cost options available next

## 3. When Aragora Must Stop

Aragora must stop, not negotiate past the boundary, when any of these are true:

- the task is outside authorized scope and no approval path is available
- the required human decision-maker is unavailable
- the evidence is insufficient to continue truthfully
- validation fails in a way the lane cannot repair inside scope
- instructions conflict in a way that changes the outcome materially
- the requested action is unsafe, prohibited, deceptive, or would conceal
  uncertainty from the operator
- the system detects that continuing would fabricate state, fake completion, or
  claim authority it does not have

Typical `must stop` outputs:

- a blocker receipt
- exact reason for termination
- files or artifacts examined
- what remains unresolved
- the next human action required to resume

Stopping is a feature, not a failure mode. Aragora should prefer a truthful
halt over a smooth but false continuation.

## Decision Table

| Situation | State | Required behavior |
|---|---|---|
| Drafting a plan, patch, or review in approved scope | `propose` | Produce the draft, show assumptions, keep it reversible |
| Running local checks and collecting evidence | `propose` | Execute and attach receipts / results |
| Need to merge, deploy, publish, spend, or contact outsiders | `must ask` | Pause and request explicit approval |
| Need to widen scope or choose between materially different strategies | `must ask` | Surface options, tradeoffs, and recommend one |
| Missing authority, missing evidence, unsafe request, or unresolved contradiction | `must stop` | Terminate truthfully with blocker and next action |

## Operating Principles

### 1. Humans own commitment

Aragora may prepare commitments, but humans own the final commitment when the
organization becomes bound by the result.

### 2. Reversibility buys autonomy

The more reversible the work, the more Aragora can do without waiting.
Irreversibility moves the system from `propose` to `must ask`.

### 3. Ambiguity is a gate, not a license

When material ambiguity appears, the system should narrow, ask, or stop. It
should not improvise a hidden policy.

### 4. Truthful stopping beats fake completion

The system must never mask uncertainty with authoritative tone, invented
progress, or unearned "done" states.

### 5. Override must stay real

Operators need a real ability to inspect, disregard, reverse, or interrupt the
system. Human oversight is not satisfied by a decorative approval checkbox.

## Product Implication

Aragora's core control-plane promise is not maximum autonomy. It is
**bounded autonomy with explicit human authority at consequential edges**.

That means the product should optimize for:

- clear state transitions between `propose`, `must ask`, and `must stop`
- receipts that explain why a boundary was crossed
- low-friction approval UX at real decision points
- truthful blocker summaries instead of silent retries or scope drift

If Aragora gets this boundary right, it becomes trustworthy precisely because
it does not pretend every problem should be solved autonomously.

# Design Partner First-Week Journey

**Date:** March 25, 2026
**Goal:** take a new design partner from setup to one receipt-backed result they can trust enough to act on or reject with a clear reason.

## Week-One Outcome

At the end of week one, the partner should have:

- one bounded recurring workflow selected
- one real artifact or inbox batch run through Aragora
- one visible receipt with evidence, dissent, and next action
- one explicit human decision: act, reject, or hold
- one truthful understanding of what Aragora can and cannot yet automate for them

This is the first trustworthy result. It is not "full autonomy." It is a
receipt-backed decision on a narrow workflow with explicit stop reasons.

## Default Week-One Workflow Choice

Start with the narrowest workflow that can produce a useful receipt quickly.

Recommended order:

1. **Decision review**
   - spec, PR, architecture proposal, incident writeup, or policy draft
2. **Inbox trust wedge**
   - Gmail triage in `--dry-run` or approval-gated mode
3. **Bounded repo execution**
   - only after the partner is comfortable reviewing receipts and stop reasons

Do not start week one with broad unattended execution, autonomous merge
authority, or org-wide rollout.

## Journey

| Day | Objective | What happens | Evidence produced |
|---|---|---|---|
| Day 0 | Qualify the lane | Pick one recurring workflow, one owner, one success metric, and 3-10 representative artifacts | named workflow, owner, sample inputs, success metric |
| Day 1 | Setup and readiness | Connect provider credentials, confirm product surface access, and run the quickstart path or live demo path | successful setup transcript, readiness status, first receipt ID |
| Day 2 | Establish the trust contract | Explain the workflow-specific truth boundary, operator role, approval points, and stop conditions before real use | written truth boundary, operator checklist, blocked states |
| Day 3 | Run the first real artifact | Use a real partner artifact or inbox batch in a narrow lane; keep action gated by a human | debate output, visible receipt, dissent trail, cited evidence |
| Day 4 | Review quality and friction | Compare receipt usefulness against the partner's current process and note missing evidence or unclear output | issue list, friction notes, trust blockers |
| Day 5 | Produce the first trustworthy result | Re-run on the same workflow with any fixes or tighter scope so the partner can make one real decision from the receipt | receipt-backed decision, decision owner, action taken or rejected |
| Days 6-7 | Lock the repeatable loop | Schedule the recurring trigger, define who reviews receipts, and set the expansion rule for week two | recurring cadence, weekly metric, next-scope rule |

## Stage Details

### Day 0: Qualify the lane

The partner must arrive with one concrete workflow, not a vague "use AI
better" objective.

Required inputs:

- one champion who can review results
- one recurring trigger such as a new PR, design doc, or inbox batch
- one bounded artifact set that can be sanitized if needed
- one success metric such as review latency, triage time, or defect catch rate

If the workflow has no clear trigger or owner, stop before setup. That is a
sales/discovery problem, not a product problem.

### Day 1: Setup and readiness

The first day should prove that the partner can reach a live Aragora path
without hidden manual rescue.

Minimum setup proof:

- credentials configured
- the chosen workflow surface is reachable
- a receipt is created and visible on a product or CLI surface
- the run either completes or stops with a direct reason

If setup succeeds only through internal shell surgery or undocumented fallback,
the workflow is not ready for partner week one.

### Day 2: Establish the trust contract

Before the first real artifact, say the boundary out loud:

- what Aragora decides automatically
- what Aragora only recommends
- where human approval is mandatory
- what evidence appears in the receipt
- what "needs human" or blocked states mean operationally

The design partner should hear one sentence that is hard to misread:

> Aragora can truthfully govern this bounded workflow, produce receipts, and
> stop with an explicit blocker; it is not claiming outcome correctness beyond
> the evidence shown in the receipt.

### Day 3: Run the first real artifact

Use the partner's real workflow in the safest shape that still matters.

Examples:

- review one real spec or PR and decide whether it is ready for human approval
- triage one real inbox batch in `--dry-run` before any side effects
- execute one bounded repo task behind review gates

The output must be visible to the partner, not just to Aragora operators.

### Day 4: Review quality and friction

The point is not to defend the output. The point is to find whether the
partner can understand why Aragora advanced, hesitated, or stopped.

Questions to answer:

- did the receipt contain enough evidence to support a decision
- was the dissent trail useful or noisy
- did the stop reason reduce operator confusion
- what part of the workflow still felt "demo-shaped"

### Day 5: Produce the first trustworthy result

A trustworthy result in week one means:

- the task was real
- the scope was narrow
- the receipt was visible
- the evidence and dissent were understandable
- the human could take or reject an action with a documented reason

This can be a "do not act" result. A truthful stop is acceptable. A silent or
hand-waved stop is not.

### Days 6-7: Lock the repeatable loop

Week one is only complete when the partner knows how the next run will happen.

Define:

- trigger: what event causes the next run
- reviewer: who reads the receipt
- action policy: what can happen automatically, with approval, or never
- expansion rule: what must be proven before widening scope

## Explicit Truth Boundaries

These are the boundaries Aragora should state plainly to a new design partner
as of March 25, 2026.

### What Aragora can truthfully claim in week one

- It can run a bounded workflow through a multi-agent debate or gated execution path.
- It can produce a receipt with provenance, dissent, and visible output.
- It can stop with a specific blocker instead of pretending work is complete.
- It can keep approval and merge/action gates explicit.
- It can help the partner review consequential artifacts faster and with a better audit trail.

### What Aragora must not claim in week one

- It does not guarantee that the winning answer is correct in the real world.
- It does not eliminate the need for a responsible human approver.
- It is not yet proving safe broad autonomy across an entire organization.
- It is not a substitute for pentest, certification, or regulated sign-off.
- It should not claim trustworthiness if the receipt is missing, hidden, or unsupported by evidence.

### Hard stop conditions

Stop or downgrade the workflow if any of these are true:

- the partner cannot see the receipt or stop reason
- the evidence used is incomplete, stale, or obviously irrelevant
- human approval points are ambiguous
- the system needs undocumented operator rescue to finish the run
- the workflow widens from one bounded lane into general automation

## Week-One Exit Gate

Do not call the partner "live" until all of the following are true:

- one real workflow is named and owned
- one setup path completed on the partner's environment
- one real receipt-backed run completed or stopped truthfully
- one human reviewer used the receipt to make a real decision
- one list of trust blockers and next actions is written down

## Expansion Rule For Week Two

Only widen scope after the first workflow becomes routine.

Allowed week-two expansions:

- more volume on the same workflow
- tighter evidence formatting and better summaries
- moving from dry-run to approval-gated action
- adding a second reviewer or second artifact type in the same lane

Not allowed as an automatic next step:

- autonomous merge authority
- org-wide agent rollout
- replacing human review with silent automation
- claiming "AI employee" behavior without new proof

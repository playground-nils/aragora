# Aragora Competitive Framing Memo — March 2026

> This document augments, not replaces, the broader vision in
> [CANONICAL_GOALS](../CANONICAL_GOALS.md),
> [WHY_ARAGORA](../WHY_ARAGORA.md), and
> [COMMERCIAL_OVERVIEW](../COMMERCIAL_OVERVIEW.md). It adds competitive
> context and priority ordering based on the current agent-tool landscape. For
> the explicit anti-commodity memo, see
> [WHY_NOT_GENERIC_AGENTS](./WHY_NOT_GENERIC_AGENTS.md).

## One-Sentence Framing

Aragora is best framed as an **auditable control plane for consequential
AI-assisted work**: it adds adversarial review, receipts, provenance, and
truthful gates above worker agents, review loops, and automation runtimes.

That is a more credible category than:

- "general-purpose agent framework"
- "faster PR review bot"
- "replacement for Temporal-style workflow engines"
- "replacement for accountable human decision makers"

## What The Repo Actually Shows Today

These are the product surfaces that are easy to defend from the current repo:

| Repo-visible capability | Evidence in repo | Safe claim |
|---|---|---|
| Multi-agent debate and review | [README](../../README.md), [Developer Quickstart](../QUICKSTART_DEVELOPER.md) | Aragora can run structured multi-agent review flows and expose pass / changes-requested / blocked outcomes. |
| Review artifacts on real PR heads | [Developer Quickstart](../QUICKSTART_DEVELOPER.md) | Aragora can review the current remote PR head and persist structured review artifacts to disk. |
| Decision receipts and audit-oriented artifacts | [README](../../README.md), [Feature Discovery](../FEATURE_DISCOVERY.md) | Aragora already treats receipts as first-class outputs, not just logs. |
| Bounded delegation with leases and isolated worktrees | [Feature Discovery](../FEATURE_DISCOVERY.md) | Aragora has supervisor, worker-launch, and reconciliation primitives for bounded multi-agent execution. |
| Queue / pipeline / workflow surfaces | [README](../../README.md), [Feature Discovery](../FEATURE_DISCOVERY.md) | Aragora has workflow and pipeline surfaces, but those should support the control-plane story rather than become the primary pitch. |
| Human approval and blocker handling | [Feature Discovery](../FEATURE_DISCOVERY.md) | Aragora is designed to stop, classify blockers, and route the next action instead of pretending every run is fully autonomous. |

The repo also shows constraints that should shape the pitch:

- [Feature Gap List](../FEATURE_GAP_LIST.md) still calls out control-plane truth
  gaps around universal per-lane receipts, claims, and integrator visibility.
- [Feature Discovery](../FEATURE_DISCOVERY.md) marks some receipt and inbox
  surfaces as integrated or partial rather than uniformly complete.
- The strongest "real today" proof path is review, debate, bounded delegation,
  and receipt capture, not "fully autonomous organization."

## The Competitive Frame By Category

Aragora sits next to four categories that buyers will naturally compare:

| Category | What that category is good at | Where Aragora should concede ground | Where Aragora has a real wedge | Correct positioning |
|---|---|---|---|---|
| Agent frameworks | Wiring tasks, tool calls, agent roles, and graph execution | They are usually simpler and better known for cooperative automation plumbing | Aragora is stronger when the work needs explicit disagreement, review evidence, receipts, and truthful stopping | Use frameworks to execute or orchestrate; use Aragora when the decision or merge step needs governance |
| Review tools | Fast feedback on code diffs, lint-like issues, and routine PR checks | Simple review bots are lower-friction for everyday diffs and narrow defect classes | Aragora is stronger for consequential review where dissent, blocker classification, and durable artifacts matter | Aragora is a governed review layer, not just a comment bot |
| Workflow tools | Durable retries, scheduling, queues, SLAs, and stateful automation | They are better default choices for generic business-process automation and background job reliability | Aragora is stronger at the judgment-heavy gates inside a workflow: review, approval, escalation, and evidence capture | Use workflow engines for execution reliability; call Aragora at high-consequence decision points |
| Internal human processes | Accountability, domain context, politics, and final approval authority | Humans still own accountability, exception handling, and irreversible decisions | Aragora is stronger at compressing first-pass analysis, preserving rationale, and surfacing disagreement before meetings or approvals | Aragora should tighten human review loops, not claim to replace them |

## 1. Aragora Vs Agent Frameworks

Examples in the repo and surrounding docs include LangGraph, CrewAI, AutoGen,
and external framework integrations.

The honest comparison is:

- agent frameworks are primarily about coordination and execution structure
- Aragora's best story is not "more orchestration"
- Aragora's best story is "better governed judgment"

What to say:

- Aragora treats disagreement as a feature, not a routing failure.
- Aragora preserves receipts, provenance, and explicit terminal states.
- Aragora can sit above worker runtimes and frameworks rather than replace them.

What not to say:

- Aragora has a stronger orchestration ecosystem than the incumbent frameworks.
- Aragora is the easiest way to build ordinary cooperative automations.
- multi-provider breadth by itself is the moat.

The clean line is:

**Use an agent framework to run the work. Use Aragora to vet consequential
outputs before they ship, merge, or trigger irreversible actions.**

## 2. Aragora Vs Review Tools

This category includes PR review bots, static analyzers, CI gates, and
single-model review loops.

The honest comparison is:

- review tools are optimized for speed, coverage, and low ceremony
- Aragora adds overhead on purpose when the review outcome matters
- Aragora should win on review governance, not on "fewest seconds to first comment"

What to say:

- Aragora can review a live GitHub PR head and persist structured artifacts.
- Aragora can return `passed`, `changes_requested`, or `blocked` style outcomes.
- Aragora is a better fit when teams need evidence for why a change advanced or stopped.

What not to say:

- Aragora should replace every ordinary PR bot or static analysis rule.
- Aragora is always cheaper or faster than a single-reviewer path.
- every receipt is already complete enough for every compliance workflow.

The clean line is:

**Review bots are good at fast comments. Aragora is for review decisions that
need dissent, receipts, and truthful blocker handling.**

## 3. Aragora Vs Workflow Tools

This category includes workflow engines, queue systems, and DAG runtimes.
The repo does show workflow and queue surfaces, but that does not mean Aragora
should be sold as a generic workflow winner.

The honest comparison is:

- workflow tools own durability, retries, scheduling, and operational cadence
- Aragora owns the judgment-heavy control points inside those flows
- the wedge is not "more DAGs"; it is "better governed decisions inside DAGs"

What to say:

- Aragora already has queue, pipeline, and workflow components.
- Those components are most useful when tied to receipts, approvals, and review evidence.
- Aragora can be the policy and evidence layer around a broader execution stack.

What not to say:

- Aragora should replace purpose-built workflow infrastructure everywhere.
- generic workflow breadth is the differentiator buyers should care about first.
- durable execution alone creates a moat.

The clean line is:

**Use workflow tooling to move work reliably. Use Aragora where the workflow
needs adversarial review, explicit approval, or truthful escalation.**

## 4. Aragora Vs Internal Human Processes

This category is easy to mishandle. Aragora should not be framed as "automation
that removes humans from consequential decisions."

The honest comparison is:

- humans still own accountability, context, and exception handling
- many internal review loops are slow because evidence is fragmented or lost
- Aragora is most credible when it sharpens human review rather than bypassing it

What to say:

- Aragora can produce a durable record of who argued what and why a run stopped.
- Aragora can narrow the set of questions humans need to answer.
- Aragora can make handoffs and approvals more explicit.

What not to say:

- Aragora can replace domain owners, approvers, or legal/compliance judgment.
- every decision should be fully autonomous.
- a receipt is the same thing as accountability.

The clean line is:

**Aragora reduces review latency and preserves decision evidence, but humans
remain the accountable final authority.**

## Where Aragora Should Lead

The best near-term wedge is:

**auditable multi-model review and execution governance for consequential
engineering and operational work**

Why this is the most credible beachhead:

- the repo already demonstrates debate, review, receipts, and bounded work orders
- PR review and merge decisions have clear pass / fail / blocked outcomes
- buyers can understand the cost of bad approval decisions immediately
- the control-plane story is distinct from "yet another coding agent"

## Where Aragora Should Not Lead

These themes are present in the repo, but they should not be the opening claim:

- raw agent-count breadth
- generic connector counts
- generic workflow breadth
- "fully autonomous company" rhetoric
- claims that Aragora replaces human governance
- claims that compliance is solved merely because receipts exist

Those can support the story later. They should not define the category.

## The Message Stack

If the prospect starts with agent frameworks:

**Aragora is the review and governance layer above execution frameworks.**

If the prospect starts with PR review tools:

**Aragora is for merge decisions that need evidence, dissent, and explicit stop
conditions, not just another stream of comments.**

If the prospect starts with workflow platforms:

**Aragora governs the judgment-heavy gates inside the workflow; it is not trying
to win on generic scheduling or retries.**

If the prospect starts with internal human process:

**Aragora makes human review tighter and more inspectable; it does not remove
human accountability.**

## Simple Strategic Test

If the answer to "why Aragora instead of adjacent tools?" is:

- "more models"
- "more agents"
- "more workflows"
- "more connectors"

the framing is weak.

If the answer is:

**"because this work needs adversarial review, durable receipts, provenance, and
truthful gates before it advances"**

the framing is on target.

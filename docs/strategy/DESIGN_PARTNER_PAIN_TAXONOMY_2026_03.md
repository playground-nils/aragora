# Design Partner Pain Taxonomy And Trigger Events — March 2026

This document defines the recurring pain patterns and forcing events that make
Aragora urgent enough to buy for the first design partner cohort.

It is an ICP filter, not a general market map.

## Core Rule

Aragora becomes buy-now when all four conditions are true:

- A consequential workflow repeats at least weekly
- The wrong decision is costly enough that ad hoc AI usage is no longer acceptable
- There is a clear owner and approval step
- A forcing event makes the current workaround intolerable now

If one of those is missing, there may be interest, but usually not urgency.

## Recurring Pain Taxonomy

| Pain class | Recurring workflow | Current broken workaround | Why Aragora is the wedge | Best starting surface |
|---|---|---|---|---|
| Consequential review bottleneck | PR review, architecture review, spec review, policy review | Single-model output plus senior human spot checks, Slack approvals, after-the-fact fixes | Multi-model challenge, receipts, dissent, and explicit review gates make the decision legible before it ships | `aragora review` or debate-backed spec review |
| Manual triage overload | Shared inboxes, customer escalations, security questionnaires, incident intake, approval queues | Humans skim everything, rules are too brittle, and "full auto" is too risky to trust | Receipt-before-action, explicit approve/stop behavior, and provenance on every recommendation | Inbox trust wedge (`aragora triage`) |
| Bounded execution backlog | Recurring maintenance tasks, bug-fix queues, refactors, bounded engineering work orders | AI can draft work, but humans still have to re-review everything from scratch, so backlog keeps growing | Bounded delegation, cross-model review, receipt-gated handoff, and truthful blocker handling | Autonomous repo improvement / supervised work orders |
| Audit evidence scramble | Explaining any AI-influenced decision to compliance, legal, security, customers, or leadership | Screenshots, chat logs, retroactive writeups, and no durable provenance | Decision receipts turn explanation into a byproduct instead of a separate documentation project | Layer receipts onto any of the other three workflows |

The first three are the operational wedges.
The fourth is usually the urgency amplifier, not the first wedge by itself.

## Trigger Events That Create Urgency

| Trigger family | What happened | Why budget appears now | Most affected pain classes |
|---|---|---|---|
| Miss or near miss | A bad merge, escalation miss, incorrect triage action, or preventable incident got through | Leadership now wants a gate, not just "be more careful" | Review bottleneck, triage overload, audit evidence scramble |
| Volume or staffing shock | PR volume spikes, inbox backlog grows, or a key reviewer/operator becomes the bottleneck | The manual process no longer scales, but ungated automation still feels unsafe | Review bottleneck, triage overload, bounded execution backlog |
| AI adoption outruns governance | The team is already using Codex, Claude Code, OpenCode, or internal prompts everywhere | Execution got faster, but approval, provenance, and accountability did not | Review bottleneck, bounded execution backlog, audit evidence scramble |
| External scrutiny | Audit prep, customer diligence, enterprise procurement, incident postmortem, or board review asks "why was this approved?" | Chat logs and informal approvals stop being acceptable evidence | Audit evidence scramble plus whichever operational pain produced the decision |
| Deadline compression | Release cutoff, SLA pressure, weekly support load, or compliance milestone leaves no room for rework | Latency and wrong-action cost become visible in the same week | Triage overload, review bottleneck, bounded execution backlog |

## What To Listen For In Discovery

These are strong buying-language signals:

- "We already use AI, but we cannot let it merge or act without a real gate."
- "We missed something important and now leadership wants an approval trail."
- "We are drowning in review or triage work, but full automation feels reckless."
- "Procurement, security, or compliance asked us to explain how AI-assisted decisions are documented."
- "The backlog is not the problem by itself. The problem is we do not trust the current automation path."

## First Cohort Qualification Filter

Prioritize prospects that can answer yes to all of these:

- They have one workflow with a clear trigger, owner, and action outcome
- The workflow happens at least weekly
- They can provide real artifacts, even if sanitized
- They have a forcing event expected in the next 90 days
- They are willing to start with one receipt-gated queue, not a company-wide rollout

## Not Yet A Fit

Deprioritize prospects when:

- The pain is mostly hypothetical or happens quarterly at most
- They want a generic agent platform rather than a governed workflow
- No one owns the approval step or will review the receipts
- They want open-ended autonomy before proving one bounded lane
- Compliance is the only story, with no recurring operational pain underneath it

## Messaging Implication

Lead with the recurring painful queue, not "43 agent types."

For the first cohort, the winning message is:

- fix the review bottleneck before the next bad escape
- fix the triage queue before the next missed escalation
- unlock bounded execution without giving up truthful gates
- use compliance and audit evidence as accelerants, not the primary wedge

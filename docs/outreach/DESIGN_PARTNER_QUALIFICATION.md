# Design Partner Qualification

Consolidated from:
- `docs/strategy/DESIGN_PARTNER_PAIN_TAXONOMY_2026_03.md`
- `docs/outreach/DESIGN_PARTNER_QUALIFICATION_RUBRIC.md`
- `docs/outreach/DESIGN_PARTNER_SELECTION_SCORECARD.md`

Last updated: 2026-03-25

---

## Part 1: Pain Taxonomy And Trigger Events

### Core Rule

Aragora becomes buy-now when all four conditions are true:

- A consequential workflow repeats at least weekly
- The wrong decision is costly enough that ad hoc AI usage is no longer acceptable
- There is a clear owner and approval step
- A forcing event makes the current workaround intolerable now

If one of those is missing, there may be interest, but usually not urgency.

### Recurring Pain Taxonomy

| Pain class | Recurring workflow | Current broken workaround | Why Aragora is the wedge | Best starting surface |
|---|---|---|---|---|
| Consequential review bottleneck | PR review, architecture review, spec review, policy review | Single-model output plus senior human spot checks, Slack approvals, after-the-fact fixes | Multi-model challenge, receipts, dissent, and explicit review gates make the decision legible before it ships | `aragora review` or debate-backed spec review |
| Manual triage overload | Shared inboxes, customer escalations, security questionnaires, incident intake, approval queues | Humans skim everything, rules are too brittle, and "full auto" is too risky to trust | Receipt-before-action, explicit approve/stop behavior, and provenance on every recommendation | Inbox trust wedge (`aragora triage`) |
| Bounded execution backlog | Recurring maintenance tasks, bug-fix queues, refactors, bounded engineering work orders | AI can draft work, but humans still have to re-review everything from scratch, so backlog keeps growing | Bounded delegation, cross-model review, receipt-gated handoff, and truthful blocker handling | Autonomous repo improvement / supervised work orders |
| Audit evidence scramble | Explaining any AI-influenced decision to compliance, legal, security, customers, or leadership | Screenshots, chat logs, retroactive writeups, and no durable provenance | Decision receipts turn explanation into a byproduct instead of a separate documentation project | Layer receipts onto any of the other three workflows |

The first three are the operational wedges.
The fourth is usually the urgency amplifier, not the first wedge by itself.

### Trigger Events That Create Urgency

| Trigger family | What happened | Why budget appears now | Most affected pain classes |
|---|---|---|---|
| Miss or near miss | A bad merge, escalation miss, incorrect triage action, or preventable incident got through | Leadership now wants a gate, not just "be more careful" | Review bottleneck, triage overload, audit evidence scramble |
| Volume or staffing shock | PR volume spikes, inbox backlog grows, or a key reviewer/operator becomes the bottleneck | The manual process no longer scales, but ungated automation still feels unsafe | Review bottleneck, triage overload, bounded execution backlog |
| AI adoption outruns governance | The team is already using Codex, Claude Code, OpenCode, or internal prompts everywhere | Execution got faster, but approval, provenance, and accountability did not | Review bottleneck, bounded execution backlog, audit evidence scramble |
| External scrutiny | Audit prep, customer diligence, enterprise procurement, incident postmortem, or board review asks "why was this approved?" | Chat logs and informal approvals stop being acceptable evidence | Audit evidence scramble plus whichever operational pain produced the decision |
| Deadline compression | Release cutoff, SLA pressure, weekly support load, or compliance milestone leaves no room for rework | Latency and wrong-action cost become visible in the same week | Triage overload, review bottleneck, bounded execution backlog |

### What To Listen For In Discovery

These are strong buying-language signals:

- "We already use AI, but we cannot let it merge or act without a real gate."
- "We missed something important and now leadership wants an approval trail."
- "We are drowning in review or triage work, but full automation feels reckless."
- "Procurement, security, or compliance asked us to explain how AI-assisted decisions are documented."
- "The backlog is not the problem by itself. The problem is we do not trust the current automation path."

### Messaging Implication

Lead with the recurring painful queue, not "43 agent types."

For the first cohort, the winning message is:

- fix the review bottleneck before the next bad escape
- fix the triage queue before the next missed escalation
- unlock bounded execution without giving up truthful gates
- use compliance and audit evidence as accelerants, not the primary wedge

---

## Part 2: Qualification Rubric

### Purpose

Keep outreach focused on the **first realistic wedge**, not the whole platform story.

For the first design partner cohort, Aragora is selling one narrow workflow:

`real Gmail inbox -> adversarial triage debate -> persisted receipt -> human approval or narrow auto-approval -> gmail.modify action`

Allowed v1 actions:

- `ARCHIVE`
- `STAR`
- `LABEL`
- `IGNORE`

Explicitly not in scope for the first cohort:

- reply, send, or forward generation
- customer support automation
- general-purpose agent orchestration
- autonomous repo execution as the initial sale
- broad enterprise rollout before a single inbox pilot works

### Qualification Rule

Only pursue a design partner if the account matches the inbox trust wedge well
enough that a live pilot can start quickly and produce clear proof.

If the conversation drifts into a broader platform evaluation, disqualify or
park it unless the inbox wedge is still the immediate starting point.

### Hard Qualification Gates

All of these should be true.

| Gate | What must be true | Why it matters |
|---|---|---|
| Real inbox pain | One operator has painful, recurring inbox triage work every week | The wedge only works if the pain is already real |
| Gmail fit | They use Gmail or Google Workspace for the target inbox | Current wedge is built around Gmail and `gmail.modify` |
| High-stakes messages | Missing or mishandling email has real cost: revenue, recruiting, partnerships, investor updates, or customer escalation | Receipts and human review are only valuable on consequential email |
| Narrow action fit | `ARCHIVE`, `STAR`, `LABEL`, and `IGNORE` cover the first pilot | Avoids widening into reply/send autonomy before trust exists |
| Human-in-the-loop tolerance | They are willing to review receipts and keep approval explicit at the start | Aragora's value is trust, provenance, and governed actioning |
| Clear champion | One person owns the pilot, can provide artifacts, and will join a weekly loop | Early pilots die without a direct operator owner |
| Fast start | They can start a pilot within 14 days without a long procurement/security process | First design partner motion needs fast feedback, not enterprise theater |
| Feedback data | They can provide real or sanitized examples and label outcomes | Quality improves only if the partner can help measure recall and overrides |

### Strong Positive Signals

Prioritize accounts with several of these.

| Signal | Why it is attractive |
|---|---|
| Founder, CEO, chief of staff, or business lead personally owns the inbox | The pain is urgent and adoption friction is lower |
| Inbox includes sales, partnership, recruiting, investor, or executive follow-up traffic | These are high-value messages where misses matter |
| They already triage manually using stars, labels, folders, or ad hoc AI help | Existing behavior maps cleanly to the v1 action set |
| They feel distrust toward single-model email automation | Aragora's adversarial receipt story will resonate |
| They can evaluate a 25-50 message batch during the first two weeks | Makes quality measurement practical |
| They want proof before broader automation | Good fit for receipt-first positioning |
| They are founder-led or small enough to move without layered approvals | Shortens time to first live run |

### Hard Disqualifiers

Any one of these is enough to disqualify the account for the first cohort.

| Disqualifier | Why it is out of scope now |
|---|---|
| They want autonomous replies, sends, or forwards in the first pilot | That is explicitly deferred beyond the wedge |
| They are not on Gmail / Google Workspace for the target workflow | Current proof surface is Gmail-specific |
| Their main interest is code review, generic agent swarms, or compliance dashboards rather than inbox triage | That is a different sale and will widen scope |
| They need an org-wide rollout before a single-operator pilot | First proof should stay narrow and measurable |
| They require SSO, RBAC, SOC 2, vendor onboarding, or legal review before a pilot can start | Too slow for first-wedge learning |
| They cannot provide example emails or label outcomes | No way to verify recall, overrides, or business value |
| Their inbox is low-volume or low-stakes | The wedge will not feel valuable enough to stick |
| They expect a polished dashboard-first experience and will not use a CLI-assisted workflow | Current path is still operator-led and wedge-first |

### Yellow Flags

These do not automatically kill the lead, but two or more usually mean "park for
later."

| Yellow flag | Concern |
|---|---|
| Shared inbox with multiple operators from day one | Adds coordination complexity before the single-user path is proven |
| Heavy regulated data concerns but no sandbox/sanitization path | May slow down access to real examples |
| They want many connectors in phase one | Signals platform shopping instead of wedge adoption |
| They cannot commit to a weekly 30-minute review loop | Weak feedback loop |
| They need custom labeling logic before the first pilot | Likely too much setup work |

### Green / Yellow / Red Decision

#### Greenlight now

- All hard qualification gates are true
- No hard disqualifiers are present
- At least 3 strong positive signals are present
- No more than 1 yellow flag is present

#### Nurture, but do not prioritize

- All hard qualification gates are true
- No hard disqualifiers are present
- Only 1-2 strong positive signals are present, or there are 2 yellow flags

#### Disqualify for this cohort

- Any hard disqualifier is present
- Any hard qualification gate is false
- The lead keeps pulling toward broad platform evaluation instead of the inbox wedge

### Ideal First-Cohort Personas

Start with people who already feel the inbox pain personally:

- founder or CEO of a founder-led B2B company
- chief of staff or executive assistant handling a principal's inbox
- business development or partnerships lead handling high-value inbound
- recruiting-heavy operator triaging candidate and interviewer coordination

Better early accounts usually have:

- one primary inbox owner
- fast decision-making
- enough email volume to matter
- enough message value that false negatives hurt

### Poor First-Cohort Fits

Do not spend first-wave outreach here:

- shared support or customer success queues
- large enterprise IT evaluations
- teams primarily asking for autonomous coding/repo work
- teams looking for "AI email assistant that writes replies"
- buyers who mostly want roadmap demos rather than a live pilot

### Discovery Questions

Use these to qualify fast.

1. Which inbox would we start with, and is it on Gmail/Google Workspace?
2. Who owns that inbox day to day?
3. What kinds of missed emails are actually costly?
4. Would `ARCHIVE`, `STAR`, `LABEL`, and `IGNORE` cover a useful first pilot?
5. Are you comfortable requiring a receipt before any action executes?
6. Can you review a small weekly batch and mark where Aragora was right or wrong?
7. Can we start within the next 14 days without a heavy security or procurement cycle?

### Pilot Success Criteria

The first cohort should be evaluated on measurable wedge outcomes, not generic
"AI platform" sentiment.

Track:

- important-email recall
- operator override rate
- cost per processed email
- end-to-end latency per email
- weekly time saved for the inbox owner
- whether the operator trusts the receipt enough to keep using the workflow

### Outreach Guardrail

The correct first question is not:

> "Do you want a multi-agent AI platform?"

It is:

> "Do you have a painful Gmail inbox where receipt-gated triage and actioning would immediately save time without giving up control?"

If the answer is no, move on.

### First Cohort Qualification Filter

Prioritize prospects that can answer yes to all of these:

- They have one workflow with a clear trigger, owner, and action outcome
- The workflow happens at least weekly
- They can provide real artifacts, even if sanitized
- They have a forcing event expected in the next 90 days
- They are willing to start with one receipt-gated queue, not a company-wide rollout

### Not Yet A Fit

Deprioritize prospects when:

- The pain is mostly hypothetical or happens quarterly at most
- They want a generic agent platform rather than a governed workflow
- No one owns the approval step or will review the receipts
- They want open-ended autonomy before proving one bounded lane
- Compliance is the only story, with no recurring operational pain underneath it

---

## Part 3: Selection Scorecard

### Purpose

Use this scorecard to rank design partner prospects for Aragora's current
beachhead:

- auditable multi-model decision review
- receipt-gated bounded execution
- truthful blocker handling for consequential workflows

The goal is not to pick the biggest logo. The goal is to pick the 3-5 partners
most likely to generate fast, credible proof that Aragora's wedge matters.

### Hard Gates

Do not advance a prospect if any of these are false:

1. They have one bounded recurring workflow with a clear trigger, owner, and
   success/failure outcome.
2. The workflow is consequential enough that receipts, provenance, review, or
   explicit approval gates are valuable.
3. They can provide real artifacts during the partner period. Sanitized inputs
   are acceptable.
4. They have a named champion who will join onboarding and a weekly review loop.
5. They can start with a narrow pilot in 30 days or less.

If a prospect fails a hard gate, mark them `not now` even if the weighted score
looks attractive.

### Scoring Model

Score each dimension from 1 to 5 after the first serious discovery call.

| Dimension | Weight | What it means |
|-----------|--------|---------------|
| Urgency | 30% | How painful and time-sensitive the current workflow is |
| Tractability | 30% | How easily Aragora can be piloted on one narrow workflow |
| Credibility | 20% | How likely the prospect is to run a real pilot and become a referenceable customer |
| Learning value | 20% | How much the pilot will teach Aragora about its wedge and ideal customer profile |

Formula:

`weighted score = (0.30 x urgency) + (0.30 x tractability) + (0.20 x credibility) + (0.20 x learning value)`

Multiply by 20 for a 100-point score.

### Rubric

#### 1. Urgency

| Score | Signals |
|-------|---------|
| 1 | Curiosity project, no active pain, no deadline, no owner feeling real pressure |
| 2 | Problem is acknowledged, but current workaround is acceptable for now |
| 3 | Recurring pain exists and someone cares, but the workflow is not yet breaking an SLA, audit need, or throughput goal |
| 4 | Pain is acute: review latency, triage load, audit evidence burden, or bounded backlog pressure is affecting the team now |
| 5 | The current process is visibly failing or expensive, and the champion wants a pilot immediately because delay has a real cost |

Questions to ask:

- What happens today when this workflow goes wrong?
- What manual review, audit, or triage cost shows up every week?
- Why is now the right time to run this pilot?

#### 2. Tractability

| Score | Signals |
|-------|---------|
| 1 | Prospect wants a broad AI transformation story, not one narrow workflow |
| 2 | A candidate workflow exists, but scope, owner, or success criteria are still fuzzy |
| 3 | One workflow is identifiable, but artifacts, integrations, or operating cadence are still partially unclear |
| 4 | One narrow workflow is clear, artifacts are available, success is measurable, and the pilot can start with limited integration work |
| 5 | Ideal first pilot: one recurring trigger, one operator owner, real artifacts ready, weekly feedback loop agreed, and a receipt clearly improves trust or governance |

Questions to ask:

- Can we start with one workflow before talking about broader rollout?
- What artifact starts the workflow?
- What exact human decision or action sits at the end?
- What would make the first 2 weeks clearly successful or unsuccessful?

#### 3. Credibility

| Score | Signals |
|-------|---------|
| 1 | Tire-kicker, student project, consultant without workflow ownership, or no real path to pilot |
| 2 | Friendly interest, but authority, budget, or access to operators is unclear |
| 3 | Real champion exists, but internal alignment or approval path is still uncertain |
| 4 | Champion has workflow ownership or direct influence, can bring real artifacts, and can keep a weekly cadence |
| 5 | Strong operational sponsor with authority, concrete pilot timeline, path to expansion or paid conversion, and credible willingness to be a reference if the pilot works |

Questions to ask:

- Who owns the workflow operationally?
- Who decides whether the pilot continues?
- Can this team actually provide artifacts and operator time every week?
- If the pilot works, what happens next?

#### 4. Learning Value

| Score | Signals |
|-------|---------|
| 1 | Bespoke edge case with little transfer to future customers |
| 2 | Some product learning, but mostly one-off implementation detail |
| 3 | Useful learning for one segment or one product surface |
| 4 | Teaches Aragora something important about its wedge, especially around receipts, review, governance, or bounded execution |
| 5 | High-leverage pilot that can validate positioning, generate reusable messaging, expose important failure modes, and transfer directly to multiple future prospects |

Questions to ask:

- Does this workflow test Aragora's real wedge or just generic automation?
- Will success here produce a reusable case study or proof point?
- Does the segment match the current best-fit profile?
- Will we learn something that changes roadmap or positioning decisions?

### Decision Rules

Use the weighted score, but keep simple floor rules:

- `Fast-track`:
  weighted score >= 4.2, with urgency >= 4 and tractability >= 4
- `Qualified`:
  weighted score 3.6-4.19, with no dimension below 3
- `Monitor`:
  weighted score 3.0-3.59, or learning value is high but the pilot is not yet tractable
- `Not now`:
  weighted score < 3.0, any hard gate fails, or tractability/credibility <= 2

Tiebreakers:

1. Higher tractability wins.
2. Then higher urgency.
3. Then higher learning value.

At Aragora's current stage, speed-to-proof matters more than prestige.

### Best-Fit Prospect Pattern

The best design partners usually have most of these traits:

- regulated or high-accountability environment
- recurring review or triage bottleneck
- visible trust gap with single-model workflows
- strong need for audit evidence or explicit approval gates
- one operator champion who wants to start narrow

Examples of strong first workflows:

- design doc or architecture review with decision receipts
- PR or release review for consequential engineering changes
- inbox or queue triage where receipt-before-action matters
- bounded backlog execution with explicit review and stop conditions

### Capture Template

Use this block in notes or CRM:

```md
## Design Partner Scorecard

Prospect:
Segment:
Champion:
Workflow:
Why now:

Hard gates:
- bounded recurring workflow:
- consequential enough for receipts/gates:
- real artifacts available:
- weekly champion available:
- can start in <=30 days:

Scores:
- urgency (30%):
- tractability (30%):
- credibility (20%):
- learning value (20%):

Weighted total:
Recommendation:
Key evidence:
Main risks:
```

### Operating Principle

Do not accept prospects that mainly want "general AI transformation help."
Prefer prospects where Aragora can prove:

- disagreement is useful
- receipts change trust
- review gates reduce risk
- bounded execution can be governed truthfully

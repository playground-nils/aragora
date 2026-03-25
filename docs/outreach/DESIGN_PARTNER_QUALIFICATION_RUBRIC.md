# Aragora Design Partner Qualification Rubric

Last updated: 2026-03-24

## Purpose

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

## Qualification Rule

Only pursue a design partner if the account matches the inbox trust wedge well
enough that a live pilot can start quickly and produce clear proof.

If the conversation drifts into a broader platform evaluation, disqualify or
park it unless the inbox wedge is still the immediate starting point.

## Hard Qualification Gates

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

## Strong Positive Signals

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

## Hard Disqualifiers

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

## Yellow Flags

These do not automatically kill the lead, but two or more usually mean "park for
later."

| Yellow flag | Concern |
|---|---|
| Shared inbox with multiple operators from day one | Adds coordination complexity before the single-user path is proven |
| Heavy regulated data concerns but no sandbox/sanitization path | May slow down access to real examples |
| They want many connectors in phase one | Signals platform shopping instead of wedge adoption |
| They cannot commit to a weekly 30-minute review loop | Weak feedback loop |
| They need custom labeling logic before the first pilot | Likely too much setup work |

## Green / Yellow / Red Decision

### Greenlight now

- All hard qualification gates are true
- No hard disqualifiers are present
- At least 3 strong positive signals are present
- No more than 1 yellow flag is present

### Nurture, but do not prioritize

- All hard qualification gates are true
- No hard disqualifiers are present
- Only 1-2 strong positive signals are present, or there are 2 yellow flags

### Disqualify for this cohort

- Any hard disqualifier is present
- Any hard qualification gate is false
- The lead keeps pulling toward broad platform evaluation instead of the inbox wedge

## Ideal First-Cohort Personas

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

## Poor First-Cohort Fits

Do not spend first-wave outreach here:

- shared support or customer success queues
- large enterprise IT evaluations
- teams primarily asking for autonomous coding/repo work
- teams looking for "AI email assistant that writes replies"
- buyers who mostly want roadmap demos rather than a live pilot

## Discovery Questions

Use these to qualify fast.

1. Which inbox would we start with, and is it on Gmail/Google Workspace?
2. Who owns that inbox day to day?
3. What kinds of missed emails are actually costly?
4. Would `ARCHIVE`, `STAR`, `LABEL`, and `IGNORE` cover a useful first pilot?
5. Are you comfortable requiring a receipt before any action executes?
6. Can you review a small weekly batch and mark where Aragora was right or wrong?
7. Can we start within the next 14 days without a heavy security or procurement cycle?

## Pilot Success Criteria

The first cohort should be evaluated on measurable wedge outcomes, not generic
"AI platform" sentiment.

Track:

- important-email recall
- operator override rate
- cost per processed email
- end-to-end latency per email
- weekly time saved for the inbox owner
- whether the operator trusts the receipt enough to keep using the workflow

## Outreach Guardrail

The correct first question is not:

> "Do you want a multi-agent AI platform?"

It is:

> "Do you have a painful Gmail inbox where receipt-gated triage and actioning would immediately save time without giving up control?"

If the answer is no, move on.

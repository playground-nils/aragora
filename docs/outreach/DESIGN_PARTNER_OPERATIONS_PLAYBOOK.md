# Design Partner Operations Playbook

Consolidated from:
- `docs/outreach/FOUNDER_OUTREACH_SEQUENCES.md`
- `docs/outreach/FOUNDER_DISCOVERY_CALL_SCRIPT.md`
- `docs/plans/2026-03-24-design-partner-pilot-structure.md`
- `docs/plans/2026-03-25-design-partner-first-week-journey.md`
- `docs/plans/2026-03-25-design-partner-onboarding-readiness-checklist.md`
- `docs/outreach/DESIGN_PARTNER_CASE_STUDY_TEMPLATE.md`

Last updated: 2026-03-25

---

## Part 1: Outreach Sequences

These sequences are for founder-led outreach to prospective design partners. They stay aligned with Aragora's current proof surfaces: receipt-gated decision review, the inbox trust wedge, and bounded autonomous execution under explicit policy.

### Messaging Rules

- Lead with one painful recurring workflow, not a broad platform story.
- Use plain language before category language. "Decision Integrity Platform" is useful, but the first sentence should describe the operational pain.
- Offer a narrow first step: a 15-minute call, a live demo on one real artifact, or an async receipt review.
- Do not promise unrestricted autonomy. Keep "receipt-before-action" and explicit approval gates in scope.
- Personalize with one concrete trigger: inbox triage, design review, security review, or bounded engineering backlog.

### 1. Cold Reach-Out

Best for: founder, CTO, VP Engineering, platform lead, or security lead with no prior relationship.

#### Touch 1: Initial Email

**Subject options**

- `Question on how [company] reviews high-stakes AI-assisted decisions`
- `Idea for [company]'s review / triage bottleneck`
- `Can I show you a receipt-first AI review workflow?`

```text
Hi [First Name] —

I'm reaching out because Aragora is built for teams that are already using AI in real workflows, but still do not have a defensible way to review the output before it turns into action.

We run a multi-model debate on a real artifact — a PR, spec, inbox batch, or change proposal — and produce a signed receipt showing consensus, dissent, and provenance. The point is not "more agents." The point is making an AI-assisted decision something you can actually inspect, share, and approve.

Your team came to mind because [personalized reason tied to workflow or operating posture].

If this is relevant, I'd like to show you a 15-minute demo on one bounded workflow:
- review a real spec or PR before it ships
- triage a narrow inbox queue with receipt-before-action
- run one bounded engineering task through an approval-gated agent loop

Worth a look?

[Your Name]
```

#### Touch 2: Bump

Send 3-5 days later.

```text
Hi [First Name] —

Following up in case the first note got buried.

The narrow pitch is simple: pick one recurring workflow where being wrong is expensive, run it through Aragora, and see whether the receipt is good enough that your team would actually use it.

If useful, send me one real artifact and I can reply with the kind of output we would review together on a call.
```

#### Touch 3: Close The Loop

Send 5-7 days after Touch 2.

```text
Hi [First Name] —

I'll close the loop after this.

If reviewing AI-assisted decisions, inbox triage, or bounded agent execution becomes a priority this quarter, I think Aragora is worth a look. We are working with a small number of design partners who can start with one narrow workflow and a weekly operating loop.

If timing improves later, feel free to send over the workflow that is most painful today.
```

### 2. Warm Intro Follow-Up

Best for: when an investor, founder, operator, or mutual contact has already made the introduction.

#### Touch 1: Reply To The Intro

```text
Hi [First Name] — thanks [Mutual Name].

Good to meet you. I'm building Aragora, which helps teams put AI-assisted decisions through adversarial review before they ship or trigger action.

The practical wedge is narrow: take one recurring workflow that already creates anxiety or drag — design review, inbox triage, security review, or a bounded engineering lane — and turn it into a receipt-backed decision with explicit approval points.

From what [Mutual Name] mentioned, it sounds like [company] may care about [specific pain or workflow].

If that is right, I'd suggest a short working session rather than a generic intro call. You bring one real artifact or queue, and I'll show you what Aragora produces: consensus, dissent, provenance, and a clear decision trail.

Would sometime next week work?
```

#### Touch 2: Follow-Up If No Response

Send 3-4 days later.

```text
Hi [First Name] —

Wanted to send one tighter version of the ask.

If you send a real artifact — spec, PR, policy draft, or inbox slice — I can show you in one session whether Aragora is useful for your team's actual workflow, not an abstract future workflow.

If there is a fit, the next step is usually a small design-partner motion around one bounded recurring use case. If there is no fit, that becomes obvious quickly too.
```

### 3. Post-Demo Recap

Best for: same day or next morning after a live demo or working session.

#### Touch 1: Recap + Proposed Pilot

**Subject options**

- `Recap: Aragora for [company]'s [workflow]`
- `Next step on the [workflow] pilot`
- `Summary and proposed design-partner path`

```text
Hi [First Name] —

Thanks again for the time today. My understanding of the workflow we discussed:

- Current workflow: [brief description]
- Pain point: [latency, review load, auditability gap, false positives, manual triage, etc.]
- Why it matters: [business or operational consequence]

The reason I think Aragora fits is that we can keep the scope narrow:
- trigger: [what starts the workflow]
- artifact or queue: [what gets reviewed]
- output: receipt with consensus, dissent, provenance, and recommended action
- gate: [who approves or overrides]

For a first pilot, I'd recommend:
- one bounded recurring workflow
- 2-4 real artifacts in week one
- one weekly 30-minute operating loop
- success measured by time to first receipt, approval / override rate, and whether the receipt changed the decision

If that matches your read, the next step is to pick the first artifact set and schedule the kickoff.
```

#### Touch 2: Follow-Up On Next Step

Send 2-4 days later if needed.

```text
Hi [First Name] —

Checking in on the pilot next step.

The fastest path from here is:
1. choose the first bounded workflow
2. send 2-4 real examples
3. run the first receipt together

If helpful, I can also send a one-page version of the design-partner structure before we schedule anything further.
```

### Personalization Hooks

Use one of these in the first or second paragraph so the note feels grounded:

- `[company] is clearly operating with a high volume of decisions that do not cleanly fit a rules engine.`
- `You are already AI-native, which usually means the trust and review problem shows up before the tooling does.`
- `Your team seems to have both workflow complexity and real approval risk, which is exactly where receipt-backed review matters.`
- `I suspect the painful part is not generating options; it is knowing what to trust and what to escalate.`

### Short DM Variant

Use for LinkedIn, X, or a mutual Slack channel.

```text
Building Aragora for teams that want AI-assisted decisions reviewed before they turn into action. The narrow use case is: run a real artifact or queue through multi-model debate, get a receipt with consensus + dissent, then let a human approve. If you have one recurring workflow where being wrong is expensive, I'd be interested in showing you a live example.
```

---

## Part 2: Discovery Call Script

### Objective

Use this call to determine whether a prospect has a narrow, painful, recurring
workflow that Aragora can improve with adversarial AI review and decision
receipts.

The goal is not to pitch every feature. The goal is to leave with evidence on:

- the exact workflow
- how often it happens
- who owns it
- what failure costs today
- why existing AI or manual review is not enough
- whether the team can supply real artifacts and run a 4-6 week design partner loop

### Qualification Standard

Strong discovery calls produce all of the following:

- one concrete workflow, not a vague strategy discussion
- one painful recent example, not a hypothetical future use case
- one named champion, owner, or buyer
- one artifact path for a pilot: inbox batch, PR/spec, policy doc, backlog, or comparable input
- one reason trust, auditability, or dissent visibility matters

### 30-Minute Call Flow

| Segment | Time | Goal |
|---|---:|---|
| Opening | 2 min | Set expectations and de-risk the call |
| Workflow reconstruction | 8 min | Understand the current process in detail |
| Pain and consequence | 7 min | Surface stakes, delays, and failure cost |
| Fit diagnosis | 8 min | Map the workflow to Aragora's best proof surface |
| Close | 5 min | Confirm evidence, next step, and pilot viability |

### Opening Script

Use this opener:

> Thanks for making the time. This is a discovery call, not a product demo.
> I want to understand one workflow where AI-assisted decisions are high stakes,
> slow, or hard to trust. If there is a real fit, we can identify one narrow
> pilot and the evidence we would need to validate it.

Diagnostic questions:

- What is the single decision or review workflow you most want to improve right now?
- Why is that workflow painful enough to discuss today?
- If we only talked about one workflow on this call, which one matters most?

Red flags:

- They want a generic "AI strategy" conversation with no concrete workflow.
- They jump immediately to feature requests before describing the current problem.
- The pain is interesting but not active this quarter.

### Workflow Reconstruction

Ask for the most recent real example, not the ideal process:

> Walk me through the last time this happened from trigger to final decision.
> Pretend I am shadowing the operator.

Diagnostic questions:

- What triggers the workflow?
- What artifacts go in at the start?
- Who touches it before a decision is made?
- Where does disagreement show up today?
- What tools are involved: email, docs, GitHub, ticketing, internal systems?
- How many times per week or month does this happen?
- What is the median time from trigger to decision?
- What does a "done" output look like today?

Red flags:

- The workflow is rare, ad hoc, or dependent on one founder's intuition.
- There is no stable trigger, no repeatable input artifact, or no clear output.
- No one can describe the last real example with specifics.

### Pain and Consequence

Push past "it is inefficient" and get to consequence:

> Where does this workflow actually break today: latency, mistakes, rework,
> trust, audit, or politics?

Diagnostic questions:

- What is the most expensive failure mode?
- What happens when the wrong call is made?
- What is the cost of false positives versus false negatives?
- How much human review is required before anyone trusts the output?
- Where do people ask "why did we decide that?" after the fact?
- Has this caused a customer, compliance, security, legal, or leadership issue?
- If this improved by 50%, what would change in the business?

Red flags:

- The consequence is only "it would be nice to save time."
- Mistakes are cheap and reversable, so rigor is not valuable.
- There is no trust problem, no review bottleneck, and no audit burden.

### Fit Diagnosis: Choose One Proof Surface

Do not pitch all three surfaces equally. Pick the strongest fit and test it.

#### 1. Decision Review

Best when the prospect has high-stakes decisions that already require review:
specs, PRs, policies, architecture choices, risk memos, legal analysis.

Diagnostic questions:

- What artifacts already go through approval or sign-off?
- Where do reviewers disagree or miss edge cases?
- When a decision is challenged later, what evidence is missing?
- Would a receipt showing consensus, dissent, and provenance change anything?

Red flags:

- The team does not preserve decision artifacts.
- No one needs an audit trail, rationale, or dissent visibility.
- They really want content generation, not decision vetting.

#### 2. Autonomous Repo Improvement

Best when the prospect has a bounded engineering backlog with clear acceptance
criteria and strong merge discipline.

Diagnostic questions:

- What recurring engineering work is boring, bounded, and easy to verify?
- How are issues scoped and accepted today?
- What review gates are non-negotiable before merge?
- Would the team trust autonomous work only if it shipped with a receipt and review trail?

Red flags:

- They want unbounded autonomous coding without review policy.
- There is no issue hygiene, no acceptance criteria, or no owner.
- They want a general coding copilot, not governed execution.

#### 3. Inbox Trust Wedge

Best when the prospect triages high-volume inbound items where wrong actions are
costly: founder inbox, support escalations, security intake, partner requests.

Diagnostic questions:

- Who owns inbox or queue triage today?
- What volume arrives each day or week?
- Which actions are safe, and which require high confidence?
- What is the cost of misrouting, deleting, or acting on the wrong item?
- Could the team start with receipt-before-action on a narrow queue?

Red flags:

- The inbox volume is too low to matter.
- Wrong actions are harmless, so trust is not a meaningful problem.
- They want full automation before any review loop or receipt gate.

### Buyer and Design Partner Readiness

Confirm whether they can actually run a design partner process.

Diagnostic questions:

- Who would own a pilot internally?
- Who signs off on security, legal, or procurement questions?
- Can you provide sanitized real artifacts for one bounded workflow?
- Could you support a 30-minute onboarding and weekly 30-minute check-in for 4-6 weeks?
- Is there a deadline or forcing function this quarter?
- If the pilot works, what budget or buying path would exist?

Red flags:

- No internal champion with enough authority to provide artifacts or feedback.
- Procurement is long and heavy before any discovery or pilot can start.
- They want free consulting or roadmap influence without operational commitment.
- There is no near-term forcing function.

### Closing Script

Use this close:

> Based on what you described, the strongest starting point looks like
> [decision review / autonomous repo improvement / inbox trust]. To validate
> that, we would need one real artifact set, one success metric, and one owner.
> Does that sound accurate?

Then ask:

- What artifact could you share first?
- What metric would make this pilot clearly successful?
- Who needs to be in the next conversation?
- What is the right next step: follow-up discovery, live workflow review, or pilot design?

### Evidence To Capture After Every Call

Do not leave a call with only impressions. Capture evidence while the details
are still fresh.

#### Minimum Evidence Packet

| Field | What to capture |
|---|---|
| Contact | Name, title, company, email, date |
| Candidate workflow | One sentence naming the workflow |
| Proof surface | Decision review, autonomous repo improvement, or inbox trust |
| Pain statement | One verbatim quote describing the pain |
| Last real example | Specific recent incident with date or timeframe |
| Volume and frequency | Per day, week, or month |
| Decision stakes | Cost of wrong answer, delay, or lack of trust |
| Current process | Tools, handoffs, review path |
| Required artifact | Spec, PR, inbox batch, policy doc, backlog, or equivalent |
| Champion | Person who can drive a pilot |
| Constraints | Security, compliance, deployment, procurement, data sensitivity |
| Success metric | What would prove the pilot worked |
| Next step | Concrete follow-up and owner |

#### Evidence Standards

Capture at least:

- one direct quote in the prospect's own words
- one hard number: volume, SLA, review time, backlog size, or failure cost
- one concrete artifact the team can provide
- one concrete date: next meeting, deadline, audit, launch, or budget window

If you do not have those four things, the call probably stayed too abstract.

### Post-Call Scorecard

Score each category 0-3.

| Category | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| Problem intensity | Nice to have | Mild pain | Active pain | Acute pain with visible cost |
| Workflow repeatability | Ad hoc | Occasional | Recurring | High-volume recurring |
| Trust or audit need | None | Weak | Clear | Mission-critical |
| Artifact readiness | None | Possible later | Sanitized examples | Real artifacts ready now |
| Champion strength | Curious observer | Informal contact | Operational owner | Owner with budget influence |
| Urgency | No timeline | Someday | This quarter | Immediate forcing function |

Interpretation:

- 14-18: strong design partner candidate
- 9-13: keep warm, gather more evidence
- 0-8: not a current fit

### Hard Disqualifiers

Do not force a pilot when these are true:

- no recurring workflow
- no owner
- no artifact access
- no measurable consequence for wrong decisions
- desire for unbounded autonomous action without governance
- interest driven only by curiosity, not operational pain

### Interviewer Notes

- Ask about the last real instance before asking about the ideal future.
- Prefer exact numbers over adjectives like "a lot" or "slow."
- Keep re-centering on one workflow.
- If the prospect spans multiple use cases, choose one and defer the rest.
- Do not leave the call without a next step or a clear disqualification reason.

---

## Part 3: Pilot Structure

### Pilot Shape

The pilot is a **single-workflow proof**, not a platform rollout.

- one workflow
- one internal champion
- one primary integration surface
- one agreed operating metric
- one weekly decision loop

The workflow can be one of:

1. **Decision review:** receipt-backed review of specs, PRs, architecture
   proposals, or policy drafts.
2. **Inbox trust wedge:** receipt-before-action triage on a bounded inbox or
   label queue.
3. **Bounded backlog lane:** receipt-gated execution on a small, pre-approved
   class of work.

### Scope Boundaries

#### In scope

- a recurring workflow with a clear trigger
- real partner artifacts, with sanitization if needed
- one team or one function
- founder-led onboarding and weekly tuning
- policy, prompt, and workflow iteration required to make the chosen wedge work

#### Out of scope

- multi-team rollout
- broad systems integration program
- autonomous merge authority in the partner's production codebase
- open-ended custom feature development unrelated to the chosen wedge
- enterprise procurement, security review, or compliance sign-off beyond pilot
  evidence

### Duration

Default pilot length: **4 weeks**.

- **Week 1:** kickoff, workflow definition, baseline metric capture, first live
  receipt
- **Week 2:** repeated use on real work, friction logging, prompt/policy tuning
- **Week 3:** stabilize the loop, confirm operator trust, measure time/risk
  delta
- **Week 4:** decision review, written results, expansion or stop

The pilot may extend to **6 weeks max** only if both sides agree there is a
credible path to success and the extension has a specific blocker-removal goal.

### Success Criteria

The pilot succeeds only if all of the following are true:

1. **Time-to-value is real:** first live receipt lands within 7 calendar days
   of kickoff.
2. **Usage is real:** the team completes at least 8 receipt-backed runs during
   the pilot, or at least 3 full cycles for a naturally lower-frequency
   workflow.
3. **Operational value is measurable:** one agreed primary metric improves.
   Examples:
   - review or triage turnaround improves by at least 30%
   - manual audit-evidence packaging drops materially
   - previously blocked work moves with higher confidence and lower reviewer
     load
4. **Trust is real:** the partner champion says the receipt changed or improved
   at least one real decision, not just that the output was interesting.
5. **Expansion is credible:** the closing review ends with either paid
   continuation or a clearly defined next wedge.

### Failure Criteria

The pilot is a failure and should stop if any of the following are true:

1. No first live receipt by day 7.
2. The workflow still requires repeated founder-side manual rescue after week 2.
3. Receipt quality is not trusted enough to influence a real decision.
4. The agreed metric does not move enough to justify continued usage.
5. The partner cannot supply enough real artifacts or champion attention to run
   the pilot honestly.
6. The work widens into custom services instead of product validation.

### Founder Promises

The founder is not a distant sponsor for the pilot. The founder personally
commits to:

1. Run kickoff and define the exact workflow, scope boundary, and primary
   metric with the partner champion.
2. Join the first live run and make sure a real receipt is produced on a real
   artifact.
3. Review pilot failures and friction every week, with a written summary of
   what changed and what remains blocked.
4. Personally ship, or directly supervise, pilot-critical fixes and prompt or
   policy adjustments.
5. Stay reachable as the escalation path for trust, workflow design, and
   go/no-go decisions.
6. End the pilot honestly if the value is not emerging, instead of extending it
   to protect optics.

### Closing Decision

At the end of week 4, the pilot must end in one of three explicit outcomes:

- **Expand:** the chosen wedge worked and a second bounded workflow is defined.
- **Convert:** the partner wants to keep the current wedge running under a paid
  arrangement.
- **Stop:** the workflow did not earn expansion and both sides document why.

There should be no ambiguous "keep trying" state without a new bounded goal and
owner.

---

## Part 4: First-Week Journey

### Week-One Outcome

At the end of week one, the partner should have:

- one bounded recurring workflow selected
- one real artifact or inbox batch run through Aragora
- one visible receipt with evidence, dissent, and next action
- one explicit human decision: act, reject, or hold
- one truthful understanding of what Aragora can and cannot yet automate for them

This is the first trustworthy result. It is not "full autonomy." It is a
receipt-backed decision on a narrow workflow with explicit stop reasons.

### Default Week-One Workflow Choice

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

### Journey

| Day | Objective | What happens | Evidence produced |
|---|---|---|---|
| Day 0 | Qualify the lane | Pick one recurring workflow, one owner, one success metric, and 3-10 representative artifacts | named workflow, owner, sample inputs, success metric |
| Day 1 | Setup and readiness | Connect provider credentials, confirm product surface access, and run the quickstart path or live demo path | successful setup transcript, readiness status, first receipt ID |
| Day 2 | Establish the trust contract | Explain the workflow-specific truth boundary, operator role, approval points, and stop conditions before real use | written truth boundary, operator checklist, blocked states |
| Day 3 | Run the first real artifact | Use a real partner artifact or inbox batch in a narrow lane; keep action gated by a human | debate output, visible receipt, dissent trail, cited evidence |
| Day 4 | Review quality and friction | Compare receipt usefulness against the partner's current process and note missing evidence or unclear output | issue list, friction notes, trust blockers |
| Day 5 | Produce the first trustworthy result | Re-run on the same workflow with any fixes or tighter scope so the partner can make one real decision from the receipt | receipt-backed decision, decision owner, action taken or rejected |
| Days 6-7 | Lock the repeatable loop | Schedule the recurring trigger, define who reviews receipts, and set the expansion rule for week two | recurring cadence, weekly metric, next-scope rule |

### Stage Details

#### Day 0: Qualify the lane

The partner must arrive with one concrete workflow, not a vague "use AI
better" objective.

Required inputs:

- one champion who can review results
- one recurring trigger such as a new PR, design doc, or inbox batch
- one bounded artifact set that can be sanitized if needed
- one success metric such as review latency, triage time, or defect catch rate

If the workflow has no clear trigger or owner, stop before setup. That is a
sales/discovery problem, not a product problem.

#### Day 1: Setup and readiness

The first day should prove that the partner can reach a live Aragora path
without hidden manual rescue.

Minimum setup proof:

- credentials configured
- the chosen workflow surface is reachable
- a receipt is created and visible on a product or CLI surface
- the run either completes or stops with a direct reason

If setup succeeds only through internal shell surgery or undocumented fallback,
the workflow is not ready for partner week one.

#### Day 2: Establish the trust contract

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

#### Day 3: Run the first real artifact

Use the partner's real workflow in the safest shape that still matters.

Examples:

- review one real spec or PR and decide whether it is ready for human approval
- triage one real inbox batch in `--dry-run` before any side effects
- execute one bounded repo task behind review gates

The output must be visible to the partner, not just to Aragora operators.

#### Day 4: Review quality and friction

The point is not to defend the output. The point is to find whether the
partner can understand why Aragora advanced, hesitated, or stopped.

Questions to answer:

- did the receipt contain enough evidence to support a decision
- was the dissent trail useful or noisy
- did the stop reason reduce operator confusion
- what part of the workflow still felt "demo-shaped"

#### Day 5: Produce the first trustworthy result

A trustworthy result in week one means:

- the task was real
- the scope was narrow
- the receipt was visible
- the evidence and dissent were understandable
- the human could take or reject an action with a documented reason

This can be a "do not act" result. A truthful stop is acceptable. A silent or
hand-waved stop is not.

#### Days 6-7: Lock the repeatable loop

Week one is only complete when the partner knows how the next run will happen.

Define:

- trigger: what event causes the next run
- reviewer: who reads the receipt
- action policy: what can happen automatically, with approval, or never
- expansion rule: what must be proven before widening scope

### Explicit Truth Boundaries

These are the boundaries Aragora should state plainly to a new design partner.

#### What Aragora can truthfully claim in week one

- It can run a bounded workflow through a multi-agent debate or gated execution path.
- It can produce a receipt with provenance, dissent, and visible output.
- It can stop with a specific blocker instead of pretending work is complete.
- It can keep approval and merge/action gates explicit.
- It can help the partner review consequential artifacts faster and with a better audit trail.

#### What Aragora must not claim in week one

- It does not guarantee that the winning answer is correct in the real world.
- It does not eliminate the need for a responsible human approver.
- It is not yet proving safe broad autonomy across an entire organization.
- It is not a substitute for pentest, certification, or regulated sign-off.
- It should not claim trustworthiness if the receipt is missing, hidden, or unsupported by evidence.

#### Hard stop conditions

Stop or downgrade the workflow if any of these are true:

- the partner cannot see the receipt or stop reason
- the evidence used is incomplete, stale, or obviously irrelevant
- human approval points are ambiguous
- the system needs undocumented operator rescue to finish the run
- the workflow widens from one bounded lane into general automation

### Week-One Exit Gate

Do not call the partner "live" until all of the following are true:

- one real workflow is named and owned
- one setup path completed on the partner's environment
- one real receipt-backed run completed or stopped truthfully
- one human reviewer used the receipt to make a real decision
- one list of trust blockers and next actions is written down

### Expansion Rule For Week Two

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

---

## Part 5: Onboarding Readiness Checklist

### Goal

Define the minimum bar Aragora must satisfy before inviting the next design
partner into the live founder loop.

This checklist is intentionally stricter than an internal dogfood pass and
intentionally narrower than enterprise readiness. The question is not "is the
whole platform complete?" The question is "can a founder-led live session run
truthfully, produce value quickly, and end with a credible next step for the
partner?"

### Scope And Assumptions

- This is for a founder-led live session, not a fully self-serve onboarding
  funnel.
- The session uses the **live founder loop** as the primary workflow.
- The inbox trust wedge may be shown only as a secondary proof, not as the
  onboarding dependency.
- Manual founder guidance is allowed; hidden product rescue is not.
- The bar is one trustworthy external design-partner session on current `main`,
  not broad PMF proof or enterprise certification.

### Exit Rule

Do not invite the next design partner until every **must-pass** item below is
green with linked evidence. If a must-pass item fails, record the exact blocker,
owner, and next verification step instead of widening scope.

### Must-Pass Checklist

#### 1. Live founder-loop execution is still proven on current `main`

- [ ] Run the canonical founder-loop command on current `main` and capture the
  exact command transcript.
- [ ] Complete **5 consecutive live runs** without hidden manual rescue.
- [ ] Keep runtime inside the current demonstrated band or explain the
  regression explicitly if it widens beyond it.
- [ ] Confirm each run ends in one of two truthful states only:
  - useful result delivered
  - direct blocker with precise stop reason

Evidence:
- command transcript
- run times for all 5 runs
- receipt paths or URLs for all 5 runs

#### 2. Readiness and fail-closed behavior are externally legible

- [ ] Readiness state is visible before the session starts.
- [ ] Provider and credential state are explicit; no ambient shell magic is
  required to explain why the run can proceed.
- [ ] If the environment is not ready, Aragora fails closed quickly with a
  direct reason rather than silently dropping to demo behavior.
- [ ] The founder can show the partner where the system reports readiness and
  what "not ready" looks like.

Evidence:
- readiness output or screenshot
- one verified failure-mode example with the exact surfaced message

#### 3. Receipt and result visibility work on product surfaces

- [ ] Every live run emits a structured receipt that can be inspected and
  verified.
- [ ] The resulting receipt is visible on at least one product surface the
  partner can inspect during the session.
- [ ] The founder can move from completed run to visible receipt/result without
  ad hoc spelunking.
- [ ] Share-link or API visibility is stable enough to use in a live demo.

Evidence:
- receipt verification output
- screenshot or URL of the visible receipt/result surface

#### 4. The session reaches first value fast enough to feel productized

- [ ] Time from fresh session start to first useful result is consistently short
  enough for a live call.
- [ ] The founder has one canonical prompt/topic that reliably demonstrates the
  wedge.
- [ ] The partner can substitute their own consequential question without
  breaking the flow contract.
- [ ] Operator noise is bounded: logs, warnings, or summaries do not force the
  founder to explain away obvious product roughness mid-demo.

Evidence:
- timed rehearsal from fresh start
- canonical demo prompt
- one partner-style custom prompt rehearsal

#### 5. The product story matches the actual behavior

- [ ] The founder can explain, in one short paragraph, why Aragora is better
  than a single execution substrate for this session.
- [ ] The demonstrated wedge is receipts, provenance, disagreement, and truthful
  stopping behavior, not generic model breadth.
- [ ] Known limitations are stated plainly before or during the session when
  relevant.
- [ ] The product surface shown in the session matches the current roadmap truth
  and does not imply enterprise readiness that does not exist yet.

Evidence:
- demo script or talk track
- list of limitations the founder will say out loud

#### 6. Partner-safe operating discipline exists

- [ ] There is a single named founder/operator for the session.
- [ ] There is a session checklist for preflight, live operation, and follow-up.
- [ ] The founder knows the fallback path if the primary provider or workflow
  fails during the call.
- [ ] A post-call artifact is defined: receipt pack, notes, blockers, and next
  action.

Evidence:
- founder session runbook
- fallback path note
- post-call artifact template

### Should-Pass Checklist

These do not block the invite on their own, but they materially improve the
quality of the session and should be pushed toward green.

- [ ] Inbox trust wedge has at least one real dogfood proof on a live inbox.
- [ ] Fresh-user onboarding is timed and documented under 10 minutes.
- [ ] A second operator can reproduce the session without private founder
  context.
- [ ] The partner can access a small proof pack after the call without manual
  reconstruction.

### Evidence Pack Required Before Invite

Before sending the invitation, assemble one compact evidence pack containing:

- latest 5/5 founder-loop proof
- readiness screenshot or transcript
- one verified receipt and one visible product-surface result
- canonical demo prompt and fallback prompt
- known limitations / truthful caveats
- named owner for the live session

If this pack cannot be assembled in under 15 minutes, readiness is still too
fragile for the next design-partner invite.

### Explicit Non-Gates

The following are important, but they are **not** blockers for the next
founder-led design-partner session:

- full enterprise hardening
- pentest completion
- SOC 2 completion
- broad connector coverage
- full self-serve onboarding for every user type

Those remain downstream of design-partner validation, not prerequisites for it.

### Open Questions

- Should the next design partner see only the founder loop, or should the call
  also include the inbox trust wedge as a second proof?
- What exact runtime ceiling still feels acceptable on a live call: 60 seconds,
  90 seconds, or "truthful if longer"?
- Which product surface is the canonical receipt/result view during the call:
  CLI, dashboard, or share link?

### Next Actions

1. Rehearse the founder loop on current `main` and collect the 5-run evidence
   pack.
2. Write the founder session runbook that maps directly to this checklist.
3. Dogfood the inbox trust wedge separately so it can be shown as optional
   follow-on proof, not onboarding risk.
4. Invite the next design partner only after all must-pass items are green with
   evidence links.

---

## Part 6: Case Study Template

Use this document as the canonical case-study working file for every design
partner from kickoff onward. It is intentionally not just a polished marketing
outline. It is the evidence ledger, operating log, and final packaging shell in
one place so we do not have to reconstruct proof after the fact.

### How To Use This Template

1. Duplicate this section at partner kickoff and rename it with the partner
   codename or approved company name.
2. Fill the "Partner Snapshot" and "Workflow Under Proof" sections before the
   first live run.
3. Update the "Evidence Log," "Metrics Scorecard," and "Timeline" sections
   after every meaningful milestone or weekly check-in.
4. Treat every external-facing claim as invalid until it is backed by a linked
   artifact, quote, metric source, or receipt.
5. If a claim is directionally true but not yet proven, mark it `Unverified`
   instead of smoothing over the gap.

### Evidence Rules

- Every quantified claim must name the source of truth.
- Every qualitative claim should include a dated quote, call note, or email.
- Every workflow claim should point to at least one concrete artifact:
  receipt, PR, decision log, inbox batch, spec, or screenshot.
- Preserve failures, reversals, and stop conditions. A case study that only
  records wins is not trustworthy sales proof.
- Do not publish company name, logos, or quotes until approval is explicit.

### Document Control

| Field | Value |
|---|---|
| Partner codename | [partner-codename] |
| Approved company name | [company-name or TBD] |
| Industry / segment | [regulated SaaS / fintech / healthtech / platform team / other] |
| Primary workflow | [workflow name] |
| Internal owner | [Aragora owner] |
| Partner champion | [name, role] |
| Kickoff date | [YYYY-MM-DD] |
| Current phase | [kickoff / onboarding / live proof / expansion / published / paused] |
| Publication status | [internal only / anonymized allowed / named allowed] |
| Last updated | [YYYY-MM-DD] |

### 1. Executive Summary

Write this section only after enough evidence exists to support it.

- One-sentence partner situation: [what was broken before Aragora]
- One-sentence Aragora wedge: [what bounded workflow Aragora handled]
- One-sentence outcome: [what measurably improved and over what window]
- Current confidence level: [Anecdotal / Early signal / Strong internal proof / Publishable]

### 2. Partner Snapshot

#### Team Context

- Company stage: [seed / growth / enterprise / internal platform team]
- Team size relevant to workflow: [number]
- Compliance or risk context: [none / SOC 2 / HIPAA / EU AI Act / internal audit / other]
- Existing tools in the loop: [Slack, GitHub, Gmail, ticketing, docs, internal systems]
- Why they said yes to a design partnership: [pain + urgency]

#### Pain Before Aragora

- Primary bottleneck: [review latency / triage overload / audit evidence gap / bounded backlog throughput / other]
- Frequency of the workflow: [times per day/week]
- What failure looked like before: [missed issue, manual burden, slow approval, no audit trail]
- Why the incumbent process was not enough: [single-model trust gap, fragmented evidence, too much manual review]

### 3. Workflow Under Proof

#### Workflow Definition

| Field | Value |
|---|---|
| Workflow name | [short name] |
| Trigger | [what causes a run] |
| Input artifact | [PR / inbox batch / design doc / backlog slice / other] |
| Human decision boundary | [what human still approves] |
| Aragora action boundary | [what Aragora does autonomously] |
| Stop condition | [when Aragora must halt truthfully] |
| Failure cost if wrong | [low / medium / high + note] |

#### Success Contract

| Metric | Baseline | Target | Measurement method | Source of truth |
|---|---|---|---|---|
| Time to first vetted outcome | [value] | [value] | [how measured] | [link or system] |
| Manual touches per workflow | [value] | [value] | [how measured] | [link or system] |
| Receipts captured per workflow | [value] | [value] | [how measured] | [link or system] |
| Rework / escalation rate | [value] | [value] | [how measured] | [link or system] |
| Trust signal | [value] | [value] | [survey / quote / adoption] | [link or note] |

#### Proof Surface

Mark the primary wedge being validated:

- [ ] Decision review
- [ ] Autonomous repo improvement
- [ ] Inbox trust wedge
- [ ] Other bounded workflow: [name]

### 4. Baseline Before Aragora

#### Previous Process

Describe the pre-Aragora workflow in 5-8 lines. Include who touched the work,
where evidence lived, how long it usually took, and where trust broke down.

#### Baseline Evidence

| Evidence type | Date | Summary | Link / location | Confidence |
|---|---|---|---|---|
| Call note | [YYYY-MM-DD] | [summary] | [link] | [high/medium/low] |
| Existing KPI export | [YYYY-MM-DD] | [summary] | [link] | [high/medium/low] |
| Email / Slack quote | [YYYY-MM-DD] | [summary] | [link] | [high/medium/low] |
| Screenshot / dashboard | [YYYY-MM-DD] | [summary] | [link] | [high/medium/low] |

### 5. Deployment Timeline

| Date | Milestone | What happened | Evidence link | Notes |
|---|---|---|---|---|
| [YYYY-MM-DD] | Kickoff | [scope agreed] | [link] | [note] |
| [YYYY-MM-DD] | First live run | [what ran] | [link] | [note] |
| [YYYY-MM-DD] | First trusted outcome | [what changed] | [link] | [note] |
| [YYYY-MM-DD] | Expansion / rollback | [what changed] | [link] | [note] |
| [YYYY-MM-DD] | Publication decision | [approved / anonymized / deferred] | [link] | [note] |

### 6. Evidence Log

This is the core section. Add rows continuously. Each row should support a
claim we may want to make later.

| Date | Claim or observation | Artifact type | Link / location | Supports which future claim? | Confidence | Public-safe? |
|---|---|---|---|---|---|---|
| [YYYY-MM-DD] | [example: first receipt used in real approval path] | [receipt / PR / transcript / metric / screenshot / quote] | [link] | [example: Aragora entered the real workflow] | [high/medium/low] | [yes/no] |

### 7. Metrics Scorecard

Update this table at a fixed cadence, ideally weekly.

| Metric | Baseline | Current | Delta | Observation window | Source of truth | Notes |
|---|---|---|---|---|---|---|
| Time to vetted decision | [value] | [value] | [value] | [date range] | [link] | [note] |
| Manual review steps | [value] | [value] | [value] | [date range] | [link] | [note] |
| Workflows completed with receipts | [value] | [value] | [value] | [date range] | [link] | [note] |
| False positives / bad recommendations | [value] | [value] | [value] | [date range] | [link] | [note] |
| Human overrides | [value] | [value] | [value] | [date range] | [link] | [note] |
| Operator confidence / trust score | [value] | [value] | [value] | [date range] | [survey or note] | [note] |

### 8. What Aragora Actually Did

Describe the live workflow, not the aspirational one.

- Models or agent types used: [list]
- Trigger and run frequency: [detail]
- Human checkpoints: [detail]
- Output artifacts produced: [receipts / comments / labels / PRs / summaries / other]
- Where results were visible: [dashboard / API / Slack / GitHub / inbox / other]
- What was still manual: [detail]
- What Aragora stopped on truthfully: [detail]

### 9. Trust, Dissent, And Failure Notes

This section is mandatory. It prevents the case study from collapsing into
marketing theater.

#### Notable Successes

- [example: partner adopted receipt as default review artifact]
- [example: dissent surfaced a risk the initial recommendation missed]

#### Notable Failures Or Stops

- [example: missing context caused a false escalation]
- [example: integration gap forced manual fallback]
- [example: workflow remained too high-risk for autonomous action]

#### What We Learned

- [product insight]
- [go-to-market insight]
- [scope boundary insight]

### 10. Quotes

Only include quotes with source and approval status.

| Date | Speaker | Quote | Source | Approval status | Public-safe? |
|---|---|---|---|---|---|
| [YYYY-MM-DD] | [name, role] | "[quote]" | [call / email / Slack / interview] | [pending / approved / rejected] | [yes/no] |

### 11. Draft Case Study Narrative

Fill this section only when the evidence above is strong enough.

#### Headline

[One-line measurable transformation]

#### Subhead

[Who the partner is, what workflow Aragora handled, and what changed]

#### Before Aragora

[3-5 lines]

#### Why Aragora Won This Workflow

[3-5 lines on receipts, dissent, bounded autonomy, or trust surface]

#### Measured Outcomes

- [outcome with metric and timeframe]
- [outcome with metric and timeframe]
- [qualitative outcome with quote or evidence]

#### Truthful Boundaries

- [what Aragora still does not automate here]
- [what still requires a human]
- [what evidence is strong vs early]

### 12. Publication Checklist

- [ ] Every material claim links to evidence in this document
- [ ] Metrics are reproducible from a named source of truth
- [ ] At least one failure, stop, or boundary is documented
- [ ] Quote approvals are explicit
- [ ] Naming / logo permissions are explicit
- [ ] The workflow described is the real live workflow, not roadmap fiction
- [ ] The final story matches the strongest evidence, not the most flattering framing

### Appendix A: Artifact Index

List every raw artifact we may need later.

| Artifact | Type | Date | Owner | Link / location | Included in final story? |
|---|---|---|---|---|---|
| [artifact name] | [receipt / transcript / export / screenshot / PR / email] | [YYYY-MM-DD] | [owner] | [link] | [yes/no] |

### Appendix B: Open Questions

- [What still needs to be measured?]
- [What approval is still missing?]
- [What claim do we suspect is true but cannot yet support?]

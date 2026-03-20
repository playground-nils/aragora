# Design Partner Program (Q2 2026)

Last updated: 2026-03-20

This document defines the Q2 2026 design partner program for achieving product-market fit (PMF) around Aragora's receipt-gated decision kernel. The partner motion should now be anchored to the product surfaces that are real on `main`: the inbox trust wedge, the Ralph autonomous loop, and supervisor-backed swarm orchestration. The SME Starter Pack remains a useful activation target, but it is no longer enough to describe the whole program.

Related:
- Current status: `docs/STATUS.md`, `docs/status/STATUS.md`
- Capability/backlog truth: `docs/FEATURE_GAP_LIST.md`
- Canonical execution order: `docs/status/NEXT_STEPS_CANONICAL.md`
- PMF scoring rubric: `docs/status/PMF_SCORECARD.md`
- Inbox trust wedge dogfood plan: `docs/plans/2026-03-06-openrouter-inbox-dogfood-plan.md`
- Ralph benchmark evidence: `docs/experiments/phase0b_role_benchmark/results.json`

---

## Current Product Truth

Aragora's core kernel is now:

`prompt/spec -> adversarial debate -> consensus/dissent -> signed receipt -> policy/approval gate -> execution`

Current partner-facing proof surfaces:

### 1. Inbox Trust Wedge
- Real path: `Gmail -> adversarial debate -> signed receipt -> CLI approval -> gmail.modify`
- Narrow allowed actions are already defined: `ARCHIVE`, `STAR`, `LABEL`, `IGNORE`
- Core claim: Aragora can take low-risk operational actions only after a persisted receipt and an explicit approval policy

### 2. Ralph Autonomous Loop
- Supervisor-backed repo improvement loop for bounded tasks
- Current loop shape: `spec -> deliverable -> review -> blocker classification -> repair -> PR -> merge`
- Core claim: Aragora can autonomously complete bounded engineering work, recover from critique, and advance toward merge under explicit policy

### 3. Swarm Orchestration
- Supervisor, worker launcher, reconciler, work leases, and completion receipts are shipped
- Current posture: bounded work orders, isolated worktrees, one PR-or-blocker stop condition, integrator-controlled merge authority
- Core claim: Aragora can coordinate multi-lane execution while preserving ownership, receipts, and operator visibility

### V14 Benchmark: Proof Of Autonomous Capability

The strongest current proof point for design partners is the Ralph V14 benchmark:

- Full autonomous loop validated: `spec -> deliverable -> review -> blocker classification -> repair -> PR -> admin merge`
- Zero operator intervention for the successful benchmarked path
- Cross-model review rejected two attempts and passed the third
- PR creation and merge completed autonomously
- The benchmark closed the loop for `merge_policy=admin_merge_allowed`

Use this as proof that Aragora can autonomously execute bounded work under policy. Do not pitch it as proof of unrestricted autonomy across broad external actions.

---

## Dogfood Learnings That Change The Program

Internal dogfooding narrowed what a good design partner looks like:

- Start with one painful recurring workflow, not a broad platform rollout.
- Keep the allowed action surface narrow until override and quality metrics are good.
- Keep human approval available on higher-impact paths; receipt-before-action is non-negotiable.
- The live debate plus receipt is the artifact users trust first; downstream planning automation is supporting instrumentation until proven in that workflow.
- Expansion should happen by consecutive bounded wins, not by narrative confidence.

These learnings should change both partner selection and pilot design.

---

## Program Goals

### Outcomes (Q2 2026)
- 3-5 active design partners each running one bounded workflow through Aragora weekly.
- 2 publishable case studies (anonymized if required) with hard metrics from current surfaces:
  - time to first receipt
  - override rate / approval rate
  - bounded-task completion rate
  - decision changed or escalation avoided
- Clear conversion path for each partner: paid pilot, LOI, or security/procurement green light.
- Product clarity: one default activation path per surface:
  - trust wedge
  - Ralph/swarm operator lane
  - receipt-gated design/review workflow

### Non-Goals (for this program)
- Broad connector expansion not tied to a current proof surface.
- Broad autonomous actioning with no receipt gate or human approval path.
- Multi-surface pilots at the same partner before one recurring workflow is sticky.
- Selling a generic "AI agents platform" story detached from current shipped behavior.

---

## Ideal Design Partner Profile (ICP)

Use the ICP checklist in `docs/status/POSITIONING.md` as the base, but apply the following dogfood-adjusted criteria first.

### Minimum Criteria
- Has one bounded recurring workflow with a clear trigger, owner, and success/failure outcome.
- Feels real pain from review latency, manual triage, audit evidence work, or bounded engineering backlog throughput.
- Has a clear champion who can provide artifacts, review receipts, and join a weekly operating loop.
- Has an accountable decision owner or approver for the workflow.
- Can start with a narrow receipt-gated workflow instead of demanding broad end-to-end autonomy on day 1.
- Can provide real artifacts in the first week:
  - inbox slice
  - design doc
  - policy/control requirement
  - bounded backlog issue / PR / release plan
- If the pilot is on the Ralph/swarm surface, the partner can provide bounded tasks, file-scope expectations, tests or acceptance criteria, and an explicit merge/review policy.

### Best-Fit Segments
- Regulated SaaS, FinTech, and HealthTech teams that need audit-ready receipts for technical or compliance decisions.
- Platform, security, or developer-productivity teams with recurring bounded hardening or review workflows.
- Founder-led or operator-heavy teams with painful inbox triage and willingness to start in a CLI-first, approval-gated loop.
- AI-native teams already using multiple LLMs and frustrated by single-model trust gaps.

### Anti-ICP
- Prospects asking for broad autonomous execution with no human gate on the initial rollout.
- Teams with only ad hoc quarterly decisions and no recurring workflow trigger.
- Organizations that cannot provide real artifacts or a weekly champion.
- Buyers looking for a dashboard demo but unwilling to run a real workflow.

### Target Roles
- Primary: CTO, VP Engineering, Head of Platform, Head of Security, Founder/Operator
- Secondary: CISO, Security Engineering lead, GRC lead, Head of AI Governance, Engineering Productivity lead

---

## Program Structure

### Partner Commitments
- 1 kickoff (60-90 min)
- 1 guided "magic moment" session (60 min)
- Weekly check-in (30 min) for 4-6 weeks
- Provide 2-4 real artifacts (sanitized if needed):
  - inbox batch or triage policy
  - architecture or change proposal
  - policy or compliance requirement
  - incident postmortem / "we should have caught this" example
  - one bounded repo issue, PR, or release plan

### What Aragora Commits To
- Hands-on onboarding support through first receipt and first recurring workflow.
- Surface-specific activation:
  - trust wedge: configure the inbox path, validate receipt persistence before action, and measure overrides
  - Ralph/swarm: define one bounded lane with file scope, stop condition, and merge policy
  - decision review: run one real artifact through debate plus receipt export and internal sharing
- Weekly iteration loop: capture friction, fix the top 1-2 issues, re-validate.
- A receipt package that is:
  - shareable (Slack/email/PR comment)
  - exportable (PDF/MD/JSON where supported)
  - verifiable (receipt integrity checks)

### Confidentiality & Data Handling
- Default to sanitized artifacts.
- If full artifacts are required, use self-hosted deployment and restrict logs.
- Document data boundaries in a one-page pilot data policy before kickoff.

---

## Timeline (Calendar Dates)

Current date: 2026-03-20.

Recommended Q2 2026 cadence:
- Weeks of 2026-04-06 and 2026-04-13: outreach, qualification, and surface mapping
- Weeks of 2026-04-20 and 2026-04-27: select 3-5 design partners, kickoff, and reach first receipt
- Weeks of 2026-05-04 through 2026-06-12: weekly operating loop, PMF scorecards, and proof capture
- Weeks of 2026-06-15 and 2026-06-22: case study drafting, pricing/procurement closure, and Q3 scope decision

---

## Interview Scripts

### Script 1: Discovery Call (45 minutes)

Goal: confirm ICP fit, quantify pain, and identify the first bounded workflow to pilot.

1. Context
   - "What decisions or actions in your org can hurt you if they're wrong?"
   - "Who approves them today?"
   - "How often does this happen: daily, weekly, or monthly?"

2. Current workflow
   - "Walk me through the last time this workflow happened."
   - "What artifact or queue kicked it off?"
   - "Where does the approval actually happen: inbox, Slack, PR, meeting, ticket, or doc?"

3. Dogfood fit
   - "Could we start with one narrow allowed action surface instead of the whole workflow?"
   - "Who would review the receipt or approve the action during the pilot?"
   - "Can you give us a real example in the first week?"

4. Existing tooling and constraints
   - "What are you using today: code review, GRC tools, inbox rules, ticket queues, internal AI tools?"
   - "Can you self-host? Any restrictions on cloud tools?"
   - "Do you require SSO, audit logging, or explicit approval checkpoints?"

5. Success criteria
   - "If Aragora works, what changes in 30 days?"
   - "What would make this painful to turn off?"
   - "What would you pay to make this workflow faster, safer, or more defensible?"

Capture:
- 1 primary workflow for the pilot
- Best initial surface: trust wedge, Ralph/swarm, or receipt-gated review
- 1-2 real artifacts to run in the demo session
- Buyer map: champion, economic buyer, security approver, day-to-day operator

### Script 2: "Magic Moment" Demo Session (60 minutes)

Goal: run a real artifact end-to-end and produce a receipt the partner can share internally.

Agenda:
- 10 min: confirm the workflow, artifact, and approval path
- 25 min: run one current surface live
  - trust wedge: triage a real inbox item end-to-end
  - Ralph/swarm: run one bounded backlog lane through dispatch, review, and receipt
  - decision review: run Gauntlet or multi-agent review on a real design/PR artifact
- 15 min: review findings, dissent, confidence, and what changed their mind
- 10 min: export/share the receipt and define the next recurring run

Key questions:
- "Would you trust this output enough to keep a human approval gate on top of it next week?"
- "Which finding or classification would have changed what your team did?"
- "Who else needs to see this receipt for it to matter?"

Artifacts to produce:
- Receipt export (PDF + MD or JSON where relevant)
- One surface-specific proof artifact:
  - trust wedge: approval vs override outcome
  - Ralph/swarm: bounded-lane result plus blocker/repair trail
  - decision review: decision summary with dissent and evidence

### Script 3: Pilot Kickoff (60 minutes)

Goal: define pilot scope, measures, and cadence.

1. Pick the first recurring workflow
   - trigger: "new inbox batch", "new architecture proposal", "release candidate", "bounded backlog issue", "policy update"
   - frequency: daily or weekly is ideal
   - owner: one person who runs it every time

2. Define integration + deployment mode
   - hosted vs self-hosted
   - Gmail / Slack / GitHub / docs path, depending on the surface
   - explicit human approval and merge policy for higher-impact actions

3. Define "success in 4 weeks"
   - quantitative: time saved, lower override rate, more receipts generated, bounded-task completion, fewer escalations or rework loops
   - qualitative: confidence, audit readiness, decision clarity, "painful to turn off"

4. Agree on the weekly loop
   - 30 min: usage, overrides, friction, and PMF score review
   - 30 min: choose the next improvements in product, prompts, docs, or deployment

---

## Program Artifacts (What We Maintain)

- A running score per partner using `docs/status/PMF_SCORECARD.md`
- The chosen surface and workflow trigger for each partner
- First-receipt timing, approval/override metrics, and weekly usage evidence
- A list of top onboarding blockers and the exact reproduction path
- A weekly changelog of pilot-driven fixes (link to PRs/commits if used)

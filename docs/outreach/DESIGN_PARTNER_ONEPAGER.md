# Aragora: Design Partner Brief

**Stop shipping AI-assisted decisions you can't explain.**

Aragora governs consequential AI-assisted work with multi-model review,
decision receipts, and truthful gates, so teams can move faster without losing
provenance or human control.

Last updated: 2026-03-24

---

## The Problem

Your team uses AI every day -- generating code, drafting plans, evaluating options.
But when something goes wrong, nobody can answer: *why did we decide that?*

- **No audit trail.** AI outputs are ephemeral. Decisions evaporate.
- **Single-model blind spots.** One LLM = one perspective. No adversarial vetting.
- **Compliance gaps.** Regulators want explainability. You have chat logs. EU AI Act enforcement begins August 2, 2026.
- **Painful recurring queues.** PR review, inbox triage, and bounded execution all speed up with AI until trust breaks at the approval step.

## What Aragora Does

Aragora is a **Decision Integrity Platform**. It orchestrates multiple AI agents
to adversarially vet decisions, then delivers audit-ready **decision receipts**
to any channel.

```
Your input -> multi-agent debate -> consensus + receipt -> KM feedback -> Slack / GitHub / API
```

For a first-time operator, the explanation should stay simple:

- **Receipt:** what Aragora recommended and what should happen next
- **Evidence:** what it looked at before making that recommendation
- **Dissent:** where reviewers still disagree or want a human to look closer

**What makes it different:**

1. **Disagreement becomes useful evidence.** Multiple models challenge each
   other before work advances, so dissent shows exactly where human judgment is
   still needed.

2. **Every consequential action has a receipt.** Aragora produces
   audit-ready decision receipts with provenance, votes, confidence, and the
   explicit next action.

   In plain English: the receipt is the reviewable record of what happened,
   why Aragora reached that recommendation, and where uncertainty remains.

3. **Self-improving knowledge loop.** Debate outcomes feed back into a Knowledge Mound
   (42 adapters), so the platform learns from every decision it vets.

4. **It fits above the tools you already use.** Aragora complements GitHub,
   Slack, the terminal, and existing worker runtimes instead of forcing a stack
   replacement.

## What Works End-to-End Today (March 23, 2026)

The product loop is **structurally closed** on `main`. The complete path:

```
Onboarding wizard -> API key setup -> ProviderRouter-backed debate
  -> KM-enriched context -> consensus + receipt -> KM writeback
  -> live dashboard -> demo surface
```

23 PRs merged March 21-23 closing 15 issues to wire this loop shut:

| Capability | Status | Evidence |
|------------|--------|----------|
| Multi-agent debate engine (43 agent types, 10+ concurrent) | Production | PR #1182 |
| Smart provider routing (cost/quality/latency Pareto) | Wired | PR #1167 |
| KM-enriched debate context + outcome writeback | Wired | PRs #1168, #1176 |
| Interactive onboarding wizard (landing to first debate) | Shipped | PR #1170 |
| API key management (real backend, no client-side fakes) | Shipped | PR #1169 |
| Live dashboard with active debate tracking | Shipped | PR #1175 |
| Demo surface hitting real backend | Shipped | PR #1177 |
| Decision receipts with SHA-256 audit trail | Production | |
| Autonomous repo improvement (Ralph loop) | Validated | V14 benchmark |
| Swarm orchestration (supervisor, leases, receipts) | Production | |
| Inbox trust wedge (Gmail -> debate -> receipt -> action) | Shipped | |
| EU AI Act compliance artifacts (85/100 score) | Production | |
| 210,000+ tests across 5,000+ test files | CI | |

## First Design Partner Workflow

For the first design partner cohort, we are intentionally starting with **one
workflow**, not the whole platform:

**Inbox Trust Wedge.** Gmail -> adversarial debate -> signed receipt -> CLI approval
-> action (`archive`, `star`, `label`, `ignore`).

Why this is first:

- it is already the narrowest credible proof surface on `main`
- it exercises Aragora's real differentiator: receipt-gated actioning
- success is measurable in recall, override rate, latency, and time saved

Decision review and autonomous repo improvement remain important proof surfaces,
but they are **not** the first design-partner outreach motion.

## Pain Patterns That Create Real Urgency

The best early partners are not buying generic AI governance. They are trying to
fix one painful recurring queue before the next miss, audit, or scaling cliff.

| Pain pattern | Trigger event | Start here |
|---|---|---|
| Consequential review bottleneck | A bad escape, rollback, security miss, or too many AI-generated changes for current reviewers to vet well | Decision Review |
| Manual triage overload | Missed escalation, SLA pressure, executive inbox pain, or operator bandwidth collapse | Inbox Trust Wedge |
| Bounded engineering backlog | Repetitive but consequential work is piling up, and the team does not trust ungated autopilot | Autonomous Repo Improvement |
| Audit evidence scramble | Audit request, procurement review, incident postmortem, or AI-governance question from customers or leadership | Layer decision receipts onto whichever workflow already hurts |

## What Partners Get

- A self-improving platform that learns from every decision it vets
- Autonomous repo maintenance under explicit policy and receipt gates
- Audit-ready decision receipts (SHA-256 signed, exportable, verifiable)
- Priority support, roadmap influence, and direct access to the team
- Early access to enterprise features (OIDC/SAML SSO, RBAC, multi-tenancy)

## What We Need From Partners

| From You | From Us |
|----------|---------|
| One bounded recurring workflow with a clear trigger and downside if wrong | Free access during partner period |
| 30 min onboarding + weekly 30 min check-in for 4-6 weeks | Hands-on onboarding to first receipt |
| Named buyer, daily user, evaluator, and likely blocker | Role-specific materials for each decision owner |
| Real artifacts (sanitized OK): inbox batch, design doc, bounded backlog | Priority feature requests and weekly iteration |
| Candid feedback on quality, friction, and trust | Co-marketing opportunity (anonymized case studies OK) |

## Default Bounded Pilot

Aragora pilots are intentionally narrow. We start with **one workflow, one
champion, one integration surface, and one agreed metric**. The default offer
is:

- **Scope:** Pick one wedge only: decision review, inbox trust wedge, or a
  bounded backlog lane. Out of scope for the pilot: broad org rollout,
  autonomous merges, open-ended custom builds, or multi-workflow deployment.
- **Duration:** Default **4 weeks**. Week 1 gets to the first live receipt.
  Weeks 2-3 run the real workflow and tighten prompts/policy. Week 4 ends with
  a go/no-go review.
- **Success criteria:** First live receipt in 7 days, at least 8 real
  receipt-backed runs during the pilot (or 3 full cycles for lower-frequency
  workflows), one agreed operational metric improves, and the champion wants to
  expand or convert.
- **Failure criteria:** No live receipt by day 7, repeated manual rescue after
  week 2, no measurable trust or speed improvement, or no clear expansion path
  by the final review.
- **Founder commitment:** The founder personally runs onboarding, joins the
  first live workflow, reviews failures weekly, ships or supervises pilot-
  critical fixes, and makes an honest go/no-go call instead of dragging the
  pilot out.

See also: [Bounded pilot structure](../plans/2026-03-24-design-partner-pilot-structure.md)

## Who This Is For

We are looking for **3-5 design partners** who:

- Have a painful Gmail or Google Workspace inbox triage workflow with a single clear owner
- Handle consequential messages where misses are costly: revenue, recruiting, partnerships, investor updates, or executive follow-up
- Can start with `archive`, `star`, `label`, and `ignore` before asking for reply/send automation
- Want explicit receipts and human approval before actions execute
- Have a champion who can provide sample artifacts, review receipts, and join a weekly loop

**Best-fit segments:** founder-led B2B teams, executives or chiefs of staff with painful inbox overload,
business development leaders, and recruiting-heavy operators who already feel the cost of manual triage.

## Numbers

- **216,000+ tests** across 4,700+ test files
- **3,800+ Python modules** | **3,100+ API operations**
- **42 knowledge adapters** for cross-system learning
- **43 agent types** across 6+ LLM providers
- **190+ WebSocket event types** for real-time streaming
- **Python + TypeScript SDKs** (185 Py / 183 TS namespaces)

## Next Step

**Primary CTA:** Book a 15-minute workflow scoping call.

**Secondary CTA:** Send one bounded artifact or recurring workflow and we will
show what the receipt path looks like.

**Tertiary CTA:** Reply with the team's current review bottleneck if you are
not ready for a call yet.

Contact options:

- Email: [your-email]
- Calendar: [booking-link]
- GitHub: https://github.com/synaptent/aragora

---

*Aragora is open source under the Apache 2.0 license.*
*Design partners get priority support, roadmap influence, and early access to enterprise features.*

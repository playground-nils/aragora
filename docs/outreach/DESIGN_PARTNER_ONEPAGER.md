# Aragora: Design Partner Brief

**Stop shipping AI-assisted decisions you can't explain.**

Aragora governs consequential AI-assisted work with multi-model review,
decision receipts, and truthful gates, so teams can move faster without losing
provenance or human control.

Last updated: 2026-03-25

---

## The Problem

Your team uses AI every day -- generating code, drafting plans, evaluating options.
But when something goes wrong, nobody can answer: *why did we decide that?*

- **No audit trail.** AI outputs are ephemeral. Decisions evaporate.
- **Single-model blind spots.** One LLM = one perspective. No adversarial vetting.
- **Compliance gaps.** Regulators want explainability. You have chat logs. EU AI Act enforcement begins August 2, 2026.
- **Painful recurring queues.** PR review, inbox triage, and bounded execution all speed up with AI until trust breaks at the approval step.

## What Aragora Does

Aragora is not another generic agent platform or model router.
It is an **auditable execution control plane** for consequential AI-assisted
work. Aragora orchestrates multiple AI agents to adversarially vet decisions,
then delivers audit-ready **decision receipts** to any channel.

```
Your input -> multi-agent debate -> consensus + receipt -> KM feedback -> Slack / GitHub / API
```

For a first-time operator, the explanation should stay simple:

- **Receipt:** what Aragora recommended and what should happen next
- **Evidence:** what it looked at before making that recommendation
- **Dissent:** where reviewers still disagree or want a human to look closer

**What makes it different:**

1. **Disagreement as evidence.** Aragora uses heterogeneous models to pressure-test
   decisions. Convergence matters because it survives challenge; dissent matters
   because it tells you exactly where human judgment is still required.

2. **Every consequential action has a receipt.** Aragora produces
   audit-ready decision receipts with provenance, votes, confidence, and the
   explicit next action.

3. **Truthful execution gates.** Supervisor-backed work orders with receipt gates,
   lease-based coordination, and explicit merge policy -- not unguarded autonomy.

4. **Learning from outcomes.** Debate outcomes feed back into a Knowledge Mound,
   so the platform improves how it grounds future decisions.

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
| Heterogeneous debate engine with explicit dissent trails | Production | PR #1182 |
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

## What We Can Prove Today

- **Better governed decisions than a single-model workflow.** Aragora already
  proves multi-model challenge, explicit dissent, signed receipts, and
  truthful stopping behavior on bounded workflows.
- **Repeatable live proof on the founder loop.** 5/5 consecutive live runs
  passed on March 24, 2026, with receipts visible on API/dashboard surfaces.
- **Receipt-before-action on consequential flows.** The inbox trust wedge and
  bounded repo workflows are built so action is gated by review artifacts, not
  one model's unchecked output.

## What We Are Still Proving

- **Quantified quality delta vs the strongest single-model baseline.** We have
  strong internal debate-quality evidence and real dogfood wins, but we still
  need published catch-rate deltas on partner workflows.
- **One fully continuous partner user journey.** Routing, KM enrichment,
  receipt visibility, and UI continuity are materially better on `main`, but
  one repeatable external proof is still owed.
- **High-impact external verification.** Multi-model review is stronger than
  single-model review, but correlated failure and coordinated compromise are
  not fully eliminated without stricter external verification gates.

## Three Proof Surfaces for Partners

For the first design partner cohort, we are intentionally starting with **one
workflow**, not the whole platform:

**Inbox Trust Wedge.** Gmail -> adversarial debate -> signed receipt -> CLI approval
-> action (`archive`, `star`, `label`, `ignore`).

Why this is first:

## First-Week Journey

The week-one goal is not "turn on full autonomy." It is to get from setup to
**one trustworthy result** on a narrow recurring workflow.

| Stage | Outcome |
|-------|---------|
| Day 0: qualify the lane | one workflow, one owner, one success metric, representative artifacts |
| Day 1: setup and readiness | live path works and produces a visible receipt or truthful blocker |
| Day 2: trust contract | explicit action policy, approval points, and stop conditions |
| Day 3: first real run | real artifact or inbox batch processed in a bounded lane |
| Day 4: review friction | receipt quality, evidence gaps, and trust blockers documented |
| Day 5: first trustworthy result | one receipt-backed decision a human can act on, reject, or hold |

Default order for week one:

1. Decision review
2. Inbox trust wedge in `--dry-run` or approval-gated mode
3. Bounded repo execution only after receipt review feels trustworthy

See the canonical journey and exit gate:
`docs/plans/2026-03-25-design-partner-first-week-journey.md`.

## Explicit Truth Boundaries

What we can claim in week one:

- Aragora can run a bounded workflow through debate or gated execution.
- Aragora can produce visible receipts with evidence, provenance, and dissent.
- Aragora can stop with a specific blocker instead of pretending completion.

What we do **not** claim in week one:

- guaranteed correctness of the underlying business decision
- removal of the responsible human approver
- safe broad autonomy across an entire organization
- audit/certification completion just because receipts exist

If the receipt is missing, the evidence is weak, or the workflow needs
undocumented operator rescue, we treat that as a blocker, not a success.

## What Partners Get

- A governed execution layer that makes AI-assisted decisions reviewable
- Autonomous repo maintenance under explicit policy and receipt gates
- Audit-ready decision receipts (SHA-256 signed, exportable, verifiable)
- Priority support, roadmap influence, and direct access to the team
- Early access to enterprise features (OIDC/SAML SSO, RBAC, multi-tenancy)

## How Knowledge Mound Actually Learns

**Founder version:** Every strong receipt should make the next decision cheaper and
better. Knowledge Mound is how Aragora compounds vetted work into institutional
memory without pretending every model output is true.

**Buyer version:** Aragora stores governed knowledge with provenance. It learns
high-confidence claims, evidence, and resolution patterns; it does not auto-promote
raw AI output into policy.

| Gets learned | Does not get learned | Must be reviewed |
|--------------|----------------------|------------------|
| High-confidence debate outcomes that clear writeback thresholds | Low-confidence outcomes that do not clear the threshold | Contradictions between new knowledge and existing knowledge |
| Claims, facts, insights, and references with provenance | Unresolved disagreement as if it were settled truth | Promotion of important claims into verified operating knowledge |
| Reusable patterns such as decision style, risk tolerance, domain expertise, and resolution patterns | Sensitive cost telemetry unless the opt-in adapter is enabled | Any receipt with low confidence, meaningful dissent, or high-impact side effects |
| Staleness and contradiction signals so old knowledge can be challenged over time | Stale or superseded items as evergreen truth | Irreversible or policy-setting actions before they execute |

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

## Proof Points

- **216,000+ tests** across 4,700+ test files
- **Receipt-gated repo improvement** validated on the benchmark path
- **Inbox trust wedge** shipped from debate to signed receipt to action
- **Heterogeneous provider support** across CLI, API, and local-model workers
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

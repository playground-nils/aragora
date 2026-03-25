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

## What Aragora Does

Aragora is a **Decision Integrity Platform**. It runs adversarial multi-agent
review, then delivers audit-ready **decision receipts** that explain why the
system advanced or stopped.

```
Your input -> multi-agent debate -> consensus + receipt -> KM feedback -> Slack / GitHub / API
```

**Founder-safe differentiation:**

1. **Disagreement becomes evidence.** Multiple models challenge each other so
   the operator can see convergence, dissent, and unresolved judgment calls.

2. **Receipts are first-class outputs.** Aragora stores a receipt that captures
   outcome, provenance, and why the system advanced or stopped.

3. **Actions stay bounded.** Receipt-before-action and explicit approval policy
   matter more than generic autonomy claims.

## What Aragora Can Prove Today (March 24, 2026)

These are the only top-line proof points we should lead with in partner
conversations. Source of truth: `docs/outreach/FOUNDER_PROOF_POINTS_LIBRARY.md`.

| Claim | Status | Minimum proof to show |
|-------|--------|-----------------------|
| Live decision review is repeatable on current `main` | **Proven** | One live run plus receipt ID/share link; if citing repeatability or speed, use the March 24, 2026 baseline: 5/5 consecutive founder-loop runs, 35-62s, all 7 acceptance items pass |
| Aragora shows why the system advanced or stopped | **Proven** | One stored or exported receipt showing consensus, dissent, provenance, and outcome shape; one verification surface (`aragora receipt verify`, API, or receipt store view) |
| Bounded actions can be gated on persisted receipts and explicit policy | **Dogfood-ready** | One policy-gated flow, such as inbox triage with `aragora triage auth` and `aragora triage run --dry-run`; show that receipt persistence happens before action |

## Reserve Proofs, Not Opening Claims

- **Inbox trust wedge:** Gmail -> debate -> receipt -> CLI approval -> action. Pitch as a narrow, policy-gated path that is ready for dogfood, not as broad autonomous email ops.
- **Ralph autonomous benchmark:** Use only as bounded autonomy evidence. It proves one validated benchmark path under explicit merge policy, not unrestricted autonomy.
- **EU AI Act artifacts:** Safe claim is that Aragora can generate artifact bundles from real receipts. Do not turn that into a certification claim.

## Default Partner Surface

**Decision review** is the default proof surface for partners today. Run a real
artifact (spec, PR, architecture proposal, inbox slice) through multi-agent
review, then share the receipt internally.

## Common Objections

**"Why not just use Codex, Claude Code, or OpenCode?"**
Those tools are worker runtimes. Aragora governs the layer above them: review,
receipts, provenance, dissent, and truthful stopping behavior.

**"Won't this be slower than a single model?"**
Yes, and that is the point. Use the simplest layer that preserves the needed
truthfulness. Aragora is for consequential work, not every autocomplete.

**"Are receipts just logs?"**
No. A receipt explains who said what, what evidence was used, why the system
advanced or stopped, and what the next human action is.

**"Do we have to replace our current tools?"**
No. Aragora sits above the tools your team already uses and adds governance
only where the risk justifies it.

## What Partners Get

- One receipt-backed pilot on a bounded recurring workflow
- Audit-ready decision receipts that can be exported and verified
- A narrow approval-gated automation path where it is warranted
- Priority support, roadmap influence, and direct access to the team
- Early access to enterprise features (OIDC/SAML SSO, RBAC, multi-tenancy)

## What We Need From Partners

| From You | From Us |
|----------|---------|
| One bounded recurring workflow with a clear trigger | Free access during partner period |
| 30 min onboarding + weekly 30 min check-in for 4-6 weeks | Hands-on onboarding to first receipt |
| Named buyer, daily user, evaluator, and likely blocker | Role-specific materials for each decision owner |
| Real artifacts (sanitized OK): inbox batch, design doc, bounded backlog | Priority feature requests and weekly iteration |
| Candid feedback on quality, friction, and trust | Co-marketing opportunity (anonymized case studies OK) |

## Who Owns The First Deal Decisions

Do not treat the first deal as "find one champion and hope they carry everything."
Aragora has to clear four different decisions:

| Role | Typical titles | Decision they own | What they need to see |
|------|----------------|-------------------|-----------------------|
| Buyer | CTO, VP Engineering, Head of Platform, founder | Whether this workflow deserves budget, attention, and a live pilot | Narrow scope, credible pain, clear owner, time-to-value |
| Daily user | Engineering manager, tech lead, triage owner, security analyst | Whether Aragora fits into the weekly operating loop and saves real time | Low-friction workflow, useful receipts, obvious next actions |
| Evaluator | Staff engineer, platform lead, security/compliance lead | Whether Aragora's evidence and controls are trustworthy enough for consequential use | Receipts, dissent, provenance, review gates, truthful stopping behavior |
| Blocker | Security, legal, procurement, IT admin, skeptical exec | Whether a specific control, policy, or deployment issue still prevents rollout | Precise answers on data flow, providers, auth, deployment options, exports, and guardrails |

In smaller teams one person may hold multiple roles, but the decision owners
should still be named explicitly. A deal is easier to unblock when you know
whether it is stalled on budget, operator trust, evaluator standards, or a
hard veto.

## Who This Is For

We are looking for **3-5 design partners** who:

- Feel real pain from review latency, manual triage, audit evidence work, or bounded engineering backlog throughput
- Have one recurring workflow with a clear trigger, owner, and success/failure outcome
- Can start narrow (one receipt-gated workflow) before expanding
- Can name the buyer, daily user, evaluator, and likely blocker for the first workflow
- Have a champion who can coordinate artifacts, review receipts, and pull the right decision owner into the weekly loop

**Best-fit segments:** Regulated SaaS, FinTech, HealthTech, platform/security teams,
founder-led teams with painful inbox triage, AI-native teams frustrated by single-model trust gaps.

## Supporting Facts, Not Opening Claims

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

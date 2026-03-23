# Next Steps (Canonical)

Last updated: 2026-03-23

This is the single source of truth for short-horizon execution priorities.
[CANONICAL_GOALS](../CANONICAL_GOALS.md) defines what Aragora is and why.
[ARAGORA_EVOLUTION_ROADMAP](../plans/ARAGORA_EVOLUTION_ROADMAP.md) defines the long-range architecture and moat.
[FEATURE_GAP_LIST](../FEATURE_GAP_LIST.md) is the capability and backlog truth.
[ACTIVE_EXECUTION_ISSUES](ACTIVE_EXECUTION_ISSUES.md) maps the current live GitHub issue set.

## Current Reality

- **The execution program is complete.** All 6 program epics are resolved and closed on GitHub.
- The product loop is not just structurally closed — it is operational. The complete path works end-to-end: onboarding wizard -> API key management -> ProviderRouter-backed debate -> KM-enriched context -> receipt -> KM writeback -> live dashboard -> real demo surface.
- The swarm control plane is truthful: queue-backed execution, label-scoped unattended dispatch, canonical receipts, preserved verification evidence, and terminal tranche reconciliation are all on `main`.
- Truthfulness and documentation hygiene disciplines are embedded in the workflow, not a separate tranche.
- The idea-to-execution workbench sits on top of a running product loop.
- The closed-loop backbone contracts are complete (14/14 issues).
- What remains is **operation, polish, and enterprise certification** — not building the core system.
- GitHub issues remain the live backlog. These docs summarize the active order and capability posture.
- The product strategy narrative is maintained in [ARAGORA_IDEA_TO_EXECUTION_STRATEGY](../plans/ARAGORA_IDEA_TO_EXECUTION_STRATEGY.md).

### Closed Program Epics

| Epic | Title | Closed |
|------|-------|--------|
| [#804](https://github.com/synaptent/aragora/issues/804) | Truthfulness and documentation hygiene | 2026-03-23 |
| [#806](https://github.com/synaptent/aragora/issues/806) | Sequential surface productization and value prop | 2026-03-23 |
| [#836](https://github.com/synaptent/aragora/issues/836) | Developer swarm control plane | 2026-03-23 |
| [#989](https://github.com/synaptent/aragora/issues/989) | Idea-to-execution workbench | 2026-03-23 |
| [#990](https://github.com/synaptent/aragora/issues/990) | Dogfood the pipeline to build more of Aragora | 2026-03-23 |
| [#1036](https://github.com/synaptent/aragora/issues/1036) | Continuous self-assessment and autonomous improvement cadence | 2026-03-23 |

## Execution Order

### 1) Operate And Prove (Current Phase)
- The system is running. The priority is continuous operation, real-user proof, and partner onboarding.
- No new structural wiring is needed. The obligation is to run the loop with real users, collect feedback, and fix what breaks.
- The boss loop runs unattended with label-scoped dispatch on queue v5.
- KM bidirectional flow operates: debates read org knowledge, outcomes write back.

### 2) Wave 2 Surface Polish
- Tracking: [#820](https://github.com/synaptent/aragora/issues/820) (medium priority)
- Goal: productize Wave 2 surfaces — SME onboarding, spectate, and conditional public endpoints.
- These extend the running product loop; they do not gate it.

### 3) Design Partner Refresh
- Tracking: [#1011](https://github.com/synaptent/aragora/issues/1011) (medium priority)
- Goal: refresh the design partner pipeline and prove repeatable external usage.
- First queue artifact already recovered and published via [#1108](https://github.com/synaptent/aragora/pull/1108).

### 4) Enterprise Assurance (P3 — When Ready)
- Tracking: [#273](https://github.com/synaptent/aragora/issues/273), [#274](https://github.com/synaptent/aragora/issues/274), [#509](https://github.com/synaptent/aragora/issues/509)
- Goal: pentest, SOC 2, and enterprise certification.
- These are real and parked at P3. They follow a proven, repeating product loop — they do not precede it.
- SOC 2 Type II is 98% ready; the blocker is an external pen test (~10 weeks to certification once initiated).

### Operational Incidents (Interrupt-Driven)
- Tracking: [#829](https://github.com/synaptent/aragora/issues/829) and any future incident tickets
- Rule: incidents can preempt the planned order, but they do not replace the canonical program. Once mitigated, execution returns to the order above.

## Open Issue Summary

Only 5 issues remain open:

| Issue | Priority | Category | Scope |
|-------|----------|----------|-------|
| [#820](https://github.com/synaptent/aragora/issues/820) | Medium | Surface polish | Wave 2 surfaces (SME onboarding, spectate, conditional endpoints) |
| [#1011](https://github.com/synaptent/aragora/issues/1011) | Medium | Partner refresh | Design partner pipeline and repeatable external usage |
| [#273](https://github.com/synaptent/aragora/issues/273) | P3 | Enterprise assurance | Enterprise assurance closure epic |
| [#274](https://github.com/synaptent/aragora/issues/274) | P3 | Enterprise assurance | External penetration test and remediation |
| [#509](https://github.com/synaptent/aragora/issues/509) | P3 | Enterprise assurance | Pentest vendor selection and scope sign-off |

## Operating Rules

- GitHub issues are the live execution backlog; docs summarize context, order, and capability posture.
- [ACTIVE_EXECUTION_ISSUES](ACTIVE_EXECUTION_ISSUES.md) must stay aligned with the current issue set.
- [FEATURE_GAP_LIST](../FEATURE_GAP_LIST.md) remains the capability and backlog truth for planned and partial features.
- No document should claim "only one blocker remains" unless `main` CI, deployment, and proof-run evidence support it.
- The execution program is complete. New work is operational: run the system, fix what breaks, onboard users.
- If priorities change, update the GitHub issues first, then update this file and the linked summaries.

# Active Execution Issues

Last updated: 2026-03-23

This document links Aragora's current execution program to the live GitHub issue tracker.

- Docs explain thesis, roadmap, and capability posture.
- GitHub issues track live execution status, owners, priorities, and acceptance criteria.
- Use [NEXT_STEPS_CANONICAL](NEXT_STEPS_CANONICAL.md) for execution order and this file for the current issue map.

## Program Status: COMPLETE

The active execution program is complete. All 6 program epics are closed on GitHub. The product loop is operational, the swarm control plane is truthful, and the closed-loop backbone contracts are landed. What remains is continuous operation, surface polish, and enterprise certification when ready.

### Closed Program Epics

| Epic | Title | Closed |
|------|-------|--------|
| [#804](https://github.com/synaptent/aragora/issues/804) | Truthfulness and documentation hygiene | 2026-03-23 |
| [#806](https://github.com/synaptent/aragora/issues/806) | Sequential surface productization and value prop | 2026-03-23 |
| [#836](https://github.com/synaptent/aragora/issues/836) | Developer swarm control plane | 2026-03-23 |
| [#989](https://github.com/synaptent/aragora/issues/989) | Idea-to-execution workbench | 2026-03-23 |
| [#990](https://github.com/synaptent/aragora/issues/990) | Dogfood the pipeline to build more of Aragora | 2026-03-23 |
| [#1036](https://github.com/synaptent/aragora/issues/1036) | Continuous self-assessment and autonomous improvement cadence | 2026-03-23 |

## Open Issues (5 Remaining)

### Execution Items (Medium Priority)

| Issue | State | Priority | Scope |
|-------|-------|----------|-------|
| [#820](https://github.com/synaptent/aragora/issues/820) | Open | `priority:medium` | Productize Wave 2 surfaces: SME onboarding, spectate, and conditional public endpoints |
| [#1011](https://github.com/synaptent/aragora/issues/1011) | Open | `priority:medium` | Design partner refresh and repeatable external usage |

### Enterprise Assurance (P3 — Parked)

| Issue | State | Priority | Scope |
|-------|-------|----------|-------|
| [#273](https://github.com/synaptent/aragora/issues/273) | Open | P3 | Enterprise assurance closure epic |
| [#274](https://github.com/synaptent/aragora/issues/274) | Open | P3 | External penetration test and remediation |
| [#509](https://github.com/synaptent/aragora/issues/509) | Open | P3 | Pentest vendor selection and scope sign-off |

## What Was Closed Today (March 23)

Eight issues/epics closed in the epic closure sprint:

1. **[#804](https://github.com/synaptent/aragora/issues/804)** — Truthfulness and documentation hygiene epic. All sub-issues (#807, #808, #809) were already closed; epic itself now closed.
2. **[#806](https://github.com/synaptent/aragora/issues/806)** — Sequential surface productization. Product loop operating, demo/dashboard/onboarding all wired to real backends.
3. **[#836](https://github.com/synaptent/aragora/issues/836)** — Developer swarm control plane. Queue-backed execution, label-scoped dispatch, preserved verification evidence, terminal tranche reconciliation all on `main`.
4. **[#989](https://github.com/synaptent/aragora/issues/989)** — Idea-to-execution workbench. Sits on top of a running product loop.
5. **[#990](https://github.com/synaptent/aragora/issues/990)** — Dogfood the pipeline. Pipeline used to build Aragora itself; queue artifacts recovered and published.
6. **[#1036](https://github.com/synaptent/aragora/issues/1036)** — Continuous self-assessment cadence. Assessment-to-backlog pipeline operational.
7. Additional sub-issues and cross-references within these epics also resolved.

## Operational Incidents

| Issue | State | Priority | Scope |
|-------|-------|----------|-------|
| [#829](https://github.com/synaptent/aragora/issues/829) | Open | `outage` | Service outage detected on 2026-03-07 |

## Operating Rule

When the execution program changes:

1. update the GitHub issues first
2. update [NEXT_STEPS_CANONICAL](NEXT_STEPS_CANONICAL.md)
3. update this issue map and any linked summary docs
4. if multiple open PRs cover the same slice, choose a single merge lane and close or supersede the rest with proof

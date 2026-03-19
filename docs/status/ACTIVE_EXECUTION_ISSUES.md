# Active Execution Issues

Last updated: 2026-03-18

This document links Aragora's current execution program to the live GitHub issue tracker.

- Docs explain thesis, roadmap, and capability posture.
- GitHub issues track active execution status, owners, priorities, and acceptance criteria.
- Use [NEXT_STEPS_CANONICAL](NEXT_STEPS_CANONICAL.md) for execution order and this file for the live issue map.

## Current Execution Order

1. Truthfulness and backlog canonicalization
2. Decision Integrity Kernel unification
3. Developer swarm control plane and autonomous self-improvement cadence
4. Sequential surface productization
5. Assurance closeout kept warm, not the main product lane

## Truthfulness And Backlog Canonicalization

Epic: [#804](https://github.com/synaptent/aragora/issues/804)

Tranche status: complete on `main` through [#809](https://github.com/synaptent/aragora/issues/809)

Recently completed:
- [#807](https://github.com/synaptent/aragora/issues/807) `CLOSED` - Make launch truthfulness blocking
- [#808](https://github.com/synaptent/aragora/issues/808) `CLOSED` - Make self-host readiness truthful and PR-gated
- [#809](https://github.com/synaptent/aragora/issues/809) `CLOSED` - Canonicalize the active backlog into GitHub issues

| Issue | State | Priority | Owner | Milestone | Scope |
|------|-------|----------|-------|-----------|-------|
| [#807](https://github.com/synaptent/aragora/issues/807) | Closed | `priority:critical` | `owner:team-platform` | `2026-M1 Truthfulness + Decision Integrity Core` | Make launch truthfulness blocking |
| [#808](https://github.com/synaptent/aragora/issues/808) | Closed | `priority:high` | `owner:team-platform` | `2026-M1 Truthfulness + Decision Integrity Core` | Make self-host readiness truthful and PR-gated |
| [#809](https://github.com/synaptent/aragora/issues/809) | Closed | `priority:high` | `owner:team-platform` | `2026-M1 Truthfulness + Decision Integrity Core` | Canonicalize the active backlog into GitHub issues |

## Decision Integrity Kernel Unification

Epic: [#805](https://github.com/synaptent/aragora/issues/805)

Current tranche: the base kernel is on `main` through [#811](https://github.com/synaptent/aragora/issues/811) and [#812](https://github.com/synaptent/aragora/issues/812); the remaining scale-out work is [#813](https://github.com/synaptent/aragora/issues/813) through [#816](https://github.com/synaptent/aragora/issues/816)

| Issue | State | Priority | Owner | Milestone | Scope |
|------|-------|----------|-------|-----------|-------|
| [#810](https://github.com/synaptent/aragora/issues/810) | Closed | `priority:high` | `owner:team-core` | `2026-M1 Truthfulness + Decision Integrity Core` | Add prompt -> specification -> DecisionPlan bridge |
| [#811](https://github.com/synaptent/aragora/issues/811) | Closed | `priority:high` | `owner:team-core` | `2026-M1 Truthfulness + Decision Integrity Core` | Collapse prompt/canvas/pipeline to one canonical execution runtime |
| [#812](https://github.com/synaptent/aragora/issues/812) | Closed | `priority:high` | `owner:team-core` | `2026-M1 Truthfulness + Decision Integrity Core` | Require cryptographic decision receipts before all action-taking |
| [#813](https://github.com/synaptent/aragora/issues/813) | Open | `priority:high` | `owner:team-core` | `2026-M3 Strategic Moat Scale-Out` | Integrate ProviderRouter into runtime agent selection |
| [#814](https://github.com/synaptent/aragora/issues/814) | Open | `priority:high` | `owner:team-core` | `2026-M3 Strategic Moat Scale-Out` | Make OpenClaw action dispatch real |
| [#815](https://github.com/synaptent/aragora/issues/815) | Open | `priority:high` | `owner:team-core` | `2026-M3 Strategic Moat Scale-Out` | Scale adversarial orchestration to 10+ agents |
| [#816](https://github.com/synaptent/aragora/issues/816) | Open | `priority:high` | `owner:team-core` | `2026-M3 Strategic Moat Scale-Out` | Deploy ERC-8004 identity and settlement integration |

## Developer Swarm Control Plane And Autonomous Self-Improvement Cadence

Epic: [#836](https://github.com/synaptent/aragora/issues/836), [#989](https://github.com/synaptent/aragora/issues/989), [#1036](https://github.com/synaptent/aragora/issues/1036)

Recent reality on `main`:
- File-scope ownership ([#840](https://github.com/synaptent/aragora/issues/840)) and canonical PR/supersession tracking ([#841](https://github.com/synaptent/aragora/issues/841)) are now closed on `main`.
- The canonical assessment compiler ([#1037](https://github.com/synaptent/aragora/issues/1037)) and pause-refresh shift controller ([#1038](https://github.com/synaptent/aragora/issues/1038)) are also closed on `main`.
- The remaining gap is no longer “can Aragora execute work at all?” It is whether task claims, universal run receipts, and integrator visibility stay truthful during long unattended runs.

| Issue | State | Priority | Owner | Milestone | Scope |
|------|-------|----------|-------|-----------|-------|
| [#836](https://github.com/synaptent/aragora/issues/836) | Open | `priority:high` | `owner:team-platform` | `2026-M3 Scale and Reliability` | Developer Swarm Control Plane epic |
| [#837](https://github.com/synaptent/aragora/issues/837) | Open | `priority:high` | `owner:team-platform` | `2026-M3 Scale and Reliability` | Add developer task queue and claim protocol |
| [#840](https://github.com/synaptent/aragora/issues/840) | Closed | `priority:high` | `owner:team-platform` | `2026-M3 Scale and Reliability` | Enforce file-scope ownership on agent lanes |
| [#841](https://github.com/synaptent/aragora/issues/841) | Closed | `priority:high` | `owner:team-platform` | `2026-M3 Scale and Reliability` | Add canonical PR and supersession protocol |
| [#842](https://github.com/synaptent/aragora/issues/842) | Open | `priority:high` | `owner:team-platform` | `2026-M3 Scale and Reliability` | Emit receipts and provenance for every agent run |
| [#843](https://github.com/synaptent/aragora/issues/843) | Open | `priority:high` | `owner:team-platform` | `2026-M3 Scale and Reliability` | Build integrator view for active swarm lanes |
| [#871](https://github.com/synaptent/aragora/issues/871) | Open | `priority:high` | `owner:team-platform` | `none` | Autonomous Repo Maintenance MVP via Boss loop |
| [#989](https://github.com/synaptent/aragora/issues/989) | Open | `priority:high` | `owner:team-core` | `2026-M3 Strategic Moat Scale-Out` | Bootstrapped local-first idea-to-execution workbench |
| [#990](https://github.com/synaptent/aragora/issues/990) | Open | `priority:high` | `owner:team-core` | `2026-M3 Strategic Moat Scale-Out` | Dogfood the pipeline to build more of Aragora itself |
| [#1036](https://github.com/synaptent/aragora/issues/1036) | Open | `priority:high` | `owner:team-core` | `2026-M3 Strategic Moat Scale-Out` | Continuous self-assessment and autonomous improvement cadence epic |
| [#1037](https://github.com/synaptent/aragora/issues/1037) | Closed | `priority:high` | `owner:team-core` | `2026-M3 Strategic Moat Scale-Out` | Compile a canonical repo assessment into pipeline-ready backlog artifacts |
| [#1038](https://github.com/synaptent/aragora/issues/1038) | Closed | `priority:high` | `owner:team-platform` | `2026-M3 Scale and Reliability` | Add pause-refresh checkpoints for long unattended self-improvement shifts |

## Sequential Surface Productization

Epic: [#806](https://github.com/synaptent/aragora/issues/806)

| Issue | State | Priority | Owner | Milestone | Scope |
|------|-------|----------|-------|-----------|-------|
| [#817](https://github.com/synaptent/aragora/issues/817) | Open | `priority:high` | `owner:team-integrations` | `2026-M2 Surface Productization` | Consolidate inbox and shared inbox onto the trust wedge |
| [#818](https://github.com/synaptent/aragora/issues/818) | Open | `priority:high` | `owner:team-integrations` | `2026-M2 Surface Productization` | Turn the public demo into a live proof surface |
| [#819](https://github.com/synaptent/aragora/issues/819) | Open | `priority:high` | `owner:team-integrations` | `2026-M2 Surface Productization` | Make the integrations UI trustworthy and non-demo by default |
| [#820](https://github.com/synaptent/aragora/issues/820) | Open | `priority:medium` | `owner:team-integrations` | `2026-M2 Surface Productization` | Productize Wave 2 surfaces: SME onboarding, spectate, and conditional public endpoints |

## Assurance And GTM Issues Kept Warm

These remain open and real, but they are not the primary product lane while the decision kernel and proof surfaces are still being unified.

| Issue | State | Priority | Owner | Milestone | Scope |
|------|-------|----------|-------|-----------|-------|
| [#273](https://github.com/synaptent/aragora/issues/273) | Open | `priority:critical` | `owner:team-risk` | `2026-M2 Channel and FinOps` | Enterprise Assurance Closure epic |
| [#274](https://github.com/synaptent/aragora/issues/274) | Open | `priority:critical` | `owner:team-risk` | `2026-M2 Channel and FinOps` | Execute external penetration test and remediate findings |
| [#509](https://github.com/synaptent/aragora/issues/509) | Open | `priority:critical` | `owner:team-risk` | `none` | Pentest vendor selection and scope sign-off |

## Operational Incidents

Operational incidents are not part of the planned execution epics, but they can preempt them when `main` is degraded.

| Issue | State | Priority | Scope |
|------|-------|----------|-------|
| [#829](https://github.com/synaptent/aragora/issues/829) | Open | `outage` | Service outage detected on 2026-03-07 |

## Operating Rule

When the execution program changes:

1. update the GitHub issues first
2. update [NEXT_STEPS_CANONICAL](NEXT_STEPS_CANONICAL.md)
3. update this issue map and any linked summary docs

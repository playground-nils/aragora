# Phase 1 Scope Boundaries

**Date:** March 13, 2026
**Sources:** `docs/plans/2026-03-10-bootstrap-plan.md`, `docs/governance/subsystem-ledger.md`, `docs/governance/entrypoint-inventory.md`

Phase 1 ("Controlled Self-Repair") is limited to the subsystem-ledger buckets
marked **canonical** and **core-but-messy**. Phase 1 may document or constrain
interfaces to other areas, but it does not widen implementation scope beyond
those buckets.

## In Scope

Eligible subsystem modules for Phase 1 work:

- **Canonical:** `agents`, `auth`, `cli`, `config`, `control_plane`, `core`, `db`, `debate`, `knowledge`, `memory`, `nomic`, `observability`, `rbac`, `resilience`, `server`, `storage`, `swarm`
- **Core-but-messy:** `audit`, `billing`, `connectors`, `events`, `gateway`, `integrations`, `persistence`, `queue`

These are the only buckets Phase 1 can directly consolidate, classify, or
enforce boundaries around.

## Out of Scope

Explicitly out of scope for Phase 1 implementation work:

- **Expansion bucket:** `analytics`, `canvas`, `channels`, `compliance`, `evaluation`, `evidence`, `gauntlet`, `goals`, `inbox`, `marketplace`, `mcp`, `pipeline`, `ranking`, `reasoning`, `reports`, `rlm`, `routing`, `sandbox`, `scheduler`, `services`, `skills`, `workflow`
- **Compatibility bucket:** `compat`, `harnesses`, `tenancy`, `training`
- **Defer bucket:** includes `hooks`, `ideacloud`, `interrogation`, `live`, `monitoring`, `policy`, `prompt_engine`, `tasks`, `telemetry`, `tools`, `verification`, `webhooks`, `workspace`, `worktree`

If a Phase 1 ticket touches an out-of-scope subsystem, that subsystem is an
interface dependency only. It is not a target for autonomous refactor in this
phase.

## Ticket-to-Subsystem Map

| Ticket | Title | Primary subsystem modules | Boundary note |
|---|---|---|---|
| `P1-8` | Backend Classification: Unified Server vs FastAPI | `server`, `gateway`, `cli`, `config` | Keep the canonical runtime in `server`; classify `gateway` as overlap to reduce, not a second backend authority. |
| `P1-9` | API Surface Matrix | `server`, `gateway`, `auth`, `rbac`, `cli` | API classification stays on runtime/API surfaces; frontend, SDK, and expansion APIs stay out of scope. |
| `P1-10` | Remove Duplicate Startup Logic | `server`, `cli`, `config`, `control_plane`, `swarm`, `queue` | Normalize startup paths for backend and worker entrypoints without widening into deployment-product features. |
| `P1-11` | Domain Boundary Rules | `server`, `gateway`, `events`, `queue`, `storage`, `db`, `persistence`, `connectors`, `integrations`, `debate`, `knowledge`, `memory`, `nomic` | Resolve duplicate-cluster boundaries only inside eligible buckets. |
| `P1-12` | Static Boundary Enforcement | `server`, `gateway`, `events`, `queue`, `storage`, `db`, `persistence`, `connectors`, `integrations`, `debate`, `knowledge`, `memory`, `nomic`, `control_plane` | CI/static rules enforce the Phase 1 boundaries above; they should block new cross-layer drift. |
| `P1-13` | Memory/Knowledge Architecture Map | `memory`, `knowledge`, `debate`, `nomic`, `storage`, `db`, `persistence` | `reasoning`, `pipeline`, and `rlm` may consume these contracts later but are not Phase 1 rewrite targets. |
| `P1-14` | Nomic Subsystem Spec | `nomic`, `swarm`, `control_plane`, `queue`, `debate`, `memory`, `knowledge`, `observability` | Focus on Nomic's canonical control loop and worker/runtime touchpoints, not adjacent expansion systems. |

## Practical Rule

During Phase 1, autonomous lanes may change only the modules named in the
eligible buckets above. Expansion, compatibility, and defer modules may be
referenced for inventory, documentation, or interface mapping, but not used to
justify widening refactor scope.

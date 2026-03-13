# Duplicate Subsystem Resolution

**Date:** March 13, 2026
**Campaign:** phase0a-bootstrap-governance
**Lane:** analysis-and-design
**Purpose:** Define the canonical survivor, migration path, and target phase
for each duplicate subsystem cluster identified in
`docs/governance/subsystem-ledger.md`.

## Scope and Decision Rule

This document is design-only Phase 0A output. It does not authorize broad
code motion by itself. It gives Phase 0B and Phase 1 lanes a fixed answer to
three questions for each duplicate cluster:

1. Which subsystem survives as canonical.
2. How callers and code move to that canonical subsystem.
3. Which bootstrap phase owns the change.

## Phase Legend

| Phase | Meaning in this document |
|------|---------------------------|
| **Phase 0B prep** | No broad rewrites; freeze new duplication and add compatibility shims only in canonical surfaces |
| **Phase 1** | Main consolidation work across core-but-messy subsystems |
| **Phase 2** | Cleanup of compatibility wrappers, stale docs, and deferred extractions |

## Resolution Table

| Cluster | Canonical survivor | Migration path | Target phase |
|--------|--------------------|----------------|--------------|
| Event dispatch | `events` | Fold `hooks` and `webhooks` behind `events` interfaces; keep them as thin adapters during transition | Phase 1 |
| Platform connectors | `connectors` | Re-home `integrations` implementations under `connectors` adapter conventions; leave import-level compatibility aliases temporarily | Phase 1 |
| Storage layers | `storage` + `db` | Move durable repository and persistence flows to `storage`, keep connection/bootstrap concerns in `db`, retire `persistence` | Phase 1 |
| HTTP routing | `server` | Keep request handling and API surface in `server`; reduce `gateway` to deployment or reverse-proxy configuration only | Phase 1 |
| Monitoring | `observability` | Route metrics, tracing, and health instrumentation through `observability`; reduce `monitoring` and `telemetry` to re-exports or delete later | Phase 1 |
| Task management | `queue` + `scheduler` | Use `queue` for executable work state and worker handoff, `scheduler` for time-based triggering only, absorb `tasks` call sites into that split | Phase 1 |

## Cluster Designs

### 1. Event Dispatch

- Canonical survivor: `events`
- Target phase: Phase 1
- Migration path:
  - In Phase 0B prep, freeze any new direct feature work in `hooks` and `webhooks`.
  - Define `events` as the only place allowed to own event emission, subscription, retry, and delivery contracts.
  - Convert `hooks` into declarative adapter configuration over `events`.
  - Convert `webhooks` into HTTP delivery adapters invoked by `events`, not a peer event bus.
  - In Phase 2, remove duplicate dispatch logic from `hooks` and `webhooks` after downstream callers are moved.
- Design boundary:
  - `events` owns internal event semantics.
  - `hooks` and `webhooks` may survive only as protocol-specific adapters.

### 2. Platform Connectors

- Canonical survivor: `connectors`
- Target phase: Phase 1
- Migration path:
  - In Phase 0B prep, stop introducing net-new third-party adapters under `integrations`.
  - Establish `connectors` as the canonical package for Slack, email, chat, enterprise, and evidence-facing adapters.
  - Migrate reusable adapter primitives, auth helpers, and sync contracts from `integrations` into `connectors`.
  - Leave compatibility imports or forwarding modules in `integrations` for one cleanup phase so callers can move incrementally.
  - In Phase 2, trim `integrations` to documentation, composition glue, or remove it if empty.
- Design boundary:
  - `connectors` owns provider adapters and transport/runtime code.
  - `integrations` may describe composed workflows, but not own duplicate provider implementations.

### 3. Storage Layers

- Canonical survivor: `storage` for repositories and persistence logic; `db` for engine/bootstrap concerns
- Target phase: Phase 1
- Migration path:
  - In Phase 0B prep, block new persistence abstractions outside `storage` and `db`.
  - Route all repository implementations, caching-backed stores, and domain persistence services into `storage`.
  - Restrict `db` to connection lifecycle, engine selection, and low-level database switching concerns.
  - Move or delete overlapping repository/service code from `persistence`.
  - In Phase 2, retain only compatibility facades if unavoidable; otherwise remove `persistence`.
- Design boundary:
  - `db` is infrastructure plumbing.
  - `storage` is the canonical application-facing persistence layer.
  - `persistence` is not a long-term survivor.

### 4. HTTP Routing

- Canonical survivor: `server`
- Target phase: Phase 1
- Migration path:
  - In Phase 0B prep, freeze new externally reachable endpoints outside `server`.
  - Keep request routing, handler registration, schemas, and API lifecycle management in `server`.
  - Demote `gateway` to ingress concerns only: reverse-proxy policy, edge translation, or deployment-specific composition.
  - Any `gateway` business routing or handler duplication should be re-homed into `server`.
  - In Phase 2, either keep a slim infra-facing `gateway` package or remove it if deployment config fully replaces it.
- Design boundary:
  - `server` owns the canonical HTTP API.
  - `gateway` must not remain a second application router.

### 5. Monitoring

- Canonical survivor: `observability`
- Target phase: Phase 1
- Migration path:
  - In Phase 0B prep, direct all new metrics, traces, and runtime instrumentation to `observability`.
  - Collapse instrumentation helpers from `monitoring` and `telemetry` into `observability`.
  - Keep temporary re-export modules where needed so imports can move without breaking broad call graphs.
  - Update docs and runbooks to point to `observability` as the single instrumentation surface.
  - In Phase 2, delete thin wrappers once import migration is complete.
- Design boundary:
  - `observability` owns metrics, tracing, logging integration, and health telemetry.
  - `monitoring` and `telemetry` are compatibility names, not peer systems.

### 6. Task Management

- Canonical survivor: `queue` for execution and `scheduler` for time-based orchestration
- Target phase: Phase 1
- Migration path:
  - In Phase 0B prep, stop adding executor logic to `tasks`.
  - Recast `tasks` as a migration source, not a destination package.
  - Move worker handoff, retry, queue state, and execution semantics into `queue`.
  - Move cron, delayed execution, and calendar/time-window logic into `scheduler`.
  - Shift existing `tasks` callers to one of those two surfaces based on whether they need execution or timing.
  - In Phase 2, remove `tasks` or keep it as a narrow façade only if external compatibility requires it.
- Design boundary:
  - `queue` owns running work.
  - `scheduler` owns deciding when work should be enqueued.
  - `tasks` should not remain a third orchestration substrate.

## Sequencing Rules

1. Phase 0B lanes may add guardrails, docs, and compatibility shims, but should not deepen duplicate abstractions.
2. Phase 1 lanes should consolidate one cluster at a time with explicit caller migration plans.
3. Phase 2 lanes should remove transitional wrappers only after import and runtime ownership are verified.

## Exit Criteria for Future Implementation Lanes

A cluster can be considered resolved only when:

- one canonical survivor is documented and enforced for new work,
- duplicate modules no longer own independent business logic in that area,
- temporary wrappers are clearly marked as compatibility-only, and
- operator and developer docs point to the canonical subsystem only.

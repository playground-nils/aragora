# ADR 020: Event Dispatch Consolidation

## Status

Accepted

## Context

Aragora currently has two overlapping event dispatch subsystems with different APIs and delivery models:

1. `aragora/events/` is the general event-dispatch layer. It exposes `EventEmitter`, `dispatch_event(...)`, `WebhookDispatcher`, batch and async dispatchers, and cross-subscriber routing. Current consumers include `aragora/memory/triggers.py`, `aragora/workflow/engine.py`, `aragora/inbox/debate_router.py`, `aragora/observability/metrics/slo.py`, and `aragora/server/startup/workers.py`.
2. `aragora/connectors/enterprise/streaming/` is a second event transport layer for Kafka, RabbitMQ, and SNS/SQS. It exposes broker-specific `consume(...)` and `publish(...)` APIs and is documented as the path for real-time event ingestion into the Knowledge Mound and decision pipelines.

These subsystems overlap in responsibility:

- both move event payloads between Aragora and external consumers
- both implement retry, buffering, resilience, and delivery semantics
- both require event typing, routing, and observability
- some callers already bridge manually, such as `aragora/inbox/debate_router.py`, which emits to an event bus and separately calls `dispatch_event(...)`

This duplication creates inconsistent producer APIs, duplicated reliability logic, and pressure to keep multiple event contracts aligned.

## Decision

Aragora will consolidate duplicate event dispatch into a single canonical event bus rooted in `aragora/events/`.

The consolidation approach is:

1. `aragora/events/` becomes the only canonical producer and subscriber API for application events.
2. Webhook delivery, hook execution, WebSocket fan-out, and cross-subscriber routing become bus subscribers or adapters, not parallel dispatch entrypoints.
3. `aragora/connectors/enterprise/streaming/` becomes a transport-adapter layer. Kafka, RabbitMQ, and SNS/SQS connectors will translate broker messages into canonical bus events on ingress and subscribe to canonical bus events for egress.
4. Event schemas, correlation metadata, retry policy, rate limiting, dead-letter handling, and dispatch metrics are standardized at the bus boundary instead of being reimplemented per subsystem.
5. New code must publish once to the canonical bus and must not dual-write to a second dispatcher.

Migration will proceed in phases:

1. Define the canonical event envelope and subscriber contract in `aragora/events/`.
2. Add streaming adapters that map broker-specific payloads to and from the canonical bus event shape.
3. Repoint existing direct `dispatch_event(...)` and manual bridge call sites to publish through the canonical bus.
4. Deprecate duplicate dispatch surfaces once webhook and streaming delivery run only as adapters.

## Consequences

### Positive

- Producers get one event API instead of separate webhook and broker dispatch paths.
- Reliability behavior becomes consistent across webhook, streaming, and internal subscribers.
- Streaming connectors keep their broker-specific resilience features while losing ownership of application-level routing.
- Future integrations can attach as adapters without creating another dispatch subsystem.

### Negative

- Adapter work is required to preserve existing Kafka, RabbitMQ, and SNS/SQS semantics during migration.
- The `events` package will need cleanup because it already contains multiple dispatch variants internally.
- Short-term coexistence is unavoidable while callers migrate off dual-write behavior.

### Follow-Up Implications

- A later implementation change should define the exact canonical bus interface and deprecation path for legacy dispatcher helpers.
- Documentation for hooks, webhooks, and streaming connectors should be updated to describe them as adapters to the canonical bus.

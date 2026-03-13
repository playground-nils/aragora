# Aragora Test Taxonomy

**Date:** March 13, 2026
**Status:** Draft governance reference
**Purpose:** Define the canonical test categories used in Aragora and map
coverage expectations to the subsystem buckets in
[`subsystem-ledger.md`](./subsystem-ledger.md).

## Categories

| Category | Scope | Primary Goal | Typical Isolation Level |
|---|---|---|---|
| **unit** | Single function, class, or narrow module seam | Prove local correctness and edge-case handling | Fully isolated with mocks or fakes |
| **integration** | Multiple Aragora modules or an Aragora module plus its real persistence, queue, or network boundary | Prove subsystem contracts and composition behavior | Partial isolation with real adapters where practical |
| **e2e** | User-visible workflows exercised through CLI, API, worker, or browser surfaces | Prove the shipped path behaves correctly across major boundaries | Minimal mocking with production-like wiring |
| **benchmark** | Repeatable performance, latency, throughput, cost, or quality measurement runs | Detect regressions in speed, scale, or deliberation quality | Controlled harness and fixed workload |

## Taxonomy Rules

1. Classify a test by the highest-level behavior it proves, not by its
   directory.
2. If a test crosses a process, storage, queue, or HTTP boundary, it is not a
   unit test.
3. If a test exists mainly to measure runtime or quality deltas over time, it is
   a benchmark even when it also asserts correctness.
4. End-to-end coverage should stay narrow and focus on critical shipped flows;
   breadth belongs in unit and integration suites.

## Coverage Mapping To Subsystem Ledger Buckets

The subsystem ledger groups Aragora code into `canonical`,
`core-but-messy`, `expansion`, `compatibility`, and `defer`. Coverage
expectations should scale with the governance criticality of each bucket.

| Ledger bucket | Unit coverage expectation | Integration coverage expectation | E2E coverage expectation | Benchmark coverage expectation |
|---|---|---|---|---|
| `canonical` | Required for core logic, validation, failure paths, and edge cases | Required for all load-bearing seams between runtime subsystems | Required for critical operator and production flows | Required where latency, throughput, cost, or debate quality are release gates |
| `core-but-messy` | Required to pin down current behavior before cleanup | Required at overlap boundaries where drift risk is highest | Targeted coverage for the workflows users depend on today | Recommended for hotspots that create operational instability |
| `expansion` | Required for stable public contracts and domain logic | Required when the feature touches canonical services or external adapters | Selective, only for shipped or revenue-relevant workflows | Optional unless performance is a product claim or adoption gate |
| `compatibility` | Minimal but required for adapter invariants and translation logic | Required at legacy bridge points to prevent regressions during reduction | Rare; only when a compatibility path remains customer-facing | Optional; add only if a bridge is known to be slow or expensive |
| `defer` | Minimal smoke-level coverage only if the module still loads in CI | Avoid broad integration investment unless a deferred module blocks canonical work | Avoid by default | Avoid by default |

## Bucket-Oriented Coverage Ledger

This ledger maps the taxonomy to the subsystem buckets defined in
[`subsystem-ledger.md`](./subsystem-ledger.md).

| Subsystem ledger bucket | Representative modules from ledger | Primary test emphasis | Minimum category mix |
|---|---|---|---|
| `canonical` | `agents`, `cli`, `control_plane`, `core`, `debate`, `knowledge`, `memory`, `nomic`, `observability`, `server`, `storage`, `swarm` | Correctness of core runtime and production entrypoints | Unit plus integration everywhere; e2e for operator and user paths; benchmark for load-bearing paths |
| `core-but-messy` | `audit`, `billing`, `connectors`, `events`, `gateway`, `integrations`, `persistence`, `queue` | Contract safety across unclear or duplicated boundaries | Unit plus integration required; e2e for duplicate-cluster workflows; benchmark for high-churn hotspots |
| `expansion` | `compliance`, `documents`, `evaluation`, `gauntlet`, `inbox`, `pipeline`, `ranking`, `reports`, `workflow` | Feature correctness and dependency wiring | Unit required; integration where external systems or persisted outputs are involved; e2e for flagship flows; benchmark when product value depends on performance |
| `compatibility` | `compat`, `harnesses`, `tenancy`, `training` | Stability of bridge behavior and backwards-compat guarantees | Unit plus integration required; selective e2e; benchmark only when the bridge is operationally hot |
| `defer` | `analysis`, `bots`, `caching`, `hooks`, `monitoring`, `performance`, `policy`, `replay`, `tools`, `verification`, `webhooks`, `workspace` | Low-cost regression containment | Targeted unit tests first; selective integration coverage only when active behavior is still supported |

## Review Rules

- Every new or changed test should declare one primary category: `unit`,
  `integration`, `e2e`, or `benchmark`.
- Reviewers should ask whether the chosen category matches the subsystem
  ledger bucket of the code under change.
- Canonical and core-but-messy changes should not rely on unit-only evidence
  when behavior crosses process, storage, queue, connector, or API
  boundaries.
- Benchmark coverage is required only when non-functional regressions would
  materially affect production operation, cost, or rollout safety.

## Practical Classification Examples

| Example | Category | Ledger bucket fit |
|---|---|---|
| Validating a single permission checker branch in `rbac` | **unit** | `canonical` |
| Exercising server handlers against real storage and auth wiring | **integration** | `canonical` |
| Running a full CLI-to-worker debate flow and asserting the final receipt | **e2e** | `canonical` |
| Measuring debate completion latency across a fixed agent roster | **benchmark** | `canonical` |
| Verifying connector-to-integration translation at a duplicate abstraction boundary | **integration** | `core-but-messy` |
| Timing a high-volume connector ingestion path to catch queue backpressure regressions | **benchmark** | `core-but-messy` |
| Proving a marketplace export formatter preserves contract shape | **unit** | `expansion` |
| Checking a compatibility adapter still translates legacy fields correctly | **integration** | `compatibility` |

## Practical Usage

When opening a plan, PR, or autonomous lane:

1. Identify the subsystem ledger bucket for the modules being changed.
2. Select the minimum test category mix required by that bucket.
3. Add stricter coverage if the change crosses external boundaries or affects
   operator-visible workflows.

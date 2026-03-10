# Aragora Subsystem Classification Ledger

**Date:** March 10, 2026
**Campaign:** phase0a-bootstrap-governance
**Task:** phase0a-003
**Purpose:** Classify all top-level Aragora packages into governance buckets
for use in bootstrap phasing, scope gating, and autonomous work assignment.

## Classification Buckets

| Bucket | Definition | Autonomous Work Policy |
|--------|-----------|----------------------|
| **canonical** | Load-bearing production runtime; always loaded on server startup | Phase 0B+ only, with merge gate and verification |
| **core-but-messy** | Important but has structural debt or unclear boundaries | Phase 1+ only, with split plan required |
| **expansion** | Real features extending the platform, not in core loop | Phase 1+ for cleanup, Phase 2 for rationalization |
| **compatibility** | Exists for backwards compat or third-party bridging | Phase 2 for reduction |
| **defer** | Scaffolded, speculative, or unused; not blocking anything | No autonomous work until core is solid |

---

## Canonical (17 modules)

These are essential to production runtime, loaded during server startup,
and have high import connectivity (imported by 10+ other modules).

| Module | Files | ~LOC | Rationale |
|--------|-------|------|-----------|
| `agents` | 80 | 35.5k | Agent implementations — all debate execution flows through here |
| `auth` | 15 | 8.9k | Authentication/SSO — gate for all authenticated paths |
| `cli` | 79 | 38.5k | CLI interface — primary operator interaction surface |
| `config` | 14 | 6.6k | Configuration management — imported by 55+ modules |
| `control_plane` | 44 | 24.8k | Enterprise orchestration — agent registry, scheduling, health |
| `core` | 19 | 5.6k | Core types/primitives — foundational data structures |
| `db` | 4 | 1.6k | Database abstraction — SQLite/PostgreSQL switching |
| `debate` | 259 | 129.6k | Core debate engine — Arena, consensus, convergence |
| `knowledge` | 174 | 97.1k | Knowledge Mound — 45 adapters, semantic search, federation |
| `memory` | 56 | 23.5k | Memory systems — multi-tier continuum, consensus store |
| `nomic` | 148 | 76.5k | Self-improvement orchestrator — meta-planner, task decomposer |
| `observability` | 66 | 31k | Metrics/tracing — Prometheus, OpenTelemetry |
| `rbac` | 35 | 19.6k | Role-based access control — 360+ permissions, middleware |
| `resilience` | 13 | 4.7k | Circuit breakers, retry, timeout — fault tolerance |
| `server` | 1,087 | 487.8k | HTTP/WebSocket API — 3,000+ operations, 700+ handler modules |
| `storage` | 103 | 53.1k | Data persistence — PostgreSQL, Redis, repositories |
| `swarm` | 12 | 7.8k | Supervisor-backed orchestration — campaign execution engine |

**Subtotal:** 2,208 files, ~1,052k LOC (63% of production code)

---

## Core-but-Messy (8 modules)

Medium-high criticality with acknowledged structural issues. These work
but have unclear boundaries, duplicate abstractions, or excessive coupling.

| Module | Files | ~LOC | Structural Issue |
|--------|-------|------|-----------------|
| `audit` | 43 | 23.9k | Overlaps with compliance, observability, and gauntlet |
| `billing` | 38 | 25k | Large for current usage; budget/cost/metering/forecaster overlap |
| `connectors` | 262 | 132.9k | Largest hairball — 262 files across chat, enterprise, streaming |
| `events` | 32 | 11.9k | Overlaps with hooks, webhooks; three event dispatch mechanisms |
| `gateway` | 73 | 31k | Partially duplicates server routing; unclear boundary with server |
| `integrations` | 40 | 22.1k | Overlaps with connectors; slack/email/discord appear in both |
| `persistence` | 27 | 12.7k | Overlaps with storage and db; unclear which is canonical |
| `queue` | 17 | 5k | Redis Streams job queue — works but boundary with events unclear |

**Subtotal:** 532 files, ~265k LOC (16% of production code)

**Key duplicate clusters:**
- `events` / `hooks` / `webhooks` — three separate event dispatch systems
- `connectors` / `integrations` — overlapping platform adapters
- `persistence` / `storage` / `db` — three storage abstraction layers
- `gateway` / `server` — overlapping HTTP routing

---

## Expansion (28 modules)

Real features that extend the platform but are not in the core
debate/serve/orchestrate loop. Generally well-isolated.

| Module | Files | ~LOC | Purpose |
|--------|-------|------|---------|
| `analytics` | 25 | 13k | Dashboard, debate analytics |
| `backup` | 8 | 4.5k | Disaster recovery manager |
| `canvas` | 12 | 5.8k | Orchestration canvas / visual DAG |
| `channels` | 15 | 7.2k | Multi-platform delivery formatters |
| `compliance` | 18 | 10.5k | SOC 2 controls, EU AI Act |
| `deliberation` | 14 | 7.8k | Deliberation templates and patterns |
| `documents` | 16 | 9.2k | Document ingestion, chunking, indexing |
| `evaluation` | 12 | 6.5k | LLM-as-Judge quality dimensions |
| `evidence` | 14 | 7.8k | Evidence collection, quality scoring |
| `evolution` | 10 | 5.5k | Prompt evolution from debate patterns |
| `explainability` | 12 | 6.8k | Decision factor decomposition |
| `export` | 11 | 5.9k | Multi-format debate export |
| `gauntlet` | 36 | 16.3k | Adversarial testing, receipts |
| `goals` | 8 | 4.2k | Idea-to-goal transformation |
| `inbox` | 16 | 9.4k | Trust wedge — Gmail triage |
| `marketplace` | 14 | 7.6k | Agent/skill marketplace |
| `mcp` | 11 | 6.1k | Model Context Protocol server |
| `pipeline` | 41 | 21.3k | 4-stage idea-to-execution pipeline |
| `ranking` | 6 | 3.2k | ELO ratings and calibration |
| `reasoning` | 16 | 8.1k | Belief networks, provenance |
| `reports` | 10 | 5.5k | Report generation (PDF, MD, JSON) |
| `rlm` | 31 | 15k | Recursive Language Models |
| `routing` | 9 | 4.8k | Smart provider routing, Pareto optimizer |
| `sandbox` | 8 | 4.3k | Docker-based code execution |
| `scheduler` | 11 | 6.2k | Automated scheduling |
| `services` | 7 | 3.8k | ServiceRegistry pattern |
| `skills` | 18 | 10.2k | Skill registry, marketplace, installer |
| `workflow` | 99 | 37.7k | DAG-based automation engine |

**Subtotal:** 534 files, ~238k LOC (14% of production code)

---

## Compatibility (4 modules)

Exists for backwards compatibility or third-party bridging. Not on any
critical production path but may be needed for specific integrations.

| Module | Files | ~LOC | Purpose |
|--------|-------|------|---------|
| `compat` | 12 | 5.2k | OpenClaw compatibility layer, PR watch daemon |
| `harnesses` | 8 | 3.8k | Claude Code / Codex tool integration |
| `tenancy` | 9 | 3.5k | Multi-tenant isolation support |
| `training` | 8 | 2.5k | Fine-tuning integration (SFT, DPO) |

**Subtotal:** 37 files, ~15k LOC (0.9% of production code)

---

## Defer (64 modules)

Scaffolded, speculative, or low-priority. These do not block core
functionality and should not receive autonomous work until the canonical
and core-but-messy layers are solid.

### Scaffolded subsystems with real but unused code

| Module | Files | ~LOC | Notes |
|--------|-------|------|-------|
| `analysis` | 29 | 15.4k | NL document querying — no production callers |
| `approvals` | 6 | 3.2k | Cross-channel approval tokens — unused |
| `autonomous` | 9 | 4.8k | Self-improving loop enhancements — superseded by nomic |
| `blockchain` | 11 | 6.2k | ERC-8004 agent identity — deferred |
| `broadcast` | 10 | 5.5k | Post-debate podcast engine — speculative |
| `client` | 41 | 17.5k | Python SDK client — separate package concern |
| `computer_use` | 8 | 4.1k | Computer use detection/bridge — experimental |
| `genesis` | 12 | 6.8k | Fractal resolution, agent evolution — speculative |
| `ideacloud` | 7 | 3.6k | Idea cloud workspace — scaffolded |
| `learning` | 9 | 4.9k | Continual learning — scaffolded |
| `live` | 15 | 8.2k | Next.js frontend (separate build) — not Python runtime |
| `security` | 22 | 13.6k | Encryption/key management — overlaps with auth |
| `visualization` | 10 | 5.4k | Argument cartography — UI-dependent |

### Minimal or stub modules

| Module | Files | ~LOC | Notes |
|--------|-------|------|-------|
| `bots` | 8 | 4.2k | Bot framework — overlaps with connectors |
| `caching` | 5 | 2.8k | Result caching — zero dependents |
| `coordination` | 7 | 3.8k | Cross-workspace federation — early stage |
| `embeddings` | 3 | 1.5k | Embeddings service — zero dependents |
| `extensions` | 6 | 3.1k | Gastown/moltbot layers |
| `fabric` | 9 | 5.2k | High-scale agent substrate — speculative |
| `fixtures` | 4 | 2.1k | Test fixture utilities |
| `hooks` | 6 | 3.2k | YAML event hooks — overlaps with events |
| `implement` | 7 | 3.8k | Multi-model implementation — overlaps with nomic |
| `insights` | 6 | 3.3k | Post-debate learnings |
| `interrogation` | 8 | 4.5k | Debate-driven clarification |
| `introspection` | 7 | 3.7k | Agent self-awareness — experimental |
| `maintenance` | 4 | 2.1k | Maintenance utilities |
| `migrations` | 8 | 4.5k | Schema migration system |
| `ml` | 9 | 5.1k | Local ML: embeddings, scoring |
| `moderation` | 6 | 3.2k | Spam filtering |
| `modes` | 8 | 4.3k | Operational modes (Architect, Coder, etc.) |
| `monitoring` | 5 | 2.7k | Runtime health — overlaps with observability |
| `notifications` | 4 | 2.1k | Notification service |
| `onboarding` | 7 | 3.8k | Setup wizard — zero dependents |
| `ops` | 4 | 2.2k | Deployment validator |
| `performance` | 6 | 3.3k | Batch loading, adaptive caching |
| `playbooks` | 5 | 2.6k | Operational playbook definitions |
| `plugins` | 7 | 3.8k | Plugin architecture |
| `policy` | 6 | 3.2k | Per-tool policy enforcement |
| `privacy` | 8 | 4.5k | Anonymization, consent, GDPR |
| `prompt_engine` | 7 | 3.9k | Prompt validation via debate |
| `protocols` | 5 | 2.6k | Protocol definitions |
| `pulse` | 12 | 6.8k | Trending topics ingestion |
| `replay` | 6 | 3.3k | Debate record/replay |
| `runtime` | 5 | 2.7k | Budget autotuner |
| `shared` | 3 | 1.4k | Shared utilities |
| `spectate` | 6 | 3.2k | Real-time debate observation |
| `stores` | 4 | 2.1k | Additional store abstractions |
| `streaming` | 7 | 3.8k | WebSocket/Kafka hardening |
| `sync` | 5 | 2.7k | Directory sync — zero dependents |
| `tasks` | 6 | 3.2k | Task management — overlaps with queue |
| `telemetry` | 3 | 1.5k | Re-export of observability |
| `templates` | 8 | 4.3k | Domain debate templates |
| `tools` | 7 | 3.8k | Agent code reading/writing |
| `topics.py` | 1 | 0.3k | Topic utilities (single file) |
| `tournaments` | 8 | 4.5k | ELO competitions |
| `transcription` | 5 | 2.7k | Speech-to-text |
| `types` | 4 | 2.1k | Type definitions |
| `uncertainty` | 4 | 2.1k | Uncertainty quantification |
| `utils` | 6 | 3.2k | General utilities |
| `verification` | 5 | 2.7k | Z3/Lean formal verification |
| `verticals` | 12 | 6.8k | Domain specialists |
| `webhooks` | 6 | 3.2k | Webhook delivery — overlaps with events |
| `workspace` | 8 | 4.3k | Bead/convoy workspace |
| `worktree` | 5 | 2.7k | Git worktree fleet coordination |

**Subtotal:** ~468 files, ~174k LOC (10% of production code)

### Isolated modules (zero dependents, zero imports)

The following modules have no incoming imports from other aragora code and
are not on the server startup path. They are candidates for eventual
deprecation or extraction:

`caching`, `deliberation`, `embeddings`, `hooks`, `live`, `monitoring`,
`onboarding`, `performance`, `playbooks`, `policy`, `prompts`, `sandbox`,
`spectate`, `streaming`, `sync`, `tasks`, `telemetry`, `tools`,
`transcription`, `types`

---

## Summary

| Bucket | Modules | Files | ~LOC | % Code |
|--------|---------|-------|------|--------|
| Canonical | 17 | 2,208 | 1,052k | 63% |
| Core-but-Messy | 8 | 532 | 265k | 16% |
| Expansion | 28 | 534 | 238k | 14% |
| Compatibility | 4 | 37 | 15k | 0.9% |
| Defer | 64 | 468 | 174k | 10% |
| **Total** | **121** | **3,779** | **1,744k** | **100%** |

## Implications for Bootstrap Phasing

1. **Phase 0A** (current): Documentation only — this ledger itself is Phase 0A output
2. **Phase 0B**: Code changes restricted to canonical modules only (17 modules, 63% of code)
3. **Phase 1**: Extends to core-but-messy (8 modules) — requires split plans for duplicate clusters
4. **Phase 2**: Expansion module rationalization and defer-bucket triage
5. **No phase**: Autonomous work on defer-bucket modules is not planned

## Duplicate Subsystem Clusters Requiring Phase 1 Resolution

| Cluster | Modules | Resolution Strategy |
|---------|---------|-------------------|
| Event dispatch | `events`, `hooks`, `webhooks` | Consolidate into `events` with hook/webhook as thin adapters |
| Platform connectors | `connectors`, `integrations` | Merge into `connectors` with clear adapter pattern |
| Storage layers | `persistence`, `storage`, `db` | Canonical: `storage` + `db`; deprecate `persistence` |
| HTTP routing | `gateway`, `server` | Canonical: `server`; gateway becomes reverse-proxy config only |
| Monitoring | `monitoring`, `observability`, `telemetry` | Canonical: `observability`; others become re-exports |
| Task management | `tasks`, `queue`, `scheduler` | Canonical: `queue` for execution; `scheduler` for timing |

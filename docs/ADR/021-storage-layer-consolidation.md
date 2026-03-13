# ADR 021: Storage Layer Consolidation

## Status

Accepted

## Context

Aragora currently exposes four overlapping storage subsystems:

1. `aragora/storage/` contains repositories and runtime-facing stores for application data, spanning PostgreSQL, SQLite, and Redis-backed concerns.
2. `aragora/db/` provides lower-level database abstractions and backend switching for SQLite/PostgreSQL access.
3. `aragora/persistence/` owns path resolution, consolidated-schema definitions, and migration/config helpers for legacy and consolidated database layouts.
4. `aragora/nomic/stores/` persists Nomic and swarm state in local file-backed stores such as bead/convoy directories and JSONL receipt/run stores.

These layers overlap in naming, path ownership, and the question of where new durable state should live. The governance ledger already flags `storage`, `db`, `persistence`, and parts of `nomic/stores` as one duplicate cluster. Without a decision record, contributors can keep adding new stores to whichever layer is nearby, increasing drift between runtime persistence, migration logic, and local artifact storage.

## Decision

Aragora will use a **delineation-first consolidation strategy**:

1. **`aragora/storage/` is the canonical application storage layer.**
   All new domain repositories, cache adapters, and runtime persistence APIs for server or CLI features should live here.
2. **`aragora/db/` is the canonical database primitive layer.**
   It should provide connections, transactions, engine selection, and backend-specific helpers, but not domain-specific repositories.
3. **`aragora/persistence/` becomes a transitional compatibility layer only.**
   It remains the home for migration tooling, schema-path compatibility, and database layout translation, but it should not gain new business-facing store classes.
4. **`aragora/nomic/stores/` remains separate, but only for local Nomic artifact storage.**
   Its scope is bounded to bead/convoy state, run logs, and signed/self-improvement receipts stored in workspace or data-dir files. It is not a general-purpose persistence layer for shared product data.

This is not a full merge of all four directories into one package. It is a consolidation of responsibilities:

- `storage` answers "how application data is stored and queried"
- `db` answers "how databases are opened and managed"
- `persistence` answers "how legacy and consolidated schemas/paths are migrated"
- `nomic/stores` answers "how local Nomic artifacts are durably recorded"

## Consequences

### Positive

- New persistence work has one primary home: `aragora/storage/`, built on `aragora/db/`.
- `aragora/persistence/` stops competing with `storage` as a place to add new store implementations.
- `aragora/nomic/stores/` keeps its file-backed strengths without being mistaken for the general storage abstraction.
- Future reviews can reject storage drift based on a documented boundary instead of taste.

### Negative

- Existing code will still reflect historical overlap until follow-up migrations happen.
- Some helpers in `persistence` may need eventual relocation into `db` or `storage` to complete the cleanup.
- Teams working in Nomic must document when local artifact storage intentionally differs from runtime database storage.

### Migration Steps

1. Freeze new domain-store development in `aragora/persistence/` and `aragora/nomic/stores/`.
2. Route new runtime persistence through `aragora/storage/`, using `aragora/db/` for backend access.
3. Treat `aragora/persistence/` as migration/schema compatibility infrastructure and move any business-facing store APIs out over time.
4. Keep `aragora/nomic/stores/` limited to workspace/data-dir artifacts; if a Nomic record becomes shared runtime data, expose it through `aragora/storage/` instead.


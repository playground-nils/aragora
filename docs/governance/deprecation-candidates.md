# Defer-Bucket Deprecation Candidates

Source: [subsystem-ledger](./subsystem-ledger.md) defer bucket, with emphasis on isolated modules that are low-risk deprecation, removal, or extraction candidates.

Method: checked `tests/` for direct coverage and searched `aragora/`, `tests/`, and `scripts/` for `from aragora.<module>` / `import aragora.<module>` references. "No non-test imports found" means no production Python callers were found in that scan.

| Path | Purpose | Test status | Import status | Recommendation |
| --- | --- | --- | --- | --- |
| `aragora/caching` | Result-cache decorators and cache helpers. | Targeted unit tests present in `tests/caching/`. | No non-test imports found; only referenced by its own tests. | `remove` after a short deprecation window; the module is isolated and not carrying runtime load. |
| `aragora/embeddings` | Placeholder embeddings service surface. | Minimal import smoke coverage in `tests/embeddings/test_embeddings_imports.py`. | No non-test imports found; only test references. | `remove`; current footprint is tiny and unused. |
| `aragora/hooks` | YAML-configured event hooks and hook-condition loading. | Covered by `tests/hooks/` and one integration test. | No non-test imports found; references are test-only. | `consolidate` into canonical `events` or `webhooks`, then deprecate this package. |
| `aragora/live` | Next.js frontend subtree and UI test suite. | Extensive frontend unit and e2e coverage under `aragora/live/__tests__` and `aragora/live/e2e/`. | No Python imports found in runtime code. | `keep` only as an extracted/separate build concern; do not treat it as active Python runtime surface. |
| `aragora/onboarding` | Setup wizard scaffolding. | Covered by `tests/onboarding/test_wizard.py`. | No non-test imports found; test-only usage. | `deprecate` now and `remove` if no product owner revives it. |
| `aragora/streaming` | Reconnection, reliability, health, and replay helpers for streaming. | Covered by `tests/streaming/`. | No non-test imports found; only test references. | `deprecate`; remove unless a concrete runtime owner reconnects it to `server` or `events`. |
| `aragora/sync` | Directory-sync models, watcher, and sync manager. | Covered by `tests/sync/` and `tests/test_sync.py`. | No non-test imports found; test-only usage. | `remove`; isolated and not on a production path. |
| `aragora/telemetry` | Small telemetry collector and research-event helpers. | Covered by `tests/telemetry/test_telemetry_exports.py`. | No non-test imports found; test-only usage. | `consolidate` into `observability`, then deprecate this package. |
| `aragora/tools` | Code-reading/writing helper surface. | Covered by `tests/tools/test_code.py` and `tests/test_code_tools.py`. | No non-test imports found; test-only usage. | `consolidate` into `aragora/mcp/tools_module` or remove the standalone package. |
| `aragora/transcription` | Whisper and YouTube transcription adapters. | Covered by `tests/transcription/` and handler/worker tests. | Production imports exist in `aragora/server/handlers/transcription.py` and `aragora/queue/workers/transcription_worker.py`. | `keep` for now; it is defer-bucket by governance, but not a clean deprecation candidate yet. |

## Summary

- Highest-confidence removal candidates: `caching`, `embeddings`, `onboarding`, `streaming`, `sync`.
- Highest-confidence consolidation candidates: `hooks`, `telemetry`, `tools`.
- Extraction candidate rather than removal: `live`.
- Not ready for deprecation despite defer-bucket status: `transcription`, because runtime callers still exist.

# ADR-017: Backend Runtime Entrypoint and Compatibility

## Status
Accepted

## Context

Aragora currently exposes multiple backend startup surfaces:

- `aragora serve`
- `python -m aragora.server`
- `aragora.server.unified_server.run_unified_server(...)`
- `uvicorn aragora.server.app:app`
- `ARAGORA_USE_FASTAPI=true python -m aragora.server`

The repository documentation already distinguishes between the full unified server runtime and the partial FastAPI surface, but the distinction is spread across `aragora/server/README.md`, `aragora/server/ARCHITECTURE.md`, and implementation modules. That leaves four gaps:

1. There is no single canonical name for the backend runtime entrypoint.
2. Compatibility surfaces are not classified consistently.
3. Runtime-version migration expectations are implied but not codified.
4. The relationship between the server runtime and FastAPI is not stated as a single architecture rule.

This ADR defines the canonical backend runtime entrypoint, names the supported compatibility paths, and establishes how runtime versions and server surfaces are documented and migrated.

## Decision

### Canonical backend entrypoint

Aragora's canonical backend runtime is the **Unified Backend Runtime**.

Its naming convention is:

- Product and docs name: `Unified Backend Runtime`
- Canonical operator command: `aragora serve`
- Canonical Python module entrypoint: `python -m aragora.server`
- Canonical bootstrap callable: `aragora.server.unified_server.run_unified_server`

When documentation, scripts, or operator guidance need one backend startup command, they must prefer `aragora serve`. When Python-level implementation detail is required, they must refer to `python -m aragora.server` or `aragora.server.unified_server.run_unified_server`, not to `aragora.server.app:app`.

### Unified server and FastAPI relationship

The unified server and FastAPI are one backend system with two HTTP surfaces, not two peer backends:

- The unified server is the canonical backend runtime and owns the full production API surface plus coordinated WebSocket stream startup.
- FastAPI is the async migration surface for selected route families and targeted integrations.
- Running FastAPI through `ARAGORA_USE_FASTAPI=true` still uses the unified runtime envelope for process startup, environment handling, and stream orchestration.
- `aragora.server.app:app` is a framework-specific application object, not the canonical backend identity.

### Compatibility classification system

All backend runtime surfaces must be classified with one of these labels:

| Classification | Meaning | Stability expectation |
|---|---|---|
| `Canonical` | Default operator-facing path for the backend runtime | Preferred for docs, automation, and support |
| `Equivalent` | Alternate spelling or invocation of the same canonical runtime | Fully supported, same behavior target |
| `Compatible` | Supported bridge surface with intentionally narrower scope | Supported during migration, but not the default |
| `Deprecated` | Still recognized for backward compatibility with an announced removal path | Warn and migrate off |
| `Unsupported` | Not a supported runtime contract | No compatibility guarantees |

### Supported runtime compatibility paths

The supported backend runtime paths are:

| Path | Classification | Notes |
|---|---|---|
| `aragora serve` | `Canonical` | Default operator command for the full backend runtime |
| `python -m aragora.server` | `Equivalent` | Canonical module form of the same runtime |
| `aragora.server.unified_server.run_unified_server(...)` | `Equivalent` | Canonical programmatic bootstrap |
| `ARAGORA_USE_FASTAPI=true aragora serve` | `Compatible` | Same runtime envelope, FastAPI HTTP surface substituted |
| `ARAGORA_USE_FASTAPI=true python -m aragora.server` | `Compatible` | Module form of the same compatibility path |
| `uvicorn aragora.server.app:app` | `Compatible` | Partial FastAPI-only surface for targeted integrations and migration work |
| `aragora.server.api.run_api_server(...)` | `Deprecated` | Legacy narrow API server, not the canonical backend runtime |

No other startup path is a supported backend-runtime contract unless it is explicitly documented in a later ADR.

### Supported API compatibility paths

The supported HTTP compatibility paths under this runtime decision are:

| API path family | Classification | Notes |
|---|---|---|
| `/api/v1/*` | `Canonical` | Stable primary API family on the unified backend runtime |
| `/api/v2/*` | `Compatible` | Migration family, primarily surfaced through FastAPI route modules today |
| Legacy unversioned paths such as `/debates` and other non-versioned aliases covered by ADR-006 | `Deprecated` | Maintained only for backward compatibility and sunset-managed migration |

### Runtime version policy

Aragora distinguishes between:

- **Runtime v1**: the full unified-server surface, including handler-registry HTTP coverage and coordinated stream startup.
- **Runtime v2**: the FastAPI-native route family and compatibility surface under `/api/v2/*`.

Migration between runtime versions follows these rules:

1. Runtime migration is incremental by route family, not a flag day cutover.
2. New backend capabilities should default to the canonical runtime envelope and may expose their HTTP contract in FastAPI first when that reduces new legacy-handler debt.
3. A route family may move from `Compatible` to `Canonical` only when it has functional parity for authentication, authorization, tenancy, observability, and documented operational behavior.
4. `Equivalent` paths must remain behaviorally aligned because they are the same runtime contract expressed through different invocation forms.
5. `Compatible` paths may expose a narrower surface area, but they must not claim canonical completeness.
6. `Deprecated` paths require explicit deprecation headers or documentation, a migration target, and a sunset window consistent with ADR-006.

### Documentation rules

All future backend docs should use these naming conventions:

- Say `aragora serve` when giving a single recommended startup command.
- Say `Unified Backend Runtime` when referring to the canonical backend as a product capability.
- Say `FastAPI compatibility surface` when referring to `aragora.server.app:app` or `ARAGORA_USE_FASTAPI=true`.
- Avoid calling FastAPI "the backend" without qualification.

## Consequences

### Positive

- One backend runtime identity now exists for operators, docs, and automation.
- FastAPI is documented as part of the same backend architecture instead of a competing server.
- Compatibility promises are explicit, which reduces accidental expansion of legacy or partial surfaces.
- Runtime-version migration can proceed route-by-route without ambiguity about what is canonical.

### Negative

- Some existing documentation may need follow-up cleanup where FastAPI is described too broadly.
- The deprecated narrow API server path remains documented until follow-up removal work is planned.

### Neutral

- This ADR does not change runtime behavior or implementation.
- Existing compatibility paths remain available; only their classification and naming are standardized here.

## Related

- `aragora/server/__main__.py`
- `aragora/server/unified_server.py`
- `aragora/server/app.py`
- `aragora/server/api.py`
- `aragora/server/README.md`
- `aragora/server/ARCHITECTURE.md`
- `docs/ADR/006-api-versioning-strategy.md`

# Handler Registry Map

Read-only inventory of every HTTP handler registered in `aragora.server.handler_registry.HANDLER_REGISTRY`, with collision-cluster recommendations for the consolidation work in Waves 4-6 of the foundation-hardening plan.

> **Status:** generated audit. This doc is the spec for consolidation PRs; the snapshot test in `tests/integration/test_route_dispatch_behavior.py` locks in the current dispatch behavior so consolidation can prove "same handler still answers each path".

## Snapshot at audit time

| Metric | Count | Counting basis |
|---|---|---|
| Total handler classes registered | 303 | One top-level ClassDef per `class XxxHandler:` |
| Total unique HTTP paths | 2,039 | (method, path) pairs across all `ROUTES` |
| Cross-handler collisions, method-aware | 58 | (method, path) pairs claimed by ≥ 2 handlers — *the snapshot fixture's row count* |
| Cross-handler collisions, path-only | 51 | unique paths with ≥ 2 owners across all methods — *the test ceiling's count* |
| Collision clusters (connected components) | 12 | groups of handlers that share at least one path |

> **Two collision counts, deliberately.** The 58 method-aware count and the 51 path-only count are both correct — they answer different questions:
>
> - **51 path-only** is what `test_route_collision_count_stable` (in `tests/integration/test_handler_registry_imports.py`) ratchets. It treats `(POST /foo, GET /foo)` from two different handlers as one collision because the test cares about path-prefix routing risk.
> - **58 method-aware** is what `tests/integration/fixtures/route_dispatch_snapshot.json` records. It treats `(POST /foo, handler A)` and `(GET /foo, handler B)` as separate entries because behavior preservation cares about which handler answers each method.
>
> The roadmap table below operates on the 51 path-only basis (matching the `max_known_collisions` test ceiling that consolidation PRs ratchet). The snapshot fixture exists separately to lock per-method dispatch identity. Both metrics will trend downward together as Waves 4-6 land.

Source of truth: `aragora/server/handler_registry/__init__.py:98` — `HANDLER_REGISTRY: list[tuple[str, Any]]`. Each tuple is `(attr_name, handler_ref)` where `attr_name` (e.g. `_marketplace_handler`) is the dispatch identifier and `handler_ref` is either a handler class or a `_DeferredImport`.

## Dispatch resolution

Routes are claimed via the handler class's `ROUTES` attribute (and optional `ROUTE_PREFIXES`). When two handlers claim the same `(method, path)` pair, the registration order in `HANDLER_REGISTRY` decides which one is invoked: the first match wins.

`tests/integration/test_handler_registry_imports.py::TestRouteCollisionDetection::test_route_collision_count_stable` enforces the path-only ceiling (currently `max_known_collisions = 51`, ratcheting down via PR #6579 from a previous 61).

`tests/integration/test_route_dispatch_behavior.py::test_route_dispatch_snapshot` (added in this PR) locks the method-aware first-match-wins outcome for every colliding (method, path). Any consolidation PR that changes which handler answers a colliding (method, path) will fail this test, so behavior preservation must be intentional.

## Recommended canonical vs. current dispatch winner

**Important distinction.** The "Recommended canonical" in each cluster below is a *domain-informed* suggestion (chosen for largest LOC, most test coverage, cleanest abstraction, or most idiomatic location). The *current dispatch winner* — the handler that actually answers each path today — is recorded in `tests/integration/fixtures/route_dispatch_snapshot.json` and may differ.

When the recommended canonical and the current winner disagree, the consolidation PR has two valid choices:

1. **Match current dispatch** (no behavior change): absorb the recommended canonical's logic *into* the current winner. Snapshot fixture stays unchanged.
2. **Match the recommendation** (intentional behavior change): re-order the registry so the recommended handler wins, then run `UPDATE_ROUTE_DISPATCH_SNAPSHOT=1 pytest tests/integration/test_route_dispatch_behavior.py` to update the fixture, and explain the change in the PR body.

The snapshot test fails on either path until the consolidation is complete and the fixture matches.

A few clusters in the table below have current winners that differ from my recommendation. Those are called out per-cluster below. The `rlm_rlm` cluster is the clearest example: my recommendation was `RLMHandler` (newer, modular location), but `_rlm_context_handler` is the current winner — so I switched the recommendation to match current dispatch.

## Collision clusters (recommended canonicals for Waves 4-6)

Twelve clusters cover the 61 collisions. Each table row shows: cluster name, members, conflict path count, the recommended canonical handler that should absorb the others, and notes for the consolidation PR.

### 1. `apa_exp_inv` — accounting (15 paths)

| | |
|---|---|
| Members | `APAutomationHandler`, `ExpenseHandler`, `InvoiceHandler` |
| Modules | `aragora/server/handlers/ap_automation.py`, `expenses.py`, `invoices.py` |
| Conflict paths | 15 (largest cluster) |
| Recommended canonical | `APAutomationHandler` |
| Wave | 6 (PR 6.1 — AP automation surface clarification) |

`APAutomationHandler` is currently a facade that claims expense + invoice paths in addition to AP-specific endpoints (POs, payment scheduling). Dispatch order resolves this non-deterministically. Consolidation: trim `APAutomationHandler.ROUTES` to AP-specific only; let `ExpenseHandler` and `InvoiceHandler` keep their CRUD paths.

### 2. `aut_ema_web` — webhooks (9 paths)

| | |
|---|---|
| Members | `AutomationHandler`, `EmailWebhooksHandler`, `WebhookHandler` |
| Modules | `aragora/server/handlers/automation.py`, `email_webhooks.py`, `webhooks.py` |
| Conflict paths | 9 |
| Recommended canonical | `WebhookHandler` |
| Wave | 6 (PR 6.4 — webhooks consolidation) |

`WebhookHandler` is the only one that owns the full CRUD (including `DELETE`). Move automation- and email-specific webhook logic into sub-handlers or methods on `WebhookHandler`; delete the other two modules.

### 3. `age_ins_per` — agent metrics (4 paths)

| | |
|---|---|
| Members | `AgentsHandler`, `InsightsHandler`, `PersonaHandler` |
| Modules | `aragora/server/handlers/agents/agents.py`, `memory/insights.py`, `persona.py` |
| Conflict paths | 4 (`/api/agent/*/domains`, `/api/agent/*/performance`, `/api/flips/recent`, `/api/flips/summary`) |
| Recommended canonical | `AgentsHandler` |
| Wave | 7 (handler module-file dedup) |

Persona-specific paths (`/domains`, `/performance`) and flip-tracking paths (`/flips/*`) are both genuinely about agents. Migrate `PersonaHandler.ROUTES` and `InsightsHandler.ROUTES` flips into `AgentsHandler`. Persona core (non-routing) logic stays in its own module if it's > 100 LOC.

### 4. `pip_pro` — pipeline graph (2 paths)

| | |
|---|---|
| Members | `PipelineGraphHandler`, `ProvenanceExplorerHandler` |
| Modules | `aragora/server/handlers/pipeline_graph.py`, `provenance_explorer.py` |
| Conflict paths | 2 (`/api/v1/pipeline/graph`, `/api/v1/pipeline/graph/{id}`) |
| Recommended canonical | `PipelineGraphHandler` |
| Wave | 6 (PR 6.5 — explainability/provenance consolidation) |

`PipelineGraphHandler` already has the canonical paths in its primary surface. Move provenance lens into a sub-route (e.g. `/api/v1/pipeline/graph/{id}/provenance`) instead of a parallel handler.

### 5. `rlm_rlm` — RLM (8 paths)

| | |
|---|---|
| Members | `RLMContextHandler`, `RLMHandler` |
| Modules | `aragora/server/handlers/rlm_context.py`, `rlm.py` |
| Conflict paths | 8 (in current snapshot, `_rlm_context_handler` wins all 8 by registry order) |
| Recommended canonical | `RLMContextHandler` (matches current dispatch — minimizes behavior change) |
| Wave | 4 (lowest-risk; first consolidation PR) |

Looks like an in-flight migration. **Important:** the current dispatch winner is `_rlm_context_handler`, not `_rlm_handler`. Consolidation should either:

- Absorb `RLMHandler` into `RLMContextHandler` (preserves current behavior — recommended)
- Or absorb the other way and update the snapshot fixture to mark `_rlm_handler` as the new owner of all 8 paths (intentional behavior change — explain in PR body)

The snapshot test will fail loudly on either path until the fixture is updated.

### 6. `dec_pip` — pipeline decompose (2 paths)

| | |
|---|---|
| Members | `DecompositionHandler`, `PipelineExecuteHandler` |
| Modules | `aragora/server/handlers/decomposition.py`, `pipeline_execute.py` |
| Conflict paths | 2 (`POST /api/v1/pipeline/decompose`, `DELETE /api/v1/pipeline/decompose`) |
| Recommended canonical | `DecompositionHandler` |
| Wave | 7 |

Decomposition is the focused responsibility; `PipelineExecuteHandler` shouldn't also claim it. Strip those two routes from `PipelineExecuteHandler.ROUTES`.

### 7. `ema_deb` — outbound email (2 paths)

| | |
|---|---|
| Members | `EmailDebateHandler`, `EmailHandler` |
| Modules | `aragora/server/handlers/email_debate.py`, `email.py` |
| Conflict paths | 2 (`/api/v1/emails/outbound`, `/api/v1/emails/outbound/{id}`) |
| Recommended canonical | `EmailHandler` |
| Wave | 7 |

`EmailDebateHandler` is the debate-narrow lens; the outbound listing belongs on the general `EmailHandler`. Trim debate-handler scope.

### 8. `not_not` — notification history (2 paths)

| | |
|---|---|
| Members | `NotificationHistoryHandler`, `NotificationsHandler` |
| Modules | `aragora/server/handlers/notification_history.py`, `notifications.py` |
| Conflict paths | 2 (`/api/v1/notifications/history`, `/api/v1/notifications/history/{id}`) |
| Recommended canonical | `NotificationsHandler` |
| Wave | 7 |

History is a lens of the notifications domain. Fold `NotificationHistoryHandler` into `NotificationsHandler` as a sub-route.

### 9. `deb_sha` — sharing (2 paths)

| | |
|---|---|
| Members | `DebateShareHandler`, `SharingHandler` |
| Modules | `aragora/server/handlers/debate_share.py`, `sharing.py` |
| Conflict paths | 2 (`/api/v1/sharing/check`, `/api/v1/sharing/validate`) |
| Recommended canonical | `SharingHandler` |
| Wave | 7 |

`SharingHandler` is the more general entry; debate-share is a specific case that already has its own creation paths.

### 10. `aut_met_sys` — `/api/v1/metrics` (1 path, 4 owners)

| | |
|---|---|
| Members | `AuthHandler`, `MetricsHandler`, `SystemHandler`, `UnifiedMetricsHandler` |
| Modules | `aragora/server/handlers/auth/handler.py`, `metrics.py`, `admin/system.py`, `metrics_endpoint.py` |
| Conflict paths | 1 (`GET /api/v1/metrics`) |
| Recommended canonical | `UnifiedMetricsHandler` |
| Wave | 6 (PR 6.3 — metrics handlers) |

Four handlers all answer `GET /api/v1/metrics`. `UnifiedMetricsHandler` is the explicit unification path. The `AuthHandler` and `MetricsHandler` claims are likely accidental (e.g. legacy `ROUTES` lines that should be removed). `SystemHandler` is the admin-system surface and should not be answering Prometheus metrics.

### 11. `bil_usa` — billing plans (1 path)

| | |
|---|---|
| Members | `BillingHandler`, `UsageMeteringHandler` |
| Modules | `aragora/server/handlers/admin/billing.py`, `usage_metering.py` |
| Conflict paths | 1 (`GET /api/v1/billing/plans`) |
| Recommended canonical | `BillingHandler` |
| Wave | 7 |

Plans are billing-domain, not metering. Remove the route from `UsageMeteringHandler.ROUTES`.

### 12. `doc_exa` — `/api/v1/documents` (1 path)

| | |
|---|---|
| Members | `DocumentHandler`, `ExamplePermissionHandler` |
| Modules | `aragora/server/handlers/documents.py`, `example_permission.py` |
| Conflict paths | 1 (`GET /api/v1/documents`) |
| Recommended canonical | `DocumentHandler` |
| Wave | 7 |

`ExamplePermissionHandler` is named "example" — it should not own a real production path. Investigate whether the file is sample/fixture code that leaked into the registry.

## Wave-by-wave consolidation roadmap

| Wave | PR | Cluster(s) | Bound delta | Risk |
|---|---|---|---|---|
| 4 | RLM consolidation | `rlm_rlm` | 51 → 49 | Low |
| 5 | Marketplace trio (separately tracked, not in this audit's 12 clusters) | n/a | 49 → ~39 | Medium |
| 6 PR 6.1 | AP automation | `apa_exp_inv` | 39 → 24 | Medium-high |
| 6 PR 6.2 | Health endpoint consolidation (separately tracked) | n/a | 24 → ~20 | Medium |
| 6 PR 6.3 | Metrics handlers | `aut_met_sys` | 20 → 19 | Low |
| 6 PR 6.4 | Webhooks | `aut_ema_web` | 19 → 10 | Medium |
| 6 PR 6.5 | Provenance + explainability | `pip_pro` | 10 → 8 | Low |
| 7 | Handler module dedup | `age_ins_per`, `dec_pip`, `ema_deb`, `not_not`, `deb_sha`, `bil_usa`, `doc_exa` | 8 → ~3 | Medium (split into ~3-4 PRs) |

Final target: `max_known_collisions ≤ 5` (only intentional dispatch overlaps remaining).

## Marketplace trio

A separate cluster called out in the foundation-hardening plan but not surfaced as a single connected component in the inventory because the marketplace handlers register paths under multiple distinct path prefixes (the agent's connected-component pass treats each prefix's collision as its own micro-cluster). Cluster definition for Wave 5:

| | |
|---|---|
| Members | `MarketplaceHandler`, `TemplateMarketplaceHandler`, `MarketplaceBrowseHandler` |
| Modules | `aragora/server/handlers/marketplace.py`, `template_marketplace.py`, `marketplace_browse.py` |
| Approximate conflict paths | ~10 (categories, popular, templates, featured, etc.) |
| Recommended canonical | `TemplateMarketplaceHandler` (largest LOC, most tests) |

## How to use this doc when consolidating

1. Pick a cluster from the table above. Confirm the recommended canonical against `tests/` count and current LOC.
2. Read `tests/integration/test_route_dispatch_behavior.py` to see the locked dispatch snapshot for the cluster's paths.
3. Make the consolidation:
   - Move unique methods of the absorbed handlers into the canonical handler.
   - Remove the absorbed module's `ROUTES` entries.
   - Remove the absorbed handlers' entries from `HANDLER_REGISTRY`.
   - Optionally delete the absorbed module file if it's now empty.
4. Run `pytest tests/integration/test_route_dispatch_behavior.py -k <cluster_name>` — the test must still pass, with the canonical handler now answering the formerly-conflicting paths.
5. Ratchet `max_known_collisions` down in `tests/integration/test_handler_registry_imports.py` to match the new collision count.
6. Update this doc's "Wave-by-wave consolidation roadmap" table to mark the cluster done.

## Regenerating this audit

Two paths produce the same fixture deterministically:

```bash
# Live registry (preferred — uses HANDLER_REGISTRY at runtime, sees deferred
# imports as the dispatcher does, but requires the full transitive dep chain).
UPDATE_ROUTE_DISPATCH_SNAPSHOT=1 pytest \
    tests/integration/test_route_dispatch_behavior.py

# Static analyzer (no aragora imports — works in pre-commit hooks where
# cryptography / pydantic / etc. aren't installed).
python3 scripts/audit_handler_registry.py
```

Both regenerate `tests/integration/fixtures/route_dispatch_snapshot.json`. A
future hardening task will add a CI gate that runs both and asserts they
produce byte-identical output, which would catch any drift between the two
implementations.

## See also

- `docs/architecture/HANDLER_PATTERNS.md` — how to write a new handler (complements this inventory)
- `tests/integration/test_handler_registry_imports.py` — collision count ceiling
- `tests/integration/test_route_dispatch_behavior.py` — dispatch snapshot lock
- `aragora/server/handler_registry/__init__.py` — the live `HANDLER_REGISTRY` list

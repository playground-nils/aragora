# Handler Registry Map (Wave 3.5 audit, 2026-04-24)

## Purpose

This document maps every cross-handler colliding path in `HANDLER_REGISTRY` to its current dispatch winner and proposes a canonical handler for each cluster. It is the **input spec for Waves 4-6** of the foundation-hardening roadmap (route consolidation).

This is a read-only audit; no consolidation changes are made by the PR that introduces this document. Consolidation happens in subsequent PRs:

- **Wave 4** — RLM cluster
- **Wave 5** — Marketplace cluster
- **Wave 6** — AP automation, health, metrics, webhooks, explainability, etc.

## How dispatch resolves collisions

Per `aragora/server/handler_registry/core.py` `RouteIndex._exact_routes` build:

```python
for attr_name, _ in handler_registry:
    handler = getattr(registry_mixin, attr_name, None)
    routes = getattr(handler, "ROUTES", [])
    for path in routes:
        if path not in self._exact_routes:
            self._exact_routes[path] = (attr_name, handler)
```

→ **First handler registered in `HANDLER_REGISTRY` wins.**

Subsequent registrations on the same path are silently dropped from the exact-match index. The "losing" handlers may still match via prefix patterns if they declare `ROUTE_PREFIXES` or `can_handle()`, but for exact-path lookups the first-registered wins.

## Snapshot regression test

`tests/integration/test_route_dispatch_snapshot.py` locks in the current winner for every colliding path. Consolidation PRs that change a winner must regenerate the snapshot intentionally and document the swap in their PR description.

## Aggregate metrics (as of 2026-04-24)

| Metric | Value |
|---|---|
| Total handlers | 330 |
| Total registered paths | 2,145 |
| Cross-handler colliding paths | 51 |
| Largest single-handler collision count | 15 (`_ap_automation_handler`) |
| Largest cluster | 8 paths (RLM pair, AP+Invoice pair) |

## Cluster catalog

Sorted by cluster size descending. For each cluster:
- The **dispatch winner** (first-registered) is **bold**.
- The **canonical recommendation** is the handler we propose to keep after consolidation.
- The **Wave** indicates which roadmap wave handles this cluster.

### Cluster 1 — RLM pair (Wave 4)

**Owners:** `_rlm_context_handler` (winner), `_rlm_handler`
**Paths affected:** 8

| Path |
|---|
| `/api/v1/rlm/codebase/health` |
| `/api/v1/rlm/compress` |
| `/api/v1/rlm/contexts` |
| `/api/v1/rlm/query` |
| `/api/v1/rlm/stats` |
| `/api/v1/rlm/strategies` |
| `/api/v1/rlm/stream` |
| `/api/v1/rlm/stream/modes` |

**Canonical:** `RLMHandler` in `aragora/server/handlers/features/rlm.py` (newer, modular). Migrate any unique methods from `RLMContextHandler` (`aragora/server/handlers/rlm.py`) into it, then delete the legacy module and its registry entry.

### Cluster 2 — AP automation x Invoice (Wave 6.1)

**Owners:** `_ap_automation_handler` (winner), `_invoice_handler`
**Paths affected:** 8

| Path |
|---|
| `/api/v1/accounting/invoices` |
| `/api/v1/accounting/invoices/overdue` |
| `/api/v1/accounting/invoices/pending` |
| `/api/v1/accounting/invoices/stats` |
| `/api/v1/accounting/invoices/status` |
| `/api/v1/accounting/invoices/upload` |
| `/api/v1/accounting/payments/scheduled` |
| `/api/v1/accounting/purchase-orders` |

**Canonical:** Split surface. `_ap_automation_handler.ROUTES` should keep ONLY AP-specific endpoints (purchase orders, payment scheduling, AP-batch ops). Move `/api/v1/accounting/invoices/*` exclusively to `_invoice_handler`.

### Cluster 3 — AP automation x Expense (Wave 6.1)

**Owners:** `_ap_automation_handler` (winner), `_expense_handler`
**Paths affected:** 7

| Path |
|---|
| `/api/v1/accounting/expenses` |
| `/api/v1/accounting/expenses/categorize` |
| `/api/v1/accounting/expenses/export` |
| `/api/v1/accounting/expenses/pending` |
| `/api/v1/accounting/expenses/stats` |
| `/api/v1/accounting/expenses/sync` |
| `/api/v1/accounting/expenses/upload` |

**Canonical:** Same as Cluster 2 — move `/api/v1/accounting/expenses/*` exclusively to `_expense_handler`.

### Cluster 4 — Health x Storage Health (Wave 6.2)

**Owners:** `_health_handler` (winner), `_storage_health_handler`
**Paths affected:** 3

| Path |
|---|
| `/api/v1/health/database` |
| `/api/v1/health/stores` |
| `/api/health/stores` |

**Canonical:** `_health_handler` (the broader, current dispatch winner). Move storage-health logic into it as a sub-method or delegate.

### Cluster 5 — Health x Readiness (Wave 6.2)

**Owners:** `_health_handler` (winner), `_readiness_handler`
**Paths affected:** 2

| Path |
|---|
| `/readyz` |
| `/readyz/dependencies` |

**Canonical:** `_health_handler`. Merge readiness path-set as a sub-route.

### Cluster 6 — Health x Liveness (Wave 6.2)

**Owners:** `_health_handler` (winner), `_liveness_handler`
**Paths affected:** 1

| Path |
|---|
| `/healthz` |

**Canonical:** `_health_handler`.

### Cluster 7 — Marketplace trio (Wave 5)

**Owners:** `_marketplace_handler` (winner for most), `_template_marketplace_handler`, `_marketplace_browse_handler`
**Paths affected:** 4 distinct collision-paths spread across these three handlers

| Path | Owners |
|---|---|
| `/api/v1/marketplace/categories` | `_marketplace_handler` (W) + `_template_marketplace_handler` |
| `/api/v1/marketplace/featured` | `_template_marketplace_handler` (W) + `_marketplace_browse_handler` |
| `/api/v1/marketplace/popular` | `_marketplace_handler` (W) + `_marketplace_browse_handler` |
| `/api/v1/marketplace/templates` | `_marketplace_handler` (W) + `_template_marketplace_handler` + `_marketplace_browse_handler` |
| `/api/v1/marketplace/templates/*` | `_template_marketplace_handler` (W) + `_marketplace_browse_handler` |

**Canonical:** `TemplateMarketplaceHandler` (largest, ~1200 LOC, most tests). Move `MarketplaceBrowseHandler` browse/discovery methods and `MarketplaceHandler` list/popular methods into it. Delete the smaller two and their registry entries.

### Cluster 8 — Webhooks (Wave 6.4)

| Path | Owners | Winner |
|---|---|---|
| `/api/v1/webhooks` | `_automation_handler`, `_webhook_handler` | `_automation_handler` |
| `/api/v1/webhooks/events` | `_automation_handler`, `_webhook_handler` | `_automation_handler` |
| `/api/v1/webhooks/subscribe` | `_automation_handler`, `_email_webhooks_handler` | `_automation_handler` |

**Canonical:** `_webhook_handler`. The `_automation_handler` shouldn't be answering plain `/api/v1/webhooks` — that's misleading. Move `/api/v1/webhooks/*` into `_webhook_handler`. Move `/subscribe` into `_email_webhooks_handler` if email-specific, else `_webhook_handler`.

### Cluster 9 — Metrics (Wave 6.3)

| Path | Owners | Winner |
|---|---|---|
| `/metrics` | `_system_handler`, `_metrics_handler`, `_unified_metrics_handler` | `_system_handler` |

**Canonical:** `_unified_metrics_handler` (newest, most comprehensive). Move legacy `/metrics` impl into it, delete `_metrics_handler` and the `/metrics` route from `_system_handler`.

### Cluster 10 — Explainability (Wave 6.5)

| Path | Owners | Winner |
|---|---|---|
| `/api/v1/debates/*/summary` | `_debates_handler`, `_explainability_handler` | `_debates_handler` |

(Note: this path was a 1-path collision after Wave 0 dedup. The other 3 explainability dups in v1 of the audit were same-handler self-dups, removed by `route_owners: set` in #6579.)

**Canonical:** `_explainability_handler` for debate summaries (separates debate metadata from explanation generation).

### Cluster 11 — Email prioritization

| Path | Owners | Winner |
|---|---|---|
| `/api/v1/email/prioritize` | `_email_debate_handler`, `_email_handler` | `_email_debate_handler` |

**Canonical:** `_email_handler`. Move `prioritize` into the general email handler.

### Cluster 12 — Pipeline graph (Wave 6.5 follow-up)

| Path | Owners | Winner |
|---|---|---|
| `/api/v1/pipeline/graph` | `_pipeline_graph_handler`, `_provenance_explorer_handler` | `_pipeline_graph_handler` |
| `/api/v1/pipeline` | `_decomposition_handler`, `_pipeline_execute_handler` | `_decomposition_handler` |

**Canonical:** `_pipeline_graph_handler` for graph queries. The `_provenance_explorer_handler` should declare narrower paths (e.g. `/api/v1/pipeline/graph/*/provenance/*`). For `/api/v1/pipeline`: clarify whether decomposition or execute owns the bare path; one should narrow.

### Cluster 13 — Agents x Persona / Insights / Flips

| Path | Owners | Winner |
|---|---|---|
| `/api/agent/*/domains` | `_agents_handler`, `_persona_handler` | `_agents_handler` |
| `/api/agent/*/performance` | `_agents_handler`, `_persona_handler` | `_agents_handler` |
| `/api/flips/recent` | `_agents_handler`, `_insights_handler` | `_agents_handler` |
| `/api/flips/summary` | `_agents_handler`, `_insights_handler` | `_agents_handler` |

**Canonical:** `_agents_handler` for agent-attribute paths. The `_persona_handler` and `_insights_handler` should narrow their path declarations.

### Cluster 14 — Billing x Usage Metering

| Path | Owners | Winner |
|---|---|---|
| `/api/v1/billing/usage` | `_billing_handler`, `_usage_metering_handler` | `_billing_handler` |
| `/api/v1/billing/usage/export` | `_billing_handler`, `_usage_metering_handler` | `_billing_handler` |

**Canonical:** `_billing_handler` for the public surface. `_usage_metering_handler` should expose internal-only paths or be merged in.

### Cluster 15 — Auth revoke

| Path | Owners | Winner |
|---|---|---|
| `/api/auth/revoke` | `_system_handler`, `_auth_handler` | `_system_handler` |

**Canonical:** `_auth_handler`. Auth-specific paths shouldn't live in `_system_handler`. Move and remove from `_system_handler`.

### Cluster 16 — Notifications history

| Path | Owners | Winner |
|---|---|---|
| `/api/v1/notifications/history` | `_notification_history_handler`, `_notifications_handler` | `_notification_history_handler` |

**Canonical:** Likely `_notifications_handler` (more general); merge `_notification_history_handler` in. Or vice-versa if history is the primary concern. Decide by impl size at consolidation time.

### Cluster 17 — Debate share

| Path | Owners | Winner |
|---|---|---|
| `/api/v1/debates/*/share` | `_debate_share_handler`, `_sharing_handler` | `_debate_share_handler` |

**Canonical:** `_sharing_handler` (more general). Move debate-specific share logic into it.

## Roadmap impact

| Wave | Clusters | Bound delta | Cumulative |
|---|---|---|---|
| Wave 4 | 1 (RLM) | -8 | 51 → 43 |
| Wave 5 | 7 (marketplace, 5 paths to consolidate) | -5 | 43 → 38 |
| Wave 6.1 | 2, 3 (AP × Invoice + AP × Expense) | -15 | 38 → 23 |
| Wave 6.2 | 4, 5, 6 (health) | -6 | 23 → 17 |
| Wave 6.3 | 9 (metrics) | -2 | 17 → 15 |
| Wave 6.4 | 8 (webhooks) | -3 | 15 → 12 |
| Wave 6.5 | 10, 12 (explainability + pipeline) | -3 | 12 → 9 |
| Wave 6.6 | 11, 13, 14, 15, 16, 17 | -8 | 9 → 1 |
| **Final** | | | **≤ 5 (intentional dispatch overlaps)** |

The exact ratchet may differ by ±2 — some clusters require one canonical to also pick up another's prefix, which can introduce a *new* exact-match collision elsewhere.

## Per-PR test discipline

Every consolidation PR must:

1. Modify only the handlers in its target cluster
2. Run `pytest tests/integration/test_route_dispatch_snapshot.py` before push
3. If a winner changed, regenerate the snapshot AND call out the swap in the PR description
4. Run `pytest tests/integration/test_handler_registry_imports.py::TestRouteCollisionDetection -xvs` and ratchet `max_known_collisions` downward to match the new count
5. Add or update behavioral tests for the moved methods

## Future hardening

After Waves 4-6 land, consider:

- A pre-commit hook that runs the snapshot test on any change under `aragora/server/handler_registry/`
- A CI gate that fails if a new collision is introduced without an explicit snapshot regeneration
- A linter that flags any `ROUTES` list with overlapping path-prefixes between distinct handlers

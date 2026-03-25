# Self-Improve Hard Checks Rollout

## Objective
Roll out live-path and quality-gate hard checks safely, then tighten policy after one week of runtime signals.

## Provider Truth Contract

This rollout only counts as truthful if "live" means Aragora actually traversed a working provider path.

### Invariants

1. `requested_execution_path=live` means the operator asked for real provider calls. It is not permission to silently downgrade to canned, mock, or heuristic output.
2. A run may emit `actual_execution_path=live` only when Aragora can name the selected provider, record that a provider call was attempted, and verify that a provider response contributed to the final result.
3. Presence of a saved credential or environment variable proves only `provider_setup_state=config_present`. It does not prove that the provider path is usable.
4. Missing provider selection, missing API key, malformed API key, auth rejection (`401`/`403`), or transport/provider failure before the first successful provider response are terminal non-success states for automated runners that requested live mode.
5. Offline, demo, or heuristic output is allowed only when the operator explicitly requested `--offline`, `--demo`, or a profile that permits fallback. Those runs must never be labeled `live`.
6. Interactive/manual runners may show preview output in warn-only mode, but the receipt/status surface must label that output as preview or fallback until the live path is verified.
7. Receipts for successful and blocked outcomes must carry the same provider-truth fields: `requested_execution_path`, `actual_execution_path`, `provider_setup_state`, `provider_auth_state`, `provider_calls_detected`, `live_call_verified`, `block_reason`, and `next_operator_action`.
8. API keys are treated as secrets at every layer. Receipts and logs may record provider name, key source, and rejection class, but never raw key material.

### Canonical Provider States

| Field | Canonical values | Meaning |
|---|---|---|
| `provider_setup_state` | `not_configured`, `config_present`, `live_verified`, `fallback_used` | Distinguishes absent setup from mere key presence, verified live use, or explicit fallback. |
| `provider_auth_state` | `unknown`, `not_attempted`, `accepted`, `rejected` | Separates missing/untested credentials from an observed provider auth result. |
| `actual_execution_path` | `live`, `heuristic-fallback`, `heuristic`, `blocked` | `live` requires verified provider evidence; `blocked` is the truthful terminal state when live was requested but never established. |
| `block_reason` | `provider_not_selected`, `api_key_missing`, `api_key_invalid`, `provider_auth_rejected`, `provider_unreachable`, `provider_timeout`, `provider_rate_limited`, `provider_response_invalid`, `fallback_not_permitted` | Non-success reasons must be explicit and machine-readable. |

### Receipt Rules

1. `success` with `actual_execution_path=live` requires `provider_calls_detected=true` and `live_call_verified=true`.
2. `success` with `actual_execution_path=heuristic-fallback` is allowed only when fallback was explicitly permitted by the invoking mode/profile, and the receipt must still show `live_call_verified=false`.
3. `success` is forbidden when `provider_setup_state` is `not_configured` or when `provider_auth_state=rejected`.
4. If a run requested live mode and terminates before the first verified provider response, the canonical outcome is `blocked` or `failed`, never "completed with fallback" unless fallback was explicitly operator-authorized.

## Week 0 (Immediately)
1. Keep `pipeline self-improve` in live-default mode.
2. Enforce fail-closed for CI/dogfood profiles and any automated runner that requested live mode.
3. Keep interactive/manual usage in warn-only mode, but never stamp preview/fallback output as live success.
4. Run integration-vague dogfood profile on schedule and manual dispatch, preserving blocked receipts when the provider path is broken.

## Telemetry Signals
Collect and track:
1. `requested_execution_path` and `actual_execution_path` distribution.
2. `provider_setup_state` distribution (`not_configured`, `config_present`, `live_verified`, `fallback_used`).
3. `provider_auth_state` distribution and top `block_reason` counts.
4. `provider_calls_detected` and `live_call_verified` rate for runs that requested live mode.
5. `quality_verdict` pass/fail counts.
6. `quality_score_10` and `practicality_score_10` trend.
7. `avg_objective_fidelity` trend.
8. Improvement queue backlog growth and age.

Source:
`[self-improve-metrics] ...` lines emitted by `aragora pipeline self-improve`.

## Alert Thresholds (Week 0)
1. Any successful receipt with `actual_execution_path=live` and either `provider_calls_detected=false` or `live_call_verified=false`: treat as a P0 contract violation.
2. `heuristic-fallback` > 10% over 24h for runs that requested live mode: investigate provider health/config and whether fallback policy is too permissive.
3. `blocked` with `block_reason` in `api_key_missing`, `api_key_invalid`, or `provider_auth_rejected` > 5% over 24h: investigate provider setup UX and credential validation.
4. quality gate fail rate > 20% over 24h: inspect planner drift and contract fit.
5. improvement queue backlog growth > 2x week baseline: inspect consumer throughput.

## Week 1 Tightening Criteria
Promote fail-closed beyond CI/dogfood only if all are true for 7 days:
1. `actual_execution_path=live` in >= 95% of runs that requested live mode, with the remainder terminating truthfully as `blocked` or operator-authorized fallback.
2. zero successful receipts that violate the provider truth contract.
3. `live_call_verified=true` for 100% of successful live receipts.
4. quality gate pass rate >= 90%.
5. no sustained queue backlog growth (> 1.2x baseline).
6. no recurring objective-fidelity regression incidents.

## Week 1 Actions
1. Raise `plan_quality_min_score` from 6.0 to 7.0 in default profile.
2. Raise `plan_quality_min_practicality` from 5.0 to 6.0 in default profile.
3. Enable fail-closed by default for non-interactive automated runners.
4. Require explicit operator intent for `--offline`, `--demo`, or fallback-permitted modes on receipt-bearing surfaces.
5. Keep manual interactive mode warn-only for one additional cycle, then reassess.

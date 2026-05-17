# `blocked_auth_failure` rescue-class productization (2026-05-17)

## What this links

| | Path |
|---|---|
| Fixture | [`docs/benchmarks/auth_failure_scenarios.json`](./auth_failure_scenarios.json) |
| Tests | [`tests/benchmarks/test_auth_failure_scenarios.py`](../../tests/benchmarks/test_auth_failure_scenarios.py) |
| Classifier (canonical) | [`aragora/swarm/terminal_truth.py`](../../aragora/swarm/terminal_truth.py) — `TerminalClass.BLOCKED_AUTH_FAILURE` (line 50), `classify_from_metrics` (line 106, auth substring → line 132-133), `classify_preflight_failure` (line 151, `_PREFLIGHT_AUTH_HINTS` → line 186-187) |
| Existing rescue-productization ledger | [`docs/benchmarks/rescue_productization.json`](./rescue_productization.json) |

## Why this exists

Per the Operating Law surfaced in the operator's session-2 ground-up assessment:

> If humans intervene twice for the same class of failure, the next system
> change should absorb that rescue as product behavior — a benchmark
> fixture, sanitizer rule, preflight check, repair path, policy gate, or
> control-plane affordance.

The B0 truth scorecard for 2026-05-15 (from `docs/status/B0_BENCHMARK_TRUTH_STATUS.md`)
showed:

| Failure class | Tick count | % of total |
|---|---|---|
| `blocked_auth_failure` | **7 / 28** | **25%** |
| `blocked_not_dispatch_bounded` | 8 / 28 | 29% |
| `blocked_sanitation_failed` | 2 / 28 | 7% |
| `rescue_no_deliverable` | 1 / 28 | 4% |
| (others) | 10 / 28 | 35% |

`blocked_auth_failure` is the **single largest repeated rescue class** —
exactly the shape Operating Law tells us to productize next.

PR-1 of the [#7209 productization lane](https://github.com/synaptent/aragora/issues/7209)
absorbed `blocked_not_dispatch_bounded` (29%) via corpus-aware dispatch
upgrade (`ARAGORA_CORPUS_AWARE_DISPATCH`). This PR does the same for
`blocked_auth_failure` (25%), pushing the cumulative repeated-rescue
coverage from 29% → **54%**.

## What this PR ships

- A 5-scenario JSON fixture covering the two classifier paths the
  canonical taxonomy uses to label a tick `blocked_auth_failure`:
  1. **Preflight-check path** (4 scenarios): gh CLI not authenticated,
     HTTP 401, HTTP 403 forbidden, permission-denied-on-push. Each
     shape exercises one of the `_PREFLIGHT_AUTH_HINTS` tuple members.
  2. **Worker-outcome-metrics-row path** (1 scenario): a metrics row
     whose `worker_outcome` contains the substring `auth`.
- 10 fixture-driven tests that:
  - Confirm every scenario classifies to `TerminalClass.BLOCKED_AUTH_FAILURE`
    via the existing `classify_from_metrics` / `classify_preflight_failure`
    functions (no behavioral change, no flag flips).
  - Sanity-check that claimed `expected_triggered_hints` actually appear
    in the scenario's preflight detail.
  - Verify the fixture contains no real secret-shaped strings.
  - Enforce minimum coverage breadth (≥ 5 scenarios, both classifier
    paths exercised, unique IDs).

## What this PR does NOT do

- **No behavioral change.** Zero modification to `terminal_truth.py` or
  any classifier. The fixture is a documentation-grade pin against the
  current classifier behavior; if a future change shifts how
  `BLOCKED_AUTH_FAILURE` is reached, these tests will flag the drift.
- **No flag flips.** No new environment variables, no policy gate
  changes, no boss-loop changes.
- **No live benchmark execution.** Tests run against the in-memory
  classifier only; no agent spawning, no network, no AI provider keys.
- **No `rescue_productization.json` mutation** in this PR. Following the
  operator's "do not advance held PRs by one byte" pattern, the existing
  ledger entry that already references the broader `admission_class_corpus_synthesis_v1`
  rollup (#7209) is left untouched. A follow-up PR can append a sibling
  entry once an operator confirms it should be filed.

## How operators use this

1. **Future B0 scorecard runs**: when a new tick is classified
   `blocked_auth_failure`, operators can confirm via these tests that
   the trigger pattern matches one of the 5 canonical shapes. If it
   doesn't, the fixture needs an entry — fail the test loudly, then
   extend.
2. **Preflight tooling**: any new preflight check that wants to flag
   auth failures should match at least one of the `_PREFLIGHT_AUTH_HINTS`
   strings; the fixture confirms which shapes work end-to-end through
   the classifier.
3. **Debug session**: when an operator sees `blocked_auth_failure` in
   the boss-loop log, the fixture's `remediation` field per scenario
   names the immediate operator action (rotate token, refresh launchd
   env, etc.).

## Sequencing

- Additive only. Docs + tests. No code outside the new files.
- No `boss-ready` / `autonomous` labels.
- Depends on nothing in the open PR queue.
- Holds respected: #7209 lane (this PR adds an orthogonal rescue class,
  does not touch the existing #7209 productization work); #7173,
  #7215, #4990, #7251, #7252, #7263, #7266, #7270 metadata-only.

## Verification

```bash
pytest tests/benchmarks/test_auth_failure_scenarios.py -q
ruff check docs/benchmarks/auth_failure_scenarios.json \
            tests/benchmarks/test_auth_failure_scenarios.py
bash scripts/automation_pr_preflight.sh origin/main HEAD
```

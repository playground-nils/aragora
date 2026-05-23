# B0 Benchmark Truth Status

Last updated: 2026-05-23T14:01:34Z

This is the repo-tracked recurring `TW-02` publication surface for the fixed benchmark corpus.

## Corpus

- Corpus manifest: `docs/benchmarks/corpus.json`
- Corpus id: `tw-01-bounded-execution-v1`
- Revision: `4`
- Recorded on: `2026-04-26`
- Success contract: `mergeable_pr_or_merged_pr`
- Verified expected issues: `0`
- In-progress expected issues: `13`
- Coverage status: `complete`
- Coverage: `13`/`13` issues attempted

## Published Paths

- Latest truth artifact: `docs/status/generated/benchmark_truth_artifacts/tw-01-bounded-execution-v1/latest.json`
- Latest scorecard: `docs/status/generated/benchmark_scorecards/tw-01-bounded-execution-v1/latest.json`
- Revision-scoped truth pointer: `docs/status/generated/benchmark_truth_artifacts/tw-01-bounded-execution-v1/rev-4/latest.json`
- Revision-scoped scorecard pointer: `docs/status/generated/benchmark_scorecards/tw-01-bounded-execution-v1/rev-4/latest.json`

## Truth Metrics

| Metric | Value |
| --- | --- |
| Verified truth success rate (primary) | 0.0% |
| Full-corpus truth success rate (legacy/context) | 30.8% |
| No-rescue truth success rate | 30.8% |
| Merged-only rate | 30.8% |

## In-Flight Graduation Metrics

| Metric | Value |
| --- | --- |
| In-progress expected issues | 13 |
| In-progress attempted issues | 13 |
| In-progress successful issues | 4 |
| In-progress graduation rate | 30.8% |
| In-progress issue numbers | `#5185`, `#5187`, `#5197`, `#5198`, `#5200`, `#5426`, `#5427`, `#5428`, `#5764`, `#5789`, `#5790`, `#5839`, `#5844` |

## Proxy Metrics

| Metric | Value |
| --- | --- |
| Proxy no-rescue success rate | 0.0% |
| Unique issues attempted | 13 |
| Unique issues succeeded | 0 |
| Unique issues failed | 9 |
| Unique issues neutral | 4 |
| Total ticks | 15 |

Proxy note: neutral issue outcomes are current-corpus rows that were neither fresh success nor failure, such as `issue_already_resolved`.

## Proxy Neutral Class Distribution

- `issue_already_resolved`: 4

## Failure Class Distribution

- `blocked_auth_failure`: 3
- `blocked_not_dispatch_bounded`: 8

## Rescue Counts By Type

- none

## Previous Published Artifact

- Previous artifact path: `docs/status/generated/benchmark_scorecards/tw-01-bounded-execution-v1/rev-4/scorecard-20260521T025329Z.json`
- Previous generated_at: `2026-05-21T02:53:29Z`

## Deltas

- `merged_only_rate`: 0.0000
- `no_rescue_truth_success_rate`: 0.0000
- `proxy_no_rescue_success_rate`: -0.7690
- `truth_success_rate`: 0.0000
- `unique_issues_attempted`: 0.0000

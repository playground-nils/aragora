# Aragora Canonical Metrics

> **This doc is auto-generated.** Do not edit by hand — edits will be overwritten by the next run of `scripts/regenerate_metrics.py`. If a number here disagrees with another doc, this doc wins. Every metric below is reproducible by running the command in its row.

- **Generated at:** `2026-04-24T15:42:45.226749+00:00`
- **Git sha:** `ae534702f`
- **Regenerate:** `python scripts/regenerate_metrics.py`
- **Verify (drift check):** `python scripts/regenerate_metrics.py --check`

## Canonical numbers

| Metric | Value | Source | Command |
|---|---|---|---|
| Python files under aragora/ | `4075` | `aragora/` | `find aragora -name '*.py' -not -path '*/__pycache__/*' -type f \| wc -l` |
| Python lines of code under aragora/ | `1915808` | `aragora/` | `find aragora -name '*.py' -not -path '*/__pycache__/*' \| xargs wc -l \| tail -1` |
| Top-level modules under aragora/ | `136` | `aragora/` | `find aragora -maxdepth 1 -type d \| wc -l` |
| Test files (test_*.py under tests/) | `5074` | `tests/` | `find tests -name 'test_*.py' -type f \| wc -l` |
| Test functions (class + module level) | `215978` | `tests/` | `rg '^\s*(async )?def test_' tests/ --no-filename \| wc -l` |
| @pytest.mark.parametrize decorators | `642` | `tests/` | `rg '@pytest\.mark\.parametrize' tests/ --no-filename \| wc -l` |
| CLI top-level command modules | `60` | `aragora/cli/commands/` | `find aragora/cli/commands -maxdepth 1 -name '*.py' -not -name '__*' -type f \| wc -l` |
| OpenAPI paths | `2852` | `docs/api/openapi.json` | `python -c "import json; print(len(json.load(open('docs/api/openapi.json'))['paths']))"` |
| OpenAPI operations (HTTP verbs) | `3271` | `docs/api/openapi.json` | `python -c "import json; spec=json.load(open('docs/api/openapi.json')); print(sum(1 for p in spec['paths'].values() for m in p if m.lower() in {'get','post','put','delete','patch','head','options'}))"` |
| @require_permission decorator calls | `1367` | `aragora/` | `rg '@require_permission\(' aragora/ \| wc -l` |
| Unique permission strings | `424` | `aragora/` | `rg "@require_permission\(['\"]([^'\"]+)['\"]\)" aragora/ -o -r '$1' --no-filename \| sort -u \| wc -l` |
| Python SDK modules | `197` | `sdk/python/` | `find sdk/python/aragora_sdk -maxdepth 2 -name '*.py' -not -name '__*' -type f \| wc -l` |
| TypeScript SDK modules | `214` | `sdk/typescript/` | `find sdk/typescript/src -maxdepth 2 -name '*.ts' -type f \| wc -l` |
| Allowlisted agent types | `34` | `aragora/config/settings.py` | `grep -A 50 'ALLOWED_AGENT_TYPES' aragora/config/settings.py \| grep -oE "'[a-z-]+'" \| sort -u \| wc -l` |
| Knowledge Mound adapter specs | `41` | `aragora/knowledge/mound/adapters/factory.py` | `rg '"\.[a-z_]+_adapter"' aragora/knowledge/mound/adapters/factory.py \| wc -l` |
| Knowledge Mound adapter files | `45` | `aragora/knowledge/mound/adapters/` | `find aragora/knowledge/mound/adapters -maxdepth 1 -name '*_adapter.py' -type f \| wc -l` |
| Markdown files under docs/ | `771` | `docs/` | `find docs -name '*.md' -type f \| wc -l` |
| GitHub Actions workflows | `83` | `.github/workflows/` | `find .github/workflows -name '*.yml' -type f \| wc -l` |
| Mypy baseline errors (grandfathered) | `3317` | `.mypy-baseline` | `wc -l .mypy-baseline` |

## Notes on counting methodology

- **Test functions (class + module level):** Counts both module-level and class-nested test methods.
- **@pytest.mark.parametrize decorators:** Each decorator expands into N test cases during collection.
- **Knowledge Mound adapter specs:** Counts adapter module entries in the factory spec tuple list.

## Why this doc exists

Aragora's thesis (Commitment 4: respect the limits) requires that the product not claim capability it does not have. The same discipline applies to numeric claims. Before this doc existed, different docs cited different numbers for the same metric (e.g. test-count claims ranged from 129K to 210K+ depending on regex used). This doc is the single source of truth.

All other docs that cite a metric should link here rather than hard-code the number, or explicitly snapshot the number with a date so staleness is visible.

## Related automation

- `.github/workflows/metrics-drift.yml` runs this script nightly and opens a PR if any metric drifted by more than 0.5% since the last committed version of this doc.
- `scripts/reconcile_status.py` cross-references feature claims across CAPABILITY_MATRIX, GA_CHECKLIST, STATUS, ROADMAP.
- `scripts/validate_openapi_routes.py` verifies OpenAPI paths against actual handler implementations.

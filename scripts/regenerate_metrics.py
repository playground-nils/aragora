#!/usr/bin/env python3
"""Regenerate docs/METRICS.md from ground truth.

Single source of truth for all public numeric claims about Aragora.
Every metric has an explicit, reproducible command so a cold auditor can
verify it by running the same command.

Usage:
    python scripts/regenerate_metrics.py              # rewrite docs/METRICS.md
    python scripts/regenerate_metrics.py --check      # fail if drift > 0.5%
    python scripts/regenerate_metrics.py --json       # emit JSON only

Drift threshold is intentionally tight: claim-drift is a thesis-commitment
violation (Commitment 4: respect the limits). A drifted metric should
trigger a PR rather than a silent mismatch.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
METRICS_DOC = REPO_ROOT / "docs" / "METRICS.md"
DRIFT_THRESHOLD = 0.005  # 0.5%


@dataclass
class Metric:
    key: str
    label: str
    value: int | str
    command: str
    source: str
    notes: str = ""


@dataclass
class MetricsSnapshot:
    generated_at: str
    git_sha: str
    metrics: list[Metric] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "git_sha": self.git_sha,
            "metrics": [
                {
                    "key": m.key,
                    "label": m.label,
                    "value": m.value,
                    "command": m.command,
                    "source": m.source,
                    "notes": m.notes,
                }
                for m in self.metrics
            ],
        }


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    """Run a shell command and return stdout (stripped)."""
    result = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def _rg_count(pattern: str, path: str, flags: list[str] | None = None) -> int:
    """Count ripgrep matches across all files under path."""
    cmd = ["rg", *(flags or []), "--no-filename", pattern, path]
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # rg exits 1 if no matches; treat as 0
    if result.returncode not in (0, 1):
        raise RuntimeError(f"rg failed: {' '.join(cmd)}\n{result.stderr}")
    return len(result.stdout.splitlines())


def _find_count(args: list[str]) -> int:
    """Count files matching a find expression."""
    result = subprocess.run(
        ["find", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return len([line for line in result.stdout.splitlines() if line.strip()])


def _wc_lines(paths: list[Path]) -> int:
    """Sum line counts across paths that exist."""
    total = 0
    for p in paths:
        if p.exists():
            try:
                total += sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
            except OSError:
                pass
    return total


def gather_metrics() -> MetricsSnapshot:
    git_sha = _run(["git", "rev-parse", "--short", "HEAD"]) or "unknown"
    generated_at = datetime.now(timezone.utc).isoformat()

    metrics: list[Metric] = []

    # ----- Python surface -----
    py_files = _find_count(
        [
            "aragora",
            "-name",
            "*.py",
            "-not",
            "-path",
            "*/__pycache__/*",
            "-type",
            "f",
        ]
    )
    metrics.append(
        Metric(
            key="python_files",
            label="Python files under aragora/",
            value=py_files,
            command="find aragora -name '*.py' -not -path '*/__pycache__/*' -type f | wc -l",
            source="aragora/",
        )
    )

    # LOC via Python-native counting (avoids xargs/wc batching risks:
    # xargs may split args into multiple `wc` invocations producing
    # multiple 'total' lines where only the last is kept; filenames
    # with spaces break shell splitting). Use Path.rglob + sum instead.
    aragora_root = REPO_ROOT / "aragora"
    loc = 0
    for p in aragora_root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        try:
            with p.open(encoding="utf-8", errors="replace") as f:
                loc += sum(1 for _ in f)
        except OSError:
            pass
    metrics.append(
        Metric(
            key="python_loc",
            label="Python lines of code under aragora/",
            value=loc,
            command=(
                'python3 -c "from pathlib import Path; '
                "print(sum(sum(1 for _ in p.open(encoding='utf-8', errors='replace')) "
                "for p in Path('aragora').rglob('*.py') "
                "if '__pycache__' not in p.parts))\""
            ),
            source="aragora/",
            notes="Uses Python rglob + direct line count to avoid xargs/wc batching bugs.",
        )
    )

    # Top-level modules
    top_modules = _find_count(
        [
            "aragora",
            "-maxdepth",
            "1",
            "-type",
            "d",
            "-not",
            "-path",
            "aragora",
            "-not",
            "-name",
            "__pycache__",
        ]
    )
    metrics.append(
        Metric(
            key="top_level_modules",
            label="Top-level modules under aragora/",
            value=top_modules,
            command="find aragora -maxdepth 1 -type d | wc -l",
            source="aragora/",
        )
    )

    # ----- Tests -----
    test_files = _find_count(["tests", "-name", "test_*.py", "-type", "f"])
    metrics.append(
        Metric(
            key="test_files",
            label="Test files (test_*.py under tests/)",
            value=test_files,
            command="find tests -name 'test_*.py' -type f | wc -l",
            source="tests/",
        )
    )

    # All test functions (class-nested + module-level)
    test_fns = _rg_count(r"^\s*(async )?def test_", "tests/")
    metrics.append(
        Metric(
            key="test_functions",
            label="Test functions (class + module level)",
            value=test_fns,
            command="rg '^\\s*(async )?def test_' tests/ --no-filename | wc -l",
            source="tests/",
            notes="Counts both module-level and class-nested test methods.",
        )
    )

    # Parametrize decorators (effective cases are a multiple of these)
    parametrize_count = _rg_count(r"@pytest\.mark\.parametrize", "tests/")
    metrics.append(
        Metric(
            key="parametrize_decorators",
            label="@pytest.mark.parametrize decorators",
            value=parametrize_count,
            command="rg '@pytest\\.mark\\.parametrize' tests/ --no-filename | wc -l",
            source="tests/",
            notes="Each decorator expands into N test cases during collection.",
        )
    )

    # ----- CLI -----
    cli_command_modules = _find_count(
        [
            "aragora/cli/commands",
            "-maxdepth",
            "1",
            "-name",
            "*.py",
            "-not",
            "-name",
            "__*",
            "-type",
            "f",
        ]
    )
    metrics.append(
        Metric(
            key="cli_command_modules",
            label="CLI top-level command modules",
            value=cli_command_modules,
            command="find aragora/cli/commands -maxdepth 1 -name '*.py' -not -name '__*' -type f | wc -l",
            source="aragora/cli/commands/",
        )
    )

    # ----- OpenAPI -----
    openapi_path = REPO_ROOT / "docs" / "api" / "openapi.json"
    if openapi_path.exists():
        try:
            spec = json.loads(openapi_path.read_text())
            paths = spec.get("paths", {})
            http_methods = {"get", "post", "put", "delete", "patch", "head", "options"}
            op_count = sum(1 for p in paths.values() for m in p if m.lower() in http_methods)
            metrics.append(
                Metric(
                    key="openapi_paths",
                    label="OpenAPI paths",
                    value=len(paths),
                    command="python -c \"import json; print(len(json.load(open('docs/api/openapi.json'))['paths']))\"",
                    source="docs/api/openapi.json",
                )
            )
            metrics.append(
                Metric(
                    key="openapi_operations",
                    label="OpenAPI operations (HTTP verbs)",
                    value=op_count,
                    command="python -c \"import json; spec=json.load(open('docs/api/openapi.json')); print(sum(1 for p in spec['paths'].values() for m in p if m.lower() in {'get','post','put','delete','patch','head','options'}))\"",
                    source="docs/api/openapi.json",
                )
            )
        except (OSError, json.JSONDecodeError) as e:
            metrics.append(
                Metric(
                    key="openapi_paths",
                    label="OpenAPI paths",
                    value=f"error: {type(e).__name__}",
                    command="python -c \"import json; print(len(json.load(open('docs/api/openapi.json'))['paths']))\"",
                    source="docs/api/openapi.json",
                )
            )

    # ----- RBAC -----
    permission_calls = _rg_count(r"@require_permission\(", "aragora/")
    metrics.append(
        Metric(
            key="rbac_permission_calls",
            label="@require_permission decorator calls",
            value=permission_calls,
            command="rg '@require_permission\\(' aragora/ | wc -l",
            source="aragora/",
        )
    )

    unique_permissions_result = subprocess.run(
        "rg \"@require_permission\\((['\\\"])([^'\\\"]+)['\\\"]\\)\" aragora/ -o --no-line-number -r '$2' --no-filename 2>/dev/null | sort -u | wc -l",
        shell=True,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        unique_permissions = int(unique_permissions_result.stdout.strip() or 0)
    except ValueError:
        unique_permissions = 0
    metrics.append(
        Metric(
            key="rbac_unique_permissions",
            label="Unique permission strings",
            value=unique_permissions,
            command="rg \"@require_permission\\(['\\\"]([^'\\\"]+)['\\\"]\\)\" aragora/ -o -r '$1' --no-filename | sort -u | wc -l",
            source="aragora/",
        )
    )

    # ----- SDK -----
    py_sdk_modules = _find_count(
        [
            "sdk/python/aragora_sdk",
            "-maxdepth",
            "2",
            "-name",
            "*.py",
            "-not",
            "-name",
            "__*",
            "-type",
            "f",
        ]
    )
    metrics.append(
        Metric(
            key="python_sdk_modules",
            label="Python SDK modules",
            value=py_sdk_modules,
            command="find sdk/python/aragora_sdk -maxdepth 2 -name '*.py' -not -name '__*' -type f | wc -l",
            source="sdk/python/",
        )
    )

    ts_sdk_modules = _find_count(
        [
            "sdk/typescript/src",
            "-maxdepth",
            "2",
            "-name",
            "*.ts",
            "-type",
            "f",
        ]
    )
    metrics.append(
        Metric(
            key="typescript_sdk_modules",
            label="TypeScript SDK modules",
            value=ts_sdk_modules,
            command="find sdk/typescript/src -maxdepth 2 -name '*.ts' -type f | wc -l",
            source="sdk/typescript/",
        )
    )

    # ----- Agent registry -----
    settings_path = REPO_ROOT / "aragora" / "config" / "settings.py"
    if settings_path.exists():
        text = settings_path.read_text()
        match = re.search(
            r"ALLOWED_AGENT_TYPES[^=]*=\s*frozenset\s*\(\s*(?:\{|\[)([^}\]]+)",
            text,
            re.DOTALL,
        )
        if match:
            allowed_count = len(re.findall(r"['\"]([^'\"]+)['\"]", match.group(1)))
            metrics.append(
                Metric(
                    key="allowed_agent_types",
                    label="Allowlisted agent types",
                    value=allowed_count,
                    command="grep -A 50 'ALLOWED_AGENT_TYPES' aragora/config/settings.py | grep -oE \"'[a-z-]+'\" | sort -u | wc -l",
                    source="aragora/config/settings.py",
                )
            )

    # ----- Adapter factory -----
    adapter_factory = REPO_ROOT / "aragora" / "knowledge" / "mound" / "adapters" / "factory.py"
    if adapter_factory.exists():
        # Adapters are enumerated as tuples like ("./<name>_adapter", "<Class>", {...})
        # Count unique ".<name>_adapter" module references.
        adapter_count = _rg_count(
            r'"\.[a-z_]+_adapter"',
            str(adapter_factory.relative_to(REPO_ROOT)),
        )
        metrics.append(
            Metric(
                key="knowledge_mound_adapter_specs",
                label="Knowledge Mound adapter specs",
                value=adapter_count,
                command="rg '\"\\.[a-z_]+_adapter\"' aragora/knowledge/mound/adapters/factory.py | wc -l",
                source="aragora/knowledge/mound/adapters/factory.py",
                notes="Counts adapter module entries in the factory spec tuple list.",
            )
        )

    adapter_dir = REPO_ROOT / "aragora" / "knowledge" / "mound" / "adapters"
    if adapter_dir.exists():
        adapter_files = _find_count(
            [
                str(adapter_dir.relative_to(REPO_ROOT)),
                "-maxdepth",
                "1",
                "-name",
                "*_adapter.py",
                "-type",
                "f",
            ]
        )
        metrics.append(
            Metric(
                key="knowledge_mound_adapter_files",
                label="Knowledge Mound adapter files",
                value=adapter_files,
                command="find aragora/knowledge/mound/adapters -maxdepth 1 -name '*_adapter.py' -type f | wc -l",
                source="aragora/knowledge/mound/adapters/",
            )
        )

    # ----- Docs -----
    doc_files = _find_count(["docs", "-name", "*.md", "-type", "f"])
    metrics.append(
        Metric(
            key="doc_files",
            label="Markdown files under docs/",
            value=doc_files,
            command="find docs -name '*.md' -type f | wc -l",
            source="docs/",
        )
    )

    # ----- CI workflows -----
    workflows = _find_count([".github/workflows", "-name", "*.yml", "-type", "f"])
    metrics.append(
        Metric(
            key="ci_workflows",
            label="GitHub Actions workflows",
            value=workflows,
            command="find .github/workflows -name '*.yml' -type f | wc -l",
            source=".github/workflows/",
        )
    )

    # ----- Mypy baseline -----
    mypy_baseline = REPO_ROOT / ".mypy-baseline"
    if mypy_baseline.exists():
        mypy_errors = sum(1 for _ in mypy_baseline.open())
        metrics.append(
            Metric(
                key="mypy_baseline_errors",
                label="Mypy baseline errors (grandfathered)",
                value=mypy_errors,
                command="wc -l .mypy-baseline",
                source=".mypy-baseline",
            )
        )

    return MetricsSnapshot(
        generated_at=generated_at,
        git_sha=git_sha,
        metrics=metrics,
    )


def render_markdown(snapshot: MetricsSnapshot) -> str:
    lines: list[str] = []
    lines.append("# Aragora Canonical Metrics")
    lines.append("")
    lines.append(
        "> **This doc is auto-generated.** Do not edit by hand — edits will be "
        "overwritten by the next run of `scripts/regenerate_metrics.py`. "
        "If a number here disagrees with another doc, this doc wins. "
        "Every metric below is reproducible by running the command in its row."
    )
    lines.append("")
    lines.append(
        "> **No timestamp or git SHA is embedded in this doc by design.** "
        "Embedding either would cause two branches that both regenerated "
        "the doc to always conflict on merge, turning an honesty mechanism "
        "into a merge-conflict factory. The authoritative timestamp and SHA "
        "for any regeneration are available via `--json`."
    )
    lines.append("")
    lines.append("- **Regenerate:** `python scripts/regenerate_metrics.py`")
    lines.append("- **Verify (drift check):** `python scripts/regenerate_metrics.py --check`")
    lines.append("- **Timestamped JSON snapshot:** `python scripts/regenerate_metrics.py --json`")
    lines.append("")
    lines.append("## Canonical numbers")
    lines.append("")
    lines.append("| Metric | Value | Source | Command |")
    lines.append("|---|---|---|---|")
    for m in snapshot.metrics:
        cmd = m.command.replace("|", "\\|")
        source = m.source.replace("|", "\\|")
        lines.append(f"| {m.label} | `{m.value}` | `{source}` | `{cmd}` |")
    lines.append("")

    # Notes section
    noted = [m for m in snapshot.metrics if m.notes]
    if noted:
        lines.append("## Notes on counting methodology")
        lines.append("")
        for m in noted:
            lines.append(f"- **{m.label}:** {m.notes}")
        lines.append("")

    lines.append("## Why this doc exists")
    lines.append("")
    lines.append(
        "Aragora's thesis (Commitment 4: respect the limits) requires that "
        "the product not claim capability it does not have. The same "
        "discipline applies to numeric claims. Before this doc existed, "
        "different docs cited different numbers for the same metric "
        "(e.g. test-count claims ranged from 129K to 210K+ depending on "
        "regex used). This doc is the single source of truth."
    )
    lines.append("")
    lines.append(
        "All other docs that cite a metric should link here rather than "
        "hard-code the number, or explicitly snapshot the number with a "
        "date so staleness is visible."
    )
    lines.append("")
    lines.append("## Drift threshold")
    lines.append("")
    lines.append(
        "The `--check` mode fails if any metric moved by more than 0.5% from "
        "the committed doc. This threshold is a trade-off: lower values "
        "(e.g. 0.1%) would trigger on small absolute moves in small-denominator "
        "metrics (e.g. adapter count changing by one), forcing doc churn on "
        "normal development. Higher values (e.g. 5%) would let meaningful "
        "drift accumulate silently. 0.5% was picked as the default; it is a "
        "constant in `scripts/regenerate_metrics.py` (`DRIFT_THRESHOLD`) and "
        "can be tuned if specific metrics prove too noisy."
    )
    lines.append("")
    lines.append(
        "New metrics (present in the script but not in the committed doc) "
        "are reported as `NEW:` in the check output and force a refresh "
        "regardless of threshold."
    )
    lines.append("")
    lines.append("## Related automation")
    lines.append("")
    lines.append(
        "- `.github/workflows/metrics-drift.yml` runs this script on every PR "
        "that touches counted surfaces (`aragora/`, `tests/`, `sdk/`, "
        "`docs/api/openapi.json`, `.mypy-baseline`), and on a weekly Monday "
        "schedule. It invokes `--check` and fails the job if drift exceeds "
        "the threshold. The job does **not** auto-open a refresh PR; it "
        "fails loud and a human or follow-up automation decides whether "
        "to regenerate."
    )
    lines.append(
        "- `tests/scripts/test_regenerate_metrics.py` holds external "
        "invariants (e.g. test count > 100K, python file count > 1K) so the "
        "bootstrap is not fully self-referential: even if the committed "
        "doc were wrong, the invariant tests would catch a gross break."
    )
    lines.append(
        "- `scripts/reconcile_status.py` cross-references feature claims "
        "across CAPABILITY_MATRIX, GA_CHECKLIST, STATUS, ROADMAP."
    )
    lines.append(
        "- `scripts/validate_openapi_routes.py` verifies OpenAPI paths "
        "against actual handler implementations."
    )
    lines.append("")
    return "\n".join(lines)


def parse_current_metrics(doc_path: Path) -> dict[str, int | str]:
    """Extract metric values from an existing METRICS.md for drift comparison."""
    if not doc_path.exists():
        return {}
    text = doc_path.read_text()
    # Rows look like: | <label> | `<value>` | `<source>` | `<command>` |
    pattern = re.compile(r"^\|\s*([^|]+?)\s*\|\s*`([^`]*)`\s*\|", re.MULTILINE)
    result: dict[str, int | str] = {}
    for label, value in pattern.findall(text):
        label = label.strip()
        raw = value.strip()
        try:
            result[label] = int(raw)
        except ValueError:
            result[label] = raw
    return result


def check_drift(snapshot: MetricsSnapshot) -> tuple[bool, list[str]]:
    current = parse_current_metrics(METRICS_DOC)
    drifts: list[str] = []
    for m in snapshot.metrics:
        prev = current.get(m.label)
        if prev is None:
            drifts.append(f"NEW: {m.label} = {m.value}")
            continue
        if isinstance(prev, int) and isinstance(m.value, int):
            if prev == 0:
                delta_pct = 1.0 if m.value != 0 else 0.0
            else:
                delta_pct = abs(m.value - prev) / prev
            if delta_pct > DRIFT_THRESHOLD:
                drifts.append(f"DRIFT: {m.label} {prev} -> {m.value} ({delta_pct * 100:.1f}%)")
        else:
            if str(prev) != str(m.value):
                drifts.append(f"CHANGED: {m.label} {prev!r} -> {m.value!r}")
    return (len(drifts) > 0), drifts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any metric drifted more than 0.5% from current doc.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON snapshot to stdout instead of writing docs/METRICS.md.",
    )
    args = parser.parse_args()

    snapshot = gather_metrics()

    if args.json:
        print(json.dumps(snapshot.as_dict(), indent=2))
        return 0

    if args.check:
        drifted, drifts = check_drift(snapshot)
        if drifted:
            print("Metrics drifted:")
            for d in drifts:
                print(f"  {d}")
            print()
            print(
                "Run `python scripts/regenerate_metrics.py` to refresh "
                "docs/METRICS.md and commit the result."
            )
            return 1
        print("No drift beyond 0.5% threshold.")
        return 0

    # Regenerate the doc
    markdown = render_markdown(snapshot)
    METRICS_DOC.parent.mkdir(parents=True, exist_ok=True)
    METRICS_DOC.write_text(markdown)
    print(f"Wrote {METRICS_DOC} with {len(snapshot.metrics)} metrics.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

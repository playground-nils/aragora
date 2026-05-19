#!/usr/bin/env python3
"""Aragora Delegation Contract v0.3 — periodic predicate evaluator.

This script reads a ``GoalSpec`` JSON, evaluates every acceptance criterion
through the deterministic predicate oracle (``aragora.policy.evaluate_predicate``)
and appends a per-goal "progress ledger" JSONL record under
``.aragora/progress-ledger/<goal_id>.jsonl``.

The ledger is the substrate that makes *stall detection* possible without a
human in the loop:

- ``stalled``: K consecutive ticks (default 3) had identical progress AND no
  per-AC boolean flipped → the lane is making no forward motion.
- ``regressed_ac_ids``: an AC that was previously ``satisfied=true`` in the
  ledger is now ``satisfied=false`` → something regressed, the prior
  evaluator agreed, now it doesn't.

The script is dry-run by default. ``--apply`` writes the tick to the ledger.
``--json`` prints the full computed record.

Pure stdlib + ``aragora.policy``. No new pip deps. No protected files touched.
Schema-additive over Delegation Contract v0.1 (PR #7357) — does not modify any
v0.1 module.

v0.3 scope (this script): periodic evaluation + stall/regression telemetry.

Out of scope (later versions):
- Actually orchestrating spot-checks (v0.5)
- Mutating the lane registry as a side effect of evaluation (v0.7)
- HMAC signing of ledger entries (v0.4)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# The script imports lazily inside main() so that --help can run even from a
# stripped-down environment, but the type checker still resolves the names.
from aragora.policy import (  # noqa: E402  (after dataclass-style header)
    GOAL_SPEC_SCHEMA_VERSION,
    PredicateResult,
    evaluate_predicate,
)

LEDGER_SCHEMA_VERSION = "aragora-progress-ledger-tick/0.1"
PROGRESS_LEDGER_RELATIVE_DIR = Path(".aragora") / "progress-ledger"
USER_LEDGER_DIR = Path.home() / ".aragora" / "progress-ledger"
SUPPORTED_PROGRESS_METRICS = (
    "fraction_of_AC_satisfied",
    "all_AC_satisfied",
    "weighted_AC",
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class GoalSpecLoadError(ValueError):
    """Raised when the goal-spec JSON cannot be parsed or is malformed."""


# ---------------------------------------------------------------------------
# Lightweight goal-spec record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _AC:
    ac_id: str
    predicate: str
    weight: float = 1.0
    description: str = ""


@dataclass(frozen=True)
class _GoalSpec:
    """Trimmed mirror of ``aragora.policy.GoalSpec`` used internally.

    We deliberately don't construct the upstream dataclass here: it raises
    ``ContractValidationError`` on a missing schema_version which makes
    error reporting noisier than this script wants, and we want the
    progress evaluator to tolerate forward-compatible spec fields.
    """

    goal_id: str
    schema_version: str
    acceptance_criteria: list[_AC]
    progress_metric: str = "fraction_of_AC_satisfied"
    completion_predicate: str = ""
    anti_signals: list[str] = field(default_factory=list)


def load_goal_spec(path: Path) -> _GoalSpec:
    """Parse a GoalSpec JSON from disk."""
    if not path.exists():
        raise GoalSpecLoadError(f"goal-spec path does not exist: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GoalSpecLoadError(f"goal-spec is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise GoalSpecLoadError(f"goal-spec must be a JSON object, got {type(raw).__name__}")

    goal_id = raw.get("goal_id")
    if not isinstance(goal_id, str) or not goal_id:
        raise GoalSpecLoadError("goal-spec.goal_id must be a non-empty string")

    schema_version = raw.get("schema_version", GOAL_SPEC_SCHEMA_VERSION)
    if not isinstance(schema_version, str):
        raise GoalSpecLoadError("goal-spec.schema_version must be a string")

    ac_raw = raw.get("acceptance_criteria", [])
    if not isinstance(ac_raw, list) or not ac_raw:
        raise GoalSpecLoadError("goal-spec.acceptance_criteria must be a non-empty list")

    criteria: list[_AC] = []
    seen_ids: set[str] = set()
    for idx, entry in enumerate(ac_raw):
        if not isinstance(entry, dict):
            raise GoalSpecLoadError(f"goal-spec.acceptance_criteria[{idx}] must be an object")
        ac_id = entry.get("ac_id")
        predicate = entry.get("predicate")
        if not isinstance(ac_id, str) or not ac_id:
            raise GoalSpecLoadError(
                f"goal-spec.acceptance_criteria[{idx}].ac_id must be a non-empty string"
            )
        if not isinstance(predicate, str) or not predicate:
            raise GoalSpecLoadError(
                f"goal-spec.acceptance_criteria[{idx}].predicate must be a non-empty string"
            )
        if ac_id in seen_ids:
            raise GoalSpecLoadError(
                f"goal-spec.acceptance_criteria[{idx}].ac_id duplicate: {ac_id!r}"
            )
        seen_ids.add(ac_id)
        weight = entry.get("weight", 1.0)
        try:
            weight_f = float(weight)
        except (TypeError, ValueError) as exc:
            raise GoalSpecLoadError(
                f"goal-spec.acceptance_criteria[{idx}].weight must be numeric"
            ) from exc
        if weight_f < 0:
            raise GoalSpecLoadError(f"goal-spec.acceptance_criteria[{idx}].weight must be >= 0")
        criteria.append(
            _AC(
                ac_id=ac_id,
                predicate=predicate,
                weight=weight_f,
                description=str(entry.get("description", "")),
            )
        )

    metric = raw.get("progress_metric", "fraction_of_AC_satisfied")
    if metric not in SUPPORTED_PROGRESS_METRICS:
        raise GoalSpecLoadError(
            f"goal-spec.progress_metric must be one of "
            f"{SUPPORTED_PROGRESS_METRICS!r}; got {metric!r}"
        )

    completion_predicate = raw.get("completion_predicate", "")
    if not isinstance(completion_predicate, str):
        raise GoalSpecLoadError("goal-spec.completion_predicate must be a string")

    anti_signals_raw = raw.get("anti_signals", [])
    if not isinstance(anti_signals_raw, list):
        raise GoalSpecLoadError("goal-spec.anti_signals must be a list of strings")
    anti_signals: list[str] = []
    for idx, sig in enumerate(anti_signals_raw):
        if not isinstance(sig, str):
            raise GoalSpecLoadError(f"goal-spec.anti_signals[{idx}] must be a string")
        anti_signals.append(sig)

    return _GoalSpec(
        goal_id=goal_id,
        schema_version=schema_version,
        acceptance_criteria=criteria,
        progress_metric=metric,
        completion_predicate=completion_predicate,
        anti_signals=anti_signals,
    )


# ---------------------------------------------------------------------------
# Progress computation
# ---------------------------------------------------------------------------


def compute_progress(criteria: list[_AC], results: list[PredicateResult], metric: str) -> float:
    """Compute aggregate progress under the named metric.

    All metrics return a float in [0.0, 1.0].
    """
    if not criteria:
        return 0.0
    by_id = {ac.ac_id: ac for ac in criteria}
    # Match results to AC by index since we evaluate in declared order.
    pairs = list(zip(criteria, results, strict=True))
    if metric == "all_AC_satisfied":
        return 1.0 if all(r.satisfied for _, r in pairs) else 0.0
    if metric == "fraction_of_AC_satisfied":
        sat_count = sum(1 for _, r in pairs if r.satisfied)
        return sat_count / len(pairs)
    if metric == "weighted_AC":
        total_weight = sum(ac.weight for ac in criteria)
        if total_weight <= 0:
            # All-zero weights collapse to fraction semantics so the script
            # never returns NaN.
            sat_count = sum(1 for _, r in pairs if r.satisfied)
            return sat_count / len(pairs) if pairs else 0.0
        sat_weight = sum(by_id[ac.ac_id].weight for ac, r in pairs if r.satisfied)
        return sat_weight / total_weight
    # Defensive: load_goal_spec already validated metric.
    raise ValueError(f"unsupported progress_metric: {metric!r}")  # pragma: no cover


# ---------------------------------------------------------------------------
# Stall + regression detection
# ---------------------------------------------------------------------------


def _ac_id_to_satisfied(tick: dict[str, Any]) -> dict[str, bool]:
    """Extract {ac_id: satisfied} from a ledger tick row."""
    out: dict[str, bool] = {}
    for entry in tick.get("results", []):
        if not isinstance(entry, dict):
            continue
        ac_id = entry.get("ac_id")
        if isinstance(ac_id, str):
            out[ac_id] = bool(entry.get("satisfied"))
    return out


def detect_stall(
    history: list[dict[str, Any]], current_tick: dict[str, Any], *, window: int
) -> bool:
    """Return True if the most recent ``window`` ticks (including current) have
    identical progress AND no per-AC boolean flipped across them.
    """
    if window < 2:
        return False
    sequence = [*history[-(window - 1) :], current_tick]
    if len(sequence) < window:
        return False
    progress_values = {round(tick.get("progress", -1.0), 12) for tick in sequence}
    if len(progress_values) != 1:
        return False
    # Per-AC boolean flip check.
    snapshots = [_ac_id_to_satisfied(tick) for tick in sequence]
    all_ids = set().union(*snapshots)
    for ac_id in all_ids:
        values = {snap.get(ac_id) for snap in snapshots}
        if len(values) > 1:
            return False
    return True


def detect_regressions(history: list[dict[str, Any]], current_tick: dict[str, Any]) -> list[str]:
    """Return ac_ids that were satisfied in any prior tick but are now not."""
    current_map = _ac_id_to_satisfied(current_tick)
    previously_satisfied: set[str] = set()
    for tick in history:
        for ac_id, satisfied in _ac_id_to_satisfied(tick).items():
            if satisfied:
                previously_satisfied.add(ac_id)
    regressed = [ac_id for ac_id in sorted(previously_satisfied) if current_map.get(ac_id) is False]
    return regressed


# ---------------------------------------------------------------------------
# Ledger I/O + repo-root resolution
# ---------------------------------------------------------------------------


def find_repo_root(start: Path | None = None) -> Path | None:
    """Walk up looking for ``.aragora/agent-bridge/lanes.json``.

    Mirrors the strategy used by ``scripts/claim_active_agent_lane.py``
    (the v0.3 spec calls out the same resolver).
    """
    here = (start or Path.cwd()).resolve()
    sentinel = Path(".aragora") / "agent-bridge" / "lanes.json"
    current = here
    while True:
        if (current / sentinel).exists():
            return current
        if current.parent == current:
            return None
        current = current.parent


def resolve_ledger_dir(*, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit
    root = find_repo_root()
    if root is not None:
        return root / PROGRESS_LEDGER_RELATIVE_DIR
    return USER_LEDGER_DIR


def resolve_ledger_path(goal_id: str, *, explicit_dir: Path | None = None) -> Path:
    safe = _safe_goal_filename(goal_id)
    return resolve_ledger_dir(explicit=explicit_dir) / f"{safe}.jsonl"


def _safe_goal_filename(goal_id: str) -> str:
    """Strip characters unsafe for filenames; keep predicate uniqueness.

    Goal IDs can contain slashes (e.g. "ADC-v0.3/X") so we collapse to a
    forward-slash-free representation.
    """
    out = []
    for ch in goal_id:
        if ch.isalnum() or ch in ("-", "_", ".", "+"):
            out.append(ch)
        else:
            out.append("_")
    return "".join(out)


def load_ledger_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue  # tolerate corruption; ledger is append-only telemetry
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def append_tick(path: Path, tick: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(tick, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Tick assembly
# ---------------------------------------------------------------------------


def _result_to_dict(ac_id: str, result: PredicateResult) -> dict[str, Any]:
    return {
        "ac_id": ac_id,
        "predicate": result.predicate,
        "satisfied": bool(result.satisfied),
        "evidence": result.evidence,
        "evaluator": result.evaluator,
        "error": result.error,
    }


def _now_utc_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_tick(
    spec: _GoalSpec,
    *,
    history: list[dict[str, Any]],
    stall_window: int,
    now_iso: str | None = None,
    evaluators: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate every AC + anti-signal and assemble a ledger tick.

    ``evaluators`` is forwarded to ``evaluate_predicate`` so callers (and
    tests) can substitute a deterministic registry.
    """
    ac_results: list[PredicateResult] = []
    for ac in spec.acceptance_criteria:
        ac_results.append(evaluate_predicate(ac.predicate, evaluators=evaluators))

    progress = compute_progress(spec.acceptance_criteria, ac_results, spec.progress_metric)

    if spec.completion_predicate:
        completion_result = evaluate_predicate(spec.completion_predicate, evaluators=evaluators)
        completion_satisfied = bool(completion_result.satisfied)
    else:
        completion_satisfied = all(r.satisfied for r in ac_results)

    anti_signal_hits: list[str] = []
    for sig in spec.anti_signals:
        sig_result = evaluate_predicate(sig, evaluators=evaluators)
        if sig_result.satisfied:
            anti_signal_hits.append(sig)

    tick: dict[str, Any] = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "tick_ts": now_iso or _now_utc_iso(),
        "goal_id": spec.goal_id,
        "progress": progress,
        "completion_satisfied": completion_satisfied,
        "results": [
            _result_to_dict(ac.ac_id, result)
            for ac, result in zip(spec.acceptance_criteria, ac_results, strict=True)
        ],
        "anti_signal_hits": anti_signal_hits,
    }

    if detect_stall(history, tick, window=stall_window):
        tick["stalled"] = True
    regressed = detect_regressions(history, tick)
    if regressed:
        tick["regressed_ac_ids"] = regressed
    return tick


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Aragora Delegation Contract v0.3: evaluate a GoalSpec's "
            "acceptance criteria via the deterministic predicate oracle "
            "and append a progress-ledger tick."
        )
    )
    parser.add_argument(
        "--goal-spec",
        required=True,
        type=Path,
        help="Path to GoalSpec JSON.",
    )
    write_group = parser.add_mutually_exclusive_group()
    write_group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Print the would-be tick without touching the ledger (default).",
    )
    write_group.add_argument(
        "--apply",
        action="store_true",
        help="Append the tick to .aragora/progress-ledger/<goal_id>.jsonl.",
    )
    parser.add_argument(
        "--stall-window",
        type=int,
        default=3,
        help="K consecutive identical ticks to flag as stalled (default 3).",
    )
    parser.add_argument(
        "--ledger-dir",
        type=Path,
        default=None,
        help="Override the ledger directory (default resolves from repo root).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full tick record as JSON to stdout.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.stall_window < 2:
        print(
            "evaluate_goal_progress: --stall-window must be >= 2 to be meaningful",
            file=sys.stderr,
        )
        return 1

    try:
        spec = load_goal_spec(args.goal_spec)
    except GoalSpecLoadError as exc:
        print(f"evaluate_goal_progress: {exc}", file=sys.stderr)
        return 1

    ledger_path = resolve_ledger_path(spec.goal_id, explicit_dir=args.ledger_dir)
    history = load_ledger_history(ledger_path)

    tick = build_tick(
        spec,
        history=history,
        stall_window=args.stall_window,
    )

    if args.apply:
        try:
            append_tick(ledger_path, tick)
        except OSError as exc:
            print(
                f"evaluate_goal_progress: failed to write ledger: {exc}",
                file=sys.stderr,
            )
            return 1

    if args.json:
        print(json.dumps(tick, sort_keys=True, indent=2))
    else:
        # Compact one-line summary so periodic cron output stays small.
        summary = {
            "goal_id": tick["goal_id"],
            "progress": tick["progress"],
            "completion_satisfied": tick["completion_satisfied"],
            "stalled": tick.get("stalled", False),
            "regressed_ac_ids": tick.get("regressed_ac_ids", []),
            "anti_signal_hits": tick["anti_signal_hits"],
            "applied": bool(args.apply),
            "ledger_path": str(ledger_path),
        }
        print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

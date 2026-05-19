"""Tests for ``scripts/evaluate_goal_progress.py``.

These tests are deterministic: they monkeypatch the predicate oracle's
``EVALUATORS`` registry so no subprocess (``gh``, ``git``, ``pytest``) is
spawned. That keeps the suite hermetic and fast.
"""

from __future__ import annotations

import importlib
import json
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

# Ensure repo-root scripts/ is importable.
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

evaluate_goal_progress = importlib.import_module("evaluate_goal_progress")
from aragora.policy import predicate_oracle  # noqa: E402

PredicateResult = predicate_oracle.PredicateResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_satisfied(name: str, *, satisfied: bool, evidence: str = "stub") -> object:
    """Build a stub evaluator that always returns the named verdict."""

    def _fn(predicate: str, args: list[str]) -> PredicateResult:
        return PredicateResult(
            predicate=predicate,
            satisfied=satisfied,
            evidence=evidence,
            evaluator=name,
        )

    return _fn


@pytest.fixture
def stub_evaluators(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, object]]:
    """Replace the predicate oracle's global registry with a controllable one.

    Tests mutate ``registry`` to register named evaluators that return
    ``satisfied=True`` or ``satisfied=False`` for the duration of the test.
    """

    registry: dict[str, object] = {}
    monkeypatch.setattr(predicate_oracle, "EVALUATORS", registry)
    yield registry


def _write_goal_spec(
    path: Path,
    *,
    goal_id: str = "g1",
    criteria: list[dict] | None = None,
    progress_metric: str = "fraction_of_AC_satisfied",
    anti_signals: list[str] | None = None,
    completion_predicate: str = "",
) -> Path:
    payload = {
        "goal_id": goal_id,
        "schema_version": "aragora-goal-spec/0.1",
        "owner": "armand",
        "approved_at": "2026-05-19T13:00:00Z",
        "description": "test goal",
        "acceptance_criteria": criteria
        or [
            {"ac_id": "AC1", "predicate": "ac_one()"},
            {"ac_id": "AC2", "predicate": "ac_two()"},
        ],
        "progress_metric": progress_metric,
        "completion_predicate": completion_predicate,
        "anti_signals": anti_signals or [],
        "max_delegation_depth": 3,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 1. Happy path — all AC satisfied
# ---------------------------------------------------------------------------


def test_all_ac_satisfied_progress_is_one(
    tmp_path: Path, stub_evaluators: dict[str, object]
) -> None:
    stub_evaluators["ac_one"] = _stub_satisfied("ac_one", satisfied=True)
    stub_evaluators["ac_two"] = _stub_satisfied("ac_two", satisfied=True)
    spec_path = _write_goal_spec(tmp_path / "spec.json")
    spec = evaluate_goal_progress.load_goal_spec(spec_path)

    tick = evaluate_goal_progress.build_tick(spec, history=[], stall_window=3)

    assert tick["progress"] == 1.0
    assert tick["completion_satisfied"] is True
    assert [r["satisfied"] for r in tick["results"]] == [True, True]
    assert tick["anti_signal_hits"] == []


# ---------------------------------------------------------------------------
# 2. Partial — 2/3 satisfied under fraction metric
# ---------------------------------------------------------------------------


def test_fraction_metric_partial(tmp_path: Path, stub_evaluators: dict[str, object]) -> None:
    stub_evaluators["a"] = _stub_satisfied("a", satisfied=True)
    stub_evaluators["b"] = _stub_satisfied("b", satisfied=True)
    stub_evaluators["c"] = _stub_satisfied("c", satisfied=False)
    spec_path = _write_goal_spec(
        tmp_path / "spec.json",
        criteria=[
            {"ac_id": "A", "predicate": "a()"},
            {"ac_id": "B", "predicate": "b()"},
            {"ac_id": "C", "predicate": "c()"},
        ],
    )
    spec = evaluate_goal_progress.load_goal_spec(spec_path)

    tick = evaluate_goal_progress.build_tick(spec, history=[], stall_window=3)

    assert tick["progress"] == pytest.approx(2.0 / 3.0)
    assert tick["completion_satisfied"] is False


# ---------------------------------------------------------------------------
# 3. Weighted — 2/3 satisfied but weights (1,2,1) → 3/4
# ---------------------------------------------------------------------------


def test_weighted_metric_uses_weights(tmp_path: Path, stub_evaluators: dict[str, object]) -> None:
    stub_evaluators["a"] = _stub_satisfied("a", satisfied=True)
    stub_evaluators["b"] = _stub_satisfied("b", satisfied=True)
    stub_evaluators["c"] = _stub_satisfied("c", satisfied=False)
    spec_path = _write_goal_spec(
        tmp_path / "spec.json",
        progress_metric="weighted_AC",
        criteria=[
            {"ac_id": "A", "predicate": "a()", "weight": 1},
            {"ac_id": "B", "predicate": "b()", "weight": 2},
            {"ac_id": "C", "predicate": "c()", "weight": 1},
        ],
    )
    spec = evaluate_goal_progress.load_goal_spec(spec_path)

    tick = evaluate_goal_progress.build_tick(spec, history=[], stall_window=3)

    assert tick["progress"] == pytest.approx(3.0 / 4.0)


# ---------------------------------------------------------------------------
# 4. all_AC_satisfied collapses to 0 if any AC fails
# ---------------------------------------------------------------------------


def test_all_ac_metric_is_binary(tmp_path: Path, stub_evaluators: dict[str, object]) -> None:
    stub_evaluators["a"] = _stub_satisfied("a", satisfied=True)
    stub_evaluators["b"] = _stub_satisfied("b", satisfied=False)
    spec_path = _write_goal_spec(
        tmp_path / "spec.json",
        progress_metric="all_AC_satisfied",
        criteria=[
            {"ac_id": "A", "predicate": "a()"},
            {"ac_id": "B", "predicate": "b()"},
        ],
    )
    spec = evaluate_goal_progress.load_goal_spec(spec_path)

    tick = evaluate_goal_progress.build_tick(spec, history=[], stall_window=3)

    assert tick["progress"] == 0.0
    assert tick["completion_satisfied"] is False


# ---------------------------------------------------------------------------
# 5. Stall detection: three identical ticks → stalled=True
# ---------------------------------------------------------------------------


def test_three_consecutive_identical_ticks_flagged_stalled(
    tmp_path: Path, stub_evaluators: dict[str, object]
) -> None:
    stub_evaluators["a"] = _stub_satisfied("a", satisfied=True)
    stub_evaluators["b"] = _stub_satisfied("b", satisfied=False)
    spec_path = _write_goal_spec(
        tmp_path / "spec.json",
        criteria=[
            {"ac_id": "A", "predicate": "a()"},
            {"ac_id": "B", "predicate": "b()"},
        ],
    )
    spec = evaluate_goal_progress.load_goal_spec(spec_path)

    t1 = evaluate_goal_progress.build_tick(
        spec, history=[], stall_window=3, now_iso="2026-05-19T13:00:00Z"
    )
    t2 = evaluate_goal_progress.build_tick(
        spec, history=[t1], stall_window=3, now_iso="2026-05-19T13:05:00Z"
    )
    t3 = evaluate_goal_progress.build_tick(
        spec, history=[t1, t2], stall_window=3, now_iso="2026-05-19T13:10:00Z"
    )

    assert "stalled" not in t1
    assert "stalled" not in t2
    assert t3.get("stalled") is True


# ---------------------------------------------------------------------------
# 6. Regression detection
# ---------------------------------------------------------------------------


def test_regressed_ac_ids_populated_when_satisfied_flips_false(
    tmp_path: Path, stub_evaluators: dict[str, object]
) -> None:
    # First tick: AC1 satisfied. Second tick: AC1 no longer satisfied.
    stub_evaluators["a"] = _stub_satisfied("a", satisfied=True)
    stub_evaluators["b"] = _stub_satisfied("b", satisfied=True)
    spec_path = _write_goal_spec(
        tmp_path / "spec.json",
        criteria=[
            {"ac_id": "AC1", "predicate": "a()"},
            {"ac_id": "AC2", "predicate": "b()"},
        ],
    )
    spec = evaluate_goal_progress.load_goal_spec(spec_path)
    t1 = evaluate_goal_progress.build_tick(spec, history=[], stall_window=3)
    assert "regressed_ac_ids" not in t1

    # Now AC1 regresses.
    stub_evaluators["a"] = _stub_satisfied("a", satisfied=False)
    t2 = evaluate_goal_progress.build_tick(spec, history=[t1], stall_window=3)

    assert t2["regressed_ac_ids"] == ["AC1"]


# ---------------------------------------------------------------------------
# 7. Anti-signal hit
# ---------------------------------------------------------------------------


def test_anti_signal_hit_recorded(tmp_path: Path, stub_evaluators: dict[str, object]) -> None:
    stub_evaluators["a"] = _stub_satisfied("a", satisfied=True)
    # Synthetic anti-signal evaluator added to the registry under test.
    # Predicate names match r"^[a-z][a-z_]*$" — no digits, hence the spelled-out
    # "three" in lieu of "3_times".
    stub_evaluators["same_lane_id_claimed_three_times"] = _stub_satisfied(
        "same_lane_id_claimed_three_times", satisfied=True, evidence="three claims"
    )
    spec_path = _write_goal_spec(
        tmp_path / "spec.json",
        criteria=[{"ac_id": "A", "predicate": "a()"}],
        anti_signals=["same_lane_id_claimed_three_times()"],
    )
    spec = evaluate_goal_progress.load_goal_spec(spec_path)

    tick = evaluate_goal_progress.build_tick(spec, history=[], stall_window=3)

    assert tick["anti_signal_hits"] == ["same_lane_id_claimed_three_times()"]


# ---------------------------------------------------------------------------
# 8. Dry-run does not touch the ledger
# ---------------------------------------------------------------------------


def test_dry_run_does_not_create_ledger(
    tmp_path: Path, stub_evaluators: dict[str, object], capsys: pytest.CaptureFixture[str]
) -> None:
    stub_evaluators["ac_one"] = _stub_satisfied("ac_one", satisfied=True)
    stub_evaluators["ac_two"] = _stub_satisfied("ac_two", satisfied=True)
    spec_path = _write_goal_spec(tmp_path / "spec.json", goal_id="goal-dry")
    ledger_dir = tmp_path / "ledger"

    rc = evaluate_goal_progress.main(
        [
            "--goal-spec",
            str(spec_path),
            "--ledger-dir",
            str(ledger_dir),
            "--dry-run",
        ]
    )

    assert rc == 0
    assert not ledger_dir.exists()
    captured = capsys.readouterr().out
    summary = json.loads(captured.strip().splitlines()[-1])
    assert summary["applied"] is False
    assert summary["progress"] == 1.0


# ---------------------------------------------------------------------------
# 9. --apply creates ledger directory and appends one line
# ---------------------------------------------------------------------------


def test_apply_creates_ledger_and_appends_one_line(
    tmp_path: Path, stub_evaluators: dict[str, object]
) -> None:
    stub_evaluators["ac_one"] = _stub_satisfied("ac_one", satisfied=True)
    stub_evaluators["ac_two"] = _stub_satisfied("ac_two", satisfied=False)
    spec_path = _write_goal_spec(tmp_path / "spec.json", goal_id="apply-goal")
    ledger_dir = tmp_path / "ledger"

    rc = evaluate_goal_progress.main(
        [
            "--goal-spec",
            str(spec_path),
            "--ledger-dir",
            str(ledger_dir),
            "--apply",
        ]
    )

    assert rc == 0
    ledger_file = ledger_dir / "apply-goal.jsonl"
    assert ledger_file.exists(), "ledger file should be created on --apply"
    lines = ledger_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["schema_version"] == evaluate_goal_progress.LEDGER_SCHEMA_VERSION
    assert row["goal_id"] == "apply-goal"
    assert row["progress"] == pytest.approx(0.5)

    # A second invocation should append a second line.
    rc2 = evaluate_goal_progress.main(
        [
            "--goal-spec",
            str(spec_path),
            "--ledger-dir",
            str(ledger_dir),
            "--apply",
        ]
    )
    assert rc2 == 0
    lines = ledger_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


# ---------------------------------------------------------------------------
# 10. Malformed goal spec → exit code 1
# ---------------------------------------------------------------------------


def test_malformed_spec_returns_exit_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad_spec = tmp_path / "bad.json"
    bad_spec.write_text("this is not json", encoding="utf-8")

    rc = evaluate_goal_progress.main(["--goal-spec", str(bad_spec)])

    assert rc == 1
    captured = capsys.readouterr()
    assert "evaluate_goal_progress" in captured.err


# ---------------------------------------------------------------------------
# 11. --json prints full tick record
# ---------------------------------------------------------------------------


def test_json_flag_prints_full_record(
    tmp_path: Path, stub_evaluators: dict[str, object], capsys: pytest.CaptureFixture[str]
) -> None:
    stub_evaluators["ac_one"] = _stub_satisfied("ac_one", satisfied=True)
    stub_evaluators["ac_two"] = _stub_satisfied("ac_two", satisfied=True)
    spec_path = _write_goal_spec(tmp_path / "spec.json", goal_id="json-goal")
    ledger_dir = tmp_path / "ledger"

    rc = evaluate_goal_progress.main(
        [
            "--goal-spec",
            str(spec_path),
            "--ledger-dir",
            str(ledger_dir),
            "--json",
        ]
    )

    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["schema_version"] == evaluate_goal_progress.LEDGER_SCHEMA_VERSION
    assert parsed["goal_id"] == "json-goal"
    assert "results" in parsed and len(parsed["results"]) == 2


# ---------------------------------------------------------------------------
# 12. completion_predicate overrides default completion semantics
# ---------------------------------------------------------------------------


def test_completion_predicate_used_when_present(
    tmp_path: Path, stub_evaluators: dict[str, object]
) -> None:
    stub_evaluators["a"] = _stub_satisfied("a", satisfied=False)
    stub_evaluators["done"] = _stub_satisfied("done", satisfied=True)
    spec_path = _write_goal_spec(
        tmp_path / "spec.json",
        criteria=[{"ac_id": "A", "predicate": "a()"}],
        completion_predicate="done()",
    )
    spec = evaluate_goal_progress.load_goal_spec(spec_path)
    tick = evaluate_goal_progress.build_tick(spec, history=[], stall_window=3)

    # AC unsatisfied → progress 0.0, but completion_satisfied driven by
    # completion_predicate which is True.
    assert tick["progress"] == 0.0
    assert tick["completion_satisfied"] is True


# ---------------------------------------------------------------------------
# 13. Stall is NOT flagged when an AC boolean has flipped within the window
# ---------------------------------------------------------------------------


def test_no_stall_when_ac_boolean_flips(tmp_path: Path, stub_evaluators: dict[str, object]) -> None:
    stub_evaluators["a"] = _stub_satisfied("a", satisfied=True)
    stub_evaluators["b"] = _stub_satisfied("b", satisfied=False)
    spec_path = _write_goal_spec(
        tmp_path / "spec.json",
        progress_metric="all_AC_satisfied",  # progress collapses to 0 either way
        criteria=[
            {"ac_id": "A", "predicate": "a()"},
            {"ac_id": "B", "predicate": "b()"},
        ],
    )
    spec = evaluate_goal_progress.load_goal_spec(spec_path)
    t1 = evaluate_goal_progress.build_tick(spec, history=[], stall_window=3)

    # Flip AC1 false then back to true — progress stays 0 each tick but per-AC
    # boolean is not flat across the window.
    stub_evaluators["a"] = _stub_satisfied("a", satisfied=False)
    t2 = evaluate_goal_progress.build_tick(spec, history=[t1], stall_window=3)
    stub_evaluators["a"] = _stub_satisfied("a", satisfied=True)
    t3 = evaluate_goal_progress.build_tick(spec, history=[t1, t2], stall_window=3)

    assert "stalled" not in t3

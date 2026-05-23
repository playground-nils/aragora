"""Tests for AGT-04 SD-3: JsonlStakeableClaimStore — JSONL-backed persistence.

No network, no live queue, no GitHub token required.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aragora.prediction.stakeable_claim import (
    QuestionType,
    ResolutionStatus,
    StakeableClaim,
)
from aragora.prediction.stakeable_claim_store import JsonlStakeableClaimStore

_FLAG = "ARAGORA_PREDICTION_MARKETS_ENABLED"


def _claim(claim_id: str, *, days: int = 30) -> StakeableClaim:
    return StakeableClaim(
        claim_id=claim_id,
        question=f"Will {claim_id} happen?",
        question_type=QuestionType.PR_MERGE,
        target_ref="org/repo#1",
        expiry=(datetime.now(tz=UTC) + timedelta(days=days)).isoformat(),
    )


def _store(path: Path) -> JsonlStakeableClaimStore:
    return JsonlStakeableClaimStore(path)


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> JsonlStakeableClaimStore:
    monkeypatch.setenv(_FLAG, "1")
    return _store(tmp_path / "claims.jsonl")


# ---------------------------------------------------------------------------
# Feature gate
# ---------------------------------------------------------------------------


def test_gate_off_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_FLAG, raising=False)
    with pytest.raises(RuntimeError, match="disabled"):
        _store(tmp_path / "c.jsonl").add(_claim("x"))


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_add_and_get(store: JsonlStakeableClaimStore) -> None:
    c = _claim("c1")
    store.add(c)
    assert store.get("c1").question == c.question
    assert len(store) == 1


def test_duplicate_add_raises(store: JsonlStakeableClaimStore) -> None:
    store.add(_claim("c1"))
    with pytest.raises(ValueError, match="already exists"):
        store.add(_claim("c1"))


# ---------------------------------------------------------------------------
# Persistence — the key property of this slice
# ---------------------------------------------------------------------------


def test_add_survives_reload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_FLAG, "1")
    p = tmp_path / "c.jsonl"
    _store(p).add(_claim("c1"))
    assert _store(p).get("c1").question == "Will c1 happen?"


def test_record_position_survives_reload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_FLAG, "1")
    p = tmp_path / "c.jsonl"
    s = _store(p)
    s.add(_claim("c1"))
    s.record_position("c1", "agent-a", 0.75)
    assert _store(p).get("c1").positions["agent-a"] == pytest.approx(0.75)


def test_resolve_survives_reload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_FLAG, "1")
    p = tmp_path / "c.jsonl"
    s = _store(p)
    s.add(_claim("c1"))
    s.resolve("c1", value=True, evidence="merged")
    f = _store(p).get("c1")
    assert f.resolution_status == ResolutionStatus.RESOLVED_YES
    assert f.resolution_evidence == "merged"


def test_expire_stale_survives_reload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_FLAG, "1")
    p = tmp_path / "c.jsonl"
    s = _store(p)
    s.add(_claim("stale", days=-1))
    assert "stale" in s.expire_stale()
    assert _store(p).get("stale").resolution_status == ResolutionStatus.EXPIRED


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def test_list_open_excludes_resolved(store: JsonlStakeableClaimStore) -> None:
    store.add(_claim("c1"))
    store.add(_claim("c2"))
    store.resolve("c1", value=False)
    open_ids = [c.claim_id for c in store.list_open()]
    assert open_ids == ["c2"]


def test_list_by_type(store: JsonlStakeableClaimStore) -> None:
    store.add(_claim("pr1"))
    ic = StakeableClaim(
        "ic1",
        "Issue?",
        QuestionType.ISSUE_CLOSE,
        "org/repo#2",
        (datetime.now(tz=UTC) + timedelta(days=7)).isoformat(),
    )
    store.add(ic)
    assert len(store.list_by_type(QuestionType.ISSUE_CLOSE)) == 1
    assert len(store.list_by_type(QuestionType.PR_MERGE)) == 1

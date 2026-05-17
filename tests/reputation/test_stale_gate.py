"""Tests for aragora.reputation.stale_gate (AGT-05 / #6066).

28 tests covering flag gating, bucket classification, edge cases, and
StaleGateResult helpers.  No live network calls; no queue mutations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from aragora.reputation.stale_gate import StaleGateResult, apply_stale_gate, stale_policy_enabled
from aragora.reputation.stale_policy import StalePolicy


@dataclass
class _Pred:
    market_id: str
    agent_id: str
    predicted_at: datetime
    predicted_probability: float = 0.6


_NOW = datetime(2026, 5, 17, 12, 0, 0, tzinfo=UTC)
_POLICY = StalePolicy(fresh_days=7.0, stale_days=30.0, hard_limit_days=180.0)


def _gate(*preds: _Pred) -> StaleGateResult:
    return apply_stale_gate(list(preds), policy=_POLICY, now=_NOW)


def _pred(days_ago: float, mid: str = "m1") -> _Pred:
    return _Pred(mid, "alice", _NOW - timedelta(days=days_ago))


# ---------------------------------------------------------------------------
# Flag gating
# ---------------------------------------------------------------------------


class TestFlagGating:
    def test_disabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ARAGORA_STALE_POLICY_ENABLED", raising=False)
        assert stale_policy_enabled() is False

    @pytest.mark.parametrize("val", ["1", "true", "yes", "on"])
    def test_truthy_values_enable(self, monkeypatch: pytest.MonkeyPatch, val: str) -> None:
        monkeypatch.setenv("ARAGORA_STALE_POLICY_ENABLED", val)
        assert stale_policy_enabled() is True

    def test_flag_off_all_in_fresh(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ARAGORA_STALE_POLICY_ENABLED", raising=False)
        preds = [_pred(3), _pred(200)]
        result = apply_stale_gate(preds, policy=_POLICY, now=_NOW)
        assert len(result.fresh) == 2 and result.stale == [] and result.expired == []

    def test_flag_off_decisions_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ARAGORA_STALE_POLICY_ENABLED", raising=False)
        assert apply_stale_gate([_pred(5)], policy=_POLICY, now=_NOW).decisions == []


# ---------------------------------------------------------------------------
# Bucket classification (flag ON)
# ---------------------------------------------------------------------------


class TestClassification:
    @pytest.fixture(autouse=True)
    def _enable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ARAGORA_STALE_POLICY_ENABLED", "1")

    def test_fresh_under_7_days(self) -> None:
        result = _gate(_pred(3))
        assert len(result.fresh) == 1 and result.stale == [] and result.expired == []

    def test_stale_at_or_above_30_days(self) -> None:
        result = _gate(_pred(35))
        assert result.fresh == [] and len(result.stale) == 1 and result.expired == []

    def test_expired_past_180_days(self) -> None:
        result = _gate(_pred(181))
        assert result.fresh == [] and result.stale == [] and len(result.expired) == 1

    def test_prediction_at_stale_boundary(self) -> None:
        assert len(_gate(_pred(30.0)).stale) == 1

    def test_mixed_batch(self) -> None:
        f = _pred(3, "fresh")
        s = _pred(60, "stale")
        e = _pred(200, "expired")
        r = apply_stale_gate([f, s, e], policy=_POLICY, now=_NOW)
        assert r.fresh[0].market_id == "fresh"
        assert r.stale[0].market_id == "stale"
        assert r.expired[0].market_id == "expired"

    def test_future_dated_is_fresh(self) -> None:
        pred = _Pred("m", "a", _NOW + timedelta(days=10))
        assert len(apply_stale_gate([pred], policy=_POLICY, now=_NOW).fresh) == 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    @pytest.fixture(autouse=True)
    def _enable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ARAGORA_STALE_POLICY_ENABLED", "1")

    def test_empty_input(self) -> None:
        r = apply_stale_gate([], policy=_POLICY, now=_NOW)
        assert r.fresh == r.stale == r.expired == r.decisions == []

    def test_bucket_counts_sum_to_input(self) -> None:
        preds = [_pred(2), _pred(45), _pred(190), _pred(1)]
        r = apply_stale_gate(preds, policy=_POLICY, now=_NOW)
        assert r.total == len(preds) and len(r.decisions) == len(preds)

    def test_custom_policy_respected(self) -> None:
        tight = StalePolicy(fresh_days=1.0, stale_days=2.0, hard_limit_days=5.0)
        pred = _Pred("m", "a", _NOW - timedelta(hours=50))  # 2.08 d >= stale_days=2.0
        assert len(apply_stale_gate([pred], policy=tight, now=_NOW).stale) == 1

    def test_naive_datetime_treated_as_utc(self) -> None:
        pred = _Pred("m", "a", datetime(2026, 5, 16, 12, 0, 0))  # no tzinfo
        assert apply_stale_gate([pred], policy=_POLICY, now=_NOW).total == 1


# ---------------------------------------------------------------------------
# StaleGateResult helpers
# ---------------------------------------------------------------------------


class TestStaleGateResult:
    @pytest.fixture(autouse=True)
    def _enable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ARAGORA_STALE_POLICY_ENABLED", "1")

    def test_summary_keys(self) -> None:
        s = _gate(_pred(3)).summary()
        assert {"fresh", "stale", "expired", "total", "policy_fingerprint"} <= set(s)

    def test_summary_counts(self) -> None:
        preds = [_pred(2), _pred(50)]
        s = apply_stale_gate(preds, policy=_POLICY, now=_NOW).summary()
        assert s["fresh"] == 1 and s["stale"] == 1 and s["total"] == 2

    def test_policy_fingerprint_format(self) -> None:
        r = _gate(_pred(3))
        assert r.policy_fingerprint.startswith("sp_") and len(r.policy_fingerprint) > 4

    def test_decisions_parallel_to_input(self) -> None:
        preds = [_pred(2), _pred(60)]
        r = apply_stale_gate(preds, policy=_POLICY, now=_NOW)
        assert len(r.decisions) == 2
        assert r.decisions[0].bucket == "fresh" and r.decisions[1].bucket == "stale"

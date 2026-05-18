"""Tests for aragona.reputation.dispute_window (AGT-05 #6066 SD-4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aragora.reputation.dispute_window import (
    DEFAULT_WINDOW_HOURS,
    DisputeWindowGate,
    DisputeWindowGateDisabledError,
    DisputeWindowPolicy,
    UnknownDomainError,
    dispute_window_enabled,
)
from aragora.reputation.types import (
    DOMAIN_CODE_PR,
    DOMAIN_CRUX_RESOLUTION,
    DOMAIN_KM_CONTRIBUTION,
    DOMAIN_PREDICTION_MARKET,
    KNOWN_DOMAINS,
)

_FLAG = "ARAGORA_DISPUTE_WINDOW_ENABLED"
_BASE = datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC)
_RESOLVED = "2026-05-01T00:00:00Z"
_CLAIM = "clm_test_abc123"


def _t(hours: float) -> str:
    return (_BASE + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- Flag gating ---


def test_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_FLAG, raising=False)
    assert not dispute_window_enabled()


@pytest.mark.parametrize("val", ["1", "true", "yes", "on"])
def test_truthy_values_enable(monkeypatch: pytest.MonkeyPatch, val: str) -> None:
    monkeypatch.setenv(_FLAG, val)
    assert dispute_window_enabled()


def test_check_raises_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_FLAG, raising=False)
    with pytest.raises(DisputeWindowGateDisabledError, match=_FLAG):
        DisputeWindowGate().check(
            claim_id=_CLAIM, domain=DOMAIN_PREDICTION_MARKET,
            resolved_at=_RESOLVED, filed_at=_t(12),
        )


# --- Policy ---


def test_default_policy_covers_all_known_domains() -> None:
    policy = DisputeWindowPolicy.default()
    for d in KNOWN_DOMAINS:
        assert policy.window_for(d) > 0


def test_custom_policy_overrides_and_falls_back() -> None:
    policy = DisputeWindowPolicy(windows_hours={DOMAIN_PREDICTION_MARKET: 12.0})
    assert policy.window_for(DOMAIN_PREDICTION_MARKET) == 12.0
    assert policy.window_for(DOMAIN_CODE_PR) == DEFAULT_WINDOW_HOURS[DOMAIN_CODE_PR]


def test_unknown_domain_raises() -> None:
    with pytest.raises(UnknownDomainError, match="unknown domain"):
        DisputeWindowPolicy.default().window_for("not_a_domain")


# --- Gate checks ---


@pytest.fixture
def gate(monkeypatch: pytest.MonkeyPatch) -> DisputeWindowGate:
    monkeypatch.setenv(_FLAG, "1")
    return DisputeWindowGate()


@pytest.mark.parametrize("domain,filed_h", [
    (DOMAIN_PREDICTION_MARKET, 36),
    (DOMAIN_PREDICTION_MARKET, 72),   # boundary inclusive
    (DOMAIN_CODE_PR, 10),
    (DOMAIN_CRUX_RESOLUTION, 1),
])
def test_within_window(gate: DisputeWindowGate, domain: str, filed_h: float) -> None:
    r = gate.check(claim_id=_CLAIM, domain=domain, resolved_at=_RESOLVED, filed_at=_t(filed_h))
    assert r.within_window is True


@pytest.mark.parametrize("domain,filed_h", [
    (DOMAIN_PREDICTION_MARKET, 73),
    (DOMAIN_CODE_PR, 25),
    (DOMAIN_KM_CONTRIBUTION, 25),
])
def test_outside_window(gate: DisputeWindowGate, domain: str, filed_h: float) -> None:
    r = gate.check(claim_id=_CLAIM, domain=domain, resolved_at=_RESOLVED, filed_at=_t(filed_h))
    assert r.within_window is False


def test_negative_elapsed_is_within(gate: DisputeWindowGate) -> None:
    r = gate.check(
        claim_id=_CLAIM, domain=DOMAIN_PREDICTION_MARKET,
        resolved_at=_RESOLVED, filed_at=_t(-1),
    )
    assert r.within_window is True and r.elapsed_hours < 0


def test_record_fields_and_to_dict(gate: DisputeWindowGate) -> None:
    r = gate.check(
        claim_id="clm_xyz", domain=DOMAIN_CODE_PR,
        resolved_at=_RESOLVED, filed_at=_t(10), evidence={"src": "oracle"},
    )
    assert r.claim_id == "clm_xyz"
    assert abs(r.elapsed_hours - 10.0) < 0.01
    assert r.evidence["src"] == "oracle"
    assert set(r.to_dict()) == {
        "claim_id", "domain", "resolved_at", "filed_at",
        "window_hours", "elapsed_hours", "within_window", "evidence",
    }


def test_custom_narrow_window_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_FLAG, "1")
    gate = DisputeWindowGate(DisputeWindowPolicy({DOMAIN_PREDICTION_MARKET: 1.0}))
    assert not gate.check(
        claim_id=_CLAIM, domain=DOMAIN_PREDICTION_MARKET,
        resolved_at=_RESOLVED, filed_at=_t(2),
    ).within_window


def test_unknown_domain_through_gate(gate: DisputeWindowGate) -> None:
    with pytest.raises(UnknownDomainError):
        gate.check(claim_id=_CLAIM, domain="bad_domain",
                   resolved_at=_RESOLVED, filed_at=_t(1))


def test_malformed_timestamp_raises(gate: DisputeWindowGate) -> None:
    with pytest.raises(ValueError, match="cannot parse"):
        gate.check(claim_id=_CLAIM, domain=DOMAIN_PREDICTION_MARKET,
                   resolved_at="not-a-date", filed_at=_t(1))

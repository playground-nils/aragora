"""Tests for the AGT-02 A2A reputation read endpoint (issue #6063 sub-deliverable 5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aragora.protocols.a2a.reputation import (
    AGENT_REPUTATION_SCHEMA_VERSION,
    AgentReputationView,
    DomainReputationSlice,
    ReputationEndpointError,
    read_agent_reputation,
    read_all_agents,
    reputation_endpoint_enabled,
)
from aragora.reputation.store import ReputationStore
from aragora.reputation.types import DOMAIN_DEBATE_POSITION, DOMAIN_PREDICTION_MARKET, ReputationDelta

_FLAG = "ARAGORA_A2A_REPUTATION_ENABLED"


def _delta(
    *,
    agent_id: str,
    domain: str,
    delta: float,
    delta_id: str = "d1",
    applied_at: str | None = None,
    decay_half_life_days: float | None = None,
) -> ReputationDelta:
    return ReputationDelta(
        delta_id=delta_id,
        agent_id=agent_id,
        domain=domain,
        claim_id="cl1",
        resolution_id="res1",
        delta=delta,
        scoring_rule="binary",
        applied_at=applied_at or datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        decay_half_life_days=decay_half_life_days,
        reason={},
    )


@pytest.fixture()
def store() -> ReputationStore:
    return ReputationStore()


@pytest.fixture()
def enabled_store(store: ReputationStore, monkeypatch: pytest.MonkeyPatch) -> ReputationStore:
    monkeypatch.setenv(_FLAG, "1")
    return store


# --- Feature flag ---


def test_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_FLAG, raising=False)
    assert reputation_endpoint_enabled() is False


@pytest.mark.parametrize("v", ["1", "true", "yes", "on"])
def test_enabled_truthy(monkeypatch: pytest.MonkeyPatch, v: str) -> None:
    monkeypatch.setenv(_FLAG, v)
    assert reputation_endpoint_enabled() is True


def test_read_blocked_when_disabled(
    store: ReputationStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(_FLAG, raising=False)
    with pytest.raises(ReputationEndpointError, match=_FLAG):
        read_agent_reputation("agent-1", store)


def test_read_all_blocked_when_disabled(
    store: ReputationStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(_FLAG, raising=False)
    with pytest.raises(ReputationEndpointError, match=_FLAG):
        read_all_agents(store)


# --- read_agent_reputation ---


def test_unknown_agent_returns_zero(enabled_store: ReputationStore) -> None:
    view = read_agent_reputation("nobody", enabled_store)
    assert view.agent_id == "nobody"
    assert view.overall_score == 0.0
    assert view.delta_count == 0
    assert view.domains == ()
    assert view.schema_version == AGENT_REPUTATION_SCHEMA_VERSION


def test_single_domain_score(enabled_store: ReputationStore) -> None:
    enabled_store.record_delta(
        _delta(agent_id="a1", domain=DOMAIN_PREDICTION_MARKET, delta=0.8, delta_id="d1")
    )
    view = read_agent_reputation("a1", enabled_store)
    assert view.overall_score == pytest.approx(0.8)
    assert view.delta_count == 1
    assert len(view.domains) == 1
    assert view.domains[0].domain == DOMAIN_PREDICTION_MARKET
    assert view.domains[0].score == pytest.approx(0.8)
    assert view.domains[0].delta_count == 1


def test_multi_domain_slices(enabled_store: ReputationStore) -> None:
    enabled_store.record_delta(
        _delta(agent_id="a1", domain=DOMAIN_PREDICTION_MARKET, delta=1.0, delta_id="d1")
    )
    enabled_store.record_delta(
        _delta(agent_id="a1", domain=DOMAIN_DEBATE_POSITION, delta=0.5, delta_id="d2")
    )
    view = read_agent_reputation("a1", enabled_store)
    assert view.overall_score == pytest.approx(1.5)
    assert view.delta_count == 2
    domain_names = {s.domain for s in view.domains}
    assert domain_names == {DOMAIN_PREDICTION_MARKET, DOMAIN_DEBATE_POSITION}
    # Domains are sorted alphabetically
    assert view.domains == tuple(sorted(view.domains, key=lambda s: s.domain))


def test_schema_version_present(enabled_store: ReputationStore) -> None:
    view = read_agent_reputation("ax", enabled_store)
    assert view.schema_version == AGENT_REPUTATION_SCHEMA_VERSION


def test_queried_at_is_utc(enabled_store: ReputationStore) -> None:
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=UTC)
    view = read_agent_reputation("ax", enabled_store, now=now)
    assert "2026-05-17" in view.queried_at


def test_to_dict_shape(enabled_store: ReputationStore) -> None:
    enabled_store.record_delta(
        _delta(agent_id="a1", domain=DOMAIN_PREDICTION_MARKET, delta=2.0, delta_id="d1")
    )
    d = read_agent_reputation("a1", enabled_store).to_dict()
    assert set(d) >= {"schema_version", "agent_id", "overall_score", "delta_count", "domains", "queried_at"}
    assert d["domains"][0]["domain"] == DOMAIN_PREDICTION_MARKET


def test_decay_reduces_score(enabled_store: ReputationStore) -> None:
    old_time = (datetime.now(tz=UTC) - timedelta(days=30)).isoformat().replace("+00:00", "Z")
    enabled_store.record_delta(
        _delta(
            agent_id="a1",
            domain=DOMAIN_PREDICTION_MARKET,
            delta=1.0,
            delta_id="d1",
            applied_at=old_time,
            decay_half_life_days=7.0,
        )
    )
    decayed = read_agent_reputation("a1", enabled_store, apply_decay=True).overall_score
    raw = read_agent_reputation("a1", enabled_store, apply_decay=False).overall_score
    assert raw == pytest.approx(1.0)
    assert decayed < raw


def test_most_recent_delta_at_populated(enabled_store: ReputationStore) -> None:
    ts = "2026-05-01T10:00:00Z"
    enabled_store.record_delta(
        _delta(agent_id="a1", domain=DOMAIN_PREDICTION_MARKET, delta=1.0, delta_id="d1", applied_at=ts)
    )
    view = read_agent_reputation("a1", enabled_store)
    assert view.domains[0].most_recent_delta_at == ts


# --- read_all_agents ---


def test_read_all_agents_empty(enabled_store: ReputationStore) -> None:
    assert read_all_agents(enabled_store) == []


def test_read_all_agents_returns_all(enabled_store: ReputationStore) -> None:
    enabled_store.record_delta(_delta(agent_id="a1", domain=DOMAIN_PREDICTION_MARKET, delta=1.0, delta_id="d1"))
    enabled_store.record_delta(_delta(agent_id="a2", domain=DOMAIN_PREDICTION_MARKET, delta=2.0, delta_id="d2"))
    views = read_all_agents(enabled_store)
    agent_ids = {v.agent_id for v in views}
    assert agent_ids == {"a1", "a2"}


def test_read_all_agents_sorted_desc_by_score(enabled_store: ReputationStore) -> None:
    enabled_store.record_delta(_delta(agent_id="low", domain=DOMAIN_PREDICTION_MARKET, delta=0.1, delta_id="d1"))
    enabled_store.record_delta(_delta(agent_id="high", domain=DOMAIN_PREDICTION_MARKET, delta=5.0, delta_id="d2"))
    views = read_all_agents(enabled_store)
    assert views[0].agent_id == "high"
    assert views[1].agent_id == "low"


def test_read_all_agents_stable_sort_on_tie(enabled_store: ReputationStore) -> None:
    for aid in ["beta", "alpha"]:
        enabled_store.record_delta(
            _delta(agent_id=aid, domain=DOMAIN_PREDICTION_MARKET, delta=1.0, delta_id=f"d-{aid}")
        )
    views = read_all_agents(enabled_store)
    # Equal scores → alphabetical by agent_id
    assert views[0].agent_id == "alpha"
    assert views[1].agent_id == "beta"


def test_domain_slice_to_dict(enabled_store: ReputationStore) -> None:
    s = DomainReputationSlice(
        domain=DOMAIN_PREDICTION_MARKET,
        score=1.5,
        delta_count=3,
        most_recent_delta_at="2026-05-01T10:00:00Z",
    )
    d = s.to_dict()
    assert d["domain"] == DOMAIN_PREDICTION_MARKET
    assert d["score"] == pytest.approx(1.5)
    assert d["delta_count"] == 3
    assert d["most_recent_delta_at"] == "2026-05-01T10:00:00Z"

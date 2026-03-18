"""Tests for TeamSelector blockchain staking reputation scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from aragora.debate.team_selector import TeamSelectionConfig, TeamSelector


@dataclass
class _FakeSlashEvent:
    reason: str = "test"
    amount_slashed_wei: int = 100
    timestamp: float = 0.0
    evidence_hash: str = "abc"


@dataclass
class _FakeStakePosition:
    agent_id: str
    amount_wei: int = 1000
    effective_stake: int = 1000
    slashing_events: list[Any] = field(default_factory=list)


class _FakeAgent:
    def __init__(self, name: str):
        self.name = name
        self.role = "proposer"
        self.model = "test"


@pytest.fixture
def staking_registry():
    reg = MagicMock()
    reg.get_stake = AsyncMock(return_value=_FakeStakePosition("a", 1000, 1000))
    return reg


@pytest.fixture
def selector_with_staking(staking_registry):
    config = TeamSelectionConfig(
        enable_staking_reputation=True,
        staking_reputation_weight=0.15,
    )
    return TeamSelector(config=config, staking_registry=staking_registry)


@pytest.fixture
def selector_without_staking():
    config = TeamSelectionConfig(enable_staking_reputation=False)
    return TeamSelector(config=config)


class TestStakingReputationScoring:
    def test_disabled_by_default(self, selector_without_staking):
        """Staking reputation should be disabled by default."""
        assert not selector_without_staking.config.enable_staking_reputation
        agent = _FakeAgent("a")
        score = selector_without_staking._compute_staking_reputation_score(agent)
        assert score == 0.5  # neutral when no registry

    def test_healthy_stake_scores_high(self, selector_with_staking, staking_registry):
        """Agent with full effective stake (no slashing) should score near 1.0."""
        staking_registry.get_stake = AsyncMock(return_value=_FakeStakePosition("a", 1000, 1000))
        score = selector_with_staking._compute_staking_reputation_score(_FakeAgent("a"))
        # health=1.0*0.7 + slash_penalty=1.0*0.3 = 1.0
        assert score == pytest.approx(1.0, abs=0.01)

    def test_slashed_agent_scores_lower(self, selector_with_staking, staking_registry):
        """Agent with slashing events should score lower than unslashed."""
        slashes = [_FakeSlashEvent() for _ in range(5)]
        staking_registry.get_stake = AsyncMock(
            return_value=_FakeStakePosition("a", 1000, 500, slashes)
        )
        score = selector_with_staking._compute_staking_reputation_score(_FakeAgent("a"))
        # health=500/1000*0.7=0.35, slash_penalty=(1-5/10)*0.3=0.15, total=0.5
        assert score == pytest.approx(0.5, abs=0.01)

    def test_unstaked_agent_neutral(self, selector_with_staking, staking_registry):
        """Agent with no stake should get neutral score (0.5)."""
        staking_registry.get_stake = AsyncMock(return_value=None)
        score = selector_with_staking._compute_staking_reputation_score(_FakeAgent("b"))
        assert score == 0.5

    def test_staking_score_in_breakdown(self, selector_with_staking, staking_registry):
        """Breakdown dict should include staking_reputation key."""
        staking_registry.get_stake = AsyncMock(return_value=_FakeStakePosition("a", 1000, 1000))
        agent = _FakeAgent("a")
        breakdown: dict[str, float] = {}
        selector_with_staking._compute_score(agent, domain="test", breakdown=breakdown)
        assert "staking_reputation" in breakdown

    def test_staking_score_not_in_breakdown_when_disabled(self, selector_without_staking):
        """When disabled, breakdown should have staking_reputation=0."""
        agent = _FakeAgent("a")
        breakdown: dict[str, float] = {}
        selector_without_staking._compute_score(agent, domain="test", breakdown=breakdown)
        assert breakdown.get("staking_reputation", 0.0) == 0.0

"""Tests for PostDebateCoordinator staking rewards/penalties integration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aragora.debate.post_debate_coordinator import PostDebateConfig, PostDebateCoordinator


@dataclass
class _FakeStakePosition:
    agent_id: str
    amount_wei: int = 1000
    effective_stake: int = 1000
    slashing_events: list[Any] = field(default_factory=list)


class _FakeDebateResult:
    def __init__(self, hollow: bool = False, metadata: dict | None = None):
        self.metadata = metadata or {}
        if hollow:
            self.metadata["hollow_consensus_detected"] = True
        self.decision = "test_decision"
        self.summary = "test_summary"


class _FakeAgent:
    def __init__(self, name: str):
        self.name = name


@pytest.fixture
def staking_config():
    return PostDebateConfig(
        enable_staking=True,
        staking_reward_scale=1.0,
        staking_slash_on_hollow_consensus=True,
    )


@pytest.fixture
def coordinator(staking_config):
    return PostDebateCoordinator(config=staking_config)


class TestStakingSlashCallSignature:
    """Verify slash() is called with correct positional args: (agent_id, amount_wei, reason, evidence)."""

    def test_slash_call_signature_correct(self, coordinator):
        """Slash must pass (agent_id, amount_wei, reason, evidence_bytes) -- not kwargs."""
        mock_registry = MagicMock()
        mock_registry.get_stake = AsyncMock(return_value=_FakeStakePosition("agent_1", 1000, 1000))
        mock_registry.slash = AsyncMock()

        with patch(
            "aragora.blockchain.contracts.staking.StakingRegistry",
            return_value=mock_registry,
        ):
            result = coordinator._step_staking_rewards(
                debate_id="d1",
                debate_result=_FakeDebateResult(hollow=True),
                agents=[_FakeAgent("agent_1")],
                confidence=0.5,
            )

        mock_registry.slash.assert_called_once()
        call_args = mock_registry.slash.call_args
        # Positional args: agent_id, amount_wei, reason, evidence
        assert call_args[0][0] == "agent_1"
        assert isinstance(call_args[0][1], int)
        assert call_args[0][1] > 0
        assert call_args[0][2] == "hollow_consensus"
        assert isinstance(call_args[0][3], bytes)
        assert any(s["agent"] == "agent_1" for s in result["slashed"])

    def test_slash_amount_is_10_percent_of_effective_stake(self, coordinator):
        """Slash amount = 10% of effective_stake * staking_reward_scale."""
        mock_registry = MagicMock()
        mock_registry.get_stake = AsyncMock(return_value=_FakeStakePosition("a", 2000, 2000))
        mock_registry.slash = AsyncMock()

        with patch(
            "aragora.blockchain.contracts.staking.StakingRegistry",
            return_value=mock_registry,
        ):
            coordinator._step_staking_rewards(
                debate_id="d1",
                debate_result=_FakeDebateResult(hollow=True),
                agents=[_FakeAgent("a")],
                confidence=0.3,
            )

        expected_amount = int(2000 * 0.10 * 1.0)  # 200
        actual_amount = mock_registry.slash.call_args[0][1]
        assert actual_amount == expected_amount

    def test_slash_evidence_contains_debate_metadata(self, coordinator):
        """Evidence bytes must include debate_id, confidence, hollow_consensus flag."""
        mock_registry = MagicMock()
        mock_registry.get_stake = AsyncMock(return_value=_FakeStakePosition("a", 1000, 1000))
        mock_registry.slash = AsyncMock()

        with patch(
            "aragora.blockchain.contracts.staking.StakingRegistry",
            return_value=mock_registry,
        ):
            coordinator._step_staking_rewards(
                debate_id="debate_42",
                debate_result=_FakeDebateResult(hollow=True),
                agents=[_FakeAgent("a")],
                confidence=0.6,
            )

        evidence_bytes = mock_registry.slash.call_args[0][3]
        evidence = json.loads(evidence_bytes)
        assert evidence["debate_id"] == "debate_42"
        assert evidence["confidence"] == 0.6
        assert evidence["hollow_consensus"] is True

    def test_slash_skipped_when_no_stake(self, coordinator):
        """Agent without stake should be skipped, not cause an error."""
        mock_registry = MagicMock()
        mock_registry.get_stake = AsyncMock(return_value=None)
        mock_registry.slash = AsyncMock()

        with patch(
            "aragora.blockchain.contracts.staking.StakingRegistry",
            return_value=mock_registry,
        ):
            result = coordinator._step_staking_rewards(
                debate_id="d1",
                debate_result=_FakeDebateResult(hollow=True),
                agents=[_FakeAgent("unstaked_agent")],
                confidence=0.5,
            )

        mock_registry.slash.assert_not_called()
        assert not any(s.get("agent") == "unstaked_agent" for s in result["slashed"])


class TestStakingRewardCallSignature:
    """Verify reward() is called with correct args: (agent_id, amount_wei, reason)."""

    def test_reward_call_signature_correct(self, coordinator):
        """Reward must pass (agent_id, amount_wei, reason) -- the 'reason' arg was missing."""
        mock_registry = MagicMock()
        mock_registry.reward = AsyncMock()

        with patch(
            "aragora.blockchain.contracts.staking.StakingRegistry",
            return_value=mock_registry,
        ):
            result = coordinator._step_staking_rewards(
                debate_id="d1",
                debate_result=_FakeDebateResult(hollow=False),
                agents=[_FakeAgent("good_agent")],
                confidence=0.9,
            )

        mock_registry.reward.assert_called_once()
        call_args = mock_registry.reward.call_args
        assert call_args[0][0] == "good_agent"
        assert isinstance(call_args[0][1], int)
        assert call_args[0][1] > 0
        assert isinstance(call_args[0][2], str)  # reason string
        assert any(r["agent"] == "good_agent" for r in result["rewarded"])

    def test_reward_not_given_below_threshold(self, coordinator):
        """Confidence below 0.8 should not trigger reward."""
        mock_registry = MagicMock()
        mock_registry.reward = AsyncMock()

        with patch(
            "aragora.blockchain.contracts.staking.StakingRegistry",
            return_value=mock_registry,
        ):
            result = coordinator._step_staking_rewards(
                debate_id="d1",
                debate_result=_FakeDebateResult(hollow=False),
                agents=[_FakeAgent("agent_1")],
                confidence=0.7,
            )

        mock_registry.reward.assert_not_called()
        assert result["rewarded"] == []


class TestReceiptAnchorIntegration:
    """Verify ReceiptAnchor is called before slashing for evidence traceability."""

    def test_evidence_anchored_before_slash(self, coordinator):
        """ReceiptAnchor.anchor_receipt should be called before slash."""
        mock_registry = MagicMock()
        mock_registry.get_stake = AsyncMock(return_value=_FakeStakePosition("a", 1000, 1000))
        mock_registry.slash = AsyncMock()
        mock_anchor = MagicMock()
        mock_anchor.anchor_receipt = AsyncMock(return_value="local:abc123")

        with (
            patch(
                "aragora.blockchain.contracts.staking.StakingRegistry",
                return_value=mock_registry,
            ),
            patch(
                "aragora.blockchain.receipt_anchor.ReceiptAnchor",
                return_value=mock_anchor,
            ),
        ):
            result = coordinator._step_staking_rewards(
                debate_id="d1",
                debate_result=_FakeDebateResult(hollow=True),
                agents=[_FakeAgent("a")],
                confidence=0.5,
            )

        mock_anchor.anchor_receipt.assert_called_once()
        mock_registry.slash.assert_called_once()
        # Slashed entry should include evidence anchor ID
        assert result["slashed"][0]["evidence_anchor"] == "local:abc123"

    def test_anchor_failure_does_not_block_slash(self, coordinator):
        """If anchoring fails, slash should still proceed."""
        mock_registry = MagicMock()
        mock_registry.get_stake = AsyncMock(return_value=_FakeStakePosition("a", 1000, 1000))
        mock_registry.slash = AsyncMock()
        mock_anchor = MagicMock()
        mock_anchor.anchor_receipt = AsyncMock(side_effect=RuntimeError("anchor broken"))

        with (
            patch(
                "aragora.blockchain.contracts.staking.StakingRegistry",
                return_value=mock_registry,
            ),
            patch(
                "aragora.blockchain.receipt_anchor.ReceiptAnchor",
                return_value=mock_anchor,
            ),
        ):
            result = coordinator._step_staking_rewards(
                debate_id="d1",
                debate_result=_FakeDebateResult(hollow=True),
                agents=[_FakeAgent("a")],
                confidence=0.5,
            )

        # Slash still proceeds even when anchoring fails
        mock_registry.slash.assert_called_once()
        assert any(s["agent"] == "a" for s in result["slashed"])


class TestStakingAsyncPattern:
    """Verify deprecated asyncio.get_event_loop pattern is not used."""

    def test_no_deprecated_event_loop_usage(self):
        """The method should use _run_async_callable, not asyncio.get_event_loop()."""
        import inspect

        source = inspect.getsource(PostDebateCoordinator._step_staking_rewards)
        assert "get_event_loop" not in source
        assert "run_until_complete" not in source


class TestStakingHollowConsensusDetection:
    """Verify hollow consensus is correctly detected from debate result metadata."""

    def test_hollow_consensus_triggers_slash(self, coordinator):
        """Metadata with hollow_consensus_detected=True should trigger slashing."""
        mock_registry = MagicMock()
        mock_registry.get_stake = AsyncMock(return_value=_FakeStakePosition("a", 500, 500))
        mock_registry.slash = AsyncMock()

        with patch(
            "aragora.blockchain.contracts.staking.StakingRegistry",
            return_value=mock_registry,
        ):
            result = coordinator._step_staking_rewards(
                debate_id="d1",
                debate_result=_FakeDebateResult(hollow=True),
                agents=[_FakeAgent("a")],
                confidence=0.9,
            )

        assert any(s["agent"] == "a" for s in result["slashed"])
        assert result["rewarded"] == []  # slash takes precedence over reward

    def test_no_hollow_and_high_confidence_rewards(self, coordinator):
        """Non-hollow debate with high confidence should reward all agents."""
        mock_registry = MagicMock()
        mock_registry.reward = AsyncMock()

        with patch(
            "aragora.blockchain.contracts.staking.StakingRegistry",
            return_value=mock_registry,
        ):
            result = coordinator._step_staking_rewards(
                debate_id="d1",
                debate_result=_FakeDebateResult(hollow=False),
                agents=[_FakeAgent("a"), _FakeAgent("b")],
                confidence=0.85,
            )

        assert len(result["rewarded"]) == 2
        assert mock_registry.reward.call_count == 2

    def test_staking_disabled_returns_none(self):
        """When enable_staking=False, _step_staking_rewards should still work but the run() method gates it."""
        config = PostDebateConfig(enable_staking=False)
        coordinator = PostDebateCoordinator(config=config)
        # The method itself doesn't check the flag -- run() does
        # Verify it's importable and callable even when disabled
        mock_registry = MagicMock()
        mock_registry.reward = AsyncMock()
        with patch(
            "aragora.blockchain.contracts.staking.StakingRegistry",
            return_value=mock_registry,
        ):
            result = coordinator._step_staking_rewards(
                debate_id="d1",
                debate_result=_FakeDebateResult(hollow=False),
                agents=[],
                confidence=0.5,
            )
        assert result is not None
        assert result["rewarded"] == []
        assert result["slashed"] == []

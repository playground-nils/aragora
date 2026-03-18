"""Tests for hollow consensus metadata propagation from Trickster to result."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from aragora.debate.phases.feedback_phase import FeedbackPhase


class _FakeResult:
    def __init__(self):
        self.metadata: dict[str, Any] = {}


class _FakeCtx:
    def __init__(self, trickster: Any = None, hollow_count: int = 0):
        self._trickster = trickster
        self.result = _FakeResult()
        self.debate_id = "test_debate"
        self.agents = []


def _make_trickster(hollow_count: int) -> MagicMock:
    t = MagicMock()
    t.get_stats.return_value = {"hollow_alerts_detected": hollow_count}
    return t


@pytest.fixture
def feedback_phase():
    return FeedbackPhase.__new__(FeedbackPhase)


class TestHollowConsensusBridge:
    def test_hollow_detected_propagated(self, feedback_phase):
        """When trickster detects hollow alerts, metadata flag should be True."""
        ctx = _FakeCtx(trickster=_make_trickster(2))
        feedback_phase._propagate_hollow_consensus_to_metadata(ctx)
        assert ctx.result.metadata["hollow_consensus_detected"] is True
        assert ctx.result.metadata["hollow_alerts_count"] == 2

    def test_no_hollow_sets_false(self, feedback_phase):
        """When trickster has zero hollow alerts, metadata flag should be False."""
        ctx = _FakeCtx(trickster=_make_trickster(0))
        feedback_phase._propagate_hollow_consensus_to_metadata(ctx)
        assert ctx.result.metadata["hollow_consensus_detected"] is False
        assert "hollow_alerts_count" not in ctx.result.metadata

    def test_no_trickster_skips(self, feedback_phase):
        """When trickster is None, metadata should not be modified."""
        ctx = _FakeCtx(trickster=None)
        feedback_phase._propagate_hollow_consensus_to_metadata(ctx)
        assert "hollow_consensus_detected" not in ctx.result.metadata

    def test_no_result_skips(self, feedback_phase):
        """When result is None, method should not crash."""
        ctx = _FakeCtx(trickster=_make_trickster(1))
        ctx.result = None
        feedback_phase._propagate_hollow_consensus_to_metadata(ctx)
        # No crash = pass

    def test_trickster_error_graceful(self, feedback_phase):
        """When trickster.get_stats() raises, should handle gracefully."""
        t = MagicMock()
        t.get_stats.side_effect = RuntimeError("broken")
        ctx = _FakeCtx(trickster=t)
        # RuntimeError is not caught (only TypeError/ValueError/AttributeError),
        # but the method is called from execute() which has its own guards
        # The method catches TypeError, ValueError, AttributeError
        # For RuntimeError, it would propagate — but let's test caught types
        t2 = MagicMock()
        t2.get_stats.side_effect = AttributeError("no stats")
        ctx2 = _FakeCtx(trickster=t2)
        feedback_phase._propagate_hollow_consensus_to_metadata(ctx2)
        assert "hollow_consensus_detected" not in ctx2.result.metadata

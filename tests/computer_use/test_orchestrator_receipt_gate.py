"""Tests for receipt enforcement gate wired into Computer-Use orchestrator.

Covers:
- Task succeeds with valid receipt when enforcement is enabled
- Task fails without receipt_id when enforcement is enabled
- Task proceeds normally when enforcement flag is off
- Receipt transitions to EXECUTED after successful task completion
- receipt_id parameter threading from handler to orchestrator
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aragora.computer_use.orchestrator import (
    ComputerUseConfig,
    ComputerUseOrchestrator,
    MockActionExecutor,
    TaskStatus,
)
from aragora.pipeline.receipt_enforcement import ReceiptEnforcementError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def executor():
    """Provide a mock action executor."""
    return MockActionExecutor()


@pytest.fixture()
def orchestrator(executor):
    """Provide an orchestrator with mock executor (no bridge = stub completes after 1 step)."""
    config = ComputerUseConfig(max_steps=5, total_timeout_seconds=10)
    return ComputerUseOrchestrator(executor=executor, config=config)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestComputerUseReceiptGate:
    """Receipt enforcement gate tests for computer-use orchestrator."""

    @patch("aragora.pipeline.receipt_enforcement.is_receipt_enforcement_enabled", return_value=True)
    @patch("aragora.pipeline.receipt_enforcement.require_receipt_gate")
    @patch("aragora.pipeline.receipt_enforcement.transition_receipt_executed")
    def test_task_succeeds_with_valid_receipt(
        self, mock_transition, mock_gate, mock_enabled, orchestrator
    ):
        """When enforcement is on and a valid receipt_id is provided, task runs."""
        mock_gate.return_value = MagicMock()

        result = asyncio.run(
            orchestrator.run_task(
                goal="Test task",
                max_steps=2,
                metadata={"user_id": "user-1"},
                receipt_id="receipt-123",
            )
        )

        assert result.status == TaskStatus.COMPLETED
        mock_gate.assert_called_once()
        call_kwargs = mock_gate.call_args[1]
        assert call_kwargs["action_domain"] == "computer_use"
        assert call_kwargs["action_type"] == "run_task"
        assert call_kwargs["actor_id"] == "user-1"
        assert call_kwargs["receipt_id"] == "receipt-123"
        mock_transition.assert_called_once_with("receipt-123")

    @patch("aragora.pipeline.receipt_enforcement.is_receipt_enforcement_enabled", return_value=True)
    @patch(
        "aragora.pipeline.receipt_enforcement.require_receipt_gate",
        side_effect=ReceiptEnforcementError(
            "Receipt required",
            action_domain="computer_use",
            action_type="run_task",
        ),
    )
    def test_task_fails_without_receipt(self, mock_gate, mock_enabled, orchestrator):
        """When enforcement is on and no receipt_id is provided, raises error."""
        with pytest.raises(ReceiptEnforcementError, match="Receipt required"):
            asyncio.run(
                orchestrator.run_task(
                    goal="Test task",
                    metadata={"user_id": "user-1"},
                )
            )

    @patch(
        "aragora.pipeline.receipt_enforcement.is_receipt_enforcement_enabled", return_value=False
    )
    def test_task_proceeds_without_receipt_flag_off(self, mock_enabled, orchestrator):
        """When enforcement flag is off, task proceeds without receipt."""
        result = asyncio.run(
            orchestrator.run_task(
                goal="Test task",
                max_steps=2,
            )
        )

        assert result.status == TaskStatus.COMPLETED

    @patch("aragora.pipeline.receipt_enforcement.is_receipt_enforcement_enabled", return_value=True)
    @patch("aragora.pipeline.receipt_enforcement.require_receipt_gate")
    @patch("aragora.pipeline.receipt_enforcement.transition_receipt_executed")
    def test_receipt_transitions_to_executed(
        self, mock_transition, mock_gate, mock_enabled, orchestrator
    ):
        """After successful task completion, receipt transitions to EXECUTED."""
        mock_gate.return_value = MagicMock()

        result = asyncio.run(
            orchestrator.run_task(
                goal="Test task",
                max_steps=2,
                metadata={"user_id": "user-1"},
                receipt_id="receipt-456",
            )
        )

        assert result.status == TaskStatus.COMPLETED
        mock_transition.assert_called_once_with("receipt-456")

    @patch("aragora.pipeline.receipt_enforcement.is_receipt_enforcement_enabled", return_value=True)
    @patch("aragora.pipeline.receipt_enforcement.require_receipt_gate")
    @patch("aragora.pipeline.receipt_enforcement.transition_receipt_executed")
    def test_receipt_not_transitioned_on_failure(self, mock_transition, mock_gate, mock_enabled):
        """When task fails, receipt should NOT transition to EXECUTED."""
        mock_gate.return_value = MagicMock()

        # Create an executor that always fails
        failing_executor = MagicMock()
        failing_executor.take_screenshot = AsyncMock(side_effect=OSError("Display unavailable"))
        failing_executor.get_current_url = AsyncMock(return_value=None)

        config = ComputerUseConfig(max_steps=2, total_timeout_seconds=5)
        orch = ComputerUseOrchestrator(executor=failing_executor, config=config)

        result = asyncio.run(
            orch.run_task(
                goal="Test task",
                metadata={"user_id": "user-1"},
                receipt_id="receipt-789",
            )
        )

        assert result.status == TaskStatus.FAILED
        # Receipt gate was checked before execution
        mock_gate.assert_called_once()
        # But transition should not have been called since task failed
        mock_transition.assert_not_called()

    def test_receipt_id_parameter_accepted(self, orchestrator):
        """The receipt_id parameter is accepted by run_task signature."""
        # Just verify the parameter exists and doesn't error with None
        with patch(
            "aragora.pipeline.receipt_enforcement.is_receipt_enforcement_enabled",
            return_value=False,
        ):
            result = asyncio.run(
                orchestrator.run_task(
                    goal="Test task",
                    max_steps=1,
                    receipt_id=None,
                )
            )
            assert result.status == TaskStatus.COMPLETED

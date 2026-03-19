"""Tests for receipt enforcement gate wired into Orchestration Canvas execute pipeline.

Covers:
- Pipeline execution succeeds with valid receipt when enforcement is enabled
- Pipeline execution fails without receipt_id when enforcement is enabled
- Pipeline execution proceeds normally when enforcement flag is off
- Receipt transitions to EXECUTED after successful pipeline queue
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aragora.pipeline.receipt_enforcement import ReceiptEnforcementError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_handler():
    """Create an OrchestrationCanvasHandler with mocked dependencies."""
    from aragora.server.handlers.orchestration_canvas import OrchestrationCanvasHandler

    handler = OrchestrationCanvasHandler(ctx={})
    return handler


def _mock_auth_context():
    """Create a minimal AuthorizationContext mock."""
    ctx = MagicMock()
    ctx.user_id = "user-1"
    ctx.org_id = "org-1"
    ctx.roles = {"member"}
    return ctx


def _base_body(receipt_id: str | None = None) -> dict:
    """Minimal valid body for execute pipeline."""
    body: dict = {}
    if receipt_id is not None:
        body["receipt_id"] = receipt_id
    return body


def _mock_store_with_canvas():
    """Create a mock store that returns a valid canvas."""
    store = MagicMock()
    store.load_canvas.return_value = {
        "canvas_id": "canvas-1",
        "name": "Test Canvas",
        "metadata": {"stage": "orchestration"},
    }
    store.update_canvas.return_value = True
    return store


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestOrchestrationCanvasReceiptGate:
    """Receipt enforcement gate tests for orchestration canvas pipeline execution."""

    @patch("aragora.pipeline.receipt_enforcement.is_receipt_enforcement_enabled", return_value=True)
    @patch(
        "aragora.pipeline.receipt_enforcement.require_receipt_gate",
        side_effect=ReceiptEnforcementError(
            "Receipt required",
            action_domain="canvas",
            action_type="execute_pipeline",
        ),
    )
    def test_pipeline_fails_without_receipt(self, mock_gate, mock_enabled):
        """When enforcement is on and no receipt_id is provided, returns 428."""
        handler = _make_handler()

        body = _base_body()  # no receipt_id
        context = _mock_auth_context()

        result = handler._execute_pipeline(context, "canvas-1", body, "user-1")

        assert result.status == 428

    @patch(
        "aragora.pipeline.receipt_enforcement.is_receipt_enforcement_enabled", return_value=False
    )
    def test_pipeline_proceeds_without_receipt_flag_off(self, mock_enabled):
        """When enforcement flag is off, pipeline proceeds without receipt."""
        handler = _make_handler()
        store = _mock_store_with_canvas()
        handler._get_store = MagicMock(return_value=store)

        manager = MagicMock()
        canvas_mock = MagicMock()
        canvas_mock.nodes = {}
        canvas_mock.edges = {}
        manager.get_canvas = AsyncMock(return_value=canvas_mock)
        handler._get_canvas_manager = MagicMock(return_value=manager)
        handler._run_async = asyncio.run

        # Mock the pipeline execution imports
        mock_plan = MagicMock()
        mock_plan.id = "plan-1"
        mock_launch = {
            "execution_id": "exec-1",
            "correlation_id": "corr-1",
            "execution_mode": "workflow",
        }

        with patch(
            "aragora.server.handlers.orchestration_canvas.OrchestrationCanvasHandler._execute_pipeline",
            wraps=handler._execute_pipeline,
        ):
            with (
                patch(
                    "aragora.pipeline.canonical_execution.build_decision_plan_from_orchestration",
                    return_value=(mock_plan, []),
                ),
                patch(
                    "aragora.pipeline.canonical_execution.queue_plan_execution",
                    return_value=mock_launch,
                ),
                patch(
                    "aragora.pipeline.canonical_execution.schedule_coroutine",
                ),
            ):
                body = _base_body()
                context = _mock_auth_context()

                result = handler._execute_pipeline(context, "canvas-1", body, "user-1")

                assert result.status == 201

    @patch("aragora.pipeline.receipt_enforcement.is_receipt_enforcement_enabled", return_value=True)
    @patch("aragora.pipeline.receipt_enforcement.require_receipt_gate")
    @patch("aragora.pipeline.receipt_enforcement.transition_receipt_executed")
    def test_pipeline_succeeds_with_valid_receipt(self, mock_transition, mock_gate, mock_enabled):
        """When enforcement is on and a valid receipt_id is provided, pipeline proceeds."""
        mock_gate.return_value = MagicMock()

        handler = _make_handler()
        store = _mock_store_with_canvas()
        handler._get_store = MagicMock(return_value=store)

        manager = MagicMock()
        canvas_mock = MagicMock()
        canvas_mock.nodes = {}
        canvas_mock.edges = {}
        manager.get_canvas = AsyncMock(return_value=canvas_mock)
        handler._get_canvas_manager = MagicMock(return_value=manager)
        handler._run_async = asyncio.run

        mock_plan = MagicMock()
        mock_plan.id = "plan-1"
        mock_launch = {
            "execution_id": "exec-1",
            "correlation_id": "corr-1",
            "execution_mode": "workflow",
        }

        with (
            patch(
                "aragora.pipeline.canonical_execution.build_decision_plan_from_orchestration",
                return_value=(mock_plan, []),
            ),
            patch(
                "aragora.pipeline.canonical_execution.queue_plan_execution",
                return_value=mock_launch,
            ),
            patch(
                "aragora.pipeline.canonical_execution.schedule_coroutine",
            ),
        ):
            body = _base_body(receipt_id="receipt-789")
            context = _mock_auth_context()

            result = handler._execute_pipeline(context, "canvas-1", body, "user-1")

            assert result.status == 201
            mock_gate.assert_called_once_with(
                action_domain="canvas",
                action_type="execute_pipeline",
                actor_id="user-1",
                resource_id="canvas-1",
                receipt_id="receipt-789",
            )
            mock_transition.assert_called_once_with("receipt-789")

    @patch("aragora.pipeline.receipt_enforcement.is_receipt_enforcement_enabled", return_value=True)
    @patch("aragora.pipeline.receipt_enforcement.require_receipt_gate")
    @patch("aragora.pipeline.receipt_enforcement.transition_receipt_executed")
    def test_receipt_transitions_to_executed(self, mock_transition, mock_gate, mock_enabled):
        """After successful pipeline queue, receipt transitions to EXECUTED."""
        mock_gate.return_value = MagicMock()

        handler = _make_handler()
        store = _mock_store_with_canvas()
        handler._get_store = MagicMock(return_value=store)

        manager = MagicMock()
        canvas_mock = MagicMock()
        canvas_mock.nodes = {}
        canvas_mock.edges = {}
        manager.get_canvas = AsyncMock(return_value=canvas_mock)
        handler._get_canvas_manager = MagicMock(return_value=manager)
        handler._run_async = asyncio.run

        mock_plan = MagicMock()
        mock_plan.id = "plan-1"
        mock_launch = {
            "execution_id": "exec-1",
            "correlation_id": "corr-1",
            "execution_mode": "workflow",
        }

        with (
            patch(
                "aragora.pipeline.canonical_execution.build_decision_plan_from_orchestration",
                return_value=(mock_plan, []),
            ),
            patch(
                "aragora.pipeline.canonical_execution.queue_plan_execution",
                return_value=mock_launch,
            ),
            patch(
                "aragora.pipeline.canonical_execution.schedule_coroutine",
            ),
        ):
            body = _base_body(receipt_id="receipt-999")
            context = _mock_auth_context()

            result = handler._execute_pipeline(context, "canvas-1", body, "user-1")

            assert result.status == 201
            mock_transition.assert_called_once_with("receipt-999")

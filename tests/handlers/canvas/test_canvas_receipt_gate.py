"""Tests for receipt enforcement gate wired into Canvas execute action.

Covers:
- Action succeeds with valid receipt when enforcement is enabled
- Action fails without receipt_id when enforcement is enabled
- Action proceeds normally when enforcement flag is off
- Receipt transitions to EXECUTED after successful action
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
    """Create a CanvasHandler with mocked dependencies."""
    from aragora.server.handlers.canvas.handler import CanvasHandler

    handler = CanvasHandler(ctx={})
    return handler


def _mock_auth_context():
    """Create a minimal AuthorizationContext mock."""
    ctx = MagicMock()
    ctx.user_id = "user-1"
    ctx.org_id = "org-1"
    ctx.roles = {"member"}
    return ctx


def _base_body(receipt_id: str | None = None) -> dict:
    """Minimal valid body for execute action."""
    body = {
        "action": "run_analysis",
        "node_id": "node-1",
        "params": {},
    }
    if receipt_id is not None:
        body["receipt_id"] = receipt_id
    return body


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCanvasReceiptGate:
    """Receipt enforcement gate tests for Canvas execute action."""

    @patch.object(
        __import__(
            "aragora.server.handlers.canvas.handler", fromlist=["CanvasHandler"]
        ).CanvasHandler,
        "_get_canvas_manager",
    )
    @patch("aragora.pipeline.receipt_enforcement.is_receipt_enforcement_enabled", return_value=True)
    @patch("aragora.pipeline.receipt_enforcement.require_receipt_gate")
    @patch("aragora.pipeline.receipt_enforcement.transition_receipt_executed")
    def test_action_succeeds_with_valid_receipt(
        self, mock_transition, mock_gate, mock_enabled, mock_manager
    ):
        """When enforcement is on and a valid receipt_id is provided, action proceeds."""
        manager = MagicMock()
        manager.execute_action = AsyncMock(return_value={"status": "ok"})
        mock_manager.return_value = manager
        mock_gate.return_value = MagicMock()

        handler = _make_handler()
        handler._run_async = asyncio.run

        body = _base_body(receipt_id="receipt-123")
        context = _mock_auth_context()

        result = handler._execute_action(context, "canvas-1", body, "user-1")

        assert result.status == 200
        mock_gate.assert_called_once_with(
            action_domain="canvas",
            action_type="execute_action",
            actor_id="user-1",
            resource_id="canvas-1",
            receipt_id="receipt-123",
        )
        mock_transition.assert_called_once_with("receipt-123")

    @patch.object(
        __import__(
            "aragora.server.handlers.canvas.handler", fromlist=["CanvasHandler"]
        ).CanvasHandler,
        "_get_canvas_manager",
    )
    @patch("aragora.pipeline.receipt_enforcement.is_receipt_enforcement_enabled", return_value=True)
    @patch(
        "aragora.pipeline.receipt_enforcement.require_receipt_gate",
        side_effect=ReceiptEnforcementError(
            "Receipt required",
            action_domain="canvas",
            action_type="execute_action",
        ),
    )
    def test_action_fails_without_receipt(self, mock_gate, mock_enabled, mock_manager):
        """When enforcement is on and no receipt_id is provided, returns 428."""
        handler = _make_handler()

        body = _base_body()  # no receipt_id
        context = _mock_auth_context()

        result = handler._execute_action(context, "canvas-1", body, "user-1")

        assert result.status == 428

    @patch.object(
        __import__(
            "aragora.server.handlers.canvas.handler", fromlist=["CanvasHandler"]
        ).CanvasHandler,
        "_get_canvas_manager",
    )
    @patch(
        "aragora.pipeline.receipt_enforcement.is_receipt_enforcement_enabled", return_value=False
    )
    def test_action_proceeds_without_receipt_flag_off(self, mock_enabled, mock_manager):
        """When enforcement flag is off, action proceeds without receipt."""
        manager = MagicMock()
        manager.execute_action = AsyncMock(return_value={"status": "ok"})
        mock_manager.return_value = manager

        handler = _make_handler()
        handler._run_async = asyncio.run

        body = _base_body()  # no receipt_id
        context = _mock_auth_context()

        result = handler._execute_action(context, "canvas-1", body, "user-1")

        assert result.status == 200

    @patch.object(
        __import__(
            "aragora.server.handlers.canvas.handler", fromlist=["CanvasHandler"]
        ).CanvasHandler,
        "_get_canvas_manager",
    )
    @patch("aragora.pipeline.receipt_enforcement.is_receipt_enforcement_enabled", return_value=True)
    @patch("aragora.pipeline.receipt_enforcement.require_receipt_gate")
    @patch("aragora.pipeline.receipt_enforcement.transition_receipt_executed")
    def test_receipt_transitions_to_executed(
        self, mock_transition, mock_gate, mock_enabled, mock_manager
    ):
        """After successful action, receipt state transitions to EXECUTED."""
        manager = MagicMock()
        manager.execute_action = AsyncMock(return_value={"done": True})
        mock_manager.return_value = manager
        mock_gate.return_value = MagicMock()

        handler = _make_handler()
        handler._run_async = asyncio.run

        body = _base_body(receipt_id="receipt-456")
        context = _mock_auth_context()

        result = handler._execute_action(context, "canvas-1", body, "user-1")

        assert result.status == 200
        mock_transition.assert_called_once_with("receipt-456")

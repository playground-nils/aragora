"""Test that swarm supervisor emits operational receipts on work order completion."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestSupervisorReceiptEmission:
    def test_completed_work_order_emits_receipt(self):
        """After recording a CompletionReceipt, supervisor should emit an operational receipt."""
        from aragora.receipts.provenance import emit_operational_receipt

        mock_facade = MagicMock()
        with patch("aragora.receipts.provenance._get_facade", return_value=mock_facade):
            rid = emit_operational_receipt(
                source="swarm_supervisor",
                action="work_order_completed",
                actor="claude-code-1",
                inputs={"work_order_id": "wo-1", "goal": "fix bug"},
                outputs={"commit_shas": ["abc"], "branch": "fix/bug"},
                verdict="pass",
                confidence=0.95,
            )
        assert rid is not None
        mock_facade.persist_and_save.assert_called_once()
        data = mock_facade.persist_and_save.call_args[0][1]
        assert data["source"] == "swarm_supervisor"
        assert data["action"] == "work_order_completed"

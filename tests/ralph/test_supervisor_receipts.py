"""Test Ralph supervisor receipt emission at terminal states."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestRalphReceiptEmission:
    def test_campaign_completed_emits_receipt(self):
        from aragora.receipts.provenance import emit_operational_receipt

        mock_facade = MagicMock()
        with patch("aragora.receipts.provenance._get_facade", return_value=mock_facade):
            rid = emit_operational_receipt(
                source="ralph",
                action="campaign_completed",
                actor="ralph-repair",
                inputs={"campaign_id": "c-1"},
                outputs={"status": "completed", "projects_completed": 3},
                verdict="pass",
            )
        assert rid is not None
        mock_facade.persist_and_save.assert_called_once()
        data = mock_facade.persist_and_save.call_args[0][1]
        assert data["source"] == "ralph"
        assert data["action"] == "campaign_completed"

    def test_escalation_emits_receipt(self):
        from aragora.receipts.provenance import emit_operational_receipt

        mock_facade = MagicMock()
        with patch("aragora.receipts.provenance._get_facade", return_value=mock_facade):
            rid = emit_operational_receipt(
                source="ralph",
                action="campaign_escalated",
                actor="ralph-repair",
                inputs={"campaign_id": "c-2"},
                outputs={"reason": "budget exhausted"},
                verdict="escalated",
            )
        assert rid is not None
        data = mock_facade.persist_and_save.call_args[0][1]
        assert data["verdict"] == "escalated"
        assert data["outputs"]["reason"] == "budget exhausted"

"""Test boss loop receipt emission."""

from __future__ import annotations
from unittest.mock import MagicMock, patch
import pytest


class TestBossLoopReceiptEmission:
    def test_run_completed_emits_receipt(self):
        from aragora.receipts.provenance import emit_operational_receipt

        with patch("aragora.receipts.provenance._get_facade") as mock_gf:
            mock_facade = MagicMock()
            mock_gf.return_value = mock_facade
            rid = emit_operational_receipt(
                source="boss_loop",
                action="run_completed",
                actor="boss-loop-main",
                inputs={"run_id": "run-1", "max_iterations": 5},
                outputs={"iterations_completed": 3, "issues_resolved": 2},
                verdict="pass",
            )
            assert rid is not None
            mock_facade.persist_and_save.assert_called_once()

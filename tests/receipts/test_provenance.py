"""Tests for operational receipt emission."""

from __future__ import annotations

import hashlib
import json
from unittest.mock import MagicMock, patch

import pytest


class TestEmitOperationalReceipt:
    def test_happy_path_persists_receipt(self):
        from aragora.receipts.provenance import emit_operational_receipt

        mock_facade = MagicMock()
        with patch("aragora.receipts.provenance._get_facade", return_value=mock_facade):
            rid = emit_operational_receipt(
                source="swarm_supervisor",
                action="work_order_completed",
                actor="claude-code-1",
                inputs={"work_order_id": "wo-1"},
                outputs={"commit_shas": ["abc123"]},
                verdict="pass",
                confidence=0.95,
                duration_seconds=120.0,
            )
        assert rid is not None
        mock_facade.persist_and_save.assert_called_once()
        call_args = mock_facade.persist_and_save.call_args
        assert call_args[0][0] == rid  # receipt_id
        data = call_args[0][1]
        assert data["source"] == "swarm_supervisor"
        assert data["verdict"] == "pass"

    def test_facade_unavailable_returns_none(self):
        from aragora.receipts.provenance import emit_operational_receipt

        with patch("aragora.receipts.provenance._get_facade", return_value=None):
            rid = emit_operational_receipt(
                source="test",
                action="test",
                actor="test",
                inputs={},
                outputs={},
                verdict="pass",
            )
        assert rid is None

    def test_facade_exception_returns_none_no_raise(self):
        from aragora.receipts.provenance import emit_operational_receipt

        mock_facade = MagicMock()
        mock_facade.persist_and_save.side_effect = RuntimeError("boom")
        with patch("aragora.receipts.provenance._get_facade", return_value=mock_facade):
            rid = emit_operational_receipt(
                source="test",
                action="test",
                actor="test",
                inputs={},
                outputs={},
                verdict="pass",
            )
        assert rid is None

    def test_content_hash_deterministic(self):
        from aragora.receipts.provenance import _content_hash

        h1 = _content_hash("r1", "src", "act", {"a": 1}, {"b": 2})
        h2 = _content_hash("r1", "src", "act", {"a": 1}, {"b": 2})
        assert h1 == h2
        h3 = _content_hash("r2", "src", "act", {"a": 1}, {"b": 2})
        assert h1 != h3

    def test_signing_attempted_when_available(self):
        from aragora.receipts.provenance import emit_operational_receipt

        mock_facade = MagicMock()
        mock_signer = MagicMock()
        mock_signed = MagicMock()
        mock_signed.signature = "sig-abc"
        mock_signed.signature_metadata.key_id = "key-1"
        mock_signed.signature_metadata.timestamp = "2026-01-01T00:00:00Z"
        mock_signed.signature_metadata.algorithm = "ed25519"
        mock_signer.sign.return_value = mock_signed

        with (
            patch("aragora.receipts.provenance._get_facade", return_value=mock_facade),
            patch("aragora.receipts.provenance._get_signer", return_value=mock_signer),
        ):
            emit_operational_receipt(
                source="test",
                action="test",
                actor="test",
                inputs={},
                outputs={},
                verdict="pass",
            )
        call_kwargs = mock_facade.persist_and_save.call_args[1]
        assert call_kwargs["signature"] == "sig-abc"

    def test_signing_unavailable_still_persists(self):
        from aragora.receipts.provenance import emit_operational_receipt

        mock_facade = MagicMock()
        with (
            patch("aragora.receipts.provenance._get_facade", return_value=mock_facade),
            patch("aragora.receipts.provenance._get_signer", return_value=None),
        ):
            rid = emit_operational_receipt(
                source="test",
                action="test",
                actor="test",
                inputs={},
                outputs={},
                verdict="pass",
            )
        assert rid is not None
        call_kwargs = mock_facade.persist_and_save.call_args[1]
        assert call_kwargs["signature"] is None

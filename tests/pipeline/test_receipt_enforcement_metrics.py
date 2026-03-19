"""Tests for Prometheus metrics integration in receipt enforcement."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from aragora.config.feature_flags import reset_flag_registry
from aragora.gauntlet.receipt_models import DecisionReceipt
from aragora.gauntlet.receipt_store import ReceiptState, get_receipt_store, reset_receipt_store
from aragora.pipeline.receipt_enforcement import (
    ReceiptEnforcementError,
    ReceiptExemption,
    require_receipt_gate,
    reset_enforcement_metrics,
)
from aragora.pipeline.receipt_exemptions import ExemptionRegistry


@pytest.fixture(autouse=True)
def _reset_globals() -> None:  # type: ignore[misc]
    reset_receipt_store()
    reset_flag_registry()
    reset_enforcement_metrics()
    ExemptionRegistry.reset_instance()
    yield
    reset_receipt_store()
    reset_flag_registry()
    reset_enforcement_metrics()
    ExemptionRegistry.reset_instance()


def _debate_result() -> SimpleNamespace:
    return SimpleNamespace(
        debate_id="debate-metrics",
        task="Test metrics emission",
        final_answer="Metrics emitted.",
        confidence=0.88,
        consensus_reached=True,
        rounds_used=2,
        duration_seconds=0.5,
        consensus_strength="majority",
        participants=["claude"],
        dissenting_views=[],
        messages=[],
        votes=[],
        winner="claude",
    )


def _persist_signed_receipt(
    *,
    receipt_id: str = "receipt-m1",
    state: ReceiptState = ReceiptState.APPROVED,
) -> None:
    receipt = DecisionReceipt.from_debate_result(_debate_result())
    receipt.receipt_id = receipt_id
    receipt.artifact_hash = receipt._calculate_hash()
    receipt.sign()

    store = get_receipt_store()
    store.persist(
        receipt_id=receipt_id,
        receipt_data=receipt.to_dict(),
        signature=receipt.signature,
        signature_key_id=receipt.signature_key_id,
        signed_at=receipt.signed_at,
        signature_algorithm=receipt.signature_algorithm,
        state=state,
    )


# ------------------------------------------------------------------
# Counter tests
# ------------------------------------------------------------------


class TestEnforcementMetricsCounter:
    """Verify that the Prometheus counter is incremented for each outcome."""

    def test_counter_incremented_on_allow(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ARAGORA_RECEIPT_ENFORCEMENT_OPENCLAW", "true")
        reset_flag_registry()
        _persist_signed_receipt(receipt_id="receipt-allow")

        with patch(
            "aragora.pipeline.receipt_enforcement._record_enforcement_metric"
        ) as mock_record:
            require_receipt_gate(
                action_domain="openclaw",
                action_type="execute_action",
                actor_id="user-1",
                resource_id="res-1",
                receipt_id="receipt-allow",
            )
            mock_record.assert_called_once()
            call_args = mock_record.call_args
            assert call_args[0][0] == "openclaw"
            assert call_args[0][1] == "allowed"
            assert isinstance(call_args[0][2], float)

    def test_counter_incremented_on_block(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ARAGORA_RECEIPT_ENFORCEMENT_OPENCLAW", "true")
        reset_flag_registry()

        with patch(
            "aragora.pipeline.receipt_enforcement._record_enforcement_metric"
        ) as mock_record:
            with pytest.raises(ReceiptEnforcementError):
                require_receipt_gate(
                    action_domain="openclaw",
                    action_type="execute_action",
                    actor_id="user-1",
                    resource_id="res-1",
                    receipt_id=None,
                )
            mock_record.assert_called_once()
            call_args = mock_record.call_args
            assert call_args[0][1] == "blocked"

    def test_counter_incremented_on_exempt(self) -> None:
        with patch(
            "aragora.pipeline.receipt_enforcement._record_enforcement_metric"
        ) as mock_record:
            require_receipt_gate(
                action_domain="openclaw",
                action_type="execute_action",
                actor_id="admin",
                resource_id="res-1",
                exempt=ReceiptExemption(
                    reason="Test exemption",
                    approved_by="test",
                    category="read_only",
                ),
            )
            mock_record.assert_called_once()
            call_args = mock_record.call_args
            assert call_args[0][1] == "exempted"

    def test_counter_incremented_on_disabled(self) -> None:
        with patch(
            "aragora.pipeline.receipt_enforcement._record_enforcement_metric"
        ) as mock_record:
            require_receipt_gate(
                action_domain="openclaw",
                action_type="execute_action",
                actor_id="user-1",
                resource_id="res-1",
            )
            mock_record.assert_called_once()
            call_args = mock_record.call_args
            assert call_args[0][1] == "disabled"


# ------------------------------------------------------------------
# Latency tests
# ------------------------------------------------------------------


class TestEnforcementMetricsLatency:
    """Verify that latency is observed for every enforcement decision."""

    def test_latency_is_non_negative(self) -> None:
        with patch(
            "aragora.pipeline.receipt_enforcement._record_enforcement_metric"
        ) as mock_record:
            require_receipt_gate(
                action_domain="canvas",
                action_type="update_node",
                actor_id="user-1",
                resource_id="res-1",
            )
            elapsed = mock_record.call_args[0][2]
            assert elapsed >= 0.0


# ------------------------------------------------------------------
# Graceful degradation without prometheus_client
# ------------------------------------------------------------------


class TestMetricsWithoutPrometheus:
    """Verify that enforcement works when prometheus_client is not installed."""

    def test_graceful_without_prometheus(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Enforcement should succeed even when prometheus_client import fails."""
        reset_enforcement_metrics()

        # Temporarily hide prometheus_client from the import system
        real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        def _blocked_import(name, *args, **kwargs):
            if name == "prometheus_client":
                raise ImportError("simulated: no prometheus_client")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _blocked_import)

        # Should still work — metrics just become no-ops
        result = require_receipt_gate(
            action_domain="openclaw",
            action_type="execute_action",
            actor_id="user-1",
            resource_id="res-1",
        )
        assert result is None  # disabled → pass-through


# ------------------------------------------------------------------
# Registry-based automatic exemption wiring
# ------------------------------------------------------------------


class TestRegistryExemptionWiring:
    """Verify that ExemptionRegistry automatically exempts matching actions."""

    def test_registry_exempts_read_operations(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """read_* actions should be auto-exempted via the registry, even when
        enforcement is enabled."""
        monkeypatch.setenv("ARAGORA_RECEIPT_ENFORCEMENT_OPENCLAW", "true")
        reset_flag_registry()

        # read_config matches built-in "read_*" pattern → exempted
        result = require_receipt_gate(
            action_domain="openclaw",
            action_type="read_config",
            actor_id="user-1",
            resource_id="res-1",
        )
        assert result is None  # exempted, not blocked

    def test_registry_does_not_exempt_mutations(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Mutating actions should NOT be auto-exempted."""
        monkeypatch.setenv("ARAGORA_RECEIPT_ENFORCEMENT_OPENCLAW", "true")
        reset_flag_registry()

        with pytest.raises(ReceiptEnforcementError):
            require_receipt_gate(
                action_domain="openclaw",
                action_type="execute_action",
                actor_id="user-1",
                resource_id="res-1",
            )

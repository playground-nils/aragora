"""Tests for the canonical receipt enforcement gate.

Covers:
- Enforcement disabled (domain not enrolled) returns None
- Valid APPROVED receipt returns StoredReceipt
- Missing receipt_id raises ReceiptEnforcementError
- Receipt in wrong state (EXPIRED / CREATED) raises
- Invalid signature raises
- Exemption bypasses enforcement
- transition_receipt_executed happy path
- Transition from wrong state raises ReceiptStateError
- Structured audit logging on enforcement calls
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from aragora.gauntlet.receipt_store import (
    ReceiptState,
    ReceiptStateError,
    ReceiptStore,
    StoredReceipt,
    reset_receipt_store,
)
from aragora.pipeline.receipt_enforcement import (
    ReceiptEnforcementError,
    ReceiptExemption,
    is_receipt_enforcement_enabled,
    require_receipt_gate,
    transition_receipt_executed,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_receipt_store():
    """Reset the receipt store singleton between tests."""
    reset_receipt_store()
    yield
    reset_receipt_store()


@pytest.fixture()
def store() -> ReceiptStore:
    """Provide a fresh ReceiptStore and patch it as the singleton."""
    s = ReceiptStore()
    with patch(
        "aragora.gauntlet.receipt_store.get_receipt_store",
        return_value=s,
    ):
        yield s


@pytest.fixture()
def _enforcement_on():
    """Enable receipt enforcement for all domains."""
    with patch(
        "aragora.config.feature_flags.is_enabled",
        return_value=True,
    ):
        yield


def _persist_approved(store: ReceiptStore, receipt_id: str = "r-001") -> StoredReceipt:
    """Persist a receipt in APPROVED state with a dummy signature."""
    stored = store.persist(
        receipt_id=receipt_id,
        receipt_data={"task": "test"},
        signature="dGVzdHNpZw==",
        signature_key_id="k-1",
        signed_at="2026-01-01T00:00:00+00:00",
        signature_algorithm="HMAC-SHA256",
        state=ReceiptState.APPROVED,
    )
    return stored


# ---------------------------------------------------------------------------
# Tests: enforcement disabled
# ---------------------------------------------------------------------------


class TestEnforcementDisabled:
    def test_enforcement_disabled_returns_none(self):
        """When the domain flag is off, require_receipt_gate is a no-op."""
        with patch(
            "aragora.config.feature_flags.is_enabled",
            return_value=False,
        ):
            result = require_receipt_gate(
                action_domain="test",
                action_type="create",
                actor_id="user-1",
                resource_id="res-1",
                receipt_id="r-001",
            )
            assert result is None


# ---------------------------------------------------------------------------
# Tests: enforcement enabled
# ---------------------------------------------------------------------------


class TestEnforcementEnabled:
    @pytest.mark.usefixtures("_enforcement_on")
    def test_valid_receipt_returns_stored(self, store: ReceiptStore):
        """An APPROVED receipt with a valid signature passes the gate."""
        _persist_approved(store)

        # Patch verify_receipt to return True (we don't want real crypto here)
        store.verify_receipt = MagicMock(return_value=True)  # type: ignore[method-assign]

        result = require_receipt_gate(
            action_domain="test",
            action_type="create",
            actor_id="user-1",
            resource_id="res-1",
            receipt_id="r-001",
        )
        assert result is not None
        assert result.receipt_id == "r-001"
        assert result.state == ReceiptState.APPROVED

    @pytest.mark.usefixtures("_enforcement_on")
    def test_missing_receipt_raises(self, store: ReceiptStore):
        """When no receipt_id is provided, enforcement raises."""
        with pytest.raises(ReceiptEnforcementError, match="requires a receipt"):
            require_receipt_gate(
                action_domain="test",
                action_type="create",
                actor_id="user-1",
                resource_id="res-1",
                receipt_id=None,
            )

    @pytest.mark.usefixtures("_enforcement_on")
    def test_receipt_not_found_raises(self, store: ReceiptStore):
        """When receipt_id doesn't exist in store, enforcement raises."""
        with pytest.raises(ReceiptEnforcementError, match="not found"):
            require_receipt_gate(
                action_domain="test",
                action_type="create",
                actor_id="user-1",
                resource_id="res-1",
                receipt_id="r-nonexistent",
            )

    @pytest.mark.usefixtures("_enforcement_on")
    def test_expired_receipt_raises(self, store: ReceiptStore):
        """A receipt in EXPIRED state is rejected."""
        store.persist(
            receipt_id="r-expired",
            receipt_data={"task": "test"},
            signature="dGVzdHNpZw==",
            state=ReceiptState.APPROVED,
        )
        store.transition("r-expired", ReceiptState.EXPIRED)

        with pytest.raises(ReceiptEnforcementError, match="EXPIRED.*expected APPROVED"):
            require_receipt_gate(
                action_domain="test",
                action_type="create",
                actor_id="user-1",
                resource_id="res-1",
                receipt_id="r-expired",
            )

    @pytest.mark.usefixtures("_enforcement_on")
    def test_created_receipt_raises(self, store: ReceiptStore):
        """A receipt still in CREATED state (not yet approved) is rejected."""
        store.persist(
            receipt_id="r-created",
            receipt_data={"task": "test"},
            signature="dGVzdHNpZw==",
            state=ReceiptState.CREATED,
        )

        with pytest.raises(ReceiptEnforcementError, match="CREATED.*expected APPROVED"):
            require_receipt_gate(
                action_domain="test",
                action_type="create",
                actor_id="user-1",
                resource_id="res-1",
                receipt_id="r-created",
            )

    @pytest.mark.usefixtures("_enforcement_on")
    def test_invalid_signature_raises(self, store: ReceiptStore):
        """A receipt whose signature fails verification is rejected."""
        _persist_approved(store)
        store.verify_receipt = MagicMock(return_value=False)  # type: ignore[method-assign]

        with pytest.raises(ReceiptEnforcementError, match="signature verification"):
            require_receipt_gate(
                action_domain="test",
                action_type="create",
                actor_id="user-1",
                resource_id="res-1",
                receipt_id="r-001",
            )

    @pytest.mark.usefixtures("_enforcement_on")
    def test_exemption_returns_none(self, store: ReceiptStore):
        """Providing an exemption bypasses enforcement even when enabled."""
        exemption = ReceiptExemption(
            reason="Read-only status check",
            approved_by="system",
            category="read_only",
        )
        result = require_receipt_gate(
            action_domain="test",
            action_type="read_status",
            actor_id="user-1",
            resource_id="res-1",
            exempt=exemption,
        )
        assert result is None


# ---------------------------------------------------------------------------
# Tests: transition_receipt_executed
# ---------------------------------------------------------------------------


class TestTransitionExecuted:
    def test_transition_executed(self, store: ReceiptStore):
        """Transitions an APPROVED receipt to EXECUTED."""
        _persist_approved(store)

        result = transition_receipt_executed("r-001")

        assert result.state == ReceiptState.EXECUTED

    def test_transition_wrong_state_raises(self, store: ReceiptStore):
        """Cannot transition directly from CREATED to EXECUTED."""
        store.persist(
            receipt_id="r-created",
            receipt_data={"task": "test"},
            state=ReceiptState.CREATED,
        )

        with pytest.raises(ReceiptStateError, match="Cannot transition"):
            transition_receipt_executed("r-created")


# ---------------------------------------------------------------------------
# Tests: audit logging
# ---------------------------------------------------------------------------


class TestAuditLogging:
    @pytest.mark.usefixtures("_enforcement_on")
    def test_audit_logging_on_pass(self, store: ReceiptStore, caplog):
        """Verify structured log entries on successful enforcement."""
        _persist_approved(store)
        store.verify_receipt = MagicMock(return_value=True)  # type: ignore[method-assign]

        with caplog.at_level(logging.INFO, logger="aragora.pipeline.receipt_enforcement"):
            require_receipt_gate(
                action_domain="inbox",
                action_type="archive",
                actor_id="user-42",
                resource_id="msg-99",
                receipt_id="r-001",
            )

        assert any("receipt_enforcement_passed" in r.message for r in caplog.records)
        assert any("inbox" in r.message for r in caplog.records)

    def test_audit_logging_on_skip(self, caplog):
        """Verify structured log entries when enforcement is disabled."""
        with patch(
            "aragora.config.feature_flags.is_enabled",
            return_value=False,
        ):
            with caplog.at_level(logging.DEBUG, logger="aragora.pipeline.receipt_enforcement"):
                require_receipt_gate(
                    action_domain="canvas",
                    action_type="update",
                    actor_id="user-1",
                    resource_id="res-1",
                )

        assert any("receipt_enforcement_skip" in r.message for r in caplog.records)

    @pytest.mark.usefixtures("_enforcement_on")
    def test_audit_logging_on_exempt(self, store: ReceiptStore, caplog):
        """Verify structured log entries for exempted operations."""
        exemption = ReceiptExemption(
            reason="Metadata update",
            approved_by="admin",
            category="metadata_only",
        )
        with caplog.at_level(logging.INFO, logger="aragora.pipeline.receipt_enforcement"):
            require_receipt_gate(
                action_domain="openclaw",
                action_type="label",
                actor_id="user-7",
                resource_id="pr-42",
                exempt=exemption,
            )

        assert any("receipt_enforcement_exempt" in r.message for r in caplog.records)
        assert any("metadata_only" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Tests: is_receipt_enforcement_enabled
# ---------------------------------------------------------------------------


class TestIsReceiptEnforcementEnabled:
    def test_delegates_to_feature_flag(self):
        """is_receipt_enforcement_enabled calls the feature flag registry."""
        with patch(
            "aragora.config.feature_flags.is_enabled",
            return_value=True,
        ) as mock_enabled:
            result = is_receipt_enforcement_enabled("openclaw")
            assert result is True
            mock_enabled.assert_called_once_with("receipt_enforcement_openclaw")

    def test_defaults_to_false(self):
        """Unset flags default to False (enforcement off)."""
        with patch(
            "aragora.config.feature_flags.is_enabled",
            return_value=False,
        ):
            assert is_receipt_enforcement_enabled("canvas") is False

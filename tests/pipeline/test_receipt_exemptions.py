"""Tests for the ExemptionRegistry and built-in receipt exemptions."""

from __future__ import annotations

import pytest

from aragora.pipeline.receipt_exemptions import ExemptionRegistry, RegisteredExemption


@pytest.fixture(autouse=True)
def _reset_registry() -> None:  # type: ignore[misc]
    ExemptionRegistry.reset_instance()
    yield
    ExemptionRegistry.reset_instance()


# ------------------------------------------------------------------
# Built-in exemptions
# ------------------------------------------------------------------


class TestBuiltinExemptions:
    """Verify that built-in exemptions are registered on construction."""

    def test_read_operations_exempt(self) -> None:
        reg = ExemptionRegistry.get_instance()
        result = reg.is_exempt("openclaw", "read_state")
        assert result is not None
        assert result.category == "read_only"

    def test_list_operations_exempt(self) -> None:
        reg = ExemptionRegistry.get_instance()
        result = reg.is_exempt("canvas", "list_items")
        assert result is not None
        assert result.category == "read_only"

    def test_get_operations_exempt(self) -> None:
        reg = ExemptionRegistry.get_instance()
        result = reg.is_exempt("inbox", "get_messages")
        assert result is not None
        assert result.category == "read_only"

    def test_health_check_exempt(self) -> None:
        reg = ExemptionRegistry.get_instance()
        result = reg.is_exempt("computer_use", "health_check")
        assert result is not None
        assert result.category == "health_check"

    def test_metrics_exempt(self) -> None:
        reg = ExemptionRegistry.get_instance()
        result = reg.is_exempt("shared_inbox", "metrics")
        assert result is not None
        assert result.category == "system_internal"


# ------------------------------------------------------------------
# Custom exemptions
# ------------------------------------------------------------------


class TestCustomExemptions:
    """Verify custom exemption registration and matching."""

    def test_register_and_match(self) -> None:
        reg = ExemptionRegistry.get_instance()
        reg.register(
            domain="canvas",
            action_pattern="preview_*",
            reason="Preview actions are read-only renders",
            approved_by="eng-team",
            category="read_only",
        )
        result = reg.is_exempt("canvas", "preview_layout")
        assert result is not None
        assert result.approved_by == "eng-team"
        assert result.reason == "Preview actions are read-only renders"

    def test_register_returns_exemption(self) -> None:
        reg = ExemptionRegistry.get_instance()
        exemption = reg.register("inbox", "ack_*", "Ack is metadata", "ops", "metadata_only")
        assert isinstance(exemption, RegisteredExemption)
        assert exemption.domain == "inbox"

    def test_non_exempt_action_returns_none(self) -> None:
        reg = ExemptionRegistry.get_instance()
        result = reg.is_exempt("openclaw", "execute_action")
        assert result is None

    def test_non_exempt_mutating_action(self) -> None:
        reg = ExemptionRegistry.get_instance()
        result = reg.is_exempt("inbox", "delete_message")
        assert result is None


# ------------------------------------------------------------------
# Wildcard domain matching
# ------------------------------------------------------------------


class TestWildcardDomain:
    """Verify wildcard domain matching in built-in and custom exemptions."""

    def test_wildcard_domain_matches_any(self) -> None:
        reg = ExemptionRegistry.get_instance()
        # Built-in "read_*" uses domain="*"
        for domain in ("openclaw", "canvas", "computer_use", "inbox", "shared_inbox"):
            result = reg.is_exempt(domain, "read_config")
            assert result is not None, f"Expected exemption for {domain}/read_config"

    def test_specific_domain_does_not_cross_match(self) -> None:
        reg = ExemptionRegistry.get_instance()
        reg.register("canvas", "render_*", "Canvas render", "system", "read_only")
        assert reg.is_exempt("canvas", "render_frame") is not None
        assert reg.is_exempt("openclaw", "render_frame") is None


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------


class TestSingleton:
    """Verify singleton behaviour."""

    def test_get_instance_returns_same_object(self) -> None:
        a = ExemptionRegistry.get_instance()
        b = ExemptionRegistry.get_instance()
        assert a is b

    def test_reset_instance_creates_new(self) -> None:
        a = ExemptionRegistry.get_instance()
        ExemptionRegistry.reset_instance()
        b = ExemptionRegistry.get_instance()
        assert a is not b

    def test_exemptions_property_returns_copy(self) -> None:
        reg = ExemptionRegistry.get_instance()
        exemptions = reg.exemptions
        assert isinstance(exemptions, list)
        assert len(exemptions) == 5  # 5 built-in exemptions
        # Mutating the copy should not affect the registry
        exemptions.clear()
        assert len(reg.exemptions) == 5

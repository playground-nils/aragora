"""Tests for OpenClaw Action Dispatcher -- real execution wiring."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from aragora.compat.openclaw.action_dispatcher import (
    DispatchResult,
    OpenClawActionDispatcher,
    _build_receipt_hash,
)
from aragora.computer_use.actions import (
    ActionResult,
    ActionType,
    ClickAction,
    ScreenshotAction,
    TypeAction,
)
from aragora.computer_use.policies import (
    ComputerPolicy,
    PolicyDecision,
    create_default_computer_policy,
    create_readonly_computer_policy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_executor(
    *,
    screenshot_b64: str = "dGVzdA==",
    current_url: str = "http://localhost:8080",
    execute_success: bool = True,
    navigate_success: bool = True,
) -> AsyncMock:
    """Create a mock executor satisfying the ActionExecutor protocol."""
    executor = AsyncMock()
    executor.start = AsyncMock()
    executor.stop = AsyncMock()
    executor.take_screenshot = AsyncMock(return_value=screenshot_b64)
    executor.get_current_url = AsyncMock(return_value=current_url)
    executor.navigate = AsyncMock(return_value=navigate_success)

    async def _execute(action):
        return ActionResult(
            action_id=action.action_id,
            action_type=action.action_type,
            success=execute_success,
            screenshot_b64=screenshot_b64,
            error=None if execute_success else "mock failure",
        )

    executor.execute = AsyncMock(side_effect=_execute)
    return executor


# ---------------------------------------------------------------------------
# Tests: Dispatch routes to correct handler
# ---------------------------------------------------------------------------


class TestDispatchRouting:
    """Verify actions are routed to the correct executor method."""

    @pytest.mark.asyncio
    async def test_click_dispatches_to_executor(self) -> None:
        """A 'click' action should call executor.execute with a ClickAction."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("click", {"coordinate": [100, 200]})

        assert result.success is True
        assert result.action_type == "click"
        assert result.receipt_hash is not None
        executor.execute.assert_called_once()
        action_arg = executor.execute.call_args[0][0]
        assert isinstance(action_arg, ClickAction)
        assert action_arg.x == 100
        assert action_arg.y == 200

    @pytest.mark.asyncio
    async def test_type_dispatches_to_executor(self) -> None:
        """A 'type' action should call executor.execute with a TypeAction."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("type", {"text": "hello"})

        assert result.success is True
        action_arg = executor.execute.call_args[0][0]
        assert isinstance(action_arg, TypeAction)
        assert action_arg.text == "hello"

    @pytest.mark.asyncio
    async def test_screenshot_dispatches_to_executor(self) -> None:
        """A 'screenshot' action should call executor.execute."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("screenshot", {})

        assert result.success is True
        action_arg = executor.execute.call_args[0][0]
        assert isinstance(action_arg, ScreenshotAction)

    @pytest.mark.asyncio
    async def test_navigate_dispatches_to_executor_navigate(self) -> None:
        """A 'navigate' action should call executor.navigate, not execute."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("navigate", {"url": "https://example.com"})

        assert result.success is True
        executor.navigate.assert_called_once_with("https://example.com")
        # Should NOT have called executor.execute
        executor.execute.assert_not_called()
        # URL should be updated
        assert dispatcher.current_url == "https://example.com"

    @pytest.mark.asyncio
    async def test_navigate_without_url_fails(self) -> None:
        """Navigate with empty URL should fail."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("navigate", {"url": ""})

        assert result.success is False
        assert "URL" in (result.error or "")

    @pytest.mark.asyncio
    async def test_extract_returns_screenshot(self) -> None:
        """An 'extract' action should return a screenshot."""
        executor = _make_mock_executor(screenshot_b64="abc123")
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch(
            "extract", {"selector": "div.content", "extract_type": "text"}
        )

        assert result.success is True
        assert result.screenshot_b64 == "abc123"
        executor.take_screenshot.assert_called()

    @pytest.mark.asyncio
    async def test_unknown_action_defaults_to_screenshot(self) -> None:
        """Unknown action types should default to screenshot via bridge."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("magic_wand", {"x": 42})

        assert result.success is True
        action_arg = executor.execute.call_args[0][0]
        assert isinstance(action_arg, ScreenshotAction)

    @pytest.mark.asyncio
    async def test_dispatch_when_not_running_fails(self) -> None:
        """Dispatch should fail if dispatcher is not running."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)
        # NOT calling dispatcher.start()

        result = await dispatcher.dispatch("click", {"coordinate": [0, 0]})

        assert result.success is False
        assert "not running" in (result.error or "").lower()


# ---------------------------------------------------------------------------
# Tests: Policy enforcement
# ---------------------------------------------------------------------------


class TestPolicyEnforcement:
    """Verify policy is checked before dispatch."""

    @pytest.mark.asyncio
    async def test_readonly_policy_blocks_click(self) -> None:
        """A read-only policy should deny click actions."""
        policy = create_readonly_computer_policy()
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(policy=policy, executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("click", {"coordinate": [100, 200]})

        assert result.success is False
        assert result.policy_decision == "deny"
        assert result.policy_reason != ""
        # Executor should NOT have been called
        executor.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_readonly_policy_allows_screenshot(self) -> None:
        """A read-only policy should allow screenshot actions."""
        policy = create_readonly_computer_policy()
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(policy=policy, executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("screenshot", {})

        assert result.success is True
        assert result.policy_decision == "allow"

    @pytest.mark.asyncio
    async def test_readonly_policy_allows_scroll(self) -> None:
        """A read-only policy should allow scroll actions."""
        policy = create_readonly_computer_policy()
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(policy=policy, executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("scroll", {"direction": "down"})

        assert result.success is True

    @pytest.mark.asyncio
    async def test_skip_policy_bypasses_check(self) -> None:
        """skip_policy=True should bypass policy enforcement."""
        policy = create_readonly_computer_policy()
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(policy=policy, executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("click", {"coordinate": [100, 200]}, skip_policy=True)

        assert result.success is True
        executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_default_policy_allows_standard_actions(self) -> None:
        """Default policy should allow standard UI actions."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        for action_type in ["click", "type", "screenshot", "scroll", "key"]:
            params = {}
            if action_type == "click":
                params = {"coordinate": [50, 50]}
            elif action_type == "type":
                params = {"text": "hi"}
            elif action_type == "key":
                params = {"key": "Return"}
            elif action_type == "scroll":
                params = {"direction": "down"}

            result = await dispatcher.dispatch(action_type, params)
            assert result.success is True, f"{action_type} should be allowed"


# ---------------------------------------------------------------------------
# Tests: Receipt generation
# ---------------------------------------------------------------------------


class TestReceiptGeneration:
    """Verify receipt hashes are generated after dispatch."""

    @pytest.mark.asyncio
    async def test_successful_dispatch_has_receipt(self) -> None:
        """Successful dispatch should include a receipt hash."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("screenshot", {})

        assert result.receipt_hash is not None
        assert len(result.receipt_hash) == 16  # SHA-256 truncated to 16

    @pytest.mark.asyncio
    async def test_failed_dispatch_has_receipt(self) -> None:
        """Even failed dispatches should generate a receipt."""
        executor = _make_mock_executor(execute_success=False)
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("click", {"coordinate": [0, 0]})

        assert result.receipt_hash is not None

    def test_receipt_hash_is_deterministic_format(self) -> None:
        """Receipt hash should be a hex string of length 16."""
        h = _build_receipt_hash("click", "action-123", True)
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    @pytest.mark.asyncio
    async def test_to_action_bundle_format(self) -> None:
        """to_action_bundle should produce ComputerUseActionBundle-compatible dict."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("click", {"coordinate": [10, 20]})
        bundle = dispatcher.to_action_bundle(result)

        assert bundle["harness_name"] == "openclaw-dispatcher"
        assert bundle["action_type"] == "click"
        assert bundle["exit_code"] == 0
        assert bundle["execution_time_seconds"] >= 0
        assert isinstance(bundle["policy_violations"], list)

    @pytest.mark.asyncio
    async def test_policy_denied_has_violation_in_bundle(self) -> None:
        """When policy denies, the bundle should record the violation."""
        policy = create_readonly_computer_policy()
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(policy=policy, executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("click", {"coordinate": [10, 20]})
        bundle = dispatcher.to_action_bundle(result)

        assert bundle["exit_code"] == 1
        assert len(bundle["policy_violations"]) > 0


# ---------------------------------------------------------------------------
# Tests: Audit logging and stats
# ---------------------------------------------------------------------------


class TestAuditAndStats:
    """Verify audit log and statistics."""

    @pytest.mark.asyncio
    async def test_audit_log_populated(self) -> None:
        """Dispatch should add entries to the audit log."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        await dispatcher.dispatch("click", {"coordinate": [0, 0]})
        await dispatcher.dispatch("screenshot", {})

        log = dispatcher.get_audit_log()
        assert len(log) == 2
        assert log[0]["action_type"] == "click"
        assert log[1]["action_type"] == "screenshot"

    @pytest.mark.asyncio
    async def test_stats_track_counts(self) -> None:
        """Stats should track dispatch and error counts."""
        executor = _make_mock_executor(execute_success=False)
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        await dispatcher.dispatch("click", {"coordinate": [0, 0]})
        stats = dispatcher.get_stats()

        assert stats["dispatch_count"] == 1
        assert stats["error_count"] == 1

    @pytest.mark.asyncio
    async def test_dispatch_result_to_dict(self) -> None:
        """DispatchResult.to_dict() should produce a serializable dict."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("screenshot", {})
        d = result.to_dict()

        assert isinstance(d, dict)
        assert d["success"] is True
        assert d["action_type"] == "screenshot"
        assert "duration_ms" in d
        assert "receipt_hash" in d


# ---------------------------------------------------------------------------
# Tests: Execution error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify error handling during dispatch."""

    @pytest.mark.asyncio
    async def test_executor_exception_returns_failure(self) -> None:
        """If executor.execute raises, dispatch should return failure."""
        executor = _make_mock_executor()
        executor.execute = AsyncMock(side_effect=RuntimeError("browser crashed"))
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("click", {"coordinate": [0, 0]})

        assert result.success is False
        assert "browser crashed" in (result.error or "")
        assert dispatcher.get_stats()["error_count"] == 1

    @pytest.mark.asyncio
    async def test_navigate_failure_returns_failure(self) -> None:
        """If executor.navigate returns False, dispatch should return failure."""
        executor = _make_mock_executor(navigate_success=False)
        dispatcher = OpenClawActionDispatcher(executor=executor)
        dispatcher._running = True

        result = await dispatcher.dispatch("navigate", {"url": "https://example.com"})

        assert result.success is False
        assert "failed" in (result.error or "").lower()


# ---------------------------------------------------------------------------
# Tests: Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    """Verify start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Context manager should start and stop the dispatcher."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)

        async with dispatcher:
            assert dispatcher.is_running
            result = await dispatcher.dispatch("screenshot", {})
            assert result.success is True

        assert not dispatcher.is_running

    @pytest.mark.asyncio
    async def test_start_twice_is_idempotent(self) -> None:
        """Calling start() twice should not error."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)

        await dispatcher.start()
        await dispatcher.start()  # should not raise
        assert dispatcher.is_running

        await dispatcher.stop()

    @pytest.mark.asyncio
    async def test_stop_when_not_running_is_safe(self) -> None:
        """Calling stop() when not running should not error."""
        executor = _make_mock_executor()
        dispatcher = OpenClawActionDispatcher(executor=executor)

        await dispatcher.stop()  # should not raise

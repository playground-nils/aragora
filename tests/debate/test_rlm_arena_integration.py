"""Tests for RLM Arena integration - wiring set_rlm_context into compression pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@dataclass
class _FakeCompressionResult:
    answer: str = "Compressed summary of the context"
    used_true_rlm: bool = False
    used_compression_fallback: bool = True


class _FakeEnv:
    def __init__(self, context: str = ""):
        self.context = context
        self.task = "test task"


class _FakeDebateContext:
    def __init__(self, context: str = "", prompt_builder: Any = None):
        self.env = _FakeEnv(context)
        self._prompt_builder = prompt_builder
        self.rlm_compressed_context: str | None = None
        self.use_compressed_context = False
        self.agents = []
        self.proposers = []


@pytest.fixture
def mock_prompt_builder():
    pb = MagicMock()
    pb.set_rlm_context = MagicMock()
    return pb


class TestSetRlmContextWiring:
    """Verify set_rlm_context is called on prompt builder after RLM compression."""

    @pytest.mark.asyncio
    async def test_rlm_context_set_on_prompt_builder_after_compression(self, mock_prompt_builder):
        """After successful compression, set_rlm_context should be called."""
        from aragora.debate.phases.context_init import ContextInitializer

        init = ContextInitializer.__new__(ContextInitializer)
        init._rlm = MagicMock()
        init._rlm.compress_and_query = AsyncMock(return_value=_FakeCompressionResult())

        ctx = _FakeDebateContext(
            context="x" * 5000,  # > 1000 chars to trigger compression
            prompt_builder=mock_prompt_builder,
        )

        await init._compress_context_with_rlm(ctx)

        # Verify compressed context was stored
        assert ctx.rlm_compressed_context == "Compressed summary of the context"
        # Verify set_rlm_context was called on the prompt builder
        mock_prompt_builder.set_rlm_context.assert_called_once()

        # Verify the RLMContext object has correct structure
        rlm_ctx = mock_prompt_builder.set_rlm_context.call_args[0][0]
        assert rlm_ctx.original_content == "x" * 5000
        assert rlm_ctx.original_tokens == 5000 // 4
        assert len(rlm_ctx.levels) == 1  # SUMMARY level

    @pytest.mark.asyncio
    async def test_rlm_context_not_set_when_compression_fails(self, mock_prompt_builder):
        """When compression returns no answer, set_rlm_context should NOT be called."""
        from aragora.debate.phases.context_init import ContextInitializer

        init = ContextInitializer.__new__(ContextInitializer)
        init._rlm = MagicMock()
        init._rlm.compress_and_query = AsyncMock(return_value=_FakeCompressionResult(answer=""))

        ctx = _FakeDebateContext(
            context="x" * 5000,
            prompt_builder=mock_prompt_builder,
        )

        await init._compress_context_with_rlm(ctx)

        mock_prompt_builder.set_rlm_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_rlm_context_not_set_when_context_too_short(self, mock_prompt_builder):
        """Context shorter than 1000 chars should skip compression entirely."""
        from aragora.debate.phases.context_init import ContextInitializer

        init = ContextInitializer.__new__(ContextInitializer)
        init._rlm = MagicMock()
        init._rlm.compress_and_query = AsyncMock()

        ctx = _FakeDebateContext(
            context="short context",
            prompt_builder=mock_prompt_builder,
        )

        await init._compress_context_with_rlm(ctx)

        init._rlm.compress_and_query.assert_not_called()
        mock_prompt_builder.set_rlm_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_rlm_context_not_set_when_no_prompt_builder(self):
        """When no prompt builder on context, compression still works (no crash)."""
        from aragora.debate.phases.context_init import ContextInitializer

        init = ContextInitializer.__new__(ContextInitializer)
        init._rlm = MagicMock()
        init._rlm.compress_and_query = AsyncMock(return_value=_FakeCompressionResult())

        ctx = _FakeDebateContext(
            context="x" * 5000,
            prompt_builder=None,
        )

        await init._compress_context_with_rlm(ctx)

        # Should still store compressed context even without prompt builder
        assert ctx.rlm_compressed_context == "Compressed summary of the context"

    @pytest.mark.asyncio
    async def test_rlm_context_compression_stats(self, mock_prompt_builder):
        """RLMContext should include compression stats (true_rlm vs fallback)."""
        from aragora.debate.phases.context_init import ContextInitializer

        init = ContextInitializer.__new__(ContextInitializer)
        init._rlm = MagicMock()
        init._rlm.compress_and_query = AsyncMock(
            return_value=_FakeCompressionResult(used_true_rlm=True, used_compression_fallback=False)
        )

        ctx = _FakeDebateContext(
            context="x" * 5000,
            prompt_builder=mock_prompt_builder,
        )

        await init._compress_context_with_rlm(ctx)

        rlm_ctx = mock_prompt_builder.set_rlm_context.call_args[0][0]
        assert rlm_ctx.compression_stats["used_true_rlm"] is True
        assert rlm_ctx.compression_stats["used_compression_fallback"] is False

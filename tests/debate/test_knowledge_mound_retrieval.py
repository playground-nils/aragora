"""Tests for the reusable Knowledge Mound retrieval interface."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from aragora.knowledge.mound.retrieval import (
    KnowledgeMoundRetriever,
    build_debate_knowledge_query,
)


def _make_item(
    *,
    item_id: str = "km-1",
    source: str = "debate",
    confidence: float | str = 0.9,
    content: str = "Use shared rate-limit buckets.",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=item_id,
        source=source,
        confidence=confidence,
        content=content,
    )


class TestKnowledgeMoundRetriever:
    @pytest.mark.asyncio
    async def test_prefers_visibility_query_with_auth_context(self):
        item = _make_item()
        mound = SimpleNamespace(
            query_with_visibility=AsyncMock(return_value=SimpleNamespace(items=[item])),
            query_semantic=AsyncMock(),
            query=AsyncMock(),
        )
        retriever = KnowledgeMoundRetriever(mound)
        auth_context = SimpleNamespace(user_id="user-1", workspace_id="ws-1", org_id="org-1")

        result = await retriever.retrieve("rate limiting", auth_context=auth_context, limit=4)

        assert result is not None
        assert result.item_ids == ["km-1"]
        assert "KNOWLEDGE MOUND CONTEXT" in result.formatted_context
        mound.query_with_visibility.assert_awaited_once_with(
            "rate limiting",
            actor_id="user-1",
            actor_workspace_id="ws-1",
            actor_org_id="org-1",
            limit=4,
        )
        mound.query_semantic.assert_not_called()

    @pytest.mark.asyncio
    async def test_falls_back_to_generic_query(self):
        item = _make_item(source="fact", confidence="verified")
        mound = SimpleNamespace(
            query=AsyncMock(return_value=SimpleNamespace(items=[item])),
        )
        retriever = KnowledgeMoundRetriever(mound)

        result = await retriever.retrieve("policy", limit=3)

        assert result is not None
        assert result.item_ids == ["km-1"]
        assert "**[fact]** (confidence: 95%)" in result.formatted_context
        mound.query.assert_awaited_once_with(
            query="policy",
            sources=("all",),
            limit=3,
            workspace_id=None,
        )

    @pytest.mark.asyncio
    async def test_retries_after_initialize_when_query_reports_uninitialized(self):
        item = _make_item()
        mound = SimpleNamespace(
            query_semantic=AsyncMock(
                side_effect=[RuntimeError("KnowledgeMound not initialized"), [item]]
            ),
            initialize=AsyncMock(),
        )
        retriever = KnowledgeMoundRetriever(mound)

        result = await retriever.retrieve("rate limiting")

        assert result is not None
        assert result.item_ids == ["km-1"]
        mound.initialize.assert_awaited_once()
        assert mound.query_semantic.await_count == 2


def test_build_debate_knowledge_query_includes_recent_developments():
    query = build_debate_knowledge_query(
        "Design a rate limiter",
        "Agent A proposed token buckets. Agent B raised fairness concerns.",
    )

    assert query.startswith("Design a rate limiter")
    assert "Recent debate developments:" in query
    assert "fairness concerns" in query

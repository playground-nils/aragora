"""Tests for ObsidianAdapter conflict resolution (last-write-wins)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from aragora.knowledge.mound.adapters.obsidian_adapter import (
    ConflictRecord,
    ObsidianAdapter,
)


def _make_adapter(**kwargs) -> ObsidianAdapter:
    """Create an ObsidianAdapter with a stubbed connector."""
    connector = MagicMock()
    connector.is_configured = True
    connector.name = "obsidian-test"
    connector._config = MagicMock()
    connector._config.watch_tags = []
    return ObsidianAdapter(connector=connector, workspace_id="test-ws", **kwargs)


# ---------- resolve_conflict unit tests ----------


class TestResolveConflict:
    """Tests for the resolve_conflict method."""

    def test_conflict_vault_wins_when_newer(self) -> None:
        adapter = _make_adapter()
        vault_ts = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)
        km_ts = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)

        winner = adapter.resolve_conflict("notes/a.md", vault_ts, km_ts)

        assert winner == "vault"
        assert len(adapter.conflict_log) == 1
        assert adapter.conflict_log[0].winner == "vault"

    def test_conflict_km_wins_when_newer(self) -> None:
        adapter = _make_adapter()
        vault_ts = datetime(2026, 3, 30, 8, 0, 0, tzinfo=timezone.utc)
        km_ts = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)

        winner = adapter.resolve_conflict("notes/b.md", vault_ts, km_ts)

        assert winner == "km"
        assert adapter.conflict_log[0].winner == "km"

    def test_conflict_vault_wins_on_tie(self) -> None:
        adapter = _make_adapter()
        ts = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)

        winner = adapter.resolve_conflict("notes/c.md", ts, ts)

        assert winner == "vault"

    def test_conflict_record_str(self) -> None:
        record = ConflictRecord(
            note_path="notes/d.md",
            vault_modified=datetime(2026, 4, 2, tzinfo=timezone.utc),
            km_modified=datetime(2026, 4, 1, tzinfo=timezone.utc),
            winner="vault",
        )
        s = str(record)
        assert "notes/d.md" in s
        assert "vault" in s

    def test_conflict_logged_for_review(self, caplog) -> None:
        adapter = _make_adapter()
        vault_ts = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)
        km_ts = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)

        with caplog.at_level(
            logging.INFO, logger="aragora.knowledge.mound.adapters.obsidian_adapter"
        ):
            adapter.resolve_conflict("notes/e.md", vault_ts, km_ts)

        assert any("conflict resolved" in r.message.lower() for r in caplog.records)

    def test_multiple_conflicts_accumulated(self) -> None:
        adapter = _make_adapter()
        ts1 = datetime(2026, 4, 2, tzinfo=timezone.utc)
        ts2 = datetime(2026, 4, 1, tzinfo=timezone.utc)

        adapter.resolve_conflict("a.md", ts1, ts2)
        adapter.resolve_conflict("b.md", ts2, ts1)

        assert len(adapter.conflict_log) == 2
        assert adapter.conflict_log[0].winner == "vault"
        assert adapter.conflict_log[1].winner == "km"


# ---------- _check_conflict integration tests ----------


class TestCheckConflict:
    """Tests for _check_conflict querying KM."""

    @pytest.mark.asyncio
    async def test_no_conflict_when_note_not_in_km(self) -> None:
        adapter = _make_adapter()
        mound = AsyncMock()
        mound.query = AsyncMock(return_value=[])

        result = await adapter._check_conflict(
            mound, "notes/new.md", datetime(2026, 4, 2, tzinfo=timezone.utc)
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_conflict_vault_wins_via_check(self) -> None:
        adapter = _make_adapter()
        mound = AsyncMock()
        mound.query = AsyncMock(
            return_value=[
                {
                    "metadata": {
                        "km_validated_at": "2026-04-01T00:00:00+00:00",
                    },
                }
            ]
        )

        result = await adapter._check_conflict(
            mound, "notes/x.md", datetime(2026, 4, 2, tzinfo=timezone.utc)
        )

        assert result == "vault"
        assert len(adapter.conflict_log) == 1

    @pytest.mark.asyncio
    async def test_conflict_km_wins_via_check(self) -> None:
        adapter = _make_adapter()
        mound = AsyncMock()
        mound.query = AsyncMock(
            return_value=[
                {
                    "metadata": {
                        "km_validated_at": "2026-04-03T00:00:00+00:00",
                    },
                }
            ]
        )

        result = await adapter._check_conflict(
            mound, "notes/y.md", datetime(2026, 4, 1, tzinfo=timezone.utc)
        )

        assert result == "km"

    @pytest.mark.asyncio
    async def test_conflict_check_handles_numeric_timestamp(self) -> None:
        adapter = _make_adapter()
        mound = AsyncMock()
        # 1711929600 = 2024-04-01T00:00:00 UTC
        mound.query = AsyncMock(return_value=[{"metadata": {"ingested_at": 1711929600.0}}])

        result = await adapter._check_conflict(
            mound, "notes/z.md", datetime(2026, 4, 2, tzinfo=timezone.utc)
        )

        assert result == "vault"

    @pytest.mark.asyncio
    async def test_conflict_check_returns_none_on_query_error(self) -> None:
        adapter = _make_adapter()
        mound = AsyncMock()
        mound.query = AsyncMock(side_effect=RuntimeError("db down"))

        result = await adapter._check_conflict(
            mound, "notes/err.md", datetime(2026, 4, 2, tzinfo=timezone.utc)
        )

        assert result is None
        assert len(adapter.conflict_log) == 0


# ---------- sync_to_km conflict integration ----------


class TestSyncConflictIntegration:
    """Test that sync_to_km uses conflict detection correctly."""

    @pytest.mark.asyncio
    async def test_sync_skips_note_when_km_wins_conflict(self) -> None:
        """When KM has a newer version, the vault note should be skipped."""
        adapter = _make_adapter()

        # Stub _resilient_call to be a no-op context manager
        class _NoopCtx:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        adapter._resilient_call = MagicMock(return_value=_NoopCtx())

        # Mock _check_conflict to return "km" (KM wins)
        adapter._check_conflict = AsyncMock(return_value="km")

        # Create a fake sync item
        item = MagicMock()
        item.source_id = "notes/stale.md"
        item.content = "old vault content"
        item.confidence = 0.9
        item.title = "Stale Note"
        item.url = ""
        item.metadata = {
            "tags": [],
            "note_type": "note",
            "modified_at": 1711929600.0,
        }

        # Mock connector.sync_items as an async generator
        async def _fake_sync_items(state, batch_size=1000):
            yield item

        adapter._connector.sync_items = _fake_sync_items

        mound = AsyncMock()
        result = await adapter.sync_to_km(knowledge_mound=mound)

        assert result.records_skipped >= 1
        assert result.records_synced == 0
        mound.ingest.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_ingests_note_when_vault_wins_conflict(self) -> None:
        """When vault has a newer version, the note should be ingested."""
        adapter = _make_adapter()

        class _NoopCtx:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        adapter._resilient_call = MagicMock(return_value=_NoopCtx())
        adapter._check_conflict = AsyncMock(return_value="vault")

        item = MagicMock()
        item.source_id = "notes/fresh.md"
        item.content = "new vault content"
        item.confidence = 0.95
        item.title = "Fresh Note"
        item.url = ""
        item.metadata = {
            "tags": [],
            "note_type": "note",
            "modified_at": 1743552000.0,
        }

        async def _fake_sync_items(state, batch_size=1000):
            yield item

        adapter._connector.sync_items = _fake_sync_items

        mound = AsyncMock()
        result = await adapter.sync_to_km(knowledge_mound=mound)

        assert result.records_synced == 1
        mound.ingest.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_ingests_when_no_conflict(self) -> None:
        """When there is no existing KM entry, ingestion proceeds normally."""
        adapter = _make_adapter()

        class _NoopCtx:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        adapter._resilient_call = MagicMock(return_value=_NoopCtx())
        adapter._check_conflict = AsyncMock(return_value=None)

        item = MagicMock()
        item.source_id = "notes/new.md"
        item.content = "brand new"
        item.confidence = 0.8
        item.title = "New Note"
        item.url = ""
        item.metadata = {
            "tags": [],
            "note_type": "note",
            "modified_at": 1743552000.0,
        }

        async def _fake_sync_items(state, batch_size=1000):
            yield item

        adapter._connector.sync_items = _fake_sync_items

        mound = AsyncMock()
        result = await adapter.sync_to_km(knowledge_mound=mound)

        assert result.records_synced == 1
        mound.ingest.assert_called_once()

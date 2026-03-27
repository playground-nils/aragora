"""Async-safety regression tests for AuditTrailHandler.

Verifies that _call_store_nonblocking offloads synchronous store
operations to a thread so the event loop stays responsive.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("ARAGORA_USE_SECRETS_MANAGER", "0")

from aragora.server.handlers.audit_trail import AuditTrailHandler


# ---------------------------------------------------------------------------
# Slow store stubs — simulate blocking I/O
# ---------------------------------------------------------------------------


class _SlowAuditTrailStore:
    """Store whose sync methods sleep, proving _call_store_nonblocking
    offloads them to a thread."""

    def list_trails(self, **kwargs: Any) -> list[dict[str, Any]]:
        time.sleep(0.2)
        return [
            {
                "trail_id": "trail-1",
                "gauntlet_id": "gauntlet-1",
                "created_at": "2026-03-26T00:00:00Z",
                "verdict": "APPROVED",
                "confidence": 0.9,
                "total_findings": 0,
                "duration_seconds": 1.0,
                "checksum": "abc",
            }
        ]

    def count_trails(self, **kwargs: Any) -> int:
        time.sleep(0.2)
        return 1

    def get_trail(self, trail_id: str) -> dict[str, Any] | None:
        time.sleep(0.2)
        return {
            "trail_id": trail_id,
            "gauntlet_id": "gauntlet-1",
            "created_at": "2026-03-26T00:00:00Z",
            "verdict": "APPROVED",
            "confidence": 0.9,
            "total_findings": 0,
            "duration_seconds": 1.0,
            "findings": [],
            "agents_involved": ["claude"],
            "checksum": "abc123",
        }

    def list_receipts(self, **kwargs: Any) -> list[dict[str, Any]]:
        time.sleep(0.2)
        return [
            {
                "receipt_id": "receipt-1",
                "gauntlet_id": "gauntlet-1",
                "timestamp": "2026-03-26T00:00:00Z",
                "verdict": "APPROVED",
                "confidence": 0.9,
                "risk_level": "LOW",
                "findings_count": 0,
                "checksum": "abc",
            }
        ]

    def count_receipts(self, **kwargs: Any) -> int:
        time.sleep(0.2)
        return 1

    def get_receipt(self, receipt_id: str) -> dict[str, Any] | None:
        time.sleep(0.2)
        return {
            "receipt_id": receipt_id,
            "gauntlet_id": "gauntlet-1",
            "timestamp": "2026-03-26T00:00:00Z",
            "verdict": "APPROVED",
            "confidence": 0.9,
            "risk_level": "LOW",
            "risk_score": 0.1,
            "robustness_score": 0.9,
            "findings": [],
            "agents_involved": ["claude"],
            "checksum": "abc123",
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_handler(store: Any) -> AuditTrailHandler:
    """Build handler with injected slow store, bypassing real DB init."""
    with patch(
        "aragora.storage.audit_trail_store.get_audit_trail_store",
        return_value=store,
    ):
        handler = AuditTrailHandler(server_context={})
    return handler


async def _ticker(duration: float = 0.35) -> int:
    """Count event-loop ticks while other coroutines run."""
    ticks = 0
    start = time.perf_counter()
    while time.perf_counter() - start < duration:
        await asyncio.sleep(0.01)
        ticks += 1
    return ticks


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_receipts_does_not_block_event_loop() -> None:
    handler = _make_handler(_SlowAuditTrailStore())
    task = asyncio.create_task(_ticker())
    await asyncio.sleep(0)

    result = await handler._call_store_nonblocking("list_receipts", limit=10, offset=0)
    ticks = await task

    assert isinstance(result, list)
    assert len(result) == 1
    assert ticks >= 10, f"Event loop was blocked (only {ticks} ticks)"


@pytest.mark.asyncio
async def test_get_receipt_does_not_block_event_loop() -> None:
    handler = _make_handler(_SlowAuditTrailStore())
    task = asyncio.create_task(_ticker())
    await asyncio.sleep(0)

    result = await handler._call_store_nonblocking("get_receipt", "receipt-123")
    ticks = await task

    assert result is not None
    assert result["receipt_id"] == "receipt-123"
    assert ticks >= 10, f"Event loop was blocked (only {ticks} ticks)"


@pytest.mark.asyncio
async def test_list_audit_trails_does_not_block_event_loop() -> None:
    handler = _make_handler(_SlowAuditTrailStore())
    task = asyncio.create_task(_ticker())
    await asyncio.sleep(0)

    result = await handler._call_store_nonblocking("list_trails", limit=10, offset=0)
    ticks = await task

    assert isinstance(result, list)
    assert len(result) == 1
    assert ticks >= 10, f"Event loop was blocked (only {ticks} ticks)"


@pytest.mark.asyncio
async def test_get_audit_trail_does_not_block_event_loop() -> None:
    handler = _make_handler(_SlowAuditTrailStore())
    task = asyncio.create_task(_ticker())
    await asyncio.sleep(0)

    result = await handler._call_store_nonblocking("get_trail", "trail-123")
    ticks = await task

    assert result is not None
    assert result["trail_id"] == "trail-123"
    assert ticks >= 10, f"Event loop was blocked (only {ticks} ticks)"

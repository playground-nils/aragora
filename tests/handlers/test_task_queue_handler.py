"""Tests for task queue REST endpoints."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from aragora.server.handlers.tasks.queue import TaskQueueHandler


def _body(result) -> dict:
    """Parse JSON body from a HandlerResult."""
    raw = result["body"]
    if isinstance(raw, (bytes, bytearray)):
        return json.loads(raw.decode("utf-8"))
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


@pytest.fixture
def handler():
    """Create a TaskQueueHandler with a minimal server context."""
    ctx: dict = {}
    return TaskQueueHandler(server_context=ctx)


class TestCanHandle:
    def test_queue_root(self, handler):
        assert handler.can_handle("/api/v1/tasks/queue") is True

    def test_queue_with_id(self, handler):
        assert handler.can_handle("/api/v1/tasks/queue/w-123") is True

    def test_leases(self, handler):
        assert handler.can_handle("/api/v1/tasks/leases") is True

    def test_salvage(self, handler):
        assert handler.can_handle("/api/v1/tasks/salvage") is True

    def test_unrelated_path(self, handler):
        assert handler.can_handle("/api/v1/debates") is False

    def test_v2_tasks_not_handled(self, handler):
        assert handler.can_handle("/api/v2/tasks") is False


class TestListQueue:
    def test_list_returns_empty_queue(self, handler):
        mock_queue = MagicMock()
        mock_queue.list_items.return_value = []
        with patch.object(TaskQueueHandler, "_get_queue", return_value=mock_queue):
            result = handler.handle("/api/v1/tasks/queue", {}, MagicMock())
        assert result["status"] == 200
        body = _body(result)
        assert body["data"] == []
        assert body["count"] == 0

    def test_list_with_status_filter(self, handler):
        mock_item = MagicMock()
        mock_item.to_dict.return_value = {
            "id": "w-1",
            "status": "pending",
            "title": "Fix bug",
        }
        mock_queue = MagicMock()
        mock_queue.list_items.return_value = [mock_item]
        with patch.object(TaskQueueHandler, "_get_queue", return_value=mock_queue):
            result = handler.handle("/api/v1/tasks/queue", {"status": "pending"}, MagicMock())
        assert result["status"] == 200
        body = _body(result)
        assert body["count"] == 1
        mock_queue.list_items.assert_called_once_with(status="pending", work_type=None, limit=20)

    def test_list_import_error_returns_503(self, handler):
        with patch.object(TaskQueueHandler, "_get_queue", side_effect=ImportError("no module")):
            result = handler.handle("/api/v1/tasks/queue", {}, MagicMock())
        assert result["status"] == 503


class TestGetTask:
    def test_get_existing_task(self, handler):
        mock_item = MagicMock()
        mock_item.to_dict.return_value = {"id": "w-1", "title": "Fix bug"}
        mock_queue = MagicMock()
        mock_queue.get.return_value = mock_item
        with patch.object(TaskQueueHandler, "_get_queue", return_value=mock_queue):
            result = handler.handle("/api/v1/tasks/queue/w-1", {}, MagicMock())
        assert result["status"] == 200
        body = _body(result)
        assert body["data"]["id"] == "w-1"

    def test_get_missing_task(self, handler):
        mock_queue = MagicMock()
        mock_queue.get.return_value = None
        with patch.object(TaskQueueHandler, "_get_queue", return_value=mock_queue):
            result = handler.handle("/api/v1/tasks/queue/missing", {}, MagicMock())
        assert result["status"] == 404


class TestListLeases:
    def test_list_active_leases(self, handler):
        mock_lease = MagicMock()
        mock_lease.lease_id = "l-1"
        mock_lease.task_id = "t-1"
        mock_lease.title = "Fix bug"
        mock_lease.owner_agent = "claude"
        mock_lease.owner_session_id = "s-1"
        mock_lease.branch = "fix/bug"
        mock_lease.worktree_path = "/tmp/wt"
        mock_lease.status = "active"
        mock_lease.expires_at = "2026-03-18T12:00:00+00:00"
        mock_store = MagicMock()
        mock_store.list_active_leases.return_value = [mock_lease]
        with patch.object(TaskQueueHandler, "_get_store", return_value=mock_store):
            result = handler.handle("/api/v1/tasks/leases", {}, MagicMock())
        assert result["status"] == 200
        body = _body(result)
        assert body["count"] == 1
        assert body["data"][0]["lease_id"] == "l-1"

    def test_list_leases_empty(self, handler):
        mock_store = MagicMock()
        mock_store.list_active_leases.return_value = []
        with patch.object(TaskQueueHandler, "_get_store", return_value=mock_store):
            result = handler.handle("/api/v1/tasks/leases", {}, MagicMock())
        assert result["status"] == 200
        body = _body(result)
        assert body["count"] == 0


class TestListSalvage:
    def test_list_salvage_candidates(self, handler):
        mock_candidate = MagicMock()
        mock_candidate.to_dict.return_value = {
            "candidate_id": "sc-1",
            "source_kind": "worktree",
            "summary": "Abandoned work",
        }
        mock_store = MagicMock()
        mock_store.list_salvage_candidates.return_value = [mock_candidate]
        with patch.object(TaskQueueHandler, "_get_store", return_value=mock_store):
            result = handler.handle("/api/v1/tasks/salvage", {}, MagicMock())
        assert result["status"] == 200
        body = _body(result)
        assert body["count"] == 1


class TestClaimEndpoint:
    def test_claim_creates_lease(self, handler):
        mock_lease = MagicMock()
        mock_lease.lease_id = "l-new"
        mock_lease.task_id = "t-1"
        mock_lease.owner_agent = "claude"
        mock_lease.expires_at = "2026-03-18T20:00:00+00:00"
        mock_store = MagicMock()
        mock_store.claim_lease.return_value = mock_lease
        with patch.object(TaskQueueHandler, "_get_store", return_value=mock_store):
            with patch.object(handler, "read_json_body", return_value={"owner_agent": "claude"}):
                result = handler.handle_post("/api/v1/tasks/queue/t-1/claim", {}, MagicMock())
        assert result["status"] == 201
        body = _body(result)
        assert body["data"]["lease_id"] == "l-new"

    def test_claim_conflict_returns_409(self, handler):
        from aragora.nomic.dev_coordination import LeaseConflictError

        mock_store = MagicMock()
        mock_store.claim_lease.side_effect = LeaseConflictError([])
        with patch.object(TaskQueueHandler, "_get_store", return_value=mock_store):
            with patch.object(handler, "read_json_body", return_value={"owner_agent": "w2"}):
                result = handler.handle_post("/api/v1/tasks/queue/t-1/claim", {}, MagicMock())
        assert result["status"] == 409


class TestReleaseEndpoint:
    def test_release_delegates_to_store(self, handler):
        mock_lease = MagicMock()
        mock_lease.lease_id = "l-1"
        mock_store = MagicMock()
        mock_store.release_lease.return_value = mock_lease
        with patch.object(TaskQueueHandler, "_get_store", return_value=mock_store):
            with patch.object(handler, "read_json_body", return_value={"lease_id": "l-1"}):
                result = handler.handle_post("/api/v1/tasks/queue/t-1/release", {}, MagicMock())
        assert result["status"] == 200
        body = _body(result)
        assert body["data"]["released"] is True

    def test_release_not_found_returns_404(self, handler):
        mock_store = MagicMock()
        mock_store.release_lease.side_effect = KeyError("not found")
        with patch.object(TaskQueueHandler, "_get_store", return_value=mock_store):
            with patch.object(handler, "read_json_body", return_value={}):
                result = handler.handle_post("/api/v1/tasks/queue/t-1/release", {}, MagicMock())
        assert result["status"] == 404


class TestCompleteEndpoint:
    def test_complete_generates_receipt(self, handler):
        mock_receipt = MagicMock()
        mock_receipt.receipt_id = "r-1"
        mock_receipt.lease_id = "l-1"
        mock_receipt.confidence = 0.95
        mock_receipt.artifact_hash = "abc123"
        mock_store = MagicMock()
        mock_store.record_completion.return_value = mock_receipt
        body = {
            "lease_id": "l-1",
            "owner_agent": "claude",
            "confidence": 0.95,
        }
        with patch.object(TaskQueueHandler, "_get_store", return_value=mock_store):
            with patch.object(handler, "read_json_body", return_value=body):
                result = handler.handle_post("/api/v1/tasks/queue/t-1/complete", {}, MagicMock())
        assert result["status"] == 200
        parsed = _body(result)
        assert parsed["data"]["receipt_id"] == "r-1"
        assert parsed["data"]["confidence"] == 0.95


class TestStats:
    def test_stats_returns_statistics(self, handler):
        mock_queue = MagicMock()
        mock_queue.get_statistics.return_value = {
            "total_items": 10,
            "pending_items": 5,
            "completed_items": 2,
        }
        with patch.object(TaskQueueHandler, "_get_queue", return_value=mock_queue):
            result = handler.handle("/api/v1/tasks/queue/stats", {}, MagicMock())
        assert result["status"] == 200
        body = _body(result)
        assert body["data"]["total_items"] == 10

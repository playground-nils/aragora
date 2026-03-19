"""Tests for the public task queue handler."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from aragora.nomic.global_work_queue import WorkStatus, WorkType
from aragora.server.handlers.tasks.queue import TaskQueueHandler


def _body(result) -> dict:
    raw = result.body
    if isinstance(raw, (bytes, bytearray)):
        return json.loads(raw.decode("utf-8"))
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


@pytest.fixture
def handler() -> TaskQueueHandler:
    return TaskQueueHandler({})


class TestCanHandle:
    def test_task_queue_paths(self, handler: TaskQueueHandler):
        assert handler.can_handle("/api/v1/tasks/queue")
        assert handler.can_handle("/api/v1/tasks/queue/task:demo")
        assert handler.can_handle("/api/v1/tasks/leases")
        assert handler.can_handle("/api/v1/tasks/leases/lease-1/release")
        assert handler.can_handle("/api/v1/tasks/salvage")
        assert not handler.can_handle("/api/v2/tasks")


class TestReads:
    def test_list_queue_maps_status_and_work_type(self, handler: TaskQueueHandler):
        queue = MagicMock()
        item = MagicMock()
        item.to_dict.return_value = {
            "id": "task:demo",
            "status": "pending",
            "work_type": "custom",
            "title": "Demo task",
        }
        queue.list_items.return_value = [item]

        with (
            patch.object(handler, "require_auth_or_error", return_value=(MagicMock(), None)),
            patch.object(handler, "require_permission_or_error", return_value=(MagicMock(), None)),
            patch.object(handler, "_get_queue", return_value=queue),
        ):
            result = handler.handle(
                "/api/v1/tasks/queue",
                {"status": "pending", "work_type": "custom", "limit": "5"},
                MagicMock(),
            )

        assert result.status_code == 200
        payload = _body(result)
        assert payload["count"] == 1
        queue.list_items.assert_called_once_with(
            status=WorkStatus.PENDING,
            work_type=WorkType.CUSTOM,
            limit=5,
        )

    def test_invalid_queue_status_returns_400(self, handler: TaskQueueHandler):
        with (
            patch.object(handler, "require_auth_or_error", return_value=(MagicMock(), None)),
            patch.object(handler, "require_permission_or_error", return_value=(MagicMock(), None)),
        ):
            result = handler.handle("/api/v1/tasks/queue", {"status": "bogus"}, MagicMock())

        assert result.status_code == 400


class TestWrites:
    def test_claim_uses_task_metadata(self, handler: TaskQueueHandler):
        queue = MagicMock()
        item = MagicMock()
        item.to_dict.return_value = {
            "id": "task:demo",
            "title": "Refactor queue API",
            "metadata": {
                "allowed_paths": ["aragora/nomic/dev_coordination.py"],
                "acceptance_checks": ["pytest tests/nomic/test_dev_coordination.py -q"],
            },
        }
        queue.get.return_value = item

        lease = MagicMock()
        lease.to_dict.return_value = {
            "lease_id": "lease-1",
            "task_id": "task:demo",
            "status": "active",
        }
        store = MagicMock()
        store.claim_lease.return_value = lease

        with (
            patch.object(handler, "require_auth_or_error", return_value=(MagicMock(), None)),
            patch.object(handler, "require_permission_or_error", return_value=(MagicMock(), None)),
            patch.object(handler, "_get_queue", return_value=queue),
            patch.object(handler, "_get_store", return_value=store),
            patch.object(handler, "read_json_body", return_value={"owner_agent": "codex"}),
        ):
            result = handler.handle_post("/api/v1/tasks/queue/task:demo/claim", {}, MagicMock())

        assert result.status_code == 201
        payload = _body(result)
        assert payload["data"]["lease_id"] == "lease-1"
        kwargs = store.claim_lease.call_args.kwargs
        assert kwargs["task_id"] == "task:demo"
        assert kwargs["title"] == "Refactor queue API"
        assert kwargs["allowed_globs"] == ["aragora/nomic/dev_coordination.py"]
        assert kwargs["expected_tests"] == ["pytest tests/nomic/test_dev_coordination.py -q"]

    def test_release_is_lease_scoped(self, handler: TaskQueueHandler):
        lease = MagicMock()
        lease.to_dict.return_value = {"lease_id": "lease-1", "status": "released"}
        store = MagicMock()
        store.release_lease.return_value = lease

        with (
            patch.object(handler, "require_auth_or_error", return_value=(MagicMock(), None)),
            patch.object(handler, "require_permission_or_error", return_value=(MagicMock(), None)),
            patch.object(handler, "_get_store", return_value=store),
            patch.object(handler, "read_json_body", return_value={}),
        ):
            result = handler.handle_post("/api/v1/tasks/leases/lease-1/release", {}, MagicMock())

        assert result.status_code == 200
        store.release_lease.assert_called_once_with("lease-1")

    def test_complete_uses_active_lease_defaults(self, handler: TaskQueueHandler):
        active_lease = SimpleNamespace(
            lease_id="lease-1",
            owner_agent="codex",
            owner_session_id="session-1",
            branch="codex/demo",
            worktree_path="/tmp/wt",
        )
        receipt = MagicMock()
        receipt.to_dict.return_value = {"receipt_id": "receipt-1", "lease_id": "lease-1"}
        store = MagicMock()
        store.list_active_leases.return_value = [active_lease]
        store.record_completion.return_value = receipt

        with (
            patch.object(handler, "require_auth_or_error", return_value=(MagicMock(), None)),
            patch.object(handler, "require_permission_or_error", return_value=(MagicMock(), None)),
            patch.object(handler, "_get_store", return_value=store),
            patch.object(
                handler,
                "read_json_body",
                return_value={"head_sha": "abc123", "confidence": 0.9},
            ),
        ):
            result = handler.handle_post("/api/v1/tasks/leases/lease-1/complete", {}, MagicMock())

        assert result.status_code == 200
        payload = _body(result)
        assert payload["data"]["receipt_id"] == "receipt-1"
        kwargs = store.record_completion.call_args.kwargs
        assert kwargs["lease_id"] == "lease-1"
        assert kwargs["owner_agent"] == "codex"
        assert kwargs["owner_session_id"] == "session-1"
        assert kwargs["branch"] == "codex/demo"
        assert kwargs["worktree_path"] == "/tmp/wt"
        assert kwargs["head_sha"] == "abc123"

    def test_sync_projects_pending_and_developer_work(self, handler: TaskQueueHandler):
        store = MagicMock()
        store.sync_developer_task_queue.return_value = {"created": 2}
        store.sync_pending_work_queue.return_value = {"updated": 1}
        queue = MagicMock()

        with (
            patch.object(handler, "require_auth_or_error", return_value=(MagicMock(), None)),
            patch.object(handler, "require_permission_or_error", return_value=(MagicMock(), None)),
            patch.object(handler, "_get_store", return_value=store),
            patch.object(handler, "_get_queue", return_value=queue),
            patch.object(handler, "read_json_body", return_value={}),
        ):
            result = handler.handle_post("/api/v1/tasks/queue/sync", {}, MagicMock())

        assert result.status_code == 200
        payload = _body(result)
        assert payload["data"]["developer_tasks"]["created"] == 2
        assert payload["data"]["pending"]["updated"] == 1

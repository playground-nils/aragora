"""Task Queue Handler -- REST exposure for DevCoordinationStore and GlobalWorkQueue.

Routes:
    GET  /api/v1/tasks/queue              - List queued work items
    GET  /api/v1/tasks/queue/{task_id}    - Get specific task
    POST /api/v1/tasks/queue/{task_id}/claim    - Claim a task
    POST /api/v1/tasks/queue/{task_id}/release  - Release a claimed task
    POST /api/v1/tasks/queue/{task_id}/complete - Mark task complete
    GET  /api/v1/tasks/leases             - List active leases
    GET  /api/v1/tasks/salvage            - List salvage candidates
    GET  /api/v1/tasks/queue/stats        - Get queue statistics
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any

from aragora.server.handlers.base import (
    BaseHandler,
    HandlerResult,
    error_response,
    handle_errors,
    json_response,
)

logger = logging.getLogger(__name__)


def _await_if_coro(result: Any) -> Any:
    """Resolve a coroutine to its value when called from a sync context."""
    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


class TaskQueueHandler(BaseHandler):
    """Handler for task queue REST endpoints.

    Exposes the GlobalWorkQueue (list/get work items, statistics) and
    DevCoordinationStore (leases, salvage, claim/release/complete) over
    a JSON REST interface.
    """

    ROUTES = [
        "/api/v1/tasks/queue",
        "/api/v1/tasks/queue/*",
        "/api/v1/tasks/leases",
        "/api/v1/tasks/salvage",
    ]

    def can_handle(self, path: str, method: str = "GET") -> bool:
        """Return True if this handler should process the given path."""
        return (
            path.startswith("/api/v1/tasks/queue")
            or path == "/api/v1/tasks/leases"
            or path == "/api/v1/tasks/salvage"
        )

    # ------------------------------------------------------------------
    # Lazy accessors (avoid import-time coupling)
    # ------------------------------------------------------------------

    @staticmethod
    def _get_store():  # type: ignore[return]
        from aragora.nomic.dev_coordination import DevCoordinationStore

        return DevCoordinationStore()

    @staticmethod
    def _get_queue():  # type: ignore[return]
        from aragora.nomic.global_work_queue import GlobalWorkQueue

        return GlobalWorkQueue()

    # ------------------------------------------------------------------
    # GET dispatcher
    # ------------------------------------------------------------------

    def handle(self, path: str, query_params: dict[str, Any], handler: Any) -> HandlerResult | None:
        """Handle GET requests for task-queue endpoints."""
        if not self.can_handle(path):
            return None

        if path == "/api/v1/tasks/leases":
            return self._handle_list_leases()
        if path == "/api/v1/tasks/salvage":
            return self._handle_list_salvage()
        if path == "/api/v1/tasks/queue/stats":
            return self._handle_stats()
        if path == "/api/v1/tasks/queue":
            return self._handle_list_queue(query_params)

        # /api/v1/tasks/queue/{task_id}
        parts = path.rstrip("/").split("/")
        # ["", "api", "v1", "tasks", "queue", "<task_id>"]
        if len(parts) == 6 and parts[4] == "queue":
            task_id = parts[5]
            return self._handle_get_task(task_id)

        return error_response("Not found", 404)

    # ------------------------------------------------------------------
    # POST dispatcher
    # ------------------------------------------------------------------

    @handle_errors("task queue")
    def handle_post(
        self, path: str, query_params: dict[str, Any], handler: Any
    ) -> HandlerResult | None:
        """Handle POST requests for task-queue endpoints."""
        if not self.can_handle(path):
            return None

        parts = path.rstrip("/").split("/")

        # /api/v1/tasks/queue/{task_id}/{action}
        # ["", "api", "v1", "tasks", "queue", "<task_id>", "<action>"]
        if len(parts) == 7 and parts[4] == "queue":
            task_id = parts[5]
            action = parts[6]
            body = self.read_json_body(handler) or {}

            if action == "claim":
                return self._handle_claim(task_id, body)
            if action == "release":
                return self._handle_release(task_id, body)
            if action == "complete":
                return self._handle_complete(task_id, body)

        return error_response("Not found", 404)

    # ------------------------------------------------------------------
    # GET handlers
    # ------------------------------------------------------------------

    def _handle_list_queue(self, query_params: dict[str, Any]) -> HandlerResult:
        """List queued work items with optional filters."""
        try:
            queue = self._get_queue()
            status = query_params.get("status")
            work_type = query_params.get("work_type")
            try:
                limit = int(query_params.get("limit", 20))
            except (ValueError, TypeError):
                limit = 20
            limit = max(1, min(limit, 100))

            items = _await_if_coro(
                queue.list_items(status=status, work_type=work_type, limit=limit)
            )
            serialized = [i.to_dict() if hasattr(i, "to_dict") else i for i in items]
            return json_response({"data": serialized, "count": len(serialized)})
        except (ImportError, RuntimeError) as exc:
            logger.warning("Task queue unavailable: %s", exc)
            return error_response("Task queue unavailable", 503)

    def _handle_get_task(self, task_id: str) -> HandlerResult:
        """Get a specific task by ID."""
        try:
            queue = self._get_queue()
            item = _await_if_coro(queue.get(task_id))
            if item is None:
                return error_response(f"Task {task_id} not found", 404)
            serialized = item.to_dict() if hasattr(item, "to_dict") else item
            return json_response({"data": serialized})
        except (ImportError, RuntimeError) as exc:
            logger.warning("Task queue unavailable: %s", exc)
            return error_response("Task queue unavailable", 503)

    def _handle_list_leases(self) -> HandlerResult:
        """List all active leases."""
        try:
            store = self._get_store()
            leases = store.list_active_leases()
            serialized = [
                {
                    "lease_id": lease.lease_id,
                    "task_id": lease.task_id,
                    "title": lease.title,
                    "owner_agent": lease.owner_agent,
                    "owner_session_id": lease.owner_session_id,
                    "branch": lease.branch,
                    "worktree_path": lease.worktree_path,
                    "status": lease.status,
                    "expires_at": lease.expires_at,
                }
                for lease in leases
            ]
            return json_response({"data": serialized, "count": len(serialized)})
        except (ImportError, RuntimeError, AttributeError) as exc:
            logger.warning("Lease listing unavailable: %s", exc)
            return error_response("Lease service unavailable", 503)

    def _handle_list_salvage(self) -> HandlerResult:
        """List salvage candidates."""
        try:
            store = self._get_store()
            candidates = store.list_salvage_candidates()
            serialized = [c.to_dict() for c in candidates]
            return json_response({"data": serialized, "count": len(serialized)})
        except (ImportError, RuntimeError, AttributeError) as exc:
            logger.warning("Salvage listing unavailable: %s", exc)
            return error_response("Salvage service unavailable", 503)

    def _handle_stats(self) -> HandlerResult:
        """Return queue statistics."""
        try:
            queue = self._get_queue()
            stats = _await_if_coro(queue.get_statistics())
            return json_response({"data": stats})
        except (ImportError, RuntimeError) as exc:
            logger.warning("Queue stats unavailable: %s", exc)
            return error_response("Queue stats unavailable", 503)

    # ------------------------------------------------------------------
    # POST handlers
    # ------------------------------------------------------------------

    def _handle_claim(self, task_id: str, body: dict[str, Any]) -> HandlerResult:
        """Claim a task by creating a work lease."""
        owner_agent = body.get("owner_agent", body.get("worker_id", "unknown"))
        ttl_hours = float(body.get("ttl_hours", 8.0))
        session_id = body.get("session_id", "")
        branch = body.get("branch", "")
        worktree_path = body.get("worktree_path", "")
        title = body.get("title", f"Claimed task {task_id}")
        try:
            store = self._get_store()
            lease = store.claim_lease(
                task_id=task_id,
                title=title,
                owner_agent=owner_agent,
                owner_session_id=session_id,
                branch=branch,
                worktree_path=worktree_path,
                ttl_hours=ttl_hours,
            )
            return json_response(
                {
                    "data": {
                        "lease_id": lease.lease_id,
                        "task_id": lease.task_id,
                        "owner_agent": lease.owner_agent,
                        "expires_at": lease.expires_at,
                    }
                },
                status=201,
            )
        except ValueError as exc:
            # LeaseConflictError is a ValueError subclass
            return error_response(str(exc), 409)
        except (ImportError, RuntimeError, AttributeError) as exc:
            logger.warning("Claim failed: %s", exc)
            return error_response("Claim service unavailable", 503)

    def _handle_release(self, task_id: str, body: dict[str, Any]) -> HandlerResult:
        """Release a claimed task."""
        lease_id = body.get("lease_id", task_id)
        try:
            store = self._get_store()
            lease = store.release_lease(lease_id)
            return json_response({"data": {"released": True, "lease_id": lease.lease_id}})
        except KeyError:
            return error_response(f"Lease {lease_id} not found", 404)
        except (ImportError, RuntimeError) as exc:
            logger.warning("Release failed: %s", exc)
            return error_response("Release service unavailable", 503)

    def _handle_complete(self, task_id: str, body: dict[str, Any]) -> HandlerResult:
        """Mark a task as complete and generate a receipt."""
        try:
            store = self._get_store()
            receipt = store.record_completion(
                lease_id=body.get("lease_id", task_id),
                owner_agent=body.get("owner_agent", "unknown"),
                owner_session_id=body.get("session_id", ""),
                branch=body.get("branch", ""),
                worktree_path=body.get("worktree_path", ""),
                commit_shas=body.get("commit_shas", []),
                changed_paths=body.get("changed_paths", []),
                tests_run=body.get("tests_run", []),
                assumptions=body.get("assumptions", []),
                blockers=body.get("blockers", []),
                confidence=float(body.get("confidence", 0.0)),
            )
            return json_response(
                {
                    "data": {
                        "receipt_id": receipt.receipt_id,
                        "lease_id": receipt.lease_id,
                        "confidence": receipt.confidence,
                        "artifact_hash": receipt.artifact_hash,
                    }
                }
            )
        except (ImportError, RuntimeError, AttributeError) as exc:
            logger.warning("Complete failed: %s", exc)
            return error_response("Complete service unavailable", 503)

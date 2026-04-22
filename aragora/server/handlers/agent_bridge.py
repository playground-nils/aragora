"""Read-only HTTP handler for CLI-resume agent bridge runs."""

from __future__ import annotations

__all__ = ["AgentBridgeHandler"]

from pathlib import Path
from typing import Any
import os

from aragora.server.versioning.compat import strip_version_prefix
from aragora.swarm.agent_bridge import AgentBridgeBroker
from aragora.swarm.agent_bridge import BridgeRun
from aragora.swarm.agent_bridge import BridgeSession
from aragora.swarm.agent_bridge import TurnRecord

from .base import BaseHandler, HandlerResult, error_response, json_response


def _bridge_repo_root() -> Path:
    override = os.environ.get("ARAGORA_AGENT_BRIDGE_REPO")
    if override:
        return Path(override).resolve()
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists() or (candidate / ".aragora").exists():
            return candidate
    return cwd


def _parse_limit(raw: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(str(raw or "").strip())
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def _footer_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    footer = payload.get("footer")
    if isinstance(footer, dict):
        return footer
    parsed_turn = payload.get("parsed_turn")
    if isinstance(parsed_turn, dict):
        nested = parsed_turn.get("footer")
        if isinstance(nested, dict):
            return nested
    return None


def _event_reason(payload: dict[str, Any]) -> str | None:
    error = payload.get("error")
    if isinstance(error, str) and error.strip():
        return error.strip()
    errors = payload.get("errors")
    if isinstance(errors, list):
        parts = [str(item).strip() for item in errors if str(item).strip()]
        if parts:
            return "; ".join(parts)
    return None


def _event_summary(record: TurnRecord) -> str:
    footer = _footer_payload(record.payload)
    if footer:
        summary = footer.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
    reason = _event_reason(record.payload)
    if reason:
        return reason
    return ""


class AgentBridgeHandler(BaseHandler):
    """Expose persisted agent bridge runs to the Autonomous UI."""

    ROUTES = [
        "/api/agent-bridge/*",
        "/api/v1/agent-bridge/*",
    ]

    ROUTE_PREFIXES = [
        "/api/agent-bridge",
        "/api/agent-bridge/",
        "/api/v1/agent-bridge",
        "/api/v1/agent-bridge/",
    ]

    def __init__(self, ctx: dict[str, Any] | None = None) -> None:
        self.ctx = ctx or {}
        self._broker = AgentBridgeBroker(_bridge_repo_root())

    def can_handle(self, path: str, method: str = "GET") -> bool:
        if method.upper() != "GET":
            return False
        normalized = strip_version_prefix(path)
        return normalized == "/api/agent-bridge" or normalized.startswith("/api/agent-bridge/")

    def handle(self, path: str, query_params: dict[str, Any], handler: Any) -> HandlerResult | None:
        normalized = strip_version_prefix(path).rstrip("/")
        subpath = (
            normalized[len("/api/agent-bridge") :]
            if normalized.startswith("/api/agent-bridge")
            else ""
        )

        if subpath in ("", "/"):
            return error_response("Not found", 404)

        if subpath == "/runs":
            limit = _parse_limit(query_params.get("limit"), default=50, minimum=1, maximum=500)
            return self._list_runs(limit=limit)

        if not subpath.startswith("/runs/"):
            return error_response("Not found", 404)

        tail = subpath[len("/runs/") :]
        segments = [segment for segment in tail.split("/") if segment]
        if not segments:
            return error_response("Not found", 404)

        run_id = segments[0]
        if len(segments) == 1:
            return self._get_run(run_id)
        if len(segments) == 2 and segments[1] == "events":
            limit = _parse_limit(query_params.get("limit"), default=200, minimum=1, maximum=5000)
            return self._get_events(run_id, limit=limit)
        return error_response("Not found", 404)

    def _list_runs(self, *, limit: int) -> HandlerResult:
        runs = self._broker.list_runs()[:limit]
        payload = [self._serialize_run(run) for run in runs]
        return json_response({"runs": payload, "total": len(payload)})

    def _get_run(self, run_id: str) -> HandlerResult:
        try:
            run = self._broker.load_run(run_id)
        except FileNotFoundError:
            return error_response(f"Run not found: {run_id}", 404)
        registry = self._broker.load_sessions(run_id)
        return json_response(
            {
                "run": self._serialize_run(run),
                "sessions": [
                    self._serialize_session(name, session)
                    for name, session in sorted(registry.sessions.items())
                ],
            }
        )

    def _get_events(self, run_id: str, *, limit: int) -> HandlerResult:
        try:
            self._broker.load_run(run_id)
        except FileNotFoundError:
            return error_response(f"Run not found: {run_id}", 404)
        events = self._broker.load_events(run_id)
        if limit > 0:
            events = events[-limit:]
        payload = [self._serialize_event(event) for event in events]
        return json_response({"events": payload, "count": len(payload)})

    def _serialize_run(self, run: BridgeRun) -> dict[str, Any]:
        registry = self._broker.load_sessions(run.run_id)
        events = self._broker.load_events(run.run_id)
        last_summary = ""
        for event in reversed(events):
            last_summary = _event_summary(event)
            if last_summary:
                break
        return {
            "run_id": run.run_id,
            "task": run.task,
            "status": run.status,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
            "completed_at": run.completed_at,
            "next_actor": run.next_actor,
            "last_turn_index": run.last_turn_index,
            "last_summary": last_summary,
            "worktree_path": run.worktree_path,
            "worktree_agent_slug": run.worktree_agent_slug,
            "session_count": len(registry.sessions),
            "agents": [
                self._serialize_agent(name, session)
                for name, session in sorted(registry.sessions.items())
            ],
        }

    def _serialize_agent(self, name: str, session: BridgeSession) -> dict[str, Any]:
        return {
            "name": name,
            "harness": session.harness,
            "role": session.role,
            "model": session.model or None,
            "turn_count": session.last_turn_index,
            "status": session.session_status,
        }

    def _serialize_session(self, name: str, session: BridgeSession) -> dict[str, Any]:
        return {
            "name": name,
            "harness": session.harness,
            "role": session.role,
            "model": session.model or None,
            "session_id": session.session_id,
            "worktree_path": session.worktree_path,
            "worktree_agent_slug": session.worktree_agent_slug,
            "branch": session.branch,
            "session_status": session.session_status,
            "created_at": session.started_at,
            "updated_at": session.last_completed_at,
            "turn_count": session.last_turn_index,
        }

    def _serialize_event(self, event: TurnRecord) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "timestamp": event.ts,
            "type": event.event_type,
            "run_id": event.run_id,
            "actor": event.role,
            "harness": event.harness,
            "session_id": event.session_id,
            "parse_status": event.parse_status,
        }
        footer = _footer_payload(event.payload)
        if footer is not None:
            payload["footer"] = footer
        reason = _event_reason(event.payload)
        if reason:
            payload["reason"] = reason
        artifact_path = event.payload.get("transcript_path")
        if isinstance(artifact_path, str) and artifact_path.strip():
            payload["artifact_path"] = artifact_path
        next_actor = event.payload.get("next_actor")
        if isinstance(next_actor, str) and next_actor.strip():
            payload["next_actor"] = next_actor
        return payload

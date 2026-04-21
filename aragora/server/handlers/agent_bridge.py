"""Read-only HTTP handler for CLI-resume agent bridge runs."""

from __future__ import annotations

__all__ = ["AgentBridgeHandler"]

from pathlib import Path
from typing import Any
import os

from aragora.server.versioning.compat import strip_version_prefix
from aragora.swarm.agent_bridge import AgentBridgeBroker

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
        runs = self._broker.list_runs(limit=limit)
        payload = []
        for run in runs:
            sessions = self._broker.load_sessions(run.run_id)
            payload.append(
                {
                    **run.to_dict(),
                    "session_count": len(sessions),
                    "agents": [
                        {
                            "name": session.name,
                            "harness": session.harness.value,
                            "role": session.role,
                            "model": session.model,
                            "turn_count": session.turn_count,
                        }
                        for session in sessions
                    ],
                }
            )
        return json_response({"runs": payload, "total": len(payload)})

    def _get_run(self, run_id: str) -> HandlerResult:
        try:
            run = self._broker.load_run(run_id)
        except FileNotFoundError:
            return error_response(f"Run not found: {run_id}", 404)
        sessions = self._broker.load_sessions(run_id)
        return json_response(
            {
                "run": run.to_dict(),
                "sessions": [session.to_dict() for session in sessions],
            }
        )

    def _get_events(self, run_id: str, *, limit: int) -> HandlerResult:
        try:
            self._broker.load_run(run_id)
        except FileNotFoundError:
            return error_response(f"Run not found: {run_id}", 404)
        events = self._broker.load_events(run_id, limit=limit)
        return json_response({"events": events, "count": len(events)})

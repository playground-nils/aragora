"""Ralph orchestration observability dashboard endpoints.

Endpoints:
- GET /api/ralph/dashboard/summary   — Campaign overview (status, budget, blocker)
- GET /api/ralph/dashboard/projects  — Project lifecycle breakdown by status
- GET /api/ralph/dashboard/blockers  — Blocker frequency analysis
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from aragora.server.versioning.compat import strip_version_prefix

from .base import (
    HandlerResult,
    error_response,
    json_response,
    handle_errors,
)
from .secure import ForbiddenError, SecureHandler, UnauthorizedError
from .utils.rate_limit import RateLimiter, get_client_ip

logger = logging.getLogger(__name__)

RALPH_DASHBOARD_PERMISSION = "ralph:dashboard:read"

_ralph_dashboard_limiter = RateLimiter(requests_per_minute=60)


def _is_demo_mode() -> bool:
    """Check if server is running in demo/offline mode."""
    return os.environ.get("ARAGORA_DEMO_MODE", "").lower() in ("true", "1", "yes")


_DEMO_DATA: dict[str, dict[str, Any]] = {
    "/api/ralph/dashboard/summary": {
        "found": True,
        "campaign_id": "demo-campaign-001",
        "status": "running",
        "current_step": 12,
        "budget_spent_usd": 3.45,
        "budget_limit_usd": 50.0,
        "burn_rate_per_step": 0.2875,
        "project_count": 5,
    },
    "/api/ralph/dashboard/projects": {
        "found": True,
        "campaign_id": "demo-campaign-001",
        "total_projects": 5,
        "by_status": {
            "completed": [
                {
                    "project_id": "proj-1",
                    "title": "Fix auth flow",
                    "status": "completed",
                    "retry_count": 0,
                    "last_run_outcome": "deliverable_created",
                    "estimated_cost_usd": 1.20,
                },
            ],
            "active": [
                {
                    "project_id": "proj-2",
                    "title": "Add rate limiting",
                    "status": "active",
                    "retry_count": 0,
                    "last_run_outcome": None,
                    "estimated_cost_usd": 0.80,
                },
            ],
            "pending": [
                {
                    "project_id": "proj-3",
                    "title": "Refactor DB layer",
                    "status": "pending",
                    "retry_count": 0,
                    "last_run_outcome": None,
                    "estimated_cost_usd": 2.00,
                },
                {
                    "project_id": "proj-4",
                    "title": "Update docs",
                    "status": "pending",
                    "retry_count": 0,
                    "last_run_outcome": None,
                    "estimated_cost_usd": 0.50,
                },
            ],
            "failed": [
                {
                    "project_id": "proj-5",
                    "title": "Migrate legacy API",
                    "status": "failed",
                    "retry_count": 2,
                    "last_run_outcome": "crash",
                    "estimated_cost_usd": 1.50,
                },
            ],
        },
    },
    "/api/ralph/dashboard/blockers": {
        "found": True,
        "total_blockers": 3,
        "by_kind": {
            "scope_false_positive": 1,
            "worker_context_overflow": 1,
            "budget_exhaustion": 1,
        },
        "deterministic_count": 2,
        "escalation_count": 1,
    },
}


class RalphDashboardHandler(SecureHandler):
    """Handler for Ralph orchestration observability dashboard.

    Provides read-only endpoints for campaign status, project lifecycle,
    and blocker history from SupervisorState/CampaignManifest YAML files.
    """

    RESOURCE_TYPE = "ralph_dashboard"

    ROUTES = [
        "/api/ralph/dashboard/summary",
        "/api/ralph/dashboard/projects",
        "/api/ralph/dashboard/blockers",
    ]

    def can_handle(self, path: str, method: str = "GET") -> bool:
        """Check if this handler can process the given path."""
        normalized = strip_version_prefix(path)
        return normalized in self.ROUTES

    @handle_errors("ralph dashboard read")
    async def handle(
        self, path: str, query_params: dict[str, Any], handler: Any
    ) -> HandlerResult | None:
        """Route GET requests to dashboard endpoints."""
        normalized = strip_version_prefix(path)

        # Demo mode: return sample data without auth
        if _is_demo_mode():
            data = _DEMO_DATA.get(normalized)
            if data is not None:
                return json_response(data)

        # Rate limit check
        client_ip = get_client_ip(handler)
        if not _ralph_dashboard_limiter.is_allowed(client_ip):
            logger.warning("Rate limit exceeded for ralph dashboard: %s", client_ip)
            return error_response(
                "Rate limit exceeded. Please try again later.",
                429,
            )

        # RBAC: Require authentication and permission
        try:
            auth_context = await self.get_auth_context(handler, require_auth=True)
            self.check_permission(auth_context, RALPH_DASHBOARD_PERMISSION)
        except UnauthorizedError:
            return error_response("Authentication required", 401, code="AUTH_REQUIRED")
        except ForbiddenError as exc:
            logger.warning("Ralph dashboard access denied: %s", exc)
            return error_response("Permission denied", 403, code="PERMISSION_DENIED")

        # Resolve file paths from query params or defaults
        state_path = Path(query_params.get("state_path", ".aragora/supervisor_state.yaml"))
        manifest_path = Path(query_params.get("manifest_path", ".aragora/campaign_manifest.yaml"))

        if normalized == "/api/ralph/dashboard/summary":
            return self._handle_summary(state_path, manifest_path)
        elif normalized == "/api/ralph/dashboard/projects":
            return self._handle_projects(manifest_path)
        elif normalized == "/api/ralph/dashboard/blockers":
            return self._handle_blockers(state_path)

        return None

    def _handle_summary(self, state_path: Path, manifest_path: Path) -> HandlerResult:
        from aragora.ralph.dashboard import load_dashboard_summary

        data = load_dashboard_summary(state_path, manifest_path)
        return json_response(data)

    def _handle_projects(self, manifest_path: Path) -> HandlerResult:
        from aragora.ralph.dashboard import load_project_lifecycle

        data = load_project_lifecycle(manifest_path)
        return json_response(data)

    def _handle_blockers(self, state_path: Path) -> HandlerResult:
        from aragora.ralph.dashboard import load_blocker_history

        data = load_blocker_history(state_path)
        return json_response(data)


__all__ = ["RalphDashboardHandler"]

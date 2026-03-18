"""Ralph orchestration observability dashboard — pure data functions.

Reads SupervisorState and CampaignManifest YAML files and returns
dashboard-ready dicts for the REST API layer.
"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from aragora.ralph.classifier import BlockerKind

logger = logging.getLogger(__name__)


def load_dashboard_summary(
    state_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    """Campaign overview: status, budget, active blocker, project count.

    Returns ``{"found": False}`` when either file is missing.
    """
    if not state_path.exists() or not manifest_path.exists():
        return {"found": False}

    state = _load_yaml(state_path)
    manifest = _load_yaml(manifest_path)
    if state is None or manifest is None:
        return {"found": False}

    current_step = int(state.get("current_step", 0))
    budget_spent = float(state.get("budget_spent_usd", 0.0))
    budget_limit = float(manifest.get("budget_limit_usd", 0.0))
    burn_rate = budget_spent / max(current_step, 1)

    projects = manifest.get("projects", [])

    summary: dict[str, Any] = {
        "found": True,
        "campaign_id": state.get("campaign_id", ""),
        "status": state.get("status", "unknown"),
        "current_step": current_step,
        "budget_spent_usd": budget_spent,
        "budget_limit_usd": budget_limit,
        "burn_rate_per_step": round(burn_rate, 6),
        "project_count": len(projects),
    }

    active_blocker = state.get("active_blocker")
    if active_blocker:
        summary["active_blocker"] = active_blocker

    return summary


def load_project_lifecycle(manifest_path: Path) -> dict[str, Any]:
    """Project breakdown by status with per-project details.

    Returns ``{"found": False}`` when the manifest file is missing.
    """
    if not manifest_path.exists():
        return {"found": False}

    manifest = _load_yaml(manifest_path)
    if manifest is None:
        return {"found": False}

    projects = manifest.get("projects", [])
    status_groups: dict[str, list[dict[str, Any]]] = {}

    for proj in projects:
        status = str(proj.get("status", "unknown"))
        entry = {
            "project_id": proj.get("project_id", ""),
            "title": proj.get("title", ""),
            "status": status,
            "retry_count": int(proj.get("retry_count", 0)),
            "last_run_outcome": proj.get("last_run_outcome"),
            "estimated_cost_usd": float(proj.get("estimated_cost_usd", 0.0)),
        }
        status_groups.setdefault(status, []).append(entry)

    return {
        "found": True,
        "campaign_id": manifest.get("campaign_id", ""),
        "total_projects": len(projects),
        "by_status": status_groups,
    }


def load_blocker_history(state_path: Path) -> dict[str, Any]:
    """Blocker frequency analysis: by kind, deterministic vs escalation.

    Returns ``{"found": False}`` when the state file is missing.
    """
    if not state_path.exists():
        return {"found": False}

    state = _load_yaml(state_path)
    if state is None:
        return {"found": False}

    history = state.get("blocker_history", [])
    if not isinstance(history, list):
        history = []

    kind_counter: Counter[str] = Counter()
    deterministic_count = 0
    escalation_count = 0

    for entry in history:
        if not isinstance(entry, dict):
            continue
        kind_str = str(entry.get("kind", "unknown"))
        kind_counter[kind_str] += 1

        # Classify as deterministic or escalation using BlockerKind enum
        try:
            kind_enum = BlockerKind(kind_str)
            if kind_enum.is_deterministic:
                deterministic_count += 1
            else:
                escalation_count += 1
        except ValueError:
            # Unknown kind string — treat as escalation
            escalation_count += 1

    return {
        "found": True,
        "total_blockers": len(history),
        "by_kind": dict(kind_counter),
        "deterministic_count": deterministic_count,
        "escalation_count": escalation_count,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict[str, Any] | None:
    """Load a YAML file, returning None on any parse or I/O error."""
    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if isinstance(data, dict):
            return data
        logger.warning("Expected dict in %s, got %s", path, type(data).__name__)
        return None
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return None

"""Lightweight session coordination for multi-agent swarm work.

Multiple Claude/Codex sessions share a repo but cannot communicate directly.
This module provides a shared JSON file protocol so sessions can:
- See each other's assignments and constraints
- Claim PRs and files to avoid conflicts
- Report findings for cross-session visibility

The coordination file lives at ``.aragora/coordination/directives.json``
and is gitignored (local-only coordination).

Usage::

    from aragora.swarm.session_coordinator import (
        read_directives,
        claim_pr,
        report_finding,
        get_my_assignment,
    )

    directives = read_directives()
    claim_pr(42, "claude-a")
    report_finding("CI lint fails on line 123 of foo.py", "claude-a")
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_DEFAULT_DIR = ".aragora/coordination"
_DIRECTIVES_FILE = "directives.json"


def _resolve_coordination_dir(repo_root: Path | None = None) -> Path:
    """Return the coordination directory, creating it if needed."""
    root = repo_root or Path.cwd()
    coord_dir = root / _DEFAULT_DIR
    coord_dir.mkdir(parents=True, exist_ok=True)
    return coord_dir


def _directives_path(repo_root: Path | None = None) -> Path:
    return _resolve_coordination_dir(repo_root) / _DIRECTIVES_FILE


# ---------------------------------------------------------------------------
# Empty directives template
# ---------------------------------------------------------------------------


def _empty_directives() -> dict[str, Any]:
    return {
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "issued_by": "system",
        "sessions": {},
        "shared_findings": [],
        "claimed_prs": {},
        "claimed_files": {},
    }


# ---------------------------------------------------------------------------
# Atomic read / write with fcntl locking
# ---------------------------------------------------------------------------


def read_directives(repo_root: Path | None = None) -> dict[str, Any]:
    """Read the current directives file, returning empty defaults if absent."""
    path = _directives_path(repo_root)
    if not path.exists():
        return _empty_directives()
    try:
        with open(path, "r") as fh:
            fcntl.flock(fh, fcntl.LOCK_SH)
            try:
                data = json.load(fh)
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read directives: %s", exc)
        return _empty_directives()


def write_directives(
    directives: dict[str, Any],
    repo_root: Path | None = None,
) -> None:
    """Atomically write the directives file with exclusive locking."""
    path = _directives_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                json.dump(directives, fh, indent=2)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
        tmp_path.replace(path)
    except OSError:
        # Clean up temp file on failure
        tmp_path.unlink(missing_ok=True)
        raise


def _mutate(
    repo_root: Path | None,
    fn: Any,
) -> Any:
    """Read-modify-write helper with exclusive lock on the directives file."""
    directives = read_directives(repo_root)
    result = fn(directives)
    directives["issued_at"] = datetime.now(timezone.utc).isoformat()
    write_directives(directives, repo_root)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def claim_pr(
    pr_number: int,
    session_id: str,
    repo_root: Path | None = None,
) -> bool:
    """Claim a PR for a session. Returns False if already claimed by another."""

    def _claim(d: dict[str, Any]) -> bool:
        claimed = d.setdefault("claimed_prs", {})
        key = str(pr_number)
        existing = claimed.get(key)
        if existing and existing != session_id:
            return False
        claimed[key] = session_id
        return True

    return _mutate(repo_root, _claim)


def claim_file(
    file_path: str,
    session_id: str,
    repo_root: Path | None = None,
) -> bool:
    """Claim a file scope for a session. Returns False if already claimed by another."""

    def _claim(d: dict[str, Any]) -> bool:
        claimed = d.setdefault("claimed_files", {})
        existing = claimed.get(file_path)
        if existing and existing != session_id:
            return False
        claimed[file_path] = session_id
        return True

    return _mutate(repo_root, _claim)


def report_finding(
    finding: str,
    session_id: str,
    repo_root: Path | None = None,
) -> None:
    """Append a finding to the shared findings list."""

    def _report(d: dict[str, Any]) -> None:
        findings = d.setdefault("shared_findings", [])
        findings.append(
            {
                "reported_by": session_id,
                "reported_at": datetime.now(timezone.utc).isoformat(),
                "finding": finding,
            }
        )

    _mutate(repo_root, _report)


def get_my_assignment(
    session_id: str,
    repo_root: Path | None = None,
) -> dict[str, Any] | None:
    """Return this session's current assignment, or None if not assigned."""
    directives = read_directives(repo_root)
    sessions = directives.get("sessions", {})
    return sessions.get(session_id)


def set_assignment(
    session_id: str,
    task: str,
    scope: list[str] | None = None,
    constraints: list[str] | None = None,
    role: str | None = None,
    issued_by: str | None = None,
    repo_root: Path | None = None,
) -> None:
    """Update a session's assignment in the directives file."""

    def _assign(d: dict[str, Any]) -> None:
        sessions = d.setdefault("sessions", {})
        sessions[session_id] = {
            "role": role or session_id,
            "task": task,
            "scope": scope or [],
            "status": "active",
            "constraints": constraints or [],
        }
        if issued_by:
            d["issued_by"] = issued_by

    _mutate(repo_root, _assign)

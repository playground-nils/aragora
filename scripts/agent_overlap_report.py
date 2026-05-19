#!/usr/bin/env python3
"""Cross-family agent overlap report (v14 P75).

Read-only consolidator that answers the question every operator hits
when multiple AI agent families (Codex Desktop, Codex CLI, Factory
Droid, Claude Desktop, Claude CLI) are running concurrently against
this checkout: *what is every agent family doing across the repo right
now, and are they colliding?*

Inputs (every source is optional; missing sources never error):

- Codex Desktop:   ``~/.codex/state_5.sqlite`` (read-only URI), active
                   non-archived threads with ``updated_at_ms`` inside
                   the ``--codex-since`` window.
- Codex CLI:       ``~/.codex/log/codex-tui.log`` mtime, with the lane
                   registry's codex sources folded in as session
                   records.
- Factory Droid:   ``~/.factory/background-processes.json``.
- Claude Desktop / Claude CLI:
                   ``~/.claude/projects/<encoded-cwd>/<uuid>.jsonl``.
                   The encoded cwd is decoded back to a path and we
                   split CLI vs Desktop by whether the cwd contains
                   ``/.worktrees/`` (CLI default for disposable
                   worktrees) or is the bare repo root (Desktop).
- Lane registry:   ``.aragora/agent-bridge/lanes.json`` (repo) with
                   fallback to ``~/.aragora/agent-bridge/lanes.json``.
                   By default we read the file directly. Pass
                   ``--via-agent-bridge`` to instead invoke
                   ``scripts/agent_bridge.py operator-snapshot --json``
                   as a subprocess for the live lane snapshot.
- Open PRs:        ``gh pr list --state open --json
                   number,headRefName,author --limit 200``.
- Worktrees:       ``git worktree list --porcelain``.

Overlap kinds detected:

- ``cwd_collision``           — same cwd claimed by 2+ agent families
                                in the same window.
- ``branch_collision``        — same branch claimed by 2+ sources
                                (lane registry / open PR / worktree /
                                Codex Desktop thread / lane row).
- ``unclaimed_active_session``— a live session inside a worktree but
                                no active lane claim covers that cwd
                                or worktree.
- ``stale_lane_claim``        — a lane row is active but no live
                                process is observed at its declared
                                worktree.

Write surface: the optional ``--claim-lane LANE_ID --owner-session SID``
pair appends a single ``LaneRecord``-schema row to the lane registry
(matching ``scripts/claim_active_agent_lane.py``'s contract). The write
is atomic (tempfile + ``os.replace``) and refuses to overwrite an
existing lane row owned by a different session unless ``--force`` is
also passed. Every other code path is strictly read-only.

Pure stdlib + ``subprocess.run``. No ``aragora.*`` imports. No network
calls beyond the optional ``gh`` and ``git`` subprocess invocations.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "aragora-agent-overlap-report/1.0"

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LANE_REGISTRY = REPO_ROOT / ".aragora" / "agent-bridge" / "lanes.json"
USER_LANE_REGISTRY = Path.home() / ".aragora" / "agent-bridge" / "lanes.json"
DEFAULT_CODEX_STATE_DB = Path.home() / ".codex" / "state_5.sqlite"
DEFAULT_CODEX_TUI_LOG = Path.home() / ".codex" / "log" / "codex-tui.log"
DEFAULT_FACTORY_BG = Path.home() / ".factory" / "background-processes.json"
DEFAULT_CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"

ACTIVE_LANE_STATUSES: frozenset[str] = frozenset(
    {"active", "running", "pending", "queued", "claimed"}
)

DEFAULT_GH_TIMEOUT_SECONDS = 20
DEFAULT_GIT_TIMEOUT_SECONDS = 10
DEFAULT_BRIDGE_TIMEOUT_SECONDS = 30
DEFAULT_CODEX_SINCE = "4h"

# LaneRecord shape used by the existing agent_bridge reader.
LANE_RECORD_KEYS = (
    "lane_id",
    "owner_session",
    "goal",
    "source",
    "status",
    "next_action",
    "updated_at",
    "branch",
    "worktree",
    "pr_number",
    "conflict_session",
    "conflict_reason",
    "desktop_label",
    "codex_thread_id",
    "codex_rollout_path",
    "session_title",
)

Runner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


class ClaimError(RuntimeError):
    """Raised when ``--claim-lane`` would clobber an existing claim."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(microsecond=0)


def _iso_z(ts: dt.datetime) -> str:
    return ts.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")


def _normalize_path(value: str | None) -> str:
    if not value:
        return ""
    try:
        return os.path.normpath(os.path.expanduser(str(value))).rstrip("/")
    except (OSError, RuntimeError, TypeError):
        return str(value)


def _parse_since(value: str) -> int:
    """Parse ``--codex-since`` (e.g. ``4h``, ``30m``, ``900s``)."""
    raw = (value or "").strip().lower()
    if not raw:
        raise ValueError("empty --codex-since")
    unit_seconds = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if raw[-1] in unit_seconds:
        try:
            n = float(raw[:-1])
        except ValueError as exc:
            raise ValueError(f"invalid --codex-since {value!r}") from exc
        return int(n * unit_seconds[raw[-1]])
    return int(float(raw))


def _default_runner(timeout: float) -> Runner:
    def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    return _run


def _maybe_runner(cmd_path: str | None, timeout: float) -> Runner | None:
    if not cmd_path:
        return None
    if shutil.which(cmd_path) is None and not Path(cmd_path).is_file():
        return None
    return _default_runner(timeout)


# ---------------------------------------------------------------------------
# Source: Codex Desktop (state_5.sqlite)
# ---------------------------------------------------------------------------


def collect_codex_desktop(
    state_db: Path = DEFAULT_CODEX_STATE_DB,
    *,
    since_seconds: int,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Return Codex Desktop threads active inside ``since_seconds``."""
    if not state_db.is_file():
        return {"active_count": 0, "threads": [], "reason": f"missing: {state_db}"}
    current = now or _utc_now()
    cutoff_ms = int((current.timestamp() - since_seconds) * 1000)
    uri = f"file:{state_db}?mode=ro"
    threads: list[dict[str, Any]] = []
    try:
        con = sqlite3.connect(uri, uri=True, timeout=2.0)
    except sqlite3.DatabaseError as exc:
        return {"active_count": 0, "threads": [], "reason": f"open failed: {exc}"}
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT id, cwd, git_branch, title, source, updated_at_ms, rollout_path "
            "FROM threads WHERE archived = 0 AND updated_at_ms >= ? "
            "ORDER BY updated_at_ms DESC LIMIT 200",
            (cutoff_ms,),
        )
        for row in cur.fetchall():
            tid, cwd, branch, title, source, updated_at_ms, rollout_path = row
            threads.append(
                {
                    "thread_id": tid,
                    "cwd": _normalize_path(cwd),
                    "branch": branch or "",
                    "title": (title or "")[:120],
                    "source": source or "",
                    "updated_at_ms": int(updated_at_ms or 0),
                    "rollout_path": rollout_path or "",
                }
            )
    except sqlite3.DatabaseError as exc:
        return {"active_count": 0, "threads": [], "reason": f"query failed: {exc}"}
    finally:
        con.close()
    return {"active_count": len(threads), "threads": threads}


# ---------------------------------------------------------------------------
# Source: Codex CLI (codex-tui.log mtime + lane records tagged codex)
# ---------------------------------------------------------------------------


def collect_codex_cli(
    tui_log: Path = DEFAULT_CODEX_TUI_LOG,
    *,
    since_seconds: int,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Return Codex CLI activity inferred from the TUI log mtime."""
    current = now or _utc_now()
    processes: list[dict[str, Any]] = []
    if tui_log.is_file():
        try:
            mtime = tui_log.stat().st_mtime
        except OSError:
            mtime = 0.0
        if mtime and (current.timestamp() - mtime) <= since_seconds:
            processes.append(
                {
                    "log_path": str(tui_log),
                    "mtime_ts": int(mtime),
                    "age_seconds": int(current.timestamp() - mtime),
                }
            )
    return {"active_count": len(processes), "processes": processes}


# ---------------------------------------------------------------------------
# Source: Factory Droid (~/.factory/background-processes.json)
# ---------------------------------------------------------------------------


def collect_factory_droid(bg_path: Path = DEFAULT_FACTORY_BG) -> dict[str, Any]:
    if not bg_path.is_file():
        return {"active_count": 0, "sessions": [], "reason": f"missing: {bg_path}"}
    try:
        payload = json.loads(bg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"active_count": 0, "sessions": [], "reason": f"parse failed: {exc}"}
    raw_processes: list[Any]
    if isinstance(payload, dict):
        raw_processes = list(payload.get("processes") or payload.get("background_processes") or [])
    elif isinstance(payload, list):
        raw_processes = payload
    else:
        raw_processes = []
    sessions: list[dict[str, Any]] = []
    for entry in raw_processes:
        if not isinstance(entry, dict):
            continue
        sessions.append(
            {
                "id": entry.get("id") or entry.get("pid") or entry.get("session_id") or "",
                "cwd": _normalize_path(str(entry.get("cwd") or entry.get("worktree") or "")),
                "branch": entry.get("branch") or "",
                "status": entry.get("status") or "",
            }
        )
    return {"active_count": len(sessions), "sessions": sessions}


# ---------------------------------------------------------------------------
# Source: Claude Desktop + Claude CLI (~/.claude/projects)
# ---------------------------------------------------------------------------


def _decode_claude_project(encoded: str) -> str:
    """Reverse Claude Code's ``/`` → ``-`` project-dir encoding."""
    if not encoded:
        return ""
    if encoded.startswith("-"):
        decoded = "/" + encoded[1:].replace("-", "/")
    else:
        decoded = encoded.replace("-", "/")
    return _normalize_path(decoded)


def collect_claude_projects(
    projects_root: Path = DEFAULT_CLAUDE_PROJECTS,
    *,
    since_seconds: int,
    now: dt.datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Scan ``~/.claude/projects/<encoded-cwd>``; split CLI vs Desktop.

    Sessions whose decoded cwd contains ``/.worktrees/`` are classified
    as Claude CLI (the convention used by the ``claude-wt`` wrapper).
    Anything else is classified as Claude Desktop. Sessions older than
    ``since_seconds`` are dropped.
    """
    cli_sessions: list[dict[str, Any]] = []
    desktop_projects: list[dict[str, Any]] = []
    if not projects_root.is_dir():
        empty = {"active_count": 0, "reason": f"missing: {projects_root}"}
        return ({**empty, "projects": []}, {**empty, "sessions": []})

    current = (now or _utc_now()).timestamp()
    for project_dir in sorted(projects_root.iterdir()):
        if not project_dir.is_dir():
            continue
        decoded_cwd = _decode_claude_project(project_dir.name)
        latest_ts = 0.0
        for f in project_dir.glob("*.jsonl"):
            try:
                m = f.stat().st_mtime
            except OSError:
                continue
            if m > latest_ts:
                latest_ts = m
        if latest_ts == 0.0 or (current - latest_ts) > since_seconds:
            continue
        entry = {
            "encoded": project_dir.name,
            "cwd": decoded_cwd,
            "latest_mtime_ts": int(latest_ts),
        }
        if "/.worktrees/" in decoded_cwd:
            cli_sessions.append(entry)
        else:
            desktop_projects.append(entry)
    return (
        {"active_count": len(desktop_projects), "projects": desktop_projects},
        {"active_count": len(cli_sessions), "sessions": cli_sessions},
    )


# ---------------------------------------------------------------------------
# Source: lane registry
# ---------------------------------------------------------------------------


def _load_lane_registry_direct(registry_path: Path) -> list[dict[str, Any]]:
    if not registry_path.exists():
        return []
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def _load_lane_registry_via_bridge(
    bridge_path: Path,
    runner: Runner,
) -> list[dict[str, Any]] | None:
    try:
        result = runner([sys.executable, str(bridge_path), "operator-snapshot", "--json"])
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return None
    lanes = payload.get("lanes") if isinstance(payload, dict) else None
    if not isinstance(lanes, list):
        return None
    return [row for row in lanes if isinstance(row, dict)]


def resolve_registry_path(repo_root: Path = REPO_ROOT, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit
    repo_lane = repo_root / ".aragora" / "agent-bridge" / "lanes.json"
    if repo_lane.parent.exists():
        return repo_lane
    return USER_LANE_REGISTRY


def collect_lane_registry(
    *,
    registry_path: Path,
    via_bridge: bool = False,
    bridge_path: Path | None = None,
    bridge_runner: Runner | None = None,
) -> dict[str, Any]:
    """Return the lane registry rows + active counts."""
    rows: list[dict[str, Any]] | None = None
    if via_bridge and bridge_path is not None and bridge_runner is not None:
        rows = _load_lane_registry_via_bridge(bridge_path, bridge_runner)
    if rows is None:
        rows = _load_lane_registry_direct(registry_path)
    active = [r for r in rows if str(r.get("status") or "") in ACTIVE_LANE_STATUSES]
    return {
        "registry_path": str(registry_path),
        "via_bridge": bool(via_bridge and rows is not None),
        "active_count": len(active),
        "total_count": len(rows),
        "lanes": rows,
    }


# ---------------------------------------------------------------------------
# Source: open PRs (gh)
# ---------------------------------------------------------------------------


def collect_open_prs(gh_runner: Runner | None) -> dict[str, Any]:
    if gh_runner is None:
        return {"count": 0, "prs": [], "by_family": {}, "reason": "gh unavailable"}
    try:
        result = gh_runner(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--json",
                "number,headRefName,author",
                "--limit",
                "200",
            ]
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"count": 0, "prs": [], "by_family": {}, "reason": f"gh failed: {exc}"}
    if result.returncode != 0:
        return {
            "count": 0,
            "prs": [],
            "by_family": {},
            "reason": (result.stderr or "gh exited non-zero").strip(),
        }
    try:
        prs_raw = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        return {"count": 0, "prs": [], "by_family": {}, "reason": f"parse failed: {exc}"}
    prs: list[dict[str, Any]] = []
    by_family: dict[str, int] = {}
    for pr in prs_raw if isinstance(prs_raw, list) else []:
        if not isinstance(pr, dict):
            continue
        author = pr.get("author") or {}
        author_login = (
            author.get("login") if isinstance(author, dict) else str(author or "")
        ) or ""
        branch = pr.get("headRefName") or ""
        family = _branch_to_family(str(branch), str(author_login))
        by_family[family] = by_family.get(family, 0) + 1
        prs.append(
            {
                "number": pr.get("number"),
                "branch": branch,
                "author": author_login,
                "family": family,
            }
        )
    return {"count": len(prs), "prs": prs, "by_family": by_family}


def _branch_to_family(branch: str, author: str) -> str:
    low = branch.lower()
    if low.startswith("droid/") or "droid" in author.lower():
        return "factory_droid"
    if low.startswith("codex/") or "codex" in low:
        return "codex"
    if low.startswith("claude/") or "claude" in low:
        return "claude"
    return "other"


# ---------------------------------------------------------------------------
# Source: worktrees
# ---------------------------------------------------------------------------


def collect_worktrees(git_runner: Runner | None) -> dict[str, Any]:
    if git_runner is None:
        return {"count": 0, "worktrees": [], "by_branch": [], "reason": "git unavailable"}
    try:
        result = git_runner(["git", "worktree", "list", "--porcelain"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "count": 0,
            "worktrees": [],
            "by_branch": [],
            "reason": f"git failed: {exc}",
        }
    if result.returncode != 0:
        return {
            "count": 0,
            "worktrees": [],
            "by_branch": [],
            "reason": (result.stderr or "git exited non-zero").strip(),
        }
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in (result.stdout or "").splitlines():
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue
        key, _, val = line.partition(" ")
        if key == "worktree":
            current["path"] = _normalize_path(val)
        elif key == "branch":
            current["branch"] = val.removeprefix("refs/heads/")
        elif key == "HEAD":
            current["head"] = val
    if current:
        entries.append(current)
    by_branch: dict[str, int] = {}
    for entry in entries:
        b = entry.get("branch") or ""
        if b:
            by_branch[b] = by_branch.get(b, 0) + 1
    return {
        "count": len(entries),
        "worktrees": entries,
        "by_branch": [{"branch": k, "count": v} for k, v in sorted(by_branch.items())],
    }


# ---------------------------------------------------------------------------
# Overlap detection
# ---------------------------------------------------------------------------


def _claimants_for_cwd(families: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Build cwd → list of {family, ref} claimants."""
    cwd_map: dict[str, list[dict[str, Any]]] = {}

    def add(family: str, cwd: str, ref: str) -> None:
        cwd_n = _normalize_path(cwd)
        if not cwd_n:
            return
        cwd_map.setdefault(cwd_n, []).append({"family": family, "ref": ref})

    for thread in families.get("codex_desktop", {}).get("threads", []) or []:
        add("codex_desktop", str(thread.get("cwd") or ""), str(thread.get("thread_id") or ""))
    for session in families.get("factory_droid", {}).get("sessions", []) or []:
        add(
            "factory_droid",
            str(session.get("cwd") or ""),
            str(session.get("id") or ""),
        )
    for proj in families.get("claude_desktop", {}).get("projects", []) or []:
        add("claude_desktop", str(proj.get("cwd") or ""), str(proj.get("encoded") or ""))
    for session in families.get("claude_cli", {}).get("sessions", []) or []:
        add("claude_cli", str(session.get("cwd") or ""), str(session.get("encoded") or ""))
    return cwd_map


def _branch_claimants(
    families: dict[str, Any],
    lane_registry: dict[str, Any],
    worktrees: dict[str, Any],
    open_prs: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    branch_map: dict[str, list[dict[str, Any]]] = {}

    def add(source: str, branch: str, ref: str) -> None:
        b = (branch or "").strip()
        if not b:
            return
        branch_map.setdefault(b, []).append({"source": source, "ref": ref})

    for lane in lane_registry.get("lanes", []) or []:
        if str(lane.get("status") or "") not in ACTIVE_LANE_STATUSES:
            continue
        add("lane_registry", str(lane.get("branch") or ""), str(lane.get("lane_id") or ""))
    for wt in worktrees.get("worktrees", []) or []:
        add("worktree", str(wt.get("branch") or ""), str(wt.get("path") or ""))
    for pr in open_prs.get("prs", []) or []:
        add("open_pr", str(pr.get("branch") or ""), f"#{pr.get('number') or ''}")
    for thread in families.get("codex_desktop", {}).get("threads", []) or []:
        add("codex_desktop", str(thread.get("branch") or ""), str(thread.get("thread_id") or ""))
    for session in families.get("factory_droid", {}).get("sessions", []) or []:
        add("factory_droid", str(session.get("branch") or ""), str(session.get("id") or ""))
    return branch_map


def detect_overlaps(
    *,
    families: dict[str, Any],
    lane_registry: dict[str, Any],
    worktrees: dict[str, Any],
    open_prs: dict[str, Any],
) -> list[dict[str, Any]]:
    overlaps: list[dict[str, Any]] = []

    cwd_map = _claimants_for_cwd(families)
    for cwd, claimants in sorted(cwd_map.items()):
        families_present = {c["family"] for c in claimants}
        if len(families_present) >= 2:
            overlaps.append(
                {
                    "kind": "cwd_collision",
                    "cwd": cwd,
                    "claimants": claimants,
                }
            )

    branch_map = _branch_claimants(families, lane_registry, worktrees, open_prs)
    for branch, claimants in sorted(branch_map.items()):
        sources = {c["source"] for c in claimants}
        if len(sources) >= 2:
            overlaps.append(
                {
                    "kind": "branch_collision",
                    "branch": branch,
                    "claimants": claimants,
                }
            )

    active_lane_cwds: set[str] = set()
    for lane in lane_registry.get("lanes", []) or []:
        if str(lane.get("status") or "") in ACTIVE_LANE_STATUSES:
            wt = _normalize_path(str(lane.get("worktree") or ""))
            if wt:
                active_lane_cwds.add(wt)

    for cwd, claimants in cwd_map.items():
        if cwd in active_lane_cwds:
            continue
        if "/.worktrees/" not in cwd and "/aragora" not in cwd:
            # Only report sessions sitting inside Aragora-ish paths.
            continue
        for claimant in claimants:
            overlaps.append(
                {
                    "kind": "unclaimed_active_session",
                    "cwd": cwd,
                    "family": claimant["family"],
                    "ref": claimant["ref"],
                }
            )

    for lane in lane_registry.get("lanes", []) or []:
        if str(lane.get("status") or "") not in ACTIVE_LANE_STATUSES:
            continue
        wt = _normalize_path(str(lane.get("worktree") or ""))
        if not wt:
            continue
        if wt in cwd_map:
            continue
        overlaps.append(
            {
                "kind": "stale_lane_claim",
                "lane_id": lane.get("lane_id") or "",
                "owner_session": lane.get("owner_session") or "",
                "worktree": wt,
                "no_matching_process": True,
            }
        )

    return overlaps


# ---------------------------------------------------------------------------
# Optional write surface: --claim-lane
# ---------------------------------------------------------------------------


def _normalize_lane_row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: row[k] for k in LANE_RECORD_KEYS if row.get(k) not in (None, "")}


def _atomic_write_lanes(registry_path: Path, rows: list[dict[str, Any]]) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=registry_path.name + ".tmp.", dir=str(registry_path.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_path, registry_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def claim_lane_row(
    registry_path: Path,
    *,
    lane_id: str,
    owner_session: str,
    goal: str = "",
    source: str = "agent_overlap_report",
    status: str = "active",
    branch: str = "",
    worktree: str = "",
    pr_number: int | None = None,
    force: bool = False,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Append a single ``LaneRecord``-shaped row. Fail-closed on conflict."""
    if not lane_id:
        raise ValueError("lane_id must not be empty")
    if not owner_session:
        raise ValueError("owner_session must not be empty")
    rows = _load_lane_registry_direct(registry_path)
    for existing in rows:
        if str(existing.get("lane_id") or "") != lane_id:
            continue
        existing_owner = str(existing.get("owner_session") or "")
        existing_status = str(existing.get("status") or "")
        if (
            existing_owner
            and existing_owner != owner_session
            and existing_status in ACTIVE_LANE_STATUSES
            and not force
        ):
            raise ClaimError(
                f"lane_id={lane_id!r} already actively claimed by "
                f"owner_session={existing_owner!r}; refusing to overwrite "
                f"(pass --force to override)"
            )
    new_row = {
        "lane_id": lane_id,
        "owner_session": owner_session,
        "goal": goal,
        "source": source,
        "status": status,
        "updated_at": _iso_z(now or _utc_now()),
        "branch": branch,
        "worktree": _normalize_path(worktree),
        "pr_number": pr_number,
    }
    normalized = _normalize_lane_row(new_row)
    out_rows: list[dict[str, Any]] = []
    replaced = False
    for existing in rows:
        if str(existing.get("lane_id") or "") == lane_id and (
            str(existing.get("owner_session") or "") == owner_session or force
        ):
            out_rows.append(normalized)
            replaced = True
        else:
            out_rows.append(existing)
    if not replaced:
        out_rows.append(normalized)
    _atomic_write_lanes(registry_path, out_rows)
    return normalized


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def build_report(
    *,
    since_seconds: int,
    repo_root: Path = REPO_ROOT,
    registry_path: Path | None = None,
    via_bridge: bool = False,
    codex_state_db: Path = DEFAULT_CODEX_STATE_DB,
    codex_tui_log: Path = DEFAULT_CODEX_TUI_LOG,
    factory_bg: Path = DEFAULT_FACTORY_BG,
    claude_projects: Path = DEFAULT_CLAUDE_PROJECTS,
    gh_cmd: str | None = "gh",
    git_cmd: str | None = "git",
    bridge_path: Path | None = None,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Build the full overlap report payload (read-only)."""
    current = now or _utc_now()
    resolved_registry = resolve_registry_path(repo_root, registry_path)
    bridge = bridge_path or (repo_root / "scripts" / "agent_bridge.py")

    codex_desktop = collect_codex_desktop(codex_state_db, since_seconds=since_seconds, now=current)
    codex_cli = collect_codex_cli(codex_tui_log, since_seconds=since_seconds, now=current)
    factory_droid = collect_factory_droid(factory_bg)
    claude_desktop, claude_cli = collect_claude_projects(
        claude_projects, since_seconds=since_seconds, now=current
    )
    lane_registry = collect_lane_registry(
        registry_path=resolved_registry,
        via_bridge=via_bridge,
        bridge_path=bridge if via_bridge else None,
        bridge_runner=_maybe_runner(sys.executable, DEFAULT_BRIDGE_TIMEOUT_SECONDS)
        if via_bridge
        else None,
    )
    open_prs = collect_open_prs(_maybe_runner(gh_cmd, DEFAULT_GH_TIMEOUT_SECONDS))
    worktrees = collect_worktrees(_maybe_runner(git_cmd, DEFAULT_GIT_TIMEOUT_SECONDS))

    families = {
        "codex_desktop": codex_desktop,
        "codex_cli": codex_cli,
        "factory_droid": factory_droid,
        "claude_desktop": claude_desktop,
        "claude_cli": claude_cli,
    }
    overlaps = detect_overlaps(
        families=families,
        lane_registry=lane_registry,
        worktrees=worktrees,
        open_prs=open_prs,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _iso_z(current),
        "since_seconds": since_seconds,
        "families": families,
        "lane_registry": lane_registry,
        "open_prs": open_prs,
        "worktrees": worktrees,
        "overlaps": overlaps,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Agent Overlap Report — {report['generated_at_utc']}",
        "",
        f"_Schema: `{report['schema_version']}` · since={report['since_seconds']}s_",
        "",
        "## Families",
        "",
        "| Family | Active |",
        "| --- | --- |",
    ]
    for fam, data in report["families"].items():
        lines.append(f"| `{fam}` | {data.get('active_count', 0)} |")
    lr = report["lane_registry"]
    lines += [
        "",
        "## Lane registry",
        "",
        f"- registry: `{lr['registry_path']}`",
        f"- active lanes: {lr['active_count']} / {lr['total_count']}",
        "",
        "## Open PRs",
        "",
        f"- total open: {report['open_prs'].get('count', 0)}",
    ]
    by_family = report["open_prs"].get("by_family") or {}
    for fam, count in sorted(by_family.items()):
        lines.append(f"  - {fam}: {count}")
    lines += [
        "",
        "## Worktrees",
        "",
        f"- total: {report['worktrees'].get('count', 0)}",
        "",
        "## Overlaps",
        "",
    ]
    if not report["overlaps"]:
        lines.append("_No overlaps detected._")
    else:
        lines.append("| Kind | Detail |")
        lines.append("| --- | --- |")
        for ov in report["overlaps"]:
            kind = ov.get("kind", "")
            detail = ", ".join(f"{k}={v}" for k, v in ov.items() if k != "kind")
            lines.append(f"| `{kind}` | {detail} |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="agent_overlap_report.py",
        description=(
            "Cross-family agent overlap report consolidator. Read-only by "
            "default; --claim-lane is the only write path."
        ),
    )
    fmt = p.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true", help="Emit JSON (default).")
    fmt.add_argument("--markdown", action="store_true", help="Emit a Markdown table.")
    p.add_argument(
        "--codex-since",
        default=DEFAULT_CODEX_SINCE,
        help="Time window for Codex Desktop / Claude activity (e.g. 4h, 30m).",
    )
    p.add_argument(
        "--registry-path",
        type=Path,
        default=None,
        help="Override the lane registry path.",
    )
    p.add_argument(
        "--via-agent-bridge",
        action="store_true",
        help="Source lane records via 'agent_bridge.py operator-snapshot --json' subprocess.",
    )
    p.add_argument("--codex-state-db", type=Path, default=DEFAULT_CODEX_STATE_DB)
    p.add_argument("--codex-tui-log", type=Path, default=DEFAULT_CODEX_TUI_LOG)
    p.add_argument("--factory-bg", type=Path, default=DEFAULT_FACTORY_BG)
    p.add_argument("--claude-projects", type=Path, default=DEFAULT_CLAUDE_PROJECTS)
    p.add_argument("--gh-cmd", default="gh", help='Override gh path; pass "" to skip.')
    p.add_argument("--git-cmd", default="git", help='Override git path; pass "" to skip.')
    p.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    # write surface
    p.add_argument("--claim-lane", default="", help="Lane id to claim (LaneRecord row).")
    p.add_argument("--owner-session", default="", help="Owner session id for --claim-lane.")
    p.add_argument("--claim-goal", default="")
    p.add_argument("--claim-branch", default="")
    p.add_argument("--claim-worktree", default="")
    p.add_argument("--claim-pr-number", type=int, default=None)
    p.add_argument(
        "--force",
        action="store_true",
        help="Force-overwrite an existing active claim under --claim-lane.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        since_seconds = _parse_since(args.codex_since)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.claim_lane:
        if not args.owner_session:
            print("error: --claim-lane requires --owner-session", file=sys.stderr)
            return 2
        registry_path = resolve_registry_path(args.repo_root, args.registry_path)
        try:
            row = claim_lane_row(
                registry_path,
                lane_id=args.claim_lane,
                owner_session=args.owner_session,
                goal=args.claim_goal,
                branch=args.claim_branch,
                worktree=args.claim_worktree,
                pr_number=args.claim_pr_number,
                force=args.force,
            )
        except ClaimError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({"claimed": row, "registry_path": str(registry_path)}, indent=2))
        return 0

    report = build_report(
        since_seconds=since_seconds,
        repo_root=args.repo_root,
        registry_path=args.registry_path,
        via_bridge=args.via_agent_bridge,
        codex_state_db=args.codex_state_db,
        codex_tui_log=args.codex_tui_log,
        factory_bg=args.factory_bg,
        claude_projects=args.claude_projects,
        gh_cmd=args.gh_cmd or None,
        git_cmd=args.git_cmd or None,
    )
    if args.markdown:
        sys.stdout.write(render_markdown(report))
    else:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True))
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

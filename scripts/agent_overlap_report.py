#!/usr/bin/env python3
"""Cross-agent overlap consolidator for Aragora operator coordination.

Reads what every agent family is doing right now and emits a unified
overlap report so operators can see collisions BEFORE they happen.

Data sources (read-only, stdlib only):
  - scripts/agent_bridge.py operator-snapshot --json   (existing process census + lane registry)
  - ~/.codex/state_5.sqlite                            (Codex Desktop active threads)
  - ~/.codex/log/codex-tui.log                         (Codex CLI mtime / liveness)
  - ~/.factory/background-processes.json               (Factory Droid sessions)
  - ~/.claude/projects/*/                              (Claude Code Desktop + CLI sessions)
  - git worktree list --porcelain                      (active worktree -> branch map)
  - gh pr list --state open --json …                   (open PRs -> branch claims)

Optional write path:
  - --claim-lane <lane-id>  appends a single row to .aragora/agent-bridge/lanes.json
    matching the existing schema (without importing aragora itself).

No AI provider keys consumed. No mutation of any ~/.codex/, ~/.factory/, or
~/.claude/ tree. The only write target is .aragora/agent-bridge/lanes.json
(opt-in via --claim-lane).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
LANE_REGISTRY_PATH = REPO_ROOT / ".aragora" / "agent-bridge" / "lanes.json"
CODEX_HOME = Path(os.environ.get("ARAGORA_CODEX_HOME", "~/.codex")).expanduser()
FACTORY_HOME = Path(os.environ.get("ARAGORA_FACTORY_HOME", "~/.factory")).expanduser()
CLAUDE_PROJECTS_ROOT = Path(
    os.environ.get("ARAGORA_CLAUDE_PROJECTS_HOME", "~/.claude/projects")
).expanduser()

DEFAULT_CODEX_DESKTOP_SINCE = timedelta(hours=4)


@dataclass(frozen=True, slots=True)
class AgentSession:
    """One detected session across any agent family."""

    family: str  # codex_desktop | codex_cli | factory_droid | claude_code | aragora_lane
    session_id: str
    cwd: str | None
    branch: str | None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Overlap:
    """One detected cross-session overlap."""

    kind: str  # cwd_collision | branch_collision | lane_gap
    members: tuple[str, ...]  # session_ids involved
    detail: str
    severity: str  # low | medium | high

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Data collection (each function is read-only, returns AgentSession lists)
# ---------------------------------------------------------------------------


def _run(cmd: list[str], *, timeout: float = 10.0) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=REPO_ROOT,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return -1, "", str(exc)


def collect_operator_snapshot() -> dict[str, Any]:
    """Run scripts/agent_bridge.py operator-snapshot --json and return parsed payload.

    Returns ``{}`` on any failure rather than raising — this is a best-effort
    enrichment, not a hard dependency.
    """
    rc, out, err = _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "agent_bridge.py"),
            "operator-snapshot",
            "--json",
        ],
        timeout=20.0,
    )
    if rc != 0:
        return {"_error": (err or out).strip()[:500]}
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        return {"_error": f"json parse failed: {exc}"}


def collect_codex_desktop_threads(*, since: timedelta) -> list[AgentSession]:
    """Read recent threads from ~/.codex/state_5.sqlite via read-only URI."""
    sqlite_path = CODEX_HOME / "state_5.sqlite"
    if not sqlite_path.exists():
        return []
    cutoff = int((datetime.now(UTC) - since).timestamp())
    sessions: list[AgentSession] = []
    try:
        uri = f"file:{sqlite_path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(
                """
                SELECT id, cwd, COALESCE(git_branch, '') AS git_branch,
                       COALESCE(model, '') AS model,
                       COALESCE(tokens_used, 0) AS tokens_used,
                       updated_at
                FROM threads
                WHERE updated_at >= ? AND archived = 0
                ORDER BY updated_at DESC
                LIMIT 200
                """,
                (cutoff,),
            )
            for row in cur:
                sessions.append(
                    AgentSession(
                        family="codex_desktop",
                        session_id=str(row["id"]),
                        cwd=row["cwd"] or None,
                        branch=row["git_branch"] or None,
                        extra={
                            "model": row["model"] or None,
                            "tokens_used": int(row["tokens_used"] or 0),
                            "updated_at_epoch": int(row["updated_at"] or 0),
                        },
                    )
                )
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return [
            AgentSession(
                family="codex_desktop",
                session_id="_error",
                cwd=None,
                branch=None,
                extra={"error": str(exc)},
            )
        ]
    return sessions


def collect_codex_cli_liveness() -> list[AgentSession]:
    """Inspect ~/.codex/log/codex-tui.log mtime + alive codex_cli processes."""
    log_path = CODEX_HOME / "log" / "codex-tui.log"
    sessions: list[AgentSession] = []
    if log_path.exists():
        mtime = datetime.fromtimestamp(log_path.stat().st_mtime, tz=UTC)
        age_seconds = int((datetime.now(UTC) - mtime).total_seconds())
        sessions.append(
            AgentSession(
                family="codex_cli",
                session_id="codex-tui.log",
                cwd=None,
                branch=None,
                extra={
                    "log_path": str(log_path),
                    "last_mtime_utc": mtime.isoformat(),
                    "age_seconds": age_seconds,
                    "liveness": "active" if age_seconds < 600 else "idle",
                },
            )
        )
    return sessions


def collect_factory_droid_sessions() -> list[AgentSession]:
    """Read ~/.factory/background-processes.json for Factory Droid sessions."""
    path = FACTORY_HOME / "background-processes.json"
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        return [
            AgentSession(
                family="factory_droid",
                session_id="_error",
                cwd=None,
                branch=None,
                extra={"error": str(exc)},
            )
        ]
    if isinstance(data, dict):
        entries = data.get("processes") or data.get("background-processes") or list(data.values())
    elif isinstance(data, list):
        entries = data
    else:
        entries = []
    sessions: list[AgentSession] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        sid = (
            entry.get("id")
            or entry.get("session_id")
            or entry.get("pid")
            or entry.get("name")
            or "unknown"
        )
        cwd = entry.get("cwd") or entry.get("working_directory") or entry.get("workspace")
        sessions.append(
            AgentSession(
                family="factory_droid",
                session_id=str(sid)[:64],
                cwd=str(cwd) if cwd else None,
                branch=None,
                extra={
                    "name": entry.get("name"),
                    "status": entry.get("status") or entry.get("state"),
                    "pid": entry.get("pid"),
                },
            )
        )
    return sessions


def collect_claude_code_sessions(*, since: timedelta) -> list[AgentSession]:
    """Scan ~/.claude/projects/<encoded-path>/<session-uuid>/ for active sessions.

    The encoded-path folder name is the cwd with '/' replaced by '-', so we
    invert that mapping for the overlap detector.
    """
    if not CLAUDE_PROJECTS_ROOT.exists():
        return []
    cutoff_seconds = (datetime.now(UTC) - since).timestamp()
    sessions: list[AgentSession] = []
    try:
        project_dirs = sorted(p for p in CLAUDE_PROJECTS_ROOT.iterdir() if p.is_dir())
    except OSError:
        return []
    for project_dir in project_dirs:
        # Decode the project cwd from the folder name. Claude Code encodes
        # '/Users/x/y' as '-Users-x-y'.
        encoded = project_dir.name
        cwd = "/" + encoded.strip("-").replace("-", "/")
        try:
            session_dirs = [s for s in project_dir.iterdir() if s.is_dir()]
        except OSError:
            continue
        for session_dir in session_dirs:
            try:
                mtime = session_dir.stat().st_mtime
            except OSError:
                continue
            if mtime < cutoff_seconds:
                continue
            sessions.append(
                AgentSession(
                    family="claude_code",
                    session_id=session_dir.name,
                    cwd=cwd,
                    branch=None,
                    extra={
                        "last_mtime_utc": datetime.fromtimestamp(mtime, tz=UTC).isoformat(),
                        "age_seconds": int(datetime.now(UTC).timestamp() - mtime),
                    },
                )
            )
    return sessions


def collect_worktree_branches() -> list[AgentSession]:
    """Map active git worktrees to branches."""
    rc, out, _ = _run(["git", "worktree", "list", "--porcelain"], timeout=5.0)
    if rc != 0:
        return []
    sessions: list[AgentSession] = []
    current: dict[str, str] = {}
    for raw_line in out.splitlines() + [""]:
        line = raw_line.strip()
        if not line:
            if current:
                path = current.get("worktree")
                branch = current.get("branch")
                if path:
                    sessions.append(
                        AgentSession(
                            family="git_worktree",
                            session_id=path,
                            cwd=path,
                            branch=branch.removeprefix("refs/heads/") if branch else None,
                            extra={"head": current.get("HEAD")},
                        )
                    )
            current = {}
            continue
        if " " in line:
            key, value = line.split(" ", 1)
        else:
            key, value = line, ""
        current[key] = value
    return sessions


def collect_open_pr_branches(*, repo: str = "synaptent/aragora") -> list[AgentSession]:
    """Map open PRs to head branches via gh CLI."""
    rc, out, _ = _run(
        [
            "gh",
            "pr",
            "list",
            "-R",
            repo,
            "--state",
            "open",
            "--limit",
            "50",
            "--json",
            "number,headRefName,headRefOid,isDraft,title",
        ],
        timeout=15.0,
    )
    if rc != 0:
        return []
    try:
        rows = json.loads(out)
    except json.JSONDecodeError:
        return []
    sessions: list[AgentSession] = []
    for row in rows:
        sessions.append(
            AgentSession(
                family="open_pr",
                session_id=f"pr:{row.get('number')}",
                cwd=None,
                branch=row.get("headRefName"),
                extra={
                    "head_sha": (row.get("headRefOid") or "")[:10],
                    "draft": row.get("isDraft"),
                    "title": (row.get("title") or "")[:80],
                },
            )
        )
    return sessions


def collect_aragora_lane_claims() -> list[AgentSession]:
    """Read .aragora/agent-bridge/lanes.json (jsonl) and return active lane claims.

    Each line is a JSON object matching agent_bridge.py's lane-record schema.
    We treat the latest entry per lane_id as the current state.
    """
    if not LANE_REGISTRY_PATH.exists():
        return []
    latest: dict[str, dict[str, Any]] = {}
    try:
        with LANE_REGISTRY_PATH.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                lane_id = str(rec.get("lane_id") or rec.get("lane") or "")
                if not lane_id:
                    continue
                # Choose the newest record per lane_id by timestamp/created_at.
                existing = latest.get(lane_id)
                rec_ts = str(rec.get("timestamp") or rec.get("updated_at") or "")
                existing_ts = str(
                    (existing or {}).get("timestamp") or (existing or {}).get("updated_at") or ""
                )
                if existing is None or rec_ts > existing_ts:
                    latest[lane_id] = rec
    except OSError:
        return []
    sessions: list[AgentSession] = []
    for lane_id, rec in latest.items():
        if str(rec.get("status") or "").lower() in {"released", "archived", "expired"}:
            continue
        sessions.append(
            AgentSession(
                family="aragora_lane",
                session_id=lane_id,
                cwd=rec.get("cwd"),
                branch=rec.get("branch") or rec.get("target_branch"),
                extra={
                    "status": rec.get("status"),
                    "goal": rec.get("goal"),
                    "source": rec.get("source"),
                    "next_action": rec.get("next_action"),
                    "timestamp": rec.get("timestamp"),
                },
            )
        )
    return sessions


# ---------------------------------------------------------------------------
# Overlap detection
# ---------------------------------------------------------------------------


def detect_overlaps(sessions: list[AgentSession]) -> list[Overlap]:
    overlaps: list[Overlap] = []

    # 1. cwd_collision: same non-empty cwd touched by 2+ different agent families
    cwd_index: dict[str, list[AgentSession]] = defaultdict(list)
    for s in sessions:
        if s.cwd:
            cwd_index[s.cwd].append(s)
    for cwd, group in cwd_index.items():
        families = {g.family for g in group}
        if len(families) >= 2 or len(group) >= 3:
            severity = "high" if len(families) >= 3 else "medium"
            members = tuple(f"{g.family}:{g.session_id[:24]}" for g in group)
            overlaps.append(
                Overlap(
                    kind="cwd_collision",
                    members=members,
                    detail=f"{len(group)} session(s) across {len(families)} family/families touching cwd={cwd}",
                    severity=severity,
                )
            )

    # 2. branch_collision: same git branch claimed by 2+ sessions
    branch_index: dict[str, list[AgentSession]] = defaultdict(list)
    for s in sessions:
        if s.branch and s.branch not in ("main", "master", "HEAD"):
            branch_index[s.branch].append(s)
    for branch, group in branch_index.items():
        if len(group) >= 2:
            members = tuple(f"{g.family}:{g.session_id[:24]}" for g in group)
            overlaps.append(
                Overlap(
                    kind="branch_collision",
                    members=members,
                    detail=f"{len(group)} session(s) claiming branch={branch}",
                    severity="high",
                )
            )

    # 3. lane_gap: any active worktree/PR without a corresponding lane claim
    lane_claims = {s.branch for s in sessions if s.family == "aragora_lane" and s.branch}
    active_branches = {
        s.branch
        for s in sessions
        if s.family in {"git_worktree", "open_pr"}
        and s.branch
        and s.branch not in ("main", "master", "HEAD")
    }
    unclaimed = active_branches - lane_claims
    for branch in sorted(unclaimed):
        # find one example session
        example = next(
            (s for s in sessions if s.branch == branch and s.family in {"git_worktree", "open_pr"}),
            None,
        )
        if example is None:
            continue
        overlaps.append(
            Overlap(
                kind="lane_gap",
                members=(f"{example.family}:{example.session_id[:24]}",),
                detail=(
                    f"branch={branch} is active in {example.family} "
                    "but has no aragora lane claim — consider --claim-lane to register it"
                ),
                severity="low",
            )
        )

    return overlaps


# ---------------------------------------------------------------------------
# Lane registry write (--claim-lane)
# ---------------------------------------------------------------------------


_BRANCH_NAME_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


def claim_lane(
    lane_id: str,
    *,
    branch: str | None = None,
    cwd: str | None = None,
    goal: str = "",
    status: str = "active",
    next_action: str = "",
    source: str = "",
) -> dict[str, Any]:
    """Append one row to .aragora/agent-bridge/lanes.json matching the existing schema.

    Discipline: never overwrites or rewrites existing rows; only appends. The
    JSONL format makes this safe for concurrent writers.
    """
    if not _BRANCH_NAME_RE.match(lane_id):
        raise ValueError(f"lane_id contains invalid characters: {lane_id!r}")
    LANE_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "lane_id": lane_id,
        "claim_id": str(uuid.uuid4()),
        "branch": branch,
        "cwd": cwd or str(REPO_ROOT),
        "goal": goal,
        "status": status,
        "next_action": next_action,
        "source": source,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    with LANE_REGISTRY_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def build_report(
    *,
    since: timedelta,
    include_open_prs: bool,
    repo: str,
) -> dict[str, Any]:
    operator_snapshot = collect_operator_snapshot()
    sessions: list[AgentSession] = []
    sessions.extend(collect_codex_desktop_threads(since=since))
    sessions.extend(collect_codex_cli_liveness())
    sessions.extend(collect_factory_droid_sessions())
    sessions.extend(collect_claude_code_sessions(since=since))
    sessions.extend(collect_worktree_branches())
    if include_open_prs:
        sessions.extend(collect_open_pr_branches(repo=repo))
    sessions.extend(collect_aragora_lane_claims())

    overlaps = detect_overlaps(sessions)

    by_family: dict[str, int] = defaultdict(int)
    for s in sessions:
        if s.session_id == "_error":
            continue
        by_family[s.family] += 1

    return {
        "schema_version": "aragora-agent-overlap-report/1.0",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "since_seconds": int(since.total_seconds()),
        "repo": repo,
        "operator_snapshot_summary": operator_snapshot.get("summary", {}),
        "operator_snapshot_process_census": operator_snapshot.get("process_census", {}),
        "session_counts_by_family": dict(by_family),
        "sessions": [s.to_dict() for s in sessions],
        "overlaps": [o.to_dict() for o in overlaps],
        "overlap_count_by_severity": {
            "high": sum(1 for o in overlaps if o.severity == "high"),
            "medium": sum(1 for o in overlaps if o.severity == "medium"),
            "low": sum(1 for o in overlaps if o.severity == "low"),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    out: list[str] = []
    out.append(f"# Agent overlap report ({report['generated_at_utc']})")
    out.append("")
    census = report.get("operator_snapshot_process_census", {})
    if census.get("by_role"):
        out.append("## Process census (from `scripts/agent_bridge.py operator-snapshot`)")
        out.append("")
        for role, count in sorted(census["by_role"].items(), key=lambda kv: -kv[1]):
            out.append(f"- `{role}`: {count}")
        out.append(f"- **total**: {census.get('total', '?')}")
        out.append("")
    out.append("## Active sessions per family (in scanned window)")
    out.append("")
    for family, count in sorted(report["session_counts_by_family"].items()):
        out.append(f"- `{family}`: {count}")
    out.append("")
    overlaps = report.get("overlaps", [])
    if overlaps:
        out.append(f"## Overlaps detected ({len(overlaps)})")
        out.append("")
        for o in overlaps:
            out.append(f"- **[{o['severity'].upper()}] {o['kind']}**: {o['detail']}")
            for m in o["members"]:
                out.append(f"    - `{m}`")
        out.append("")
    else:
        out.append("## Overlaps detected")
        out.append("")
        out.append("_(none in scanned window)_")
        out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_since(value: str) -> timedelta:
    m = re.match(r"^\s*(\d+)\s*([smhd])\s*$", value or "")
    if not m:
        raise ValueError(
            f"invalid --codex-since {value!r}: expected '<int><unit>' with unit in s|m|h|d"
        )
    amount = int(m.group(1))
    return {
        "s": timedelta(seconds=amount),
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
    }[m.group(2)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--codex-since",
        default="4h",
        help="Window for Codex Desktop / Claude session activity (default: 4h)",
    )
    parser.add_argument(
        "--repo",
        default="synaptent/aragora",
        help="GitHub repo for open-PR collection (default: synaptent/aragora)",
    )
    parser.add_argument(
        "--no-prs",
        action="store_true",
        help="Skip open-PR collection (offline mode)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of markdown",
    )
    parser.add_argument(
        "--claim-lane",
        metavar="LANE_ID",
        default=None,
        help="Before report, append a self-claim to .aragora/agent-bridge/lanes.json",
    )
    parser.add_argument(
        "--claim-branch",
        default=None,
        help="Branch name to record on the --claim-lane row (default: current git HEAD)",
    )
    parser.add_argument(
        "--claim-goal",
        default="",
        help="Short goal text to record on the --claim-lane row",
    )
    parser.add_argument(
        "--claim-source",
        default="",
        help="Issue or PR reference to record on the --claim-lane row",
    )
    args = parser.parse_args(argv)

    try:
        since = _parse_since(args.codex_since)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.claim_lane:
        branch = args.claim_branch
        if branch is None:
            rc, out, _ = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=5.0)
            branch = out.strip() if rc == 0 else None
        try:
            record = claim_lane(
                args.claim_lane,
                branch=branch,
                cwd=str(REPO_ROOT),
                goal=args.claim_goal,
                source=args.claim_source,
            )
            print(f"claimed lane: {json.dumps(record, sort_keys=True)}", file=sys.stderr)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    report = build_report(since=since, include_open_prs=not args.no_prs, repo=args.repo)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())

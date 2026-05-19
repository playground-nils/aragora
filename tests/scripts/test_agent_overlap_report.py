"""Tests for ``scripts/agent_overlap_report.py`` (v14 P75).

These tests are fixture-driven and never read the live
``~/.codex/`` / ``~/.factory/`` / ``~/.claude/`` directories. All
collectors are pointed at ``tmp_path``-rooted inputs and the optional
``gh`` / ``git`` runners are replaced with stub callables so the suite
is deterministic and isolated.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "agent_overlap_report.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("agent_overlap_report_under_test", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load spec for {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


aor = _load_module()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_codex_state_db(path: Path, rows: list[dict[str, Any]], *, now_ms: int) -> Path:
    """Build a minimal Codex Desktop state_5.sqlite fixture."""
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE threads (
            id TEXT PRIMARY KEY,
            rollout_path TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            source TEXT NOT NULL,
            model_provider TEXT NOT NULL,
            cwd TEXT NOT NULL,
            title TEXT NOT NULL,
            sandbox_policy TEXT NOT NULL,
            approval_mode TEXT NOT NULL,
            tokens_used INTEGER NOT NULL DEFAULT 0,
            has_user_event INTEGER NOT NULL DEFAULT 0,
            archived INTEGER NOT NULL DEFAULT 0,
            archived_at INTEGER,
            git_sha TEXT,
            git_branch TEXT,
            git_origin_url TEXT,
            cli_version TEXT NOT NULL DEFAULT '',
            first_user_message TEXT NOT NULL DEFAULT '',
            agent_nickname TEXT,
            agent_role TEXT,
            memory_mode TEXT NOT NULL DEFAULT 'enabled',
            model TEXT,
            reasoning_effort TEXT,
            agent_path TEXT,
            created_at_ms INTEGER,
            updated_at_ms INTEGER,
            thread_source TEXT,
            preview TEXT NOT NULL DEFAULT ''
        )
        """
    )
    for row in rows:
        cur.execute(
            "INSERT INTO threads (id, rollout_path, created_at, updated_at, "
            "source, model_provider, cwd, title, sandbox_policy, approval_mode, "
            "archived, git_branch, created_at_ms, updated_at_ms) VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                row["id"],
                row.get("rollout_path", "/tmp/rollout.jsonl"),
                int(now_ms / 1000) - 60,
                int(now_ms / 1000),
                row.get("source", "cli"),
                "openai",
                row["cwd"],
                row.get("title", "test thread"),
                "{}",
                "never",
                int(row.get("archived", 0)),
                row.get("branch", ""),
                now_ms - 60_000,
                row.get("updated_at_ms", now_ms),
            ),
        )
    con.commit()
    con.close()
    return path


def _gh_stub(prs: list[dict[str, Any]]):
    def runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=json.dumps(prs), stderr=""
        )

    return runner


def _git_stub(porcelain: str):
    def runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=porcelain, stderr="")

    return runner


def _make_lane_registry(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_empty_world_no_families_no_overlaps(tmp_path: Path) -> None:
    """All inputs missing → empty families, no overlaps, valid schema."""
    registry = _make_lane_registry(tmp_path / ".aragora" / "agent-bridge" / "lanes.json", [])
    report = aor.build_report(
        since_seconds=3600,
        repo_root=tmp_path,
        registry_path=registry,
        codex_state_db=tmp_path / "missing.sqlite",
        codex_tui_log=tmp_path / "missing-tui.log",
        factory_bg=tmp_path / "missing-bg.json",
        claude_projects=tmp_path / "missing-projects",
        gh_cmd=None,
        git_cmd=None,
    )
    assert report["schema_version"] == aor.SCHEMA_VERSION
    assert report["generated_at_utc"].endswith("Z")
    for fam in (
        "codex_desktop",
        "codex_cli",
        "factory_droid",
        "claude_desktop",
        "claude_cli",
    ):
        assert report["families"][fam]["active_count"] == 0
    assert report["lane_registry"]["active_count"] == 0
    assert report["open_prs"]["count"] == 0
    assert report["worktrees"]["count"] == 0
    assert report["overlaps"] == []


def test_single_family_present_no_overlap(tmp_path: Path) -> None:
    """A single Codex Desktop thread alone is not an overlap."""
    now_ms = 1_900_000_000_000
    state_db = _make_codex_state_db(
        tmp_path / "state.sqlite",
        [
            {
                "id": "thread-A",
                "cwd": "/tmp/wt-A",
                "branch": "feat/A",
                "updated_at_ms": now_ms,
            }
        ],
        now_ms=now_ms,
    )
    registry = _make_lane_registry(tmp_path / "lanes.json", [])
    import datetime as dt

    fixed_now = dt.datetime.fromtimestamp(now_ms / 1000, tz=dt.UTC)
    report = aor.build_report(
        since_seconds=3600,
        repo_root=tmp_path,
        registry_path=registry,
        codex_state_db=state_db,
        codex_tui_log=tmp_path / "absent.log",
        factory_bg=tmp_path / "absent-bg.json",
        claude_projects=tmp_path / "absent-projects",
        gh_cmd=None,
        git_cmd=None,
        now=fixed_now,
    )
    cd = report["families"]["codex_desktop"]
    assert cd["active_count"] == 1
    assert cd["threads"][0]["thread_id"] == "thread-A"
    assert report["families"]["factory_droid"]["active_count"] == 0
    # No collision: only one family touched this cwd.
    assert all(ov["kind"] != "cwd_collision" for ov in report["overlaps"])


def test_cwd_collision_between_two_families(tmp_path: Path) -> None:
    """Same cwd touched by Codex Desktop + Factory Droid → cwd_collision."""
    now_ms = 1_900_000_000_000
    shared_cwd = "/private/tmp/shared-wt"

    state_db = _make_codex_state_db(
        tmp_path / "state.sqlite",
        [
            {
                "id": "thread-X",
                "cwd": shared_cwd,
                "branch": "feat/x",
                "updated_at_ms": now_ms,
            }
        ],
        now_ms=now_ms,
    )

    bg_path = tmp_path / "background-processes.json"
    bg_path.write_text(
        json.dumps(
            {
                "processes": [
                    {
                        "id": "droid-1",
                        "cwd": shared_cwd,
                        "branch": "droid/x",
                        "status": "running",
                    }
                ]
            }
        )
    )

    registry = _make_lane_registry(tmp_path / "lanes.json", [])

    import datetime as dt

    fixed_now = dt.datetime.fromtimestamp(now_ms / 1000, tz=dt.UTC)
    report = aor.build_report(
        since_seconds=3600,
        repo_root=tmp_path,
        registry_path=registry,
        codex_state_db=state_db,
        codex_tui_log=tmp_path / "absent.log",
        factory_bg=bg_path,
        claude_projects=tmp_path / "absent-projects",
        gh_cmd=None,
        git_cmd=None,
        now=fixed_now,
    )
    cwd_collisions = [ov for ov in report["overlaps"] if ov["kind"] == "cwd_collision"]
    assert len(cwd_collisions) == 1
    collision = cwd_collisions[0]
    assert collision["cwd"] == shared_cwd
    families = sorted(c["family"] for c in collision["claimants"])
    assert families == ["codex_desktop", "factory_droid"]


def test_claim_lane_appends_row_to_registry(tmp_path: Path) -> None:
    """--claim-lane writes a single LaneRecord row to the registry."""
    registry = tmp_path / "lanes.json"
    registry.write_text("[]", encoding="utf-8")

    row = aor.claim_lane_row(
        registry,
        lane_id="P75-test",
        owner_session="droid-TEST123",
        goal="unit test claim",
        branch="droid/P75-test-fixture",
        worktree=str(tmp_path / "wt"),
    )
    assert row["lane_id"] == "P75-test"
    assert row["owner_session"] == "droid-TEST123"
    assert row["status"] == "active"
    persisted = json.loads(registry.read_text(encoding="utf-8"))
    assert isinstance(persisted, list)
    assert len(persisted) == 1
    assert persisted[0]["lane_id"] == "P75-test"
    assert persisted[0]["updated_at"].endswith("Z")
    # The row matches LaneRecord schema keys only.
    for key in persisted[0]:
        assert key in aor.LANE_RECORD_KEYS

    # A second claim by a different owner without --force is rejected.
    with pytest.raises(aor.ClaimError):
        aor.claim_lane_row(
            registry,
            lane_id="P75-test",
            owner_session="different-owner",
        )
    # Persisted state is unchanged.
    persisted_after = json.loads(registry.read_text(encoding="utf-8"))
    assert persisted_after[0]["owner_session"] == "droid-TEST123"


def test_stale_lane_claim_detected(tmp_path: Path) -> None:
    """An active lane whose worktree has no live process is reported."""
    stale_lane = {
        "lane_id": "P00-orphan",
        "owner_session": "ghost-session",
        "source": "codex",
        "status": "active",
        "branch": "codex/orphan",
        "worktree": "/private/tmp/orphaned-wt",
        "updated_at": "2026-05-18T04:00:00Z",
    }
    registry = _make_lane_registry(tmp_path / "lanes.json", [stale_lane])
    report = aor.build_report(
        since_seconds=3600,
        repo_root=tmp_path,
        registry_path=registry,
        codex_state_db=tmp_path / "missing.sqlite",
        codex_tui_log=tmp_path / "missing.log",
        factory_bg=tmp_path / "missing-bg.json",
        claude_projects=tmp_path / "missing-projects",
        gh_cmd=None,
        git_cmd=None,
    )
    stale = [ov for ov in report["overlaps"] if ov["kind"] == "stale_lane_claim"]
    assert len(stale) == 1
    assert stale[0]["lane_id"] == "P00-orphan"
    assert stale[0]["worktree"] == "/private/tmp/orphaned-wt"
    assert stale[0]["no_matching_process"] is True


def test_branch_collision_across_sources(tmp_path: Path) -> None:
    """A branch claimed by both an active lane and an open PR collides."""
    lane = {
        "lane_id": "P10-feature",
        "owner_session": "claude-X",
        "source": "claude",
        "status": "active",
        "branch": "feature/shared-branch",
        "worktree": str(tmp_path / "wt"),
        "updated_at": "2026-05-18T04:00:00Z",
    }
    registry = _make_lane_registry(tmp_path / "lanes.json", [lane])
    gh_stub = aor._default_runner  # noqa: SLF001  (touch attr to avoid unused import warn)
    del gh_stub
    # Inject stubs by monkey-patching the helper that wraps gh / git.
    # We can avoid that by calling the lower-level collectors directly.
    families = {
        "codex_desktop": {"active_count": 0, "threads": []},
        "codex_cli": {"active_count": 0, "processes": []},
        "factory_droid": {"active_count": 0, "sessions": []},
        "claude_desktop": {"active_count": 0, "projects": []},
        "claude_cli": {"active_count": 0, "sessions": []},
    }
    lane_registry = aor.collect_lane_registry(registry_path=registry)
    open_prs = aor.collect_open_prs(
        _gh_stub(
            [
                {
                    "number": 4242,
                    "headRefName": "feature/shared-branch",
                    "author": {"login": "octocat"},
                }
            ]
        )
    )
    worktrees = aor.collect_worktrees(_git_stub(""))
    overlaps = aor.detect_overlaps(
        families=families,
        lane_registry=lane_registry,
        worktrees=worktrees,
        open_prs=open_prs,
    )
    branch_overlaps = [ov for ov in overlaps if ov["kind"] == "branch_collision"]
    assert len(branch_overlaps) == 1
    collision = branch_overlaps[0]
    assert collision["branch"] == "feature/shared-branch"
    sources = sorted(c["source"] for c in collision["claimants"])
    assert sources == ["lane_registry", "open_pr"]


def test_markdown_render_smoke(tmp_path: Path) -> None:
    """``render_markdown`` produces a non-empty table with the schema header."""
    registry = _make_lane_registry(tmp_path / "lanes.json", [])
    report = aor.build_report(
        since_seconds=3600,
        repo_root=tmp_path,
        registry_path=registry,
        codex_state_db=tmp_path / "missing.sqlite",
        codex_tui_log=tmp_path / "missing.log",
        factory_bg=tmp_path / "missing-bg.json",
        claude_projects=tmp_path / "missing-projects",
        gh_cmd=None,
        git_cmd=None,
    )
    md = aor.render_markdown(report)
    assert aor.SCHEMA_VERSION in md
    assert "## Families" in md
    assert "## Overlaps" in md
    assert "No overlaps detected" in md


def test_cli_main_json_default(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``main()`` defaults to JSON and produces a parseable payload."""
    registry = _make_lane_registry(tmp_path / "lanes.json", [])
    rc = aor.main(
        [
            "--registry-path",
            str(registry),
            "--codex-state-db",
            str(tmp_path / "missing.sqlite"),
            "--codex-tui-log",
            str(tmp_path / "missing.log"),
            "--factory-bg",
            str(tmp_path / "missing-bg.json"),
            "--claude-projects",
            str(tmp_path / "missing-projects"),
            "--gh-cmd",
            "",
            "--git-cmd",
            "",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert rc == 0
    captured = capsys.readouterr().out
    payload = json.loads(captured)
    assert payload["schema_version"] == aor.SCHEMA_VERSION
    assert payload["overlaps"] == []

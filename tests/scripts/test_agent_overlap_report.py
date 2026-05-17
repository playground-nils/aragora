"""Tests for scripts/agent_overlap_report.py — cross-agent overlap consolidator."""

from __future__ import annotations

import json
import sqlite3
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

# Add repo root to path so `import scripts.agent_overlap_report` works.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts import agent_overlap_report as mod  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures: synthetic homes for every data source.
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_codex_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "codex"
    home.mkdir()
    monkeypatch.setattr(mod, "CODEX_HOME", home)
    # Build a tiny SQLite with the threads-table subset our reader uses.
    sqlite_path = home / "state_5.sqlite"
    conn = sqlite3.connect(sqlite_path)
    conn.executescript(
        """
        CREATE TABLE threads (
            id TEXT PRIMARY KEY,
            cwd TEXT NOT NULL,
            git_branch TEXT,
            model TEXT,
            tokens_used INTEGER DEFAULT 0,
            updated_at INTEGER NOT NULL,
            archived INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    now = int(time.time())
    rows = [
        ("recent-a", "/Users/test/repo", "main", "gpt-5.5", 1234, now - 600, 0),
        ("recent-b", "/Users/test/other", "feature/x", "gpt-5.5", 50, now - 60, 0),
        ("old-c", "/Users/test/repo", "main", "gpt-5.4", 0, now - 10 * 86400, 0),
        ("archived-d", "/Users/test/repo", "main", "gpt-5.4", 0, now - 60, 1),
    ]
    conn.executemany(
        "INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    # Also stage a codex-tui.log so the CLI liveness collector finds something.
    log_dir = home / "log"
    log_dir.mkdir()
    (log_dir / "codex-tui.log").write_text("hello\n", encoding="utf-8")
    return home


@pytest.fixture
def fake_factory_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "factory"
    home.mkdir()
    monkeypatch.setattr(mod, "FACTORY_HOME", home)
    (home / "background-processes.json").write_text(
        json.dumps(
            [
                {
                    "id": "droid-001",
                    "name": "engineering-droid",
                    "cwd": "/Users/test/repo",
                    "status": "running",
                    "pid": 1234,
                },
                {
                    "id": "droid-002",
                    "name": "review-droid",
                    "cwd": "/Users/test/repo",
                    "status": "running",
                    "pid": 5678,
                },
            ]
        ),
        encoding="utf-8",
    )
    return home


@pytest.fixture
def fake_claude_projects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "claude_projects"
    root.mkdir()
    monkeypatch.setattr(mod, "CLAUDE_PROJECTS_ROOT", root)
    # Encode "/Users/test/repo" → "-Users-test-repo"
    proj = root / "-Users-test-repo"
    proj.mkdir()
    sess = proj / "018dc901-963a-4968-a7da-530058561c48"
    sess.mkdir()
    return root


@pytest.fixture
def fake_lane_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    registry = tmp_path / "lanes.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mod, "LANE_REGISTRY_PATH", registry)
    return registry


# ---------------------------------------------------------------------------
# Per-collector tests
# ---------------------------------------------------------------------------


def test_codex_desktop_collector_returns_recent_unarchived_only(fake_codex_home: Path) -> None:
    sessions = mod.collect_codex_desktop_threads(since=timedelta(hours=2))
    ids = {s.session_id for s in sessions}
    assert "recent-a" in ids
    assert "recent-b" in ids
    assert "old-c" not in ids  # outside window
    assert "archived-d" not in ids  # archived excluded
    # Schema sanity
    recent = next(s for s in sessions if s.session_id == "recent-a")
    assert recent.family == "codex_desktop"
    assert recent.cwd == "/Users/test/repo"
    assert recent.branch == "main"
    assert recent.extra["model"] == "gpt-5.5"


def test_codex_cli_collector_emits_log_liveness(fake_codex_home: Path) -> None:
    sessions = mod.collect_codex_cli_liveness()
    assert len(sessions) == 1
    assert sessions[0].family == "codex_cli"
    assert sessions[0].extra["liveness"] in {"active", "idle"}


def test_factory_droid_collector_parses_list(fake_factory_home: Path) -> None:
    sessions = mod.collect_factory_droid_sessions()
    ids = {s.session_id for s in sessions}
    assert ids == {"droid-001", "droid-002"}
    assert all(s.family == "factory_droid" for s in sessions)
    assert all(s.cwd == "/Users/test/repo" for s in sessions)


def test_factory_droid_collector_handles_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mod, "FACTORY_HOME", tmp_path / "nope")
    assert mod.collect_factory_droid_sessions() == []


def test_claude_code_collector_decodes_cwd(fake_claude_projects: Path) -> None:
    sessions = mod.collect_claude_code_sessions(since=timedelta(days=1))
    assert len(sessions) == 1
    s = sessions[0]
    assert s.family == "claude_code"
    assert s.cwd == "/Users/test/repo"
    assert s.session_id == "018dc901-963a-4968-a7da-530058561c48"


def test_claude_code_collector_skips_old_sessions(
    fake_claude_projects: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Backdate the session dir to 10 days ago
    sess = fake_claude_projects / "-Users-test-repo" / "018dc901-963a-4968-a7da-530058561c48"
    old = time.time() - 10 * 86400
    import os

    os.utime(sess, (old, old))
    sessions = mod.collect_claude_code_sessions(since=timedelta(hours=1))
    assert sessions == []


# ---------------------------------------------------------------------------
# Overlap detection
# ---------------------------------------------------------------------------


def _sess(
    family: str, sid: str, cwd: str | None = None, branch: str | None = None
) -> "mod.AgentSession":
    return mod.AgentSession(family=family, session_id=sid, cwd=cwd, branch=branch, extra={})


def test_detect_cwd_collision_across_families() -> None:
    sessions = [
        _sess("codex_desktop", "a", cwd="/repo"),
        _sess("factory_droid", "b", cwd="/repo"),
        _sess("claude_code", "c", cwd="/repo"),
    ]
    overlaps = mod.detect_overlaps(sessions)
    cwd = [o for o in overlaps if o.kind == "cwd_collision"]
    assert len(cwd) == 1
    assert cwd[0].severity == "high"  # 3 distinct families
    assert "/repo" in cwd[0].detail


def test_detect_branch_collision() -> None:
    sessions = [
        _sess("codex_desktop", "a", branch="feature/x"),
        _sess("aragora_lane", "b", branch="feature/x"),
        _sess("open_pr", "pr:42", branch="other"),
    ]
    overlaps = mod.detect_overlaps(sessions)
    branch = [o for o in overlaps if o.kind == "branch_collision"]
    assert len(branch) == 1
    assert branch[0].severity == "high"


def test_detect_branch_collision_ignores_main() -> None:
    sessions = [
        _sess("codex_desktop", "a", branch="main"),
        _sess("aragora_lane", "b", branch="main"),
    ]
    overlaps = mod.detect_overlaps(sessions)
    assert all(o.kind != "branch_collision" for o in overlaps)


def test_detect_lane_gap_for_unclaimed_active_branch() -> None:
    sessions = [
        _sess("git_worktree", "/path/wt", cwd="/path/wt", branch="codex/foo"),
        # No aragora_lane with matching branch
    ]
    overlaps = mod.detect_overlaps(sessions)
    gaps = [o for o in overlaps if o.kind == "lane_gap"]
    assert len(gaps) == 1
    assert "codex/foo" in gaps[0].detail


def test_detect_no_lane_gap_when_claim_exists() -> None:
    sessions = [
        _sess("git_worktree", "/path/wt", cwd="/path/wt", branch="codex/foo"),
        _sess("aragora_lane", "codex/foo-lane", branch="codex/foo"),
    ]
    overlaps = mod.detect_overlaps(sessions)
    assert all(o.kind != "lane_gap" for o in overlaps)


# ---------------------------------------------------------------------------
# Lane claim writer
# ---------------------------------------------------------------------------


def test_claim_lane_appends_jsonl_row(fake_lane_registry: Path) -> None:
    record = mod.claim_lane(
        "test-lane-001",
        branch="my-branch",
        cwd="/tmp/x",
        goal="testing",
        source="#999",
    )
    assert record["lane_id"] == "test-lane-001"
    assert record["branch"] == "my-branch"
    assert "claim_id" in record
    assert "timestamp" in record
    # File should be JSONL with our one row
    content = fake_lane_registry.read_text(encoding="utf-8").strip().splitlines()
    assert len(content) == 1
    parsed = json.loads(content[0])
    assert parsed["lane_id"] == "test-lane-001"
    assert parsed["goal"] == "testing"


def test_claim_lane_rejects_invalid_id(fake_lane_registry: Path) -> None:
    with pytest.raises(ValueError):
        mod.claim_lane("bad lane id with spaces")


def test_claim_lane_appends_does_not_overwrite(fake_lane_registry: Path) -> None:
    mod.claim_lane("lane-1", goal="first")
    mod.claim_lane("lane-2", goal="second")
    mod.claim_lane("lane-1", goal="updated")
    lines = fake_lane_registry.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3


def test_aragora_lane_collector_picks_latest_per_lane(fake_lane_registry: Path) -> None:
    # Two records for same lane_id; latest should win
    mod.claim_lane("lane-x", goal="v1", branch="feat")
    # Force a microsecond difference
    time.sleep(0.001)
    mod.claim_lane("lane-x", goal="v2", branch="feat", status="active")
    mod.claim_lane("lane-released", branch="released-branch", status="released")
    sessions = mod.collect_aragora_lane_claims()
    # released lane filtered out; lane-x present with latest goal
    ids = {s.session_id for s in sessions}
    assert "lane-x" in ids
    assert "lane-released" not in ids
    lane_x = next(s for s in sessions if s.session_id == "lane-x")
    assert lane_x.extra["goal"] == "v2"


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------


def test_render_markdown_includes_session_counts(
    fake_codex_home: Path,
    fake_factory_home: Path,
    fake_claude_projects: Path,
    fake_lane_registry: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Block subprocess calls (gh / git) for offline test
    def fake_run(cmd, **kwargs):
        return -1, "", "blocked in test"

    monkeypatch.setattr(mod, "_run", fake_run)
    monkeypatch.setattr(
        mod, "collect_operator_snapshot", lambda: {"summary": {}, "process_census": {}}
    )

    report = mod.build_report(since=timedelta(hours=4), include_open_prs=False, repo="x/y")
    md = mod.render_markdown(report)
    assert "Active sessions per family" in md
    assert "codex_desktop" in md
    assert "factory_droid" in md
    assert "claude_code" in md


def test_build_report_json_shape(
    fake_codex_home: Path,
    fake_factory_home: Path,
    fake_claude_projects: Path,
    fake_lane_registry: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(cmd, **kwargs):
        return -1, "", "blocked"

    monkeypatch.setattr(mod, "_run", fake_run)
    monkeypatch.setattr(
        mod, "collect_operator_snapshot", lambda: {"summary": {}, "process_census": {}}
    )

    report = mod.build_report(since=timedelta(hours=4), include_open_prs=False, repo="x/y")
    assert report["schema_version"] == "aragora-agent-overlap-report/1.0"
    assert "sessions" in report
    assert "overlaps" in report
    assert "overlap_count_by_severity" in report
    assert "session_counts_by_family" in report


# ---------------------------------------------------------------------------
# Safety: no aragora imports
# ---------------------------------------------------------------------------


def test_script_has_no_aragora_imports() -> None:
    text = (REPO_ROOT / "scripts" / "agent_overlap_report.py").read_text(encoding="utf-8")
    forbidden = (
        "import aragora",
        "from aragora",
        "from aragora.",
    )
    for needle in forbidden:
        assert needle not in text, f"agent_overlap_report.py should not contain {needle!r}"


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def test_main_emits_markdown_by_default(
    fake_codex_home: Path,
    fake_factory_home: Path,
    fake_claude_projects: Path,
    fake_lane_registry: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mod, "_run", lambda *_a, **_k: (-1, "", "blocked"))
    monkeypatch.setattr(
        mod, "collect_operator_snapshot", lambda: {"summary": {}, "process_census": {}}
    )
    rc = mod.main(["--no-prs"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Agent overlap report" in out
    assert "Active sessions per family" in out


def test_main_emits_json_when_flag_set(
    fake_codex_home: Path,
    fake_factory_home: Path,
    fake_claude_projects: Path,
    fake_lane_registry: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mod, "_run", lambda *_a, **_k: (-1, "", "blocked"))
    monkeypatch.setattr(
        mod, "collect_operator_snapshot", lambda: {"summary": {}, "process_census": {}}
    )
    rc = mod.main(["--no-prs", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["schema_version"] == "aragora-agent-overlap-report/1.0"


def test_main_claim_lane_writes_then_reports(
    fake_codex_home: Path,
    fake_factory_home: Path,
    fake_claude_projects: Path,
    fake_lane_registry: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mod, "_run", lambda *_a, **_k: (0, "fake-branch\n", ""))
    monkeypatch.setattr(
        mod, "collect_operator_snapshot", lambda: {"summary": {}, "process_census": {}}
    )
    rc = mod.main(["--no-prs", "--json", "--claim-lane", "test-lane", "--claim-goal", "demo"])
    out = capsys.readouterr()
    assert rc == 0
    assert "claimed lane" in out.err
    payload = json.loads(out.out)
    # The lane we just claimed should appear in the sessions list (as aragora_lane)
    lane_ids = [s["session_id"] for s in payload["sessions"] if s["family"] == "aragora_lane"]
    assert "test-lane" in lane_ids


def test_main_rejects_bad_since(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = mod.main(["--no-prs", "--codex-since", "nonsense"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "invalid" in err.lower()

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import scripts.audit_branch_backlog_parallel as mod


UTC = timezone.utc


def _branch_row(name: str = "codex/active") -> dict[str, Any]:
    return {
        "name": name,
        "head_sha": "abc1234",
        "committed_at": datetime.now(UTC).isoformat(),
        "ahead_count": "1",
        "subject": "fix automation classifier",
    }


def test_has_active_session_recognizes_canonical_codex_marker(tmp_path: Path) -> None:
    (tmp_path / ".codex_session_active").write_text("active\n", encoding="utf-8")

    assert mod._has_active_session(tmp_path) is True


def test_classify_one_protects_canonical_active_session_marker(tmp_path: Path) -> None:
    branch = "codex/active"
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / ".codex_session_active").write_text("active\n", encoding="utf-8")

    record = mod._classify_one(
        branch_row=_branch_row(branch),
        open_pr_branches={},
        receipted_branches=set(),
        outbox_branches=set(),
        worktrees={branch: [worktree]},
        merged=set(),
        remotes=set(),
        patch_equivalents={},
        handoff_patch_ids=set(),
        branch_patch_ids_map={},
        recent_threshold=datetime.now(UTC) - timedelta(hours=72),
    )

    assert record["category"] == mod.CATEGORY_PROTECTED_ACTIVE_WT
    assert record["active_session"] is True
    assert record["worktree_paths"] == [str(worktree)]

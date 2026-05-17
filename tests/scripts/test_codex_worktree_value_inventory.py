"""Tests for scripts/codex_worktree_value_inventory.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from collections.abc import Generator
from typing import Any

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


@pytest.fixture(autouse=True)
def _setup_path() -> Generator[None, None, None]:
    sys.path.insert(0, str(SCRIPTS_DIR))
    yield
    sys.path.remove(str(SCRIPTS_DIR))


def _context(tmp_path: Path, **overrides: Any) -> Any:
    import codex_worktree_value_inventory as mod

    values: dict[str, Any] = {
        "repo": tmp_path,
        "base": "origin/main",
        "base_sha": "base-sha",
        "repo_remote_urls": {"https://example.test/target"},
        "strict_repo_identity": False,
        "outbox_dir": tmp_path / ".aragora" / "automation-outbox",
        "receipt_dir": tmp_path / ".aragora" / "automation-receipts",
        "worktrees_by_path": {},
        "unresolved_outbox_branches": set(),
        "terminal_receipt_branch_heads": {},
        "skip_gh": False,
        "git_timeout": 1,
        "gh_timeout": 1,
        "patch_timeout": 1,
    }
    values.update(overrides)
    outbox_dir = values["outbox_dir"]
    receipt_dir = values["receipt_dir"]
    assert isinstance(outbox_dir, Path)
    assert isinstance(receipt_dir, Path)
    outbox_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    return mod.InventoryContext(**values)


def _candidate(tmp_path: Path, name: str = "abcd", *, repo: bool = True) -> Path:
    root = tmp_path / name
    root.mkdir(parents=True)
    if repo:
        repo_path = root / "aragora"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()
    return root


def _stub_clean_git(
    monkeypatch: pytest.MonkeyPatch,
    *,
    branch: str | None = "codex/test",
    head: str | None = "abcdef123456",
    ahead: int | None = 0,
    behind: int | None = 0,
    dirty: bool = False,
    open_prs: list[dict[str, Any]] | None = None,
    open_pr_failed: bool = False,
    patch_equivalent: bool = False,
) -> None:
    import codex_worktree_value_inventory as mod

    monkeypatch.setattr(mod, "git_branch", lambda *_args, **_kwargs: (branch, False, None))
    monkeypatch.setattr(mod, "git_head", lambda *_args, **_kwargs: (head, False, None))
    monkeypatch.setattr(mod, "git_status_dirty", lambda *_args, **_kwargs: (dirty, False, None))
    monkeypatch.setattr(
        mod,
        "git_ahead_behind",
        lambda *_args, **_kwargs: (ahead, behind, False, None),
    )
    monkeypatch.setattr(
        mod,
        "lookup_open_prs",
        lambda *_args, **_kwargs: (
            open_prs or [],
            open_pr_failed,
            "open PR lookup failed" if open_pr_failed else None,
        ),
    )
    monkeypatch.setattr(mod, "is_patch_equivalent", lambda *_args, **_kwargs: patch_equivalent)


def test_default_scan_preserves_foreign_repo_as_lookup_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    root = _candidate(tmp_path)
    _stub_clean_git(monkeypatch, ahead=0)
    monkeypatch.setattr(
        mod, "repo_remote_urls", lambda *_args, **_kwargs: {"https://example.test/other"}
    )

    candidate = mod.classify_candidate(
        root,
        context=_context(
            tmp_path,
            strict_repo_identity=True,
            repo_remote_urls={"https://example.test/target"},
        ),
        size_bytes=1024,
        size_lookup_failed=False,
    )

    assert candidate.classification == "lookup_failed"
    assert candidate.cleanup_candidate is False
    assert candidate.decision == "preserve"
    assert "repo identity does not match target repo" in candidate.proof
    assert "repo identity does not match target repo" in candidate.git.lookup_errors


def test_explicit_root_scan_allows_foreign_repo_for_backwards_compat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    root = _candidate(tmp_path)
    _stub_clean_git(monkeypatch, ahead=0)
    monkeypatch.setattr(
        mod, "repo_remote_urls", lambda *_args, **_kwargs: {"https://example.test/other"}
    )

    candidate = mod.classify_candidate(
        root,
        context=_context(
            tmp_path,
            strict_repo_identity=False,
            repo_remote_urls={"https://example.test/target"},
        ),
        size_bytes=1024,
        size_lookup_failed=False,
    )

    assert candidate.classification == "unregistered_git_residue"
    assert candidate.cleanup_candidate is True


def test_no_git_cache_residue_is_cleanup_candidate(tmp_path: Path) -> None:
    import codex_worktree_value_inventory as mod

    root = _candidate(tmp_path, repo=False)

    candidate = mod.classify_candidate(
        root,
        context=_context(tmp_path),
        size_bytes=1024,
        size_lookup_failed=False,
    )

    assert candidate.classification == "no_git_cache_residue"
    assert candidate.cleanup_candidate is True
    assert candidate.decision == "cleanup_candidate"


def test_no_git_active_marker_is_preserved(tmp_path: Path) -> None:
    import codex_worktree_value_inventory as mod

    root = _candidate(tmp_path, repo=False)
    (root / ".codex_session_active").write_text("active\n")

    candidate = mod.classify_candidate(
        root,
        context=_context(tmp_path),
        size_bytes=1024,
        size_lookup_failed=False,
    )

    assert candidate.classification == "active_or_dirty"
    assert candidate.cleanup_candidate is False
    assert candidate.decision == "preserve"


def test_dirty_repo_takes_priority_over_unique_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    root = _candidate(tmp_path)
    _stub_clean_git(monkeypatch, ahead=3, dirty=True)

    candidate = mod.classify_candidate(
        root,
        context=_context(tmp_path),
        size_bytes=1024,
        size_lookup_failed=False,
    )

    assert candidate.classification == "active_or_dirty"
    assert "git status is dirty or unavailable" in candidate.proof


def test_open_pr_classification_blocks_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    root = _candidate(tmp_path)
    _stub_clean_git(
        monkeypatch,
        ahead=2,
        open_prs=[{"number": 1, "title": "PR", "url": "https://example.test/pr/1"}],
    )

    candidate = mod.classify_candidate(
        root,
        context=_context(tmp_path),
        size_bytes=1024,
        size_lookup_failed=False,
    )

    assert candidate.classification == "open_pr_or_outbox"
    assert candidate.cleanup_candidate is False


def test_unresolved_outbox_classification_blocks_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    root = _candidate(tmp_path)
    _stub_clean_git(monkeypatch, ahead=2)

    candidate = mod.classify_candidate(
        root,
        context=_context(tmp_path, unresolved_outbox_branches={"codex/test"}),
        size_bytes=1024,
        size_lookup_failed=False,
    )

    assert candidate.classification == "open_pr_or_outbox"
    assert "unresolved automation outbox references branch" in candidate.proof


def test_terminal_receipt_classification_blocks_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    root = _candidate(tmp_path)
    _stub_clean_git(monkeypatch, ahead=2, head="abcdef123456")

    candidate = mod.classify_candidate(
        root,
        context=_context(tmp_path, terminal_receipt_branch_heads={"codex/test": {"abcdef1"}}),
        size_bytes=1024,
        size_lookup_failed=False,
    )

    assert candidate.classification == "receipt_protected"
    assert candidate.cleanup_candidate is False


def test_unique_unharvested_when_ahead_and_not_patch_equivalent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    root = _candidate(tmp_path)
    _stub_clean_git(monkeypatch, ahead=2, patch_equivalent=False)

    candidate = mod.classify_candidate(
        root,
        context=_context(tmp_path),
        size_bytes=1024,
        size_lookup_failed=False,
    )

    assert candidate.classification == "unique_unharvested"
    assert candidate.decision == "harvest_candidate"
    assert candidate.cleanup_candidate is False


def test_patch_equivalent_ahead_work_is_cleanup_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    root = _candidate(tmp_path)
    _stub_clean_git(monkeypatch, ahead=2, patch_equivalent=True)

    candidate = mod.classify_candidate(
        root,
        context=_context(tmp_path),
        size_bytes=1024,
        size_lookup_failed=False,
    )

    assert candidate.classification == "patch_equivalent_or_merged"
    assert candidate.cleanup_candidate is True


def test_lookup_failure_preserves_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    root = _candidate(tmp_path)
    _stub_clean_git(monkeypatch, ahead=0, open_pr_failed=True)

    candidate = mod.classify_candidate(
        root,
        context=_context(tmp_path),
        size_bytes=1024,
        size_lookup_failed=False,
    )

    assert candidate.classification == "lookup_failed"
    assert candidate.cleanup_candidate is False
    assert "open PR lookup failed" in candidate.git.lookup_errors


def test_summary_reports_top_cleanup_and_harvest_candidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    cleanup_root = _candidate(tmp_path, "cleanup")
    unique_root = _candidate(tmp_path, "unique")
    _stub_clean_git(monkeypatch, ahead=0)
    cleanup = mod.classify_candidate(
        cleanup_root,
        context=_context(tmp_path),
        size_bytes=2048,
        size_lookup_failed=False,
    )
    _stub_clean_git(monkeypatch, ahead=1, patch_equivalent=False)
    unique = mod.classify_candidate(
        unique_root,
        context=_context(tmp_path),
        size_bytes=4096,
        size_lookup_failed=False,
    )

    summary = mod.build_summary([cleanup, unique])

    assert summary["cleanup_candidate_count"] == 1
    assert summary["harvest_candidate_count"] == 1
    assert summary["top_cleanup_candidates"][0]["path"] == str(cleanup_root)
    assert summary["top_unique_unharvested"][0]["path"] == str(unique_root)


def test_write_ledger_creates_snapshot_latest_and_jsonl(tmp_path: Path) -> None:
    import codex_worktree_value_inventory as mod

    payload = {
        "schema": mod.SCHEMA,
        "generated_at": "2026-05-16T17:00:00+00:00",
        "root": "/tmp/root",
        "summary": {"total_candidates": 0},
    }

    written = mod.write_ledger(tmp_path / "ledger", payload)

    assert Path(written["snapshot"]).is_file()
    assert Path(written["latest"]).is_file()
    ledger_lines = Path(written["ledger"]).read_text(encoding="utf-8").splitlines()
    assert len(ledger_lines) == 1
    assert json.loads(ledger_lines[0])["event_type"] == "inventory"


def test_resolve_default_roots_picks_canonical_then_legacy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    repo = tmp_path / "repo"
    canonical = repo / mod.DEFAULT_CANONICAL_REL_ROOT
    legacy = tmp_path / "home" / ".codex" / "worktrees"
    canonical.mkdir(parents=True)
    legacy.mkdir(parents=True)
    monkeypatch.setattr(mod, "DEFAULT_LEGACY_ROOT", legacy)

    roots = mod.resolve_default_roots(repo)

    assert roots == [canonical.resolve(), legacy.resolve()]


def test_resolve_default_roots_skips_missing_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    repo = tmp_path / "repo"
    repo.mkdir()
    legacy = tmp_path / "home" / ".codex" / "worktrees"
    legacy.mkdir(parents=True)
    monkeypatch.setattr(mod, "DEFAULT_LEGACY_ROOT", legacy)

    roots = mod.resolve_default_roots(repo)

    assert roots == [legacy.resolve()]


def test_resolve_default_roots_empty_when_neither_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    repo = tmp_path / "repo"
    repo.mkdir()
    legacy = tmp_path / "nonexistent" / ".codex" / "worktrees"
    monkeypatch.setattr(mod, "DEFAULT_LEGACY_ROOT", legacy)

    roots = mod.resolve_default_roots(repo)

    assert roots == []


def test_resolve_default_roots_dedups_when_paths_resolve_equal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    repo = tmp_path / "repo"
    canonical = repo / mod.DEFAULT_CANONICAL_REL_ROOT
    canonical.mkdir(parents=True)
    legacy_alias = tmp_path / "legacy-link"
    legacy_alias.symlink_to(canonical, target_is_directory=True)
    monkeypatch.setattr(mod, "DEFAULT_LEGACY_ROOT", legacy_alias)

    roots = mod.resolve_default_roots(repo)

    assert roots == [canonical.resolve()]


def test_resolve_default_roots_uses_git_common_dir_for_managed_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    repo = tmp_path / "repo"
    main_canonical = repo / mod.DEFAULT_CANONICAL_REL_ROOT
    managed_worktree = main_canonical / "codex-session"
    git_common_dir = repo / ".git"
    main_canonical.mkdir(parents=True)
    managed_worktree.mkdir()
    git_common_dir.mkdir()
    legacy = tmp_path / "home" / ".codex" / "worktrees"
    legacy.mkdir(parents=True)
    monkeypatch.setattr(mod, "DEFAULT_LEGACY_ROOT", legacy)
    monkeypatch.setattr(mod, "_git_common_dir", lambda _repo: git_common_dir)

    roots = mod.resolve_default_roots(managed_worktree)

    assert roots == [main_canonical.resolve(), legacy.resolve()]


def test_candidate_roots_from_unions_entries_across_roots(tmp_path: Path) -> None:
    import codex_worktree_value_inventory as mod

    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    (root_a / "alpha").mkdir(parents=True)
    (root_a / "beta").mkdir()
    (root_b / "gamma").mkdir(parents=True)
    (root_a / "ignored.txt").write_text("not a dir")

    result = mod.candidate_roots_from([root_a, root_b])

    assert result == [root_a / "alpha", root_a / "beta", root_b / "gamma"]


def test_candidate_roots_from_dedups_same_resolved_path(tmp_path: Path) -> None:
    import codex_worktree_value_inventory as mod

    root_a = tmp_path / "a"
    root_b_alias = tmp_path / "b-link"
    (root_a / "alpha").mkdir(parents=True)
    root_b_alias.symlink_to(root_a, target_is_directory=True)

    result = mod.candidate_roots_from([root_a, root_b_alias])

    assert result == [root_a / "alpha"]


def test_candidate_roots_from_applies_overall_limit(tmp_path: Path) -> None:
    import codex_worktree_value_inventory as mod

    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    for name in ("alpha", "beta", "gamma"):
        (root_a / name).mkdir(parents=True)
    for name in ("delta",):
        (root_b / name).mkdir(parents=True)

    result = mod.candidate_roots_from([root_a, root_b], limit=2)

    assert len(result) == 2
    assert result[0].name == "alpha"
    assert result[1].name == "beta"


def test_candidate_roots_from_skips_missing_roots(tmp_path: Path) -> None:
    import codex_worktree_value_inventory as mod

    root_a = tmp_path / "a"
    missing = tmp_path / "missing"
    (root_a / "alpha").mkdir(parents=True)

    result = mod.candidate_roots_from([missing, root_a])

    assert result == [root_a / "alpha"]


def test_inventory_runtime_budget_truncates_candidate_processing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    root = tmp_path / "root"
    for name in ("alpha", "beta", "gamma"):
        (root / name).mkdir(parents=True)
    now = [0.0]
    monkeypatch.setattr(mod.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(mod, "resolve_repo", lambda _repo: tmp_path)
    monkeypatch.setattr(mod, "resolve_ref", lambda *_args, **_kwargs: "base-sha")
    monkeypatch.setattr(mod, "repo_remote_urls", lambda *_args, **_kwargs: set())
    monkeypatch.setattr(mod, "parse_worktree_list", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(mod, "unresolved_outbox_handoff_branches", lambda *_args, **_kwargs: set())
    monkeypatch.setattr(
        mod,
        "terminal_receipted_handoff_branch_heads",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        mod,
        "measure_sizes",
        lambda paths, **_kwargs: ({str(path): 0 for path in paths}, set()),
    )

    def fake_classify(path: Path, **_kwargs: Any) -> Any:
        now[0] += 2.0
        return mod.build_candidate(
            path,
            None,
            0,
            False,
            "no_git_cache_residue",
            False,
            [],
            mod.GitInfo(),
            {"open_prs": [], "outbox_files": [], "receipt_files": []},
            ["fake candidate"],
        )

    monkeypatch.setattr(mod, "classify_candidate", fake_classify)

    payload = mod.inventory(
        roots=[root],
        repo=tmp_path,
        base="origin/main",
        outbox_dir=tmp_path / "outbox",
        receipt_dir=tmp_path / "receipts",
        limit=None,
        size_mode="stat",
        size_timeout=120,
        skip_gh=True,
        git_timeout=30,
        gh_timeout=30,
        patch_timeout=30,
        max_runtime_seconds=1,
    )

    summary = payload["summary"]
    assert summary["candidate_count_total"] == 3
    assert summary["candidate_count_scanned"] == 1
    assert summary["candidates_skipped_by_runtime_budget"] == 2
    assert summary["truncated_by_runtime_budget"] is True
    assert len(payload["candidates"]) == 1


def test_inventory_runtime_budget_caps_size_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import codex_worktree_value_inventory as mod

    root = tmp_path / "root"
    (root / "alpha").mkdir(parents=True)
    captured: dict[str, int] = {}
    now = [0.0]
    monkeypatch.setattr(mod.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(mod, "resolve_repo", lambda _repo: tmp_path)
    monkeypatch.setattr(mod, "resolve_ref", lambda *_args, **_kwargs: "base-sha")
    monkeypatch.setattr(mod, "repo_remote_urls", lambda *_args, **_kwargs: set())
    monkeypatch.setattr(mod, "parse_worktree_list", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(mod, "unresolved_outbox_handoff_branches", lambda *_args, **_kwargs: set())
    monkeypatch.setattr(
        mod,
        "terminal_receipted_handoff_branch_heads",
        lambda *_args, **_kwargs: {},
    )

    def fake_measure_sizes(paths: list[Path], **kwargs: Any) -> tuple[dict[str, int], set[str]]:
        captured["timeout"] = kwargs["timeout"]
        return {str(path): 0 for path in paths}, set()

    monkeypatch.setattr(mod, "measure_sizes", fake_measure_sizes)
    monkeypatch.setattr(
        mod,
        "classify_candidate",
        lambda path, **_kwargs: mod.build_candidate(
            path,
            None,
            0,
            False,
            "no_git_cache_residue",
            False,
            [],
            mod.GitInfo(),
            {"open_prs": [], "outbox_files": [], "receipt_files": []},
            ["fake candidate"],
        ),
    )

    payload = mod.inventory(
        roots=[root],
        repo=tmp_path,
        base="origin/main",
        outbox_dir=tmp_path / "outbox",
        receipt_dir=tmp_path / "receipts",
        limit=None,
        size_mode="du",
        size_timeout=120,
        skip_gh=True,
        git_timeout=30,
        gh_timeout=30,
        patch_timeout=30,
        max_runtime_seconds=3,
    )

    assert captured["timeout"] == 3
    assert payload["max_runtime_seconds"] == 3
    assert payload["summary"]["truncated_by_runtime_budget"] is False


def test_build_parser_root_action_append(tmp_path: Path) -> None:
    import codex_worktree_value_inventory as mod

    parser = mod.build_parser()

    args = parser.parse_args(["--root", "/tmp/a", "--root", "/tmp/b"])

    assert args.root == [Path("/tmp/a"), Path("/tmp/b")]


def test_build_parser_root_omitted_yields_none(tmp_path: Path) -> None:
    import codex_worktree_value_inventory as mod

    parser = mod.build_parser()

    args = parser.parse_args([])

    assert args.root is None


def test_build_parser_accepts_max_runtime_seconds(tmp_path: Path) -> None:
    import codex_worktree_value_inventory as mod

    parser = mod.build_parser()

    args = parser.parse_args(["--max-runtime-seconds", "30.5"])

    assert args.max_runtime_seconds == 30.5

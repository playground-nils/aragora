"""Unit tests for ``scripts/auto_approve_safe_prs.py``.

These tests exercise the pure decision logic, safety features, and mocked
GitHub API integration without ever hitting the network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.auto_approve_safe_prs import (
    DEFAULT_ALLOWED_AUTHORS,
    DEFAULT_OPTIN_LABELS,
    PROTECTED_PATH_PATTERNS,
    ApprovalPolicy,
    CheckRun,
    GitHubClient,
    PRSnapshot,
    PriorReview,
    RateLimitState,
    _load_rate_limit,
    _save_rate_limit,
    any_protected_paths,
    append_audit_record,
    build_approval_body,
    build_snapshot,
    evaluate_pr,
    is_live_mode,
    kill_switch_engaged,
    path_is_protected,
    rate_limit_check_and_reserve,
    run,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _pr(
    number: int = 1,
    *,
    author: str = "an0mium",
    labels: tuple[str, ...] = ("autonomous",),
    changed_files: tuple[str, ...] = ("aragora/server/handlers/new.py",),
    is_draft: bool = False,
    mergeable: str = "MERGEABLE",
    checks: tuple[CheckRun, ...] | None = None,
    prior_reviews: tuple[PriorReview, ...] = (),
    head_sha: str = "abcd" * 10,
    additions: int = 50,
    deletions: int = 10,
) -> PRSnapshot:
    if checks is None:
        checks = (
            CheckRun(name="tests", status="completed", conclusion="success"),
            CheckRun(name="lint", status="completed", conclusion="success"),
        )
    return PRSnapshot(
        number=number,
        title=f"PR #{number}",
        html_url=f"https://github.com/synaptent/aragora/pull/{number}",
        author=author,
        head_sha=head_sha,
        head_ref=f"feature/pr-{number}",
        is_draft=is_draft,
        mergeable=mergeable,
        labels=labels,
        changed_files=changed_files,
        additions=additions,
        deletions=deletions,
        checks=checks,
        prior_reviews=prior_reviews,
    )


def _policy(**overrides: Any) -> ApprovalPolicy:
    defaults: dict[str, Any] = {
        "allowed_authors": DEFAULT_ALLOWED_AUTHORS,
        "optin_labels": DEFAULT_OPTIN_LABELS,
        "protected_paths": PROTECTED_PATH_PATTERNS,
        "max_diff_loc": 5000,
    }
    defaults.update(overrides)
    return ApprovalPolicy(**defaults)


# ---------------------------------------------------------------------------
# Path protection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "CLAUDE.md",
        "aragora/CLAUDE.md",
        "aragora/tests/CLAUDE.md",
        "scripts/CLAUDE.md",
        ".env",
        ".env.production",
        "aragora/.env",
        "scripts/nomic_loop.py",
        "aragora/__init__.py",
        ".github/workflows/ci.yml",
        "scripts/baselines/check_sdk_parity.json",
        "some/dir/github-app.pem",
        "aragora/secrets.py",
        "aragora/config/secrets_manager.py",
        "vendor/aws-private-key.pem",
        "priv/server-private-key.txt",
    ],
)
def test_path_is_protected_positive(path: str) -> None:
    assert path_is_protected(path, PROTECTED_PATH_PATTERNS), path


@pytest.mark.parametrize(
    "path",
    [
        "aragora/server/handlers/new.py",
        "docs/guide.md",
        "tests/test_foo.py",
        "sdk/python/aragora_sdk/namespaces/costs.py",
        "README.md",
        "scripts/auto_approve_safe_prs.py",
    ],
)
def test_path_is_protected_negative(path: str) -> None:
    assert not path_is_protected(path, PROTECTED_PATH_PATTERNS), path


def test_any_protected_paths_returns_subset() -> None:
    paths = ("ok.py", "CLAUDE.md", "other.py", ".env")
    hits = any_protected_paths(paths, PROTECTED_PATH_PATTERNS)
    assert hits == ["CLAUDE.md", ".env"]


# ---------------------------------------------------------------------------
# evaluate_pr gates
# ---------------------------------------------------------------------------


def test_evaluate_pr_approves_when_all_gates_pass() -> None:
    decision = evaluate_pr(_pr(), _policy())
    assert decision.approve is True
    assert decision.reason == "eligible"


def test_evaluate_pr_rejects_self_authored() -> None:
    decision = evaluate_pr(_pr(author="aragora-automation[bot]"), _policy())
    assert decision.approve is False
    assert decision.reason == "self_authored"


def test_evaluate_pr_rejects_draft() -> None:
    decision = evaluate_pr(_pr(is_draft=True), _policy())
    assert decision.approve is False
    assert decision.reason == "draft"


def test_evaluate_pr_rejects_not_mergeable() -> None:
    decision = evaluate_pr(_pr(mergeable="CONFLICTING"), _policy())
    assert decision.approve is False
    assert decision.reason == "not_mergeable"


def test_evaluate_pr_rejects_non_allowlisted_author() -> None:
    decision = evaluate_pr(_pr(author="random-human"), _policy())
    assert decision.approve is False
    assert decision.reason == "author_not_allowlisted"


def test_evaluate_pr_rejects_missing_optin_label() -> None:
    decision = evaluate_pr(_pr(labels=("bug",)), _policy())
    assert decision.approve is False
    assert decision.reason == "missing_optin_label"


def test_evaluate_pr_accepts_any_optin_label() -> None:
    for label in DEFAULT_OPTIN_LABELS:
        decision = evaluate_pr(_pr(labels=(label,)), _policy())
        assert decision.approve is True, f"should accept {label}"


def test_evaluate_pr_rejects_pending_checks() -> None:
    pending = (CheckRun(name="tests", status="in_progress", conclusion=""),)
    decision = evaluate_pr(_pr(checks=pending), _policy())
    assert decision.approve is False
    assert decision.reason.startswith("checks_pending")


def test_evaluate_pr_rejects_failed_checks() -> None:
    failed = (
        CheckRun(name="tests", status="completed", conclusion="success"),
        CheckRun(name="lint", status="completed", conclusion="failure"),
    )
    decision = evaluate_pr(_pr(checks=failed), _policy())
    assert decision.approve is False
    assert decision.reason.startswith("checks_failed")


def test_evaluate_pr_rejects_cancelled_checks() -> None:
    cancelled = (CheckRun(name="smoke", status="completed", conclusion="cancelled"),)
    decision = evaluate_pr(_pr(checks=cancelled), _policy())
    assert decision.approve is False
    assert "cancelled" in decision.reason


def test_evaluate_pr_accepts_neutral_and_skipped_checks() -> None:
    runs = (
        CheckRun(name="tests", status="completed", conclusion="success"),
        CheckRun(name="optional", status="completed", conclusion="neutral"),
        CheckRun(name="docs-only", status="completed", conclusion="skipped"),
    )
    decision = evaluate_pr(_pr(checks=runs), _policy())
    assert decision.approve is True


def test_evaluate_pr_rejects_no_checks_reported() -> None:
    decision = evaluate_pr(_pr(checks=()), _policy())
    assert decision.approve is False
    assert decision.reason == "no_checks_reported"


def test_evaluate_pr_rejects_protected_paths() -> None:
    decision = evaluate_pr(
        _pr(changed_files=("aragora/server/handlers/ok.py", "CLAUDE.md")),
        _policy(),
    )
    assert decision.approve is False
    assert decision.reason == "protected_paths_touched"


def test_evaluate_pr_rejects_large_diff() -> None:
    decision = evaluate_pr(_pr(additions=4000, deletions=2000), _policy(max_diff_loc=5000))
    assert decision.approve is False
    assert decision.reason == "diff_too_large"


def test_evaluate_pr_idempotent_when_already_approved_same_head() -> None:
    sha = "deadbeef" * 5
    prior = (
        PriorReview(
            user_login="aragora-automation[bot]",
            state="APPROVED",
            commit_id=sha,
            submitted_at="2026-04-18T00:00:00Z",
        ),
    )
    decision = evaluate_pr(_pr(head_sha=sha, prior_reviews=prior), _policy())
    assert decision.approve is False
    assert decision.reason == "already_approved"


def test_evaluate_pr_re_approves_when_head_changed() -> None:
    old_sha = "deadbeef" * 5
    new_sha = "cafebabe" * 5
    prior = (
        PriorReview(
            user_login="aragora-automation[bot]",
            state="APPROVED",
            commit_id=old_sha,
            submitted_at="2026-04-18T00:00:00Z",
        ),
    )
    decision = evaluate_pr(_pr(head_sha=new_sha, prior_reviews=prior), _policy())
    assert decision.approve is True
    assert decision.reason == "eligible"


def test_evaluate_pr_ignores_non_app_prior_reviews() -> None:
    sha = "feedbeef" * 5
    prior = (
        PriorReview(
            user_login="some-human",
            state="APPROVED",
            commit_id=sha,
            submitted_at="2026-04-18T00:00:00Z",
        ),
    )
    decision = evaluate_pr(_pr(head_sha=sha, prior_reviews=prior), _policy())
    assert decision.approve is True


# ---------------------------------------------------------------------------
# Rate limit + kill switch + live flag
# ---------------------------------------------------------------------------


def test_kill_switch_detects_file(tmp_path: Path) -> None:
    flag = tmp_path / "auto_approver.disabled"
    assert not kill_switch_engaged(flag)
    flag.touch()
    assert kill_switch_engaged(flag)


def test_is_live_mode_requires_flag(tmp_path: Path) -> None:
    flag = tmp_path / "auto_approver.live"
    assert not is_live_mode(flag)
    flag.touch()
    assert is_live_mode(flag)


def test_rate_limit_allows_up_to_quota(tmp_path: Path) -> None:
    path = tmp_path / "rate.json"
    now = 1_000_000.0
    for i in range(3):
        allowed, state = rate_limit_check_and_reserve(path, limit_per_hour=3, now_epoch=now + i)
        assert allowed is True, f"iteration {i}"
        _save_rate_limit(path, state)
    # 4th in same window — denied.
    allowed, _ = rate_limit_check_and_reserve(path, limit_per_hour=3, now_epoch=now + 10)
    assert allowed is False


def test_rate_limit_rolls_over_after_hour(tmp_path: Path) -> None:
    path = tmp_path / "rate.json"
    now = 1_000_000.0
    for i in range(3):
        allowed, state = rate_limit_check_and_reserve(path, limit_per_hour=3, now_epoch=now + i)
        assert allowed is True
        _save_rate_limit(path, state)
    # After the window rolls over, quota resets.
    allowed, state = rate_limit_check_and_reserve(path, limit_per_hour=3, now_epoch=now + 3600 + 5)
    assert allowed is True
    _save_rate_limit(path, state)
    assert state.approvals_in_window == 1


def test_rate_limit_round_trips_through_disk(tmp_path: Path) -> None:
    path = tmp_path / "rate.json"
    assert _load_rate_limit(path) is None
    state = RateLimitState(window_start_epoch=123.0, approvals_in_window=4)
    _save_rate_limit(path, state)
    loaded = _load_rate_limit(path)
    assert loaded is not None
    assert loaded.window_start_epoch == 123.0
    assert loaded.approvals_in_window == 4


def test_append_audit_record_writes_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    append_audit_record(path, {"n": 1, "reason": "eligible"})
    append_audit_record(path, {"n": 2, "reason": "draft"})
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["n"] == 1
    assert json.loads(lines[1])["reason"] == "draft"


# ---------------------------------------------------------------------------
# build_approval_body
# ---------------------------------------------------------------------------


def test_build_approval_body_includes_audit_trail() -> None:
    body = build_approval_body(_pr(number=42))
    assert "Auto-approved" in body
    assert "an0mium" in body
    assert "autonomous" in body
    assert "kill switch" in body.lower() or "auto_approver.disabled" in body


# ---------------------------------------------------------------------------
# Mocked GitHubClient / run() integration
# ---------------------------------------------------------------------------


class FakeGitHub:
    """In-memory stand-in for GitHubClient, mimicking just the shape we need."""

    def __init__(self, prs: list[dict[str, Any]]) -> None:
        self.prs = prs
        self.submitted_reviews: list[dict[str, Any]] = []

    # Emulate the client's public surface used by ``run``/``build_snapshot``.
    def list_open_prs(self, per_page: int = 30) -> list[dict[str, Any]]:
        return [{"number": pr["number"]} for pr in self.prs]

    def _find(self, number: int) -> dict[str, Any]:
        for pr in self.prs:
            if pr["number"] == number:
                return pr
        raise KeyError(number)

    def get_pr(self, number: int) -> dict[str, Any]:
        pr = self._find(number)
        return {
            "number": pr["number"],
            "title": pr.get("title", f"PR {number}"),
            "html_url": f"https://github.com/synaptent/aragora/pull/{number}",
            "draft": pr.get("draft", False),
            "mergeable_state": pr.get("mergeable_state", "clean"),
            "mergeable": pr.get("mergeable", True),
            "additions": pr.get("additions", 10),
            "deletions": pr.get("deletions", 5),
            "head": {"sha": pr.get("sha", "a" * 40), "ref": pr.get("ref", "feature/x")},
            "user": {"login": pr.get("author", "an0mium")},
            "labels": [{"name": n} for n in pr.get("labels", ["autonomous"])],
        }

    def get_pr_files(self, number: int) -> list[dict[str, Any]]:
        pr = self._find(number)
        return [{"filename": f} for f in pr.get("files", ["aragora/ok.py"])]

    def get_commit_checks(self, sha: str) -> list[dict[str, Any]]:
        # Single "tests" success by default; per-PR override via ``checks``.
        for pr in self.prs:
            if pr.get("sha") == sha:
                return pr.get(
                    "checks",
                    [{"name": "tests", "status": "completed", "conclusion": "success"}],
                )
        return [{"name": "tests", "status": "completed", "conclusion": "success"}]

    def list_reviews(self, number: int) -> list[dict[str, Any]]:
        return self._find(number).get("reviews", [])

    def submit_review(self, number: int, *, body: str, event: str = "APPROVE") -> dict[str, Any]:
        self.submitted_reviews.append({"number": number, "body": body, "event": event})
        return {"id": 9000 + number, "state": event}


@pytest.fixture
def _state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # Point the script's default state paths into a tmp dir.
    import scripts.auto_approve_safe_prs as module

    monkeypatch.setattr(module, "KILL_SWITCH_PATH", tmp_path / "auto_approver.disabled")
    monkeypatch.setattr(module, "LIVE_FLAG_PATH", tmp_path / "auto_approver.live")
    monkeypatch.setattr(module, "RATE_LIMIT_PATH", tmp_path / "rate.json")
    monkeypatch.setattr(module, "AUDIT_LOG_PATH", tmp_path / "audit.jsonl")
    monkeypatch.setattr(module, "SCRIPT_LOG_PATH", tmp_path / "script.log")
    return tmp_path


def _install_fake_token(monkeypatch: pytest.MonkeyPatch, token: str = "fake-token") -> None:
    import scripts.auto_approve_safe_prs as module

    monkeypatch.setattr(module, "get_github_app_installation_token", lambda: token)


def test_run_dry_run_does_not_submit(_state_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_token(monkeypatch)
    fake = FakeGitHub([{"number": 1, "sha": "a" * 40}])
    summary = run(
        "synaptent/aragora",
        policy=_policy(),
        dry_run=True,
        rate_limit_per_hour=10,
        rate_limit_path=_state_dir / "rate.json",
        audit_log_path=_state_dir / "audit.jsonl",
        kill_switch_path=_state_dir / "auto_approver.disabled",
        live_flag_path=_state_dir / "auto_approver.live",
        client_factory=lambda repo, token: fake,  # type: ignore[arg-type,return-value]
    )
    assert summary["mode"] == "dry-run"
    assert len(summary["approvals"]) == 1
    assert summary["approvals"][0]["mode"] == "dry-run"
    assert fake.submitted_reviews == []


def test_run_live_mode_requires_flag_file(
    _state_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_token(monkeypatch)
    fake = FakeGitHub([{"number": 1, "sha": "a" * 40}])
    # dry_run=False but no live flag → still dry-run.
    summary = run(
        "synaptent/aragora",
        policy=_policy(),
        dry_run=False,
        rate_limit_per_hour=10,
        rate_limit_path=_state_dir / "rate.json",
        audit_log_path=_state_dir / "audit.jsonl",
        kill_switch_path=_state_dir / "auto_approver.disabled",
        live_flag_path=_state_dir / "auto_approver.live",
        client_factory=lambda repo, token: fake,  # type: ignore[arg-type,return-value]
    )
    assert summary["mode"] == "dry-run"
    assert fake.submitted_reviews == []


def test_run_live_mode_submits_when_flag_exists(
    _state_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_token(monkeypatch)
    (_state_dir / "auto_approver.live").touch()
    fake = FakeGitHub([{"number": 42, "sha": "b" * 40}])
    summary = run(
        "synaptent/aragora",
        policy=_policy(),
        dry_run=False,
        rate_limit_per_hour=10,
        rate_limit_path=_state_dir / "rate.json",
        audit_log_path=_state_dir / "audit.jsonl",
        kill_switch_path=_state_dir / "auto_approver.disabled",
        live_flag_path=_state_dir / "auto_approver.live",
        client_factory=lambda repo, token: fake,  # type: ignore[arg-type,return-value]
    )
    assert summary["mode"] == "live"
    assert len(fake.submitted_reviews) == 1
    assert fake.submitted_reviews[0]["number"] == 42
    assert fake.submitted_reviews[0]["event"] == "APPROVE"


def test_run_kill_switch_short_circuits(_state_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_token(monkeypatch)
    (_state_dir / "auto_approver.disabled").touch()
    fake = FakeGitHub([{"number": 1, "sha": "a" * 40}])
    summary = run(
        "synaptent/aragora",
        policy=_policy(),
        dry_run=False,
        rate_limit_per_hour=10,
        rate_limit_path=_state_dir / "rate.json",
        audit_log_path=_state_dir / "audit.jsonl",
        kill_switch_path=_state_dir / "auto_approver.disabled",
        live_flag_path=_state_dir / "auto_approver.live",
        client_factory=lambda repo, token: fake,  # type: ignore[arg-type,return-value]
    )
    assert summary["kill_switch"] is True
    assert summary["approvals"] == []
    assert fake.submitted_reviews == []


def test_run_rate_limit_blocks_second_approval(
    _state_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_token(monkeypatch)
    (_state_dir / "auto_approver.live").touch()
    fake = FakeGitHub(
        [
            {"number": 1, "sha": "a" * 40},
            {"number": 2, "sha": "b" * 40},
        ]
    )
    summary = run(
        "synaptent/aragora",
        policy=_policy(),
        dry_run=False,
        rate_limit_per_hour=1,
        rate_limit_path=_state_dir / "rate.json",
        audit_log_path=_state_dir / "audit.jsonl",
        kill_switch_path=_state_dir / "auto_approver.disabled",
        live_flag_path=_state_dir / "auto_approver.live",
        client_factory=lambda repo, token: fake,  # type: ignore[arg-type,return-value]
    )
    assert summary["rate_limited"] is True
    assert len(fake.submitted_reviews) == 1  # only the first
    reasons = [s["reason"] for s in summary["skips"]]
    assert "rate_limited" in reasons


def test_run_skips_protected_path_in_live_mode(
    _state_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_token(monkeypatch)
    (_state_dir / "auto_approver.live").touch()
    fake = FakeGitHub([{"number": 1, "sha": "a" * 40, "files": ["CLAUDE.md"]}])
    summary = run(
        "synaptent/aragora",
        policy=_policy(),
        dry_run=False,
        rate_limit_per_hour=10,
        rate_limit_path=_state_dir / "rate.json",
        audit_log_path=_state_dir / "audit.jsonl",
        kill_switch_path=_state_dir / "auto_approver.disabled",
        live_flag_path=_state_dir / "auto_approver.live",
        client_factory=lambda repo, token: fake,  # type: ignore[arg-type,return-value]
    )
    assert fake.submitted_reviews == []
    assert summary["skips"][0]["reason"] == "protected_paths_touched"


def test_build_snapshot_maps_github_payload() -> None:
    fake = FakeGitHub(
        [
            {
                "number": 7,
                "sha": "c" * 40,
                "files": ["aragora/foo.py"],
                "labels": ["autonomous", "docs"],
                "reviews": [
                    {
                        "user": {"login": "some-human"},
                        "state": "COMMENTED",
                        "commit_id": "c" * 40,
                        "submitted_at": "2026-04-17T12:00:00Z",
                    }
                ],
            }
        ]
    )
    snapshot = build_snapshot(fake, 7)  # type: ignore[arg-type]
    assert snapshot.number == 7
    assert snapshot.head_sha == "c" * 40
    assert "autonomous" in snapshot.labels
    assert snapshot.changed_files == ("aragora/foo.py",)
    assert snapshot.prior_reviews[0].state == "COMMENTED"
    assert snapshot.checks[0].conclusion == "success"


def test_githubclient_urlopen_rejects_non_github_host() -> None:
    client = GitHubClient("synaptent/aragora", token="fake")
    with pytest.raises(RuntimeError, match="non-GitHub URL"):
        GitHubClient._urlopen(
            "https://evil.example.com/api",
            method="GET",
            headers={},
        )

#!/usr/bin/env python3
"""Auto-approve safe automation PRs via the ``aragora-automation`` GitHub App.

This script is the receipt-gated approver that removes the single biggest human
gate on the autonomous merge pipeline. It scans open pull requests in the
configured repository and submits ``APPROVE`` reviews using the App installation
token **only when every conservative guardrail passes**.

Guardrails (ALL must hold):

1. PR is OPEN and ``mergeable`` (not ``CONFLICTING``/``UNKNOWN``).
2. PR is not a draft.
3. PR author is on the automation allowlist (``an0mium``, ``factory-droid[bot]``, ...).
4. PR carries at least one opt-in label (``autonomous``, ``codex-automation``, ...).
5. All required CI checks have ``conclusion: SUCCESS`` (no pending, failed, cancelled).
6. PR does not touch any protected path (CLAUDE.md, secrets, CI configs, baselines, ...).
7. PR diff is under the configurable LOC threshold.
8. The App has not already approved the PR's current head SHA (idempotency).

Additional safety features:

- ``--dry-run`` logs what WOULD be approved; default to live only when the
  ``~/.aragora/auto_approver.live`` flag exists.
- Kill switch: presence of ``~/.aragora/auto_approver.disabled`` exits with 0.
- Rate limit: at most ``N`` approvals per hour (default 10); persistent counter.
- Audit log: every invocation appends a JSON line to
  ``~/.aragora/auto_approver_audit.jsonl`` with full decision trace.
- Self-approval protection: refuses to approve PRs authored by the App bot itself.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping

# Allow importing the ``aragora`` package when running from the repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aragora.swarm.github_app_auth import get_github_app_installation_token  # noqa: E402

logger = logging.getLogger("auto_approve_safe_prs")

# ---------------------------------------------------------------------------
# Defaults — kept conservative on purpose. Operators can widen via CLI flags
# once behavior is verified in dry-run mode.
# ---------------------------------------------------------------------------

DEFAULT_REPO = "synaptent/aragora"
DEFAULT_MAX_DIFF_LOC = 5000
DEFAULT_RATE_LIMIT_PER_HOUR = 10
DEFAULT_PER_PAGE = 30

DEFAULT_ALLOWED_AUTHORS: tuple[str, ...] = (
    "an0mium",
    "factory-droid[bot]",
    "codex-bot",
    "aragora-automation[bot]",
    "app/aragora-automation",
)

DEFAULT_OPTIN_LABELS: tuple[str, ...] = (
    "autonomous",
    "codex-automation",
    "droid-generated",
    "auto-approve",
)

# Protected paths. Patterns accepted by :func:`fnmatch.fnmatchcase`.
# Normalize to forward slashes at compare time.
PROTECTED_PATH_PATTERNS: tuple[str, ...] = (
    "CLAUDE.md",
    "**/CLAUDE.md",
    "aragora/__init__.py",
    ".env",
    ".env.*",
    "**/.env",
    "**/.env.*",
    "scripts/nomic_loop.py",
    ".github/workflows/*",
    ".github/workflows/**",
    "scripts/baselines/*",
    "scripts/baselines/**",
    "**/secrets*",
    "**/*secrets*",
    "**/*private-key*",
    "**/*private_key*",
    "**/github-app.pem",
    "*.pem",
    "**/*.pem",
)

# Paths under ~/.aragora used for persistent state and kill switch.
STATE_DIR = Path.home() / ".aragora"
KILL_SWITCH_PATH = STATE_DIR / "auto_approver.disabled"
LIVE_FLAG_PATH = STATE_DIR / "auto_approver.live"
RATE_LIMIT_PATH = STATE_DIR / "auto_approver_rate.json"
AUDIT_LOG_PATH = STATE_DIR / "auto_approver_audit.jsonl"
SCRIPT_LOG_PATH = STATE_DIR / "auto_approver.log"

# Identity of the App bot, used to detect our own prior reviews / PRs.
# ``aragora-automation`` is the slug of App ID 3328101. GitHub reports this
# author as ``aragora-automation[bot]`` on REST responses.
APP_BOT_LOGIN = "aragora-automation[bot]"

GITHUB_API = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckRun:
    name: str
    status: str  # e.g. "completed", "in_progress", "queued"
    conclusion: str  # e.g. "success", "failure", "cancelled", ""


@dataclass(frozen=True)
class PriorReview:
    user_login: str
    state: str  # "APPROVED", "CHANGES_REQUESTED", "COMMENTED", "DISMISSED"
    commit_id: str
    submitted_at: str


@dataclass(frozen=True)
class PRSnapshot:
    number: int
    title: str
    html_url: str
    author: str
    head_sha: str
    head_ref: str
    is_draft: bool
    mergeable: str  # GitHub REST: "MERGEABLE", "CONFLICTING", "UNKNOWN"
    labels: tuple[str, ...]
    changed_files: tuple[str, ...]
    additions: int
    deletions: int
    checks: tuple[CheckRun, ...]
    prior_reviews: tuple[PriorReview, ...]


@dataclass(frozen=True)
class ApprovalPolicy:
    allowed_authors: tuple[str, ...] = DEFAULT_ALLOWED_AUTHORS
    optin_labels: tuple[str, ...] = DEFAULT_OPTIN_LABELS
    protected_paths: tuple[str, ...] = PROTECTED_PATH_PATTERNS
    max_diff_loc: int = DEFAULT_MAX_DIFF_LOC
    app_bot_login: str = APP_BOT_LOGIN


@dataclass
class ApprovalDecision:
    number: int
    approve: bool
    reason: str  # single-word/phrase machine-readable reason
    details: list[str] = field(default_factory=list)  # human-readable explanation lines
    head_sha: str = ""
    url: str = ""


@dataclass
class RateLimitState:
    window_start_epoch: float
    approvals_in_window: int


# ---------------------------------------------------------------------------
# Pure decision logic — fully testable with mocked snapshots.
# ---------------------------------------------------------------------------


def _normalize_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    # Strip a leading "./" if present, but never a bare "." which would eat
    # dotfiles like ".env".
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def path_is_protected(path: str, patterns: tuple[str, ...]) -> bool:
    """Return True when ``path`` matches any protected pattern."""
    normalized = _normalize_path(path)
    lowered = normalized.lower()
    for pattern in patterns:
        # ``fnmatch`` handles ``*`` and ``?`` but treats ``**`` as ``*``. We
        # additionally try a direct substring-style contains check for patterns
        # that use ``**`` at segment boundaries.
        if fnmatch.fnmatchcase(normalized, pattern) or fnmatch.fnmatchcase(
            lowered, pattern.lower()
        ):
            return True
        # Expand ``**/X`` to any suffix match.
        if pattern.startswith("**/"):
            tail = pattern[3:]
            if fnmatch.fnmatchcase(normalized, tail):
                return True
            if normalized.endswith("/" + tail):
                return True
        # Expand ``X/**`` prefix match.
        if pattern.endswith("/**"):
            head = pattern[:-3]
            if normalized == head or normalized.startswith(head + "/"):
                return True
    return False


def any_protected_paths(paths: tuple[str, ...], patterns: tuple[str, ...]) -> list[str]:
    return [p for p in paths if path_is_protected(p, patterns)]


def _author_allowed(author: str, allowed: tuple[str, ...]) -> bool:
    return author.lower() in {name.lower() for name in allowed}


def _has_optin_label(labels: tuple[str, ...], optin: tuple[str, ...]) -> bool:
    label_set = {label.lower() for label in labels}
    return any(opt.lower() in label_set for opt in optin)


# Check-run conclusions that are non-blocking for auto-approval.
# Consistent with scripts/merge_codex_automation_prs.py SAFE_CHECK_CONCLUSIONS.
_SAFE_CHECK_CONCLUSIONS = frozenset({"success", "neutral", "skipped"})


def _checks_all_successful(checks: tuple[CheckRun, ...]) -> tuple[bool, str]:
    if not checks:
        return False, "no_checks_reported"
    for run in checks:
        status = (run.status or "").lower()
        conclusion = (run.conclusion or "").lower()
        if status != "completed":
            return False, f"checks_pending:{run.name}"
        if conclusion not in _SAFE_CHECK_CONCLUSIONS:
            return False, f"checks_failed:{run.name}:{conclusion or 'unknown'}"
    return True, "checks_success"


def _already_approved_current_head(
    prior_reviews: tuple[PriorReview, ...],
    *,
    app_login: str,
    head_sha: str,
) -> bool:
    app_lower = app_login.lower()
    for review in prior_reviews:
        if review.user_login.lower() != app_lower:
            continue
        if review.state.upper() != "APPROVED":
            continue
        if review.commit_id == head_sha:
            return True
    return False


def evaluate_pr(pr: PRSnapshot, policy: ApprovalPolicy) -> ApprovalDecision:
    """Apply the 8 approval gates to ``pr`` and return a decision.

    Pure function — no side effects. Suitable for unit testing.
    """
    decision = ApprovalDecision(
        number=pr.number,
        approve=False,
        reason="",
        head_sha=pr.head_sha,
        url=pr.html_url,
    )

    # Gate 0: never approve our own PRs (self-approval loop guard).
    if pr.author.lower() == policy.app_bot_login.lower():
        decision.reason = "self_authored"
        decision.details.append(f"author={pr.author} is the App bot itself")
        return decision

    # Gate 1: mergeability (state is known to be OPEN since we only fetch open PRs).
    if pr.mergeable.upper() != "MERGEABLE":
        decision.reason = "not_mergeable"
        decision.details.append(f"mergeable={pr.mergeable}")
        return decision

    # Gate 2: not a draft.
    if pr.is_draft:
        decision.reason = "draft"
        decision.details.append("PR is marked as draft")
        return decision

    # Gate 3: author allowlist.
    if not _author_allowed(pr.author, policy.allowed_authors):
        decision.reason = "author_not_allowlisted"
        decision.details.append(f"author={pr.author} not in {list(policy.allowed_authors)}")
        return decision

    # Gate 4: opt-in label.
    if not _has_optin_label(pr.labels, policy.optin_labels):
        decision.reason = "missing_optin_label"
        decision.details.append(
            f"labels={list(pr.labels)} does not intersect {list(policy.optin_labels)}"
        )
        return decision

    # Gate 5: CI checks.
    checks_ok, check_reason = _checks_all_successful(pr.checks)
    if not checks_ok:
        decision.reason = check_reason
        decision.details.append(check_reason)
        return decision

    # Gate 6: protected paths.
    protected_hits = any_protected_paths(pr.changed_files, policy.protected_paths)
    if protected_hits:
        decision.reason = "protected_paths_touched"
        decision.details.append(f"protected={protected_hits[:5]}")
        return decision

    # Gate 7: diff size.
    net_loc = pr.additions + pr.deletions
    if net_loc > policy.max_diff_loc:
        decision.reason = "diff_too_large"
        decision.details.append(f"net_loc={net_loc} > {policy.max_diff_loc}")
        return decision

    # Gate 8: idempotency — do not re-approve same head SHA.
    if _already_approved_current_head(
        pr.prior_reviews,
        app_login=policy.app_bot_login,
        head_sha=pr.head_sha,
    ):
        decision.reason = "already_approved"
        decision.details.append(f"App already approved head_sha={pr.head_sha}")
        return decision

    # All gates passed.
    decision.approve = True
    decision.reason = "eligible"
    decision.details.append(
        f"author={pr.author} labels={list(pr.labels)} net_loc={net_loc} head_sha={pr.head_sha[:8]}"
    )
    decision.details.append("all_checks_success=" + ",".join(sorted({c.name for c in pr.checks})))
    return decision


# ---------------------------------------------------------------------------
# Rate limit + kill switch + audit log
# ---------------------------------------------------------------------------


def kill_switch_engaged(path: Path = KILL_SWITCH_PATH) -> bool:
    return path.exists()


def is_live_mode(path: Path = LIVE_FLAG_PATH) -> bool:
    return path.exists()


def _load_rate_limit(path: Path) -> RateLimitState | None:
    """Load persisted state, or return None when absent/corrupt."""
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8") or "{}")
    except (OSError, json.JSONDecodeError):
        return None
    try:
        return RateLimitState(
            window_start_epoch=float(payload.get("window_start_epoch")),
            approvals_in_window=int(payload.get("approvals_in_window") or 0),
        )
    except (TypeError, ValueError):
        return None


def _save_rate_limit(path: Path, state: RateLimitState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "window_start_epoch": state.window_start_epoch,
                "approvals_in_window": state.approvals_in_window,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def rate_limit_check_and_reserve(
    path: Path,
    *,
    limit_per_hour: int,
    now_epoch: float | None = None,
) -> tuple[bool, RateLimitState]:
    """Return ``(allowed, updated_state)``.

    Reserves one slot on success. When ``allowed`` is False the caller must not
    approve. The updated state is always persisted by the caller via
    :func:`_save_rate_limit` to keep this function testable without disk I/O
    beyond the initial load. ``now_epoch`` is injectable for testing.
    """
    now = time.time() if now_epoch is None else now_epoch
    loaded = _load_rate_limit(path)
    if loaded is None:
        state = RateLimitState(window_start_epoch=now, approvals_in_window=0)
    elif now - loaded.window_start_epoch >= 3600:
        # Window rolled over.
        state = RateLimitState(window_start_epoch=now, approvals_in_window=0)
    else:
        state = loaded
    if state.approvals_in_window >= limit_per_hour:
        return False, state
    state = RateLimitState(
        window_start_epoch=state.window_start_epoch,
        approvals_in_window=state.approvals_in_window + 1,
    )
    return True, state


def append_audit_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True, default=str)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


# ---------------------------------------------------------------------------
# GitHub REST helpers
# ---------------------------------------------------------------------------


class GitHubClient:
    """Thin urllib-based wrapper around the GitHub REST API.

    Uses the App installation token from :mod:`aragora.swarm.github_app_auth`.
    Dependency-injectable for testing via the ``request`` callable.
    """

    def __init__(
        self,
        repo: str,
        *,
        token: str,
        request: Callable[..., Any] | None = None,
    ) -> None:
        self.repo = repo
        self._token = token
        default_request: Callable[..., Any] = self._urlopen
        self._request: Callable[..., Any] = request if request is not None else default_request

    def _headers(self, *, accept: str = "application/vnd.github+json") -> dict[str, str]:
        return {
            "Authorization": f"token {self._token}",
            "Accept": accept,
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": "aragora-auto-approver/1.0",
        }

    @staticmethod
    def _urlopen(
        url: str,
        *,
        method: str = "GET",
        headers: Mapping[str, str],
        data: bytes | None = None,
        timeout: float = 20.0,
    ) -> Any:
        req = urllib.request.Request(url, method=method, headers=dict(headers), data=data)
        if urllib.parse.urlparse(url).netloc != "api.github.com":
            raise RuntimeError(f"refusing non-GitHub URL: {url}")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            return json.loads(resp.read().decode("utf-8") or "null")

    def get(self, endpoint: str, *, accept: str = "application/vnd.github+json") -> Any:
        url = f"{GITHUB_API}{endpoint}"
        return self._request(url, method="GET", headers=self._headers(accept=accept))

    def post(self, endpoint: str, payload: dict[str, Any]) -> Any:
        url = f"{GITHUB_API}{endpoint}"
        return self._request(
            url,
            method="POST",
            headers=self._headers(),
            data=json.dumps(payload).encode("utf-8"),
        )

    # ---- High level: build a PRSnapshot ------------------------------------

    def list_open_prs(self, per_page: int = DEFAULT_PER_PAGE) -> list[dict[str, Any]]:
        return list(self.get(f"/repos/{self.repo}/pulls?state=open&per_page={per_page}") or [])

    def get_pr(self, number: int) -> dict[str, Any]:
        return dict(self.get(f"/repos/{self.repo}/pulls/{number}") or {})

    def get_pr_files(self, number: int) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = self.get(f"/repos/{self.repo}/pulls/{number}/files?per_page=100&page={page}")
            items = list(batch or [])
            pages.extend(items)
            if len(items) < 100:
                break
            page += 1
            if page > 10:  # safety: PRs with >1000 files are clearly not auto-approvable
                break
        return pages

    def get_commit_checks(self, sha: str) -> list[dict[str, Any]]:
        # Combine check-runs (GitHub Checks API) + commit statuses.
        runs: list[dict[str, Any]] = []
        batch = self.get(f"/repos/{self.repo}/commits/{sha}/check-runs?per_page=100")
        for entry in (batch or {}).get("check_runs", []) or []:
            runs.append(
                {
                    "name": str(entry.get("name") or ""),
                    "status": str(entry.get("status") or ""),
                    "conclusion": str(entry.get("conclusion") or ""),
                }
            )
        status_payload = self.get(f"/repos/{self.repo}/commits/{sha}/status")
        for entry in (status_payload or {}).get("statuses", []) or []:
            state = str(entry.get("state") or "").lower()
            runs.append(
                {
                    "name": str(entry.get("context") or "status"),
                    "status": "completed"
                    if state in {"success", "failure", "error"}
                    else "pending",
                    "conclusion": "success" if state == "success" else state,
                }
            )
        return runs

    def list_reviews(self, number: int) -> list[dict[str, Any]]:
        return list(self.get(f"/repos/{self.repo}/pulls/{number}/reviews?per_page=100") or [])

    def submit_review(self, number: int, *, body: str, event: str = "APPROVE") -> dict[str, Any]:
        return dict(
            self.post(
                f"/repos/{self.repo}/pulls/{number}/reviews",
                {"body": body, "event": event},
            )
            or {}
        )


def build_snapshot(client: GitHubClient, number: int) -> PRSnapshot:
    pr = client.get_pr(number)
    head = pr.get("head") or {}
    user = pr.get("user") or {}
    labels_raw = pr.get("labels") or []
    labels = tuple(sorted({str(item.get("name") or "") for item in labels_raw if item.get("name")}))
    files = client.get_pr_files(number)
    changed = tuple(str(entry.get("filename") or "") for entry in files if entry.get("filename"))
    sha = str(head.get("sha") or "")
    raw_mergeable_state = str(pr.get("mergeable_state") or "")
    raw_mergeable_flag = pr.get("mergeable")
    checks_raw = client.get_commit_checks(sha) if sha else []
    checks = tuple(
        CheckRun(
            name=str(c.get("name") or ""),
            status=str(c.get("status") or ""),
            conclusion=str(c.get("conclusion") or ""),
        )
        for c in checks_raw
    )
    reviews_raw = client.list_reviews(number)
    prior_reviews = tuple(
        PriorReview(
            user_login=str((r.get("user") or {}).get("login") or ""),
            state=str(r.get("state") or ""),
            commit_id=str(r.get("commit_id") or ""),
            submitted_at=str(r.get("submitted_at") or ""),
        )
        for r in reviews_raw
    )
    return PRSnapshot(
        number=int(pr.get("number") or number),
        title=str(pr.get("title") or ""),
        html_url=str(pr.get("html_url") or ""),
        author=str(user.get("login") or ""),
        head_sha=sha,
        head_ref=str(head.get("ref") or ""),
        is_draft=bool(pr.get("draft") or False),
        mergeable=_mergeability_from_state(raw_mergeable_state, raw_mergeable_flag),
        labels=labels,
        changed_files=changed,
        additions=int(pr.get("additions") or 0),
        deletions=int(pr.get("deletions") or 0),
        checks=checks,
        prior_reviews=prior_reviews,
    )


def _mergeability_from_state(mergeable_state: str, mergeable: bool | None) -> str:
    """Map GitHub's detailed ``mergeable_state`` to our 3-value enum.

    GitHub returns detailed states: ``clean``, ``unstable``, ``has_hooks``,
    ``blocked``, ``dirty``, ``behind``, ``unknown``. We map these to
    MERGEABLE / CONFLICTING / UNKNOWN with the following rationale:

    - ``clean``/``unstable``/``has_hooks`` → MERGEABLE. The CI-check gate
      independently verifies all checks are SUCCESS.
    - ``blocked`` → MERGEABLE. "blocked" typically means "missing required
      approval" (the exact state we want to approve). If it's blocked on a
      failing required check, the independent check gate will still reject.
    - ``dirty`` (conflicts) / ``behind`` (needs rebase) → CONFLICTING.
    - ``unknown`` (still computing) → UNKNOWN. Caller falls through to the
      ``mergeable`` boolean when available.
    """
    state = (mergeable_state or "").lower()
    if state in {"clean", "has_hooks", "unstable", "blocked"}:
        return "MERGEABLE"
    if state in {"dirty", "behind"}:
        return "CONFLICTING"
    if mergeable is True:
        return "MERGEABLE"
    if mergeable is False:
        return "CONFLICTING"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


APPROVAL_BODY_TEMPLATE = """\
✅ **Auto-approved by aragora-automation[bot]**

This PR satisfied every conservative auto-approval gate:

- Author on allowlist: `{author}`
- Opt-in label(s) present: `{labels}`
- All CI checks `SUCCESS` ({check_count} runs)
- No protected paths touched ({file_count} files, {loc} LOC net)
- Head SHA: `{sha}`

Audit trail: see `~/.aragora/auto_approver_audit.jsonl`.
Kill switch: `touch ~/.aragora/auto_approver.disabled`.

This is an automated review — any human reviewer may override or dismiss it.
"""


def build_approval_body(pr: PRSnapshot) -> str:
    return APPROVAL_BODY_TEMPLATE.format(
        author=pr.author,
        labels=", ".join(pr.labels),
        check_count=len(pr.checks),
        file_count=len(pr.changed_files),
        loc=pr.additions + pr.deletions,
        sha=pr.head_sha[:12],
    )


def configure_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    # Also echo to stderr for launchd / interactive runs.
    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(stream)


def run(
    repo: str,
    *,
    policy: ApprovalPolicy,
    dry_run: bool,
    rate_limit_per_hour: int,
    rate_limit_path: Path = RATE_LIMIT_PATH,
    audit_log_path: Path = AUDIT_LOG_PATH,
    kill_switch_path: Path = KILL_SWITCH_PATH,
    live_flag_path: Path = LIVE_FLAG_PATH,
    client_factory: Callable[[str, str], GitHubClient] | None = None,
    per_page: int = DEFAULT_PER_PAGE,
    now_epoch: float | None = None,
) -> dict[str, Any]:
    """Run a single pass. Returns a summary dict suitable for JSON output."""
    now_iso = datetime.now(tz=UTC).isoformat()
    summary: dict[str, Any] = {
        "repo": repo,
        "timestamp": now_iso,
        "mode": "dry-run" if dry_run else "live",
        "decisions": [],
        "approvals": [],
        "skips": [],
        "kill_switch": False,
        "rate_limited": False,
    }

    if kill_switch_engaged(kill_switch_path):
        summary["kill_switch"] = True
        logger.warning("Kill switch engaged at %s; exiting without work.", kill_switch_path)
        append_audit_record(
            audit_log_path,
            {
                "timestamp": now_iso,
                "repo": repo,
                "event": "kill_switch_engaged",
                "path": str(kill_switch_path),
            },
        )
        return summary

    # Effective mode: caller can force dry_run=True, but live requires the flag.
    effective_dry_run = dry_run or not is_live_mode(live_flag_path)
    summary["mode"] = "dry-run" if effective_dry_run else "live"

    token = get_github_app_installation_token()
    if not token:
        summary["error"] = "no_installation_token"
        logger.error("Could not mint GitHub App installation token; aborting.")
        append_audit_record(
            audit_log_path,
            {"timestamp": now_iso, "repo": repo, "event": "token_mint_failed"},
        )
        return summary

    factory = client_factory or (lambda r, t: GitHubClient(r, token=t))
    client = factory(repo, token)

    try:
        open_prs = client.list_open_prs(per_page=per_page)
    except urllib.error.HTTPError as exc:
        summary["error"] = f"list_prs_failed:{exc.code}"
        logger.error("Failed to list open PRs: %s", exc)
        return summary

    logger.info("Inspecting %d open PR(s) in %s (mode=%s).", len(open_prs), repo, summary["mode"])

    for pr_summary in open_prs:
        number = int(pr_summary.get("number") or 0)
        if not number:
            continue
        try:
            snapshot = build_snapshot(client, number)
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("Failed to build snapshot for #%d: %s", number, exc)
            summary["skips"].append(
                {"number": number, "reason": "snapshot_failed", "error": str(exc)}
            )
            continue

        decision = evaluate_pr(snapshot, policy)
        summary["decisions"].append(asdict(decision))

        logger.info(
            "PR #%d: approve=%s reason=%s head_sha=%s",
            decision.number,
            decision.approve,
            decision.reason,
            decision.head_sha[:8] if decision.head_sha else "?",
        )

        audit_record = {
            "timestamp": now_iso,
            "repo": repo,
            "number": decision.number,
            "head_sha": decision.head_sha,
            "author": snapshot.author,
            "labels": list(snapshot.labels),
            "approve": decision.approve,
            "reason": decision.reason,
            "details": decision.details,
            "mode": summary["mode"],
            "url": decision.url,
        }

        if not decision.approve:
            summary["skips"].append(
                {"number": decision.number, "reason": decision.reason, "url": decision.url}
            )
            audit_record["event"] = "skip"
            append_audit_record(audit_log_path, audit_record)
            continue

        # Rate limit — reserve a slot before network call.
        allowed, new_state = rate_limit_check_and_reserve(
            rate_limit_path,
            limit_per_hour=rate_limit_per_hour,
            now_epoch=now_epoch,
        )
        if not allowed:
            summary["rate_limited"] = True
            summary["skips"].append(
                {
                    "number": decision.number,
                    "reason": "rate_limited",
                    "url": decision.url,
                }
            )
            audit_record["event"] = "rate_limited"
            append_audit_record(audit_log_path, audit_record)
            logger.warning(
                "Rate limit reached (%d/hr); PR #%d deferred.",
                rate_limit_per_hour,
                decision.number,
            )
            # Do not persist the reservation since we didn't actually approve.
            break

        body = build_approval_body(snapshot)

        if effective_dry_run:
            audit_record["event"] = "dry_run_approve"
            audit_record["body"] = body
            append_audit_record(audit_log_path, audit_record)
            summary["approvals"].append(
                {
                    "number": decision.number,
                    "head_sha": decision.head_sha,
                    "url": decision.url,
                    "mode": "dry-run",
                }
            )
            logger.info(
                "[dry-run] Would approve PR #%d (head=%s).",
                decision.number,
                decision.head_sha[:8],
            )
            continue

        # Live approval.
        try:
            response = client.submit_review(decision.number, body=body, event="APPROVE")
        except Exception as exc:  # pragma: no cover - network errors
            audit_record["event"] = "approve_failed"
            audit_record["error"] = str(exc)
            append_audit_record(audit_log_path, audit_record)
            logger.error("Failed to approve PR #%d: %s", decision.number, exc)
            summary["skips"].append(
                {
                    "number": decision.number,
                    "reason": "approve_failed",
                    "error": str(exc),
                    "url": decision.url,
                }
            )
            continue

        # Persist the rate-limit reservation only after a successful live approval.
        _save_rate_limit(rate_limit_path, new_state)
        audit_record["event"] = "approved"
        audit_record["review_id"] = response.get("id")
        append_audit_record(audit_log_path, audit_record)
        summary["approvals"].append(
            {
                "number": decision.number,
                "head_sha": decision.head_sha,
                "url": decision.url,
                "mode": "live",
                "review_id": response.get("id"),
            }
        )
        logger.info(
            "Approved PR #%d (review_id=%s head=%s).",
            decision.number,
            response.get("id"),
            decision.head_sha[:8],
        )

    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-approve safe automation PRs via the aragora-automation GitHub App."
    )
    parser.add_argument("--repo", default=DEFAULT_REPO, help="OWNER/NAME (default: %(default)s)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log would-approve decisions without submitting reviews.",
    )
    parser.add_argument(
        "--max-diff-loc",
        type=int,
        default=DEFAULT_MAX_DIFF_LOC,
        help="Maximum additions+deletions for auto-approval (default: %(default)s).",
    )
    parser.add_argument(
        "--rate-limit-per-hour",
        type=int,
        default=DEFAULT_RATE_LIMIT_PER_HOUR,
        help="Maximum auto-approvals per rolling hour (default: %(default)s).",
    )
    parser.add_argument(
        "--allowed-author",
        action="append",
        default=None,
        help="Override allowed authors. Repeatable; replaces defaults when provided.",
    )
    parser.add_argument(
        "--optin-label",
        action="append",
        default=None,
        help="Override opt-in labels. Repeatable; replaces defaults when provided.",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=DEFAULT_PER_PAGE,
        help="PRs per page to fetch (default: %(default)s).",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable summary.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(SCRIPT_LOG_PATH)

    policy = ApprovalPolicy(
        allowed_authors=tuple(args.allowed_author)
        if args.allowed_author
        else DEFAULT_ALLOWED_AUTHORS,
        optin_labels=tuple(args.optin_label) if args.optin_label else DEFAULT_OPTIN_LABELS,
        protected_paths=PROTECTED_PATH_PATTERNS,
        max_diff_loc=args.max_diff_loc,
    )

    summary = run(
        args.repo,
        policy=policy,
        dry_run=args.dry_run,
        rate_limit_per_hour=args.rate_limit_per_hour,
        per_page=args.per_page,
    )

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    else:
        approvals = summary.get("approvals") or []
        skips = summary.get("skips") or []
        print(f"mode={summary['mode']} repo={summary['repo']}")
        print(f"approvals: {len(approvals)}")
        for item in approvals:
            print(f"  APPROVE #{item['number']} {item.get('url', '')}")
        print(f"skips: {len(skips)}")
        for item in skips:
            print(f"  skip #{item['number']} reason={item.get('reason', '?')}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

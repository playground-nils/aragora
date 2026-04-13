"""Issue selection and deduplication helpers for the boss loop.

Extracted from boss_loop.py to keep the main module under the LOC ratchet.
These are pure-logic functions that operate on issue lists without boss loop
instance state.
"""

from __future__ import annotations

import asyncio
import json as _json
import logging
import os
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aragora.swarm.boss_loop import GitHubIssue

logger = logging.getLogger(__name__)


def semantic_dedup_issues(issues: list[GitHubIssue]) -> list[GitHubIssue]:
    """Use LLM to cluster semantically duplicate issues, keep one per cluster."""
    if len(issues) < 6:
        return issues

    try:
        from aragora.agents.base import create_agent

        agent = None
        if os.environ.get("OPENROUTER_API_KEY"):
            agent = create_agent(
                "openrouter", name="dedup", role="proposer", model="deepseek/deepseek-chat"
            )
        elif os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            agent = create_agent("gemini", name="dedup", role="proposer", model="gemini-2.0-flash")
        if agent is None:
            return issues

        issue_map = {
            str(i.number): re.sub(r"\[from #\d+\]\s*", "", i.title).strip() for i in issues
        }
        prompt = (
            "You are deduplicating GitHub issues. Group semantically equivalent tasks. "
            "Return ONLY a JSON array of arrays: [[num1,num2],[num3],...]\n\n"
            + "\n".join(f"#{num}: {title}" for num, title in issue_map.items())
        )

        try:
            asyncio.get_running_loop()
            return issues  # Can't call asyncio.run inside running loop
        except RuntimeError:
            pass

        raw = asyncio.run(agent.generate(prompt))
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return issues

        clusters = _json.loads(match.group())
        if not isinstance(clusters, list):
            return issues

        kept = {int(c[0]) for c in clusters if isinstance(c, list) and c}
        all_clustered = {int(n) for c in clusters if isinstance(c, list) for n in c}
        deduped = [i for i in issues if i.number in kept or i.number not in all_clustered]

        logger.info("Semantic dedup: %d → %d issues", len(issues), len(deduped))
        return deduped
    except Exception as exc:
        logger.debug("Semantic dedup skipped: %s", exc)
        return issues


def scope_hint_is_specific(scope_entry: str) -> bool:
    """Check if a scope entry is file-specific (has extension or glob)."""
    basename = str(scope_entry or "").rstrip("/").rsplit("/", 1)[-1]
    return "*" in scope_entry or "." in basename


def scope_hint_is_validation_command_scope(issue: GitHubIssue, scope_entry: str) -> bool:
    """Check if scope_entry only appears as part of a validation command."""
    if scope_hint_is_specific(scope_entry):
        return False
    scope = str(scope_entry or "").strip().rstrip("/")
    if not scope:
        return False
    validation_command_re = re.compile(
        r"\b(pytest|ruff|mypy|npm|pnpm|yarn|python\s+-m\s+pytest)\b",
        re.IGNORECASE,
    )
    for line in str(issue.body or "").splitlines():
        normalized = line.strip().strip("-* ").replace("`", "").rstrip("/")
        if scope in normalized and validation_command_re.search(normalized):
            return True
    return False


def parallel_claim_scope_entries(issue: GitHubIssue) -> list[str]:
    """Get scope entries that represent exclusive edit claims."""
    from aragora.swarm.boss_loop import infer_issue_scope_entries

    return [
        scope_entry
        for scope_entry in infer_issue_scope_entries(issue)
        if not scope_hint_is_validation_command_scope(issue, scope_entry)
    ]


def has_explicit_parallel_lane_hint(issue: GitHubIssue) -> bool:
    """Check if an issue has explicit lane/area metadata."""
    if any(
        re.match(r"^(?:lane|area)[:/]", str(label or "").strip(), re.IGNORECASE)
        for label in issue.labels
    ):
        return True
    combined = "\n".join(
        part for part in (str(issue.title or "").strip(), str(issue.body or "").strip()) if part
    )
    return bool(re.search(r"(?im)^(?:lane|owner lane|lane id)\s*:", combined))


def select_issues_for_batch(
    issues: list[GitHubIssue],
    *,
    limit: int | None,
    blocked_scopes: set[str] | None = None,
    skip_labels: set[str] | frozenset[str] | None = None,
    require_labels: set[str] | frozenset[str] | None = None,
    issue_number: int | None = None,
    dedup_fn: Any | None = None,
) -> list[GitHubIssue]:
    """Select non-overlapping issues for one iteration batch.

    This is the extracted core of BossLoop._select_issues_for_iteration.
    """
    from aragora.swarm.boss_loop import (
        infer_issue_lane_hints,
        select_eligible_issue,
    )

    blocked_scope_entries = set(blocked_scopes or set())

    if limit is not None and limit <= 1:
        if issue_number is not None:
            target = next((i for i in issues if i.number == issue_number), None)
            selected = (
                select_eligible_issue(
                    [target],
                    skip_labels=skip_labels,
                    require_labels=require_labels,
                    blocked_scopes=blocked_scope_entries,
                )
                if target is not None
                else None
            )
            return [selected] if selected is not None else []
        selected = select_eligible_issue(
            issues,
            skip_labels=skip_labels,
            require_labels=require_labels,
            blocked_scopes=blocked_scope_entries,
        )
        return [selected] if selected is not None else []

    if issue_number is not None:
        target = next((i for i in issues if i.number == issue_number), None)
        selected = (
            select_eligible_issue(
                [target],
                skip_labels=skip_labels,
                require_labels=require_labels,
                blocked_scopes=blocked_scope_entries,
            )
            if target is not None
            else None
        )
        return [selected] if selected is not None else []

    # Semantic dedup
    pre_dedup = [issue for issue in issues if not (set(issue.labels) & set(skip_labels or set()))]
    _dedup = dedup_fn if dedup_fn is not None else semantic_dedup_issues
    issues = _dedup(pre_dedup)

    selected_issues: list[GitHubIssue] = []
    claimed_scopes: set[str] = set(blocked_scope_entries)
    claimed_lanes: set[str] = set()
    claimed_stems: set[str] = set()

    for issue in issues:
        candidate = select_eligible_issue(
            [issue],
            skip_labels=skip_labels,
            require_labels=require_labels,
            blocked_scopes=claimed_scopes,
        )
        if candidate is None:
            continue

        claim_scope_hints = set(parallel_claim_scope_entries(candidate))
        if claim_scope_hints and claim_scope_hints & claimed_scopes:
            continue
        lane_hints = (
            set(infer_issue_lane_hints(candidate))
            if claim_scope_hints or has_explicit_parallel_lane_hint(candidate)
            else set()
        )
        if lane_hints and lane_hints & claimed_lanes:
            continue

        stem = re.sub(r"\[from #\d+\]\s*", "", candidate.title).strip().lower()[:60]
        if stem in claimed_stems:
            continue

        selected_issues.append(candidate)
        claimed_scopes.update(claim_scope_hints)
        claimed_lanes.update(lane_hints)
        claimed_stems.add(stem)
        if limit is not None and len(selected_issues) >= limit:
            break
    return selected_issues

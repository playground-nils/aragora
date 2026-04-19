"""Batched human-in-the-loop review queue for automation PRs."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aragora.cli.commands import review_pr
from aragora.swarm.merge_arbiter import (
    MergeArbiterConfig,
    READY_SUITE_GATE_CHECKS,
    _classify_non_passing_checks,
    _classify_required_checks,
    _get_check_status,
    _get_required_checks,
    _list_candidate_prs,
    _ready_suite_check_names,
)
from aragora.worktree.fleet import resolve_repo_root

logger = logging.getLogger(__name__)

UTC = timezone.utc


def cmd_review_queue(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(Path.cwd())
    action = str(getattr(args, "review_queue_command", "") or "build")

    if action == "build":
        queue = build_review_queue(
            repo_root=repo_root,
            limit=int(getattr(args, "limit", 30)),
            ready_only=bool(getattr(args, "ready_only", False)),
            refresh_packets=bool(getattr(args, "refresh_packets", False)),
        )
        if bool(getattr(args, "json_output", False)):
            print(json.dumps(queue, indent=2))
        else:
            _print_queue(queue)
        return 0

    if action == "packet":
        packet = build_review_packet(
            pr_ref=str(getattr(args, "pr")),
            repo_root=repo_root,
            refresh=bool(getattr(args, "refresh", False)),
        )
        print(json.dumps(packet, indent=2))
        return 0

    if action == "run":
        return run_review_queue_session(
            repo_root=repo_root,
            limit=int(getattr(args, "limit", 30)),
            ready_only=bool(getattr(args, "ready_only", False)),
            refresh_packets=bool(getattr(args, "refresh_packets", False)),
        )

    raise SystemExit(f"Unknown review-queue action: {action}")


def build_review_queue(
    *,
    repo_root: Path,
    limit: int = 30,
    ready_only: bool = False,
    refresh_packets: bool = False,
) -> list[dict[str, Any]]:
    config = MergeArbiterConfig()
    candidates = sorted(_list_candidate_prs(config), key=lambda item: int(item.get("number", 0)))
    queue: list[dict[str, Any]] = []
    for pr in candidates[:limit]:
        target = review_pr._fetch_pr_target(
            str(pr["number"]),
            repo_override=config.repo,
            repo_root=repo_root,
        )
        packet = _load_packet(repo_root, target.number, target.head_sha)
        if refresh_packets:
            packet = build_review_packet(
                pr_ref=str(target.number), repo_root=repo_root, refresh=True
            )
        queue.append(_build_queue_item(target=target, packet=packet))
    if ready_only:
        queue = [item for item in queue if item["bucket"] == "ready_now"]
    return queue


def build_review_packet(
    *,
    pr_ref: str,
    repo_root: Path,
    refresh: bool = False,
) -> dict[str, Any]:
    target = review_pr._fetch_pr_target(pr_ref, repo_override=None, repo_root=repo_root)
    if not refresh:
        cached = _load_packet(repo_root, target.number, target.head_sha)
        if cached is not None:
            return cached

    run_payload = asyncio.run(
        review_pr.run_review_pr_loop(
            pr_ref=str(target.number),
            repo_root=repo_root,
            repo_override=target.repo,
            reviewer="claude",
            fixer=None,
            auto_rerun=False,
            artifact_root=None,
            keep_worktree=False,
            publish_review=False,
        )
    )
    refreshed_target = review_pr._fetch_pr_target(
        str(target.number), repo_override=target.repo, repo_root=repo_root
    )
    diff_text = review_pr._fetch_pr_diff(refreshed_target)
    additions, deletions, changed_files = _diff_stats(diff_text)
    checks = _get_check_status(refreshed_target.number, refreshed_target.repo)
    packet = _build_packet(
        target=refreshed_target,
        checks=checks,
        review_payload=run_payload,
        diff_stats={
            "files_changed": changed_files,
            "additions": additions,
            "deletions": deletions,
        },
    )
    _write_packet(repo_root, packet)
    return packet


def run_review_queue_session(
    *,
    repo_root: Path,
    limit: int = 30,
    ready_only: bool = False,
    refresh_packets: bool = False,
) -> int:
    queue = build_review_queue(
        repo_root=repo_root,
        limit=limit,
        ready_only=ready_only,
        refresh_packets=refresh_packets,
    )
    if not queue:
        print("No candidate automation PRs in the review queue.")
        return 0

    processed = 0
    for item in queue:
        packet = build_review_packet(
            pr_ref=str(item["pr_number"]),
            repo_root=repo_root,
            refresh=refresh_packets or not bool(item.get("packet_fresh")),
        )
        while True:
            _print_packet_summary(packet)
            choice = (
                input(
                    "[a]pprove / [r]equest changes / [d]efer / [o]pen diff / [p]acket / [q]uit > "
                )
                .strip()
                .lower()
            )
            if choice == "a":
                _approve_packet(repo_root, packet)
                processed += 1
                break
            if choice == "r":
                reason = input("Request changes reason: ").strip()
                _request_changes_packet(repo_root, packet, reason)
                processed += 1
                break
            if choice == "d":
                reason = input("Defer note (optional): ").strip()
                _defer_packet(repo_root, packet, reason)
                processed += 1
                break
            if choice == "o":
                _run_gh(
                    [
                        "pr",
                        "diff",
                        str(packet["pr_number"]),
                        "--repo",
                        str(packet["repo"]),
                    ]
                )
                continue
            if choice == "p":
                print(json.dumps(packet, indent=2))
                continue
            if choice == "q":
                return processed
            print("Unrecognized choice. Use a/r/d/o/p/q.")
    return processed


def _build_packet(
    *,
    target: review_pr.PullRequestTarget,
    checks: dict[str, str],
    review_payload: dict[str, Any],
    diff_stats: dict[str, int],
) -> dict[str, Any]:
    required_checks = _get_required_checks(target.repo, target.base_ref or "main")
    missing_required, failing_required = _classify_required_checks(
        checks, required_checks=required_checks
    )
    missing_ready_gates = sorted(name for name in READY_SUITE_GATE_CHECKS if name not in checks)
    ready_suite_checks = _ready_suite_check_names(checks, required_checks=required_checks)
    ready_suite_statuses = {name: checks[name] for name in ready_suite_checks}
    waiting_ready, failing_ready = _classify_non_passing_checks(ready_suite_statuses)

    review_runs = review_payload.get("review_runs") or []
    latest_review = review_runs[-1] if isinstance(review_runs, list) and review_runs else {}
    findings = latest_review.get("findings") if isinstance(latest_review, dict) else []
    findings_count = len(findings) if isinstance(findings, list) else 0

    risk_flags: list[str] = []
    if target.is_draft:
        risk_flags.append("draft_pr")
    if target.mergeable and target.mergeable != "MERGEABLE":
        risk_flags.append(f"mergeable={target.mergeable.lower()}")
    if diff_stats["files_changed"] > 25:
        risk_flags.append("large_diff_files")
    if diff_stats["additions"] + diff_stats["deletions"] > 800:
        risk_flags.append("large_diff_lines")
    if findings_count:
        risk_flags.append("machine_findings_present")
    if missing_required:
        risk_flags.append("missing_required_checks")
    if failing_required:
        risk_flags.append("failing_required_checks")
    if missing_ready_gates:
        risk_flags.append("missing_ready_gate_checks")
    if waiting_ready:
        risk_flags.append("full_suite_pending")
    if failing_ready:
        risk_flags.append("full_suite_failures")

    final_status = str(review_payload.get("final_status", "")).strip().lower()
    machine_recommendation = _machine_recommendation(
        final_status=final_status,
        target=target,
        missing_required=missing_required,
        failing_required=failing_required,
        missing_ready_gates=missing_ready_gates,
        waiting_ready=waiting_ready,
        failing_ready=failing_ready,
        risk_flags=risk_flags,
    )
    bucket = _bucket_for_packet(
        target=target,
        machine_recommendation=machine_recommendation,
        missing_required=missing_required,
        failing_required=failing_required,
        missing_ready_gates=missing_ready_gates,
        waiting_ready=waiting_ready,
        failing_ready=failing_ready,
        packet_fresh=True,
    )

    packet: dict[str, Any] = {
        "pr_number": target.number,
        "repo": target.repo,
        "url": target.url,
        "title": target.title,
        "base_ref": target.base_ref,
        "branch": target.head_ref,
        "head_sha": target.head_sha,
        "review_decision": target.review_decision,
        "mergeable": target.mergeable,
        "is_draft": target.is_draft,
        "packet_generated_at": _now_iso(),
        "artifact_dir": review_payload.get("artifact_dir"),
        "packet_fresh": True,
        "diff_stats": diff_stats,
        "checks": checks,
        "check_summary": {
            "missing_required": missing_required,
            "failing_required": failing_required,
            "missing_ready_gates": missing_ready_gates,
            "waiting_ready": waiting_ready,
            "failing_ready": failing_ready,
        },
        "machine_review": {
            "status": final_status,
            "summary": str(latest_review.get("summary", "")).strip(),
            "reviewer": latest_review.get("reviewer"),
            "reviewed_at": latest_review.get("reviewed_at"),
            "findings_count": findings_count,
        },
        "machine_recommendation": machine_recommendation,
        "bucket": bucket,
        "risk_flags": risk_flags,
    }
    packet["packet_sha"] = _packet_sha(packet)
    return packet


def _build_queue_item(
    *,
    target: review_pr.PullRequestTarget,
    packet: dict[str, Any] | None,
) -> dict[str, Any]:
    checks = _get_check_status(target.number, target.repo)
    required_checks = _get_required_checks(target.repo, target.base_ref or "main")
    missing_required, failing_required = _classify_required_checks(
        checks, required_checks=required_checks
    )
    missing_ready_gates = sorted(name for name in READY_SUITE_GATE_CHECKS if name not in checks)
    ready_suite_checks = _ready_suite_check_names(checks, required_checks=required_checks)
    ready_suite_statuses = {name: checks[name] for name in ready_suite_checks}
    waiting_ready, failing_ready = _classify_non_passing_checks(ready_suite_statuses)
    packet_fresh = bool(packet)
    risk_flags = list(packet.get("risk_flags", [])) if packet else ["packet_missing"]
    machine_recommendation = (
        str(packet.get("machine_recommendation"))
        if packet
        else _machine_recommendation(
            final_status="",
            target=target,
            missing_required=missing_required,
            failing_required=failing_required,
            missing_ready_gates=missing_ready_gates,
            waiting_ready=waiting_ready,
            failing_ready=failing_ready,
            risk_flags=risk_flags,
        )
    )
    bucket = (
        str(packet.get("bucket"))
        if packet
        else _bucket_for_packet(
            target=target,
            machine_recommendation=machine_recommendation,
            missing_required=missing_required,
            failing_required=failing_required,
            missing_ready_gates=missing_ready_gates,
            waiting_ready=waiting_ready,
            failing_ready=failing_ready,
            packet_fresh=packet_fresh,
        )
    )
    return {
        "pr_number": target.number,
        "repo": target.repo,
        "title": target.title,
        "url": target.url,
        "branch": target.head_ref,
        "head_sha": target.head_sha,
        "bucket": bucket,
        "machine_recommendation": machine_recommendation,
        "packet_fresh": packet_fresh,
        "review_decision": target.review_decision,
        "mergeable": target.mergeable,
        "risk_flags": risk_flags,
        "checks": checks,
        "machine_summary": packet.get("machine_review", {}).get("summary") if packet else None,
    }


def _bucket_for_packet(
    *,
    target: review_pr.PullRequestTarget,
    machine_recommendation: str,
    missing_required: list[str],
    failing_required: list[str],
    missing_ready_gates: list[str],
    waiting_ready: list[str],
    failing_ready: list[str],
    packet_fresh: bool,
) -> str:
    if target.mergeable and target.mergeable != "MERGEABLE":
        return "parked"
    if machine_recommendation == "repair_first" or missing_required or failing_required:
        return "repairable"
    if target.head_ref == "" or target.mergeable == "UNKNOWN":
        return "parked"
    if (
        packet_fresh
        and machine_recommendation == "approve_candidate"
        and not missing_ready_gates
        and not waiting_ready
        and not failing_ready
    ):
        return "ready_now"
    return "needs_attention"


def _machine_recommendation(
    *,
    final_status: str,
    target: review_pr.PullRequestTarget,
    missing_required: list[str],
    failing_required: list[str],
    missing_ready_gates: list[str],
    waiting_ready: list[str],
    failing_ready: list[str],
    risk_flags: list[str],
) -> str:
    if target.mergeable and target.mergeable != "MERGEABLE":
        return "needs_human_attention"
    if final_status == "changes_requested":
        return "repair_first"
    if final_status == "blocked_nonreviewable":
        return "needs_human_attention"
    if (
        missing_required
        or failing_required
        or missing_ready_gates
        or waiting_ready
        or failing_ready
    ):
        return "repair_first"
    if risk_flags:
        return "needs_human_attention"
    return "approve_candidate"


def _packet_root(repo_root: Path) -> Path:
    root = repo_root / ".aragora" / "review-queue" / "packets"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _settlement_root(repo_root: Path) -> Path:
    root = repo_root / ".aragora" / "review-queue" / "settlements"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _packet_file(repo_root: Path, pr_number: int, head_sha: str) -> Path:
    slug = head_sha[:12] if head_sha else "unknown"
    return _packet_root(repo_root) / f"pr-{pr_number}-{slug}.json"


def _settlement_file(repo_root: Path, pr_number: int, head_sha: str, action: str) -> Path:
    slug = head_sha[:12] if head_sha else "unknown"
    return _settlement_root(repo_root) / f"pr-{pr_number}-{slug}-{action}.json"


def _load_packet(repo_root: Path, pr_number: int, head_sha: str) -> dict[str, Any] | None:
    packet_path = _packet_file(repo_root, pr_number, head_sha)
    if not packet_path.exists():
        return None
    try:
        return json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_packet(repo_root: Path, packet: dict[str, Any]) -> None:
    path = _packet_file(repo_root, int(packet["pr_number"]), str(packet["head_sha"]))
    path.write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")


def _write_settlement(
    repo_root: Path,
    packet: dict[str, Any],
    *,
    action: str,
    reason: str,
) -> None:
    payload = {
        "pr_number": packet["pr_number"],
        "repo": packet["repo"],
        "head_sha": packet["head_sha"],
        "packet_sha": packet["packet_sha"],
        "action": action,
        "reason": reason,
        "recorded_at": _now_iso(),
    }
    _settlement_file(
        repo_root, int(packet["pr_number"]), str(packet["head_sha"]), action
    ).write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _approve_packet(repo_root: Path, packet: dict[str, Any]) -> None:
    target = _ensure_packet_head_matches(repo_root, packet)
    body = (
        f"Approved via `aragora review-queue`.\n\n"
        f"- Packet SHA: `{packet['packet_sha']}`\n"
        f"- Head SHA: `{packet['head_sha']}`"
    )
    _run_gh(
        [
            "pr",
            "review",
            str(target.number),
            "--repo",
            target.repo,
            "--approve",
            "--body",
            body,
        ]
    )
    _write_settlement(repo_root, packet, action="approve", reason=body)


def _request_changes_packet(repo_root: Path, packet: dict[str, Any], reason: str) -> None:
    target = _ensure_packet_head_matches(repo_root, packet)
    body = reason or "Changes requested via `aragora review-queue`."
    _run_gh(
        [
            "pr",
            "review",
            str(target.number),
            "--repo",
            target.repo,
            "--request-changes",
            "--body",
            body,
        ]
    )
    _write_settlement(repo_root, packet, action="request_changes", reason=body)


def _defer_packet(repo_root: Path, packet: dict[str, Any], reason: str) -> None:
    note = reason or "Deferred via `aragora review-queue`."
    _write_settlement(repo_root, packet, action="defer", reason=note)


def _ensure_packet_head_matches(
    repo_root: Path, packet: dict[str, Any]
) -> review_pr.PullRequestTarget:
    target = review_pr._fetch_pr_target(
        str(packet["pr_number"]),
        repo_override=str(packet["repo"]),
        repo_root=repo_root,
    )
    if target.head_sha != str(packet["head_sha"]):
        raise RuntimeError(
            f"PR #{target.number} head moved from {packet['head_sha']} to {target.head_sha}; "
            "rebuild the packet before settling."
        )
    return target


def _run_gh(args: list[str]) -> None:
    result = subprocess.run(args=["gh", *args], check=False)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed with exit code {result.returncode}")


def _packet_sha(packet: dict[str, Any]) -> str:
    payload = {key: value for key, value in packet.items() if key != "packet_sha"}
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _diff_stats(diff_text: str) -> tuple[int, int, int]:
    additions = 0
    deletions = 0
    changed_files = 0
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            changed_files += 1
            continue
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line.startswith("+"):
            additions += 1
        elif line.startswith("-"):
            deletions += 1
    return additions, deletions, changed_files


def _print_queue(queue: list[dict[str, Any]]) -> None:
    for item in queue:
        flags = ",".join(item.get("risk_flags") or [])
        print(
            f"#{item['pr_number']} {item['bucket']} {item['machine_recommendation']} "
            f"{item['branch']} packet_fresh={item['packet_fresh']} flags=[{flags}]"
        )


def _print_packet_summary(packet: dict[str, Any]) -> None:
    diff_stats = packet.get("diff_stats", {})
    machine_review = packet.get("machine_review", {})
    print()
    print(f"PR #{packet['pr_number']} — {packet['title']}")
    print(f"Branch: {packet['branch']}")
    print(f"Head SHA: {packet['head_sha']}")
    print(f"Bucket: {packet['bucket']} | Recommendation: {packet['machine_recommendation']}")
    print(
        f"Mergeable: {packet.get('mergeable')} | Review decision: {packet.get('review_decision')}"
    )
    print(
        "Diff: "
        f"{diff_stats.get('files_changed', 0)} files, "
        f"+{diff_stats.get('additions', 0)} / -{diff_stats.get('deletions', 0)}"
    )
    summary = str(machine_review.get("summary", "")).strip() or "(no machine summary yet)"
    print(f"Machine summary: {summary}")
    risk_flags = packet.get("risk_flags") or []
    print(f"Risk flags: {', '.join(risk_flags) if risk_flags else '(none)'}")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()

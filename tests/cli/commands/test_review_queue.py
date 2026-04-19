from __future__ import annotations

import json
from pathlib import Path

from aragora.cli.commands import review_pr, review_queue
from aragora.cli.parser import build_parser


def test_review_queue_parser_accepts_build_packet_and_run() -> None:
    parser = build_parser()

    build_args = parser.parse_args(
        ["review-queue", "build", "--limit", "12", "--ready-only", "--json"]
    )
    assert build_args.command == "review-queue"
    assert build_args.review_queue_command == "build"
    assert build_args.limit == 12
    assert build_args.ready_only is True
    assert build_args.json_output is True

    packet_args = parser.parse_args(["review-queue", "packet", "123", "--refresh"])
    assert packet_args.review_queue_command == "packet"
    assert packet_args.pr == "123"
    assert packet_args.refresh is True

    run_args = parser.parse_args(["review-queue", "run", "--limit", "5"])
    assert run_args.review_queue_command == "run"
    assert run_args.limit == 5


def test_build_review_packet_persists_advisory_packet(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = review_pr.PullRequestTarget(
        number=6279,
        repo="synaptent/aragora",
        url="https://github.com/synaptent/aragora/pull/6279",
        title="docs: design human-in-loop batched PR triage",
        base_ref="main",
        head_ref="codex/batched-pr-triage-design",
        head_sha="abc123def4567890",
        files=["docs/plans/2026-04-19-batched-pr-review-triage.md"],
        mergeable="MERGEABLE",
        review_decision="REVIEW_REQUIRED",
        is_draft=False,
    )

    monkeypatch.setattr(review_pr, "_fetch_pr_target", lambda *_, **__: target)
    monkeypatch.setattr(
        review_pr, "_fetch_pr_diff", lambda *_: "diff --git a/a b/a\n+line\n-line\n"
    )

    async def _fake_run_review_pr_loop(**_: object) -> dict[str, object]:
        return {
            "artifact_dir": str(tmp_path / "artifacts"),
            "final_status": "passed",
            "review_runs": [
                {
                    "reviewer": "claude",
                    "reviewed_at": "2026-04-19T13:00:00+00:00",
                    "summary": "Scoped change with test coverage.",
                    "findings": [],
                }
            ],
        }

    monkeypatch.setattr(review_pr, "run_review_pr_loop", _fake_run_review_pr_loop)
    monkeypatch.setattr(
        review_queue,
        "_get_check_status",
        lambda *_: {
            "lint": "SUCCESS",
            "typecheck": "SUCCESS",
            "sdk-parity": "SUCCESS",
            "Generate & Validate": "SUCCESS",
            "TypeScript SDK Type Check": "SUCCESS",
            "Prioritize Required Checks": "SUCCESS",
            "Quality Gates": "SUCCESS",
        },
    )
    monkeypatch.setattr(
        review_queue,
        "_get_required_checks",
        lambda *_args, **_kwargs: [
            "lint",
            "typecheck",
            "sdk-parity",
            "Generate & Validate",
            "TypeScript SDK Type Check",
        ],
    )

    packet = review_queue.build_review_packet(pr_ref="6279", repo_root=tmp_path, refresh=True)

    assert packet["pr_number"] == 6279
    assert packet["machine_recommendation"] == "approve_candidate"
    assert packet["bucket"] == "ready_now"
    assert packet["machine_review"]["status"] == "passed"
    packet_path = tmp_path / ".aragora" / "review-queue" / "packets" / "pr-6279-abc123def456.json"
    assert packet_path.exists()
    persisted = json.loads(packet_path.read_text(encoding="utf-8"))
    assert persisted["packet_sha"] == packet["packet_sha"]


def test_build_review_queue_ready_only_filters_non_ready_packets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pr_one = {
        "number": 100,
        "headRefName": "codex/ready",
        "headRefOid": "abc1234567890000",
        "isDraft": False,
        "reviewDecision": "APPROVED",
    }
    pr_two = {
        "number": 101,
        "headRefName": "codex/repair",
        "headRefOid": "def1234567890000",
        "isDraft": False,
        "reviewDecision": "REVIEW_REQUIRED",
    }
    targets = {
        100: review_pr.PullRequestTarget(
            number=100,
            repo="synaptent/aragora",
            url="https://github.com/synaptent/aragora/pull/100",
            title="ready",
            base_ref="main",
            head_ref="codex/ready",
            head_sha="abc1234567890000",
            mergeable="MERGEABLE",
            review_decision="APPROVED",
        ),
        101: review_pr.PullRequestTarget(
            number=101,
            repo="synaptent/aragora",
            url="https://github.com/synaptent/aragora/pull/101",
            title="repair",
            base_ref="main",
            head_ref="codex/repair",
            head_sha="def1234567890000",
            mergeable="MERGEABLE",
            review_decision="REVIEW_REQUIRED",
        ),
    }
    monkeypatch.setattr(review_queue, "_list_candidate_prs", lambda *_: [pr_one, pr_two])
    monkeypatch.setattr(
        review_pr,
        "_fetch_pr_target",
        lambda pr_ref, **_: targets[int(str(pr_ref))],
    )
    monkeypatch.setattr(review_queue, "_get_check_status", lambda *_: {})
    monkeypatch.setattr(review_queue, "_get_required_checks", lambda *_args, **_kwargs: [])

    ready_packet = {
        "pr_number": 100,
        "head_sha": "abc1234567890000",
        "bucket": "ready_now",
        "machine_recommendation": "approve_candidate",
        "risk_flags": [],
        "machine_review": {"summary": "ready"},
    }
    repair_packet = {
        "pr_number": 101,
        "head_sha": "def1234567890000",
        "bucket": "repairable",
        "machine_recommendation": "repair_first",
        "risk_flags": ["machine_findings_present"],
        "machine_review": {"summary": "repair"},
    }
    monkeypatch.setattr(
        review_queue,
        "_load_packet",
        lambda _repo_root, pr_number, _head_sha: ready_packet
        if pr_number == 100
        else repair_packet,
    )

    queue = review_queue.build_review_queue(repo_root=tmp_path, ready_only=True)

    assert [item["pr_number"] for item in queue] == [100]
    assert queue[0]["bucket"] == "ready_now"

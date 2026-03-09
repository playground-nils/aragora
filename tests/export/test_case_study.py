from __future__ import annotations

from aragora.compat.openclaw.pr_review_runner import (
    PRMetadata,
    ReviewFinding,
    ReviewReceipt,
    ReviewResult,
)
from aragora.export.case_study import (
    build_case_study_packet,
    finding_excerpt,
    normalize_finding_key,
    review_result_is_empty,
    sanitize_public_excerpt,
)


def _result(*findings: ReviewFinding, error: str | None = None) -> ReviewResult:
    return ReviewResult(
        pr_url="https://github.com/synaptent/aragora/pull/856",
        pr_number=856,
        repo="synaptent/aragora",
        findings=list(findings),
        agreement_score=0.8,
        agents_used=["anthropic-api", "openai-api"],
        comment_posted=False,
        comment_url=None,
        receipt=ReviewReceipt(
            review_id="r1",
            pr_url="https://github.com/synaptent/aragora/pull/856",
            started_at=1.0,
            completed_at=2.0,
            findings_count=len(findings),
            critical_count=sum(1 for finding in findings if finding.severity == "critical"),
            high_count=sum(1 for finding in findings if finding.severity == "high"),
            medium_count=sum(1 for finding in findings if finding.severity == "medium"),
            low_count=sum(1 for finding in findings if finding.severity == "low"),
            agreement_score=0.8,
            agents_used=["anthropic-api", "openai-api"],
            policy_name="pr-reviewer",
            policy_violations=[],
            checksum="abc123",
        ),
        raw_findings={},
        error=error,
    )


def test_sanitize_public_excerpt_collapses_and_truncates() -> None:
    text = "alpha\n\nbeta   gamma `" + ("z" * 220)
    excerpt = sanitize_public_excerpt(text, max_chars=40)
    assert "\n" not in excerpt
    assert "`" not in excerpt
    assert excerpt.endswith("...")


def test_normalize_finding_key_is_stable() -> None:
    finding = ReviewFinding(severity="high", title="SQL injection!", description="SQL injection!")
    assert normalize_finding_key(finding) == "sql injection"


def test_finding_excerpt_is_public_safe() -> None:
    finding = ReviewFinding(severity="critical", title="x", description="line1\nline2")
    excerpt = finding_excerpt(finding)
    assert excerpt.startswith("[critical] ")
    assert "\n" not in excerpt


def test_review_result_is_empty_when_no_findings_or_issue_lists() -> None:
    result = _result()
    assert review_result_is_empty(result) is True


def test_build_case_study_packet_published_delta() -> None:
    metadata = PRMetadata(
        pr_url="https://github.com/synaptent/aragora/pull/856",
        repo="synaptent/aragora",
        pr_number=856,
        title="Example",
        state="OPEN",
        base_ref="main",
        base_sha="base123",
        head_ref="feature",
        head_sha="head123",
    )
    baseline = _result(
        ReviewFinding(severity="high", title="Shared finding", description="Shared finding"),
    )
    adversarial = _result(
        ReviewFinding(severity="high", title="Shared finding", description="Shared finding"),
        ReviewFinding(severity="critical", title="Aragora only", description="Aragora only"),
    )

    packet = build_case_study_packet(
        case_id="case-1",
        metadata=metadata,
        pr_url=metadata.pr_url,
        baseline_result=baseline,
        adversarial_result=adversarial,
    )
    data = packet.to_dict()

    assert packet.status == "published"
    assert data["target"]["pr_url"] == metadata.pr_url
    assert data["delta"]["aragora_found_baseline_missed"] == ["[critical] Aragora only"]
    assert data["delta"]["both_found"] == ["[high] Shared finding"]


def test_build_case_study_packet_blocks_failed_review() -> None:
    packet = build_case_study_packet(
        case_id="case-2",
        metadata=None,
        pr_url="https://github.com/synaptent/aragora/pull/999",
        baseline_result=_result(error="network failure"),
        adversarial_result=None,
    )
    assert packet.status == "blocked"
    assert "baseline_review_failed" in (packet.reason or "")


def test_build_case_study_packet_fixture_only_skips() -> None:
    packet = build_case_study_packet(
        case_id="case-3",
        metadata=None,
        pr_url="https://github.com/synaptent/aragora/pull/999",
        baseline_result=None,
        adversarial_result=None,
        fixture_only=True,
    )
    assert packet.status == "skipped"
    assert packet.reason == "fixture_only_mode"

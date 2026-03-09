"""Publication-safe public PR review case study artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aragora.compat.openclaw.pr_review_runner import PRMetadata, ReviewFinding, ReviewResult

MAX_EXCERPTS = 5
MAX_EXCERPT_CHARS = 200


def sanitize_public_excerpt(text: str, *, max_chars: int = MAX_EXCERPT_CHARS) -> str:
    """Collapse and trim text for publication-safe evidence excerpts."""
    collapsed = re.sub(r"\s+", " ", text).strip()
    collapsed = collapsed.replace("```", "").replace("`", "")
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[: max_chars - 3].rstrip() + "..."


def normalize_finding_key(finding: ReviewFinding) -> str:
    """Produce a stable comparison key for a finding."""
    base = finding.title or finding.description
    normalized = sanitize_public_excerpt(base, max_chars=160).lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def finding_excerpt(finding: ReviewFinding) -> str:
    """Render a short evidence excerpt for a finding."""
    prefix = f"[{finding.severity}] "
    return sanitize_public_excerpt(prefix + (finding.description or finding.title))


@dataclass
class ReviewPacketSummary:
    """Publication-safe summary of one review path."""

    mode: str
    status: str
    reason: str | None
    findings_count: int = 0
    severity_counts: dict[str, int] = field(default_factory=dict)
    agreement_score: float | None = None
    evidence_excerpts: list[str] = field(default_factory=list)
    receipt_checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "status": self.status,
            "reason": self.reason,
            "findings_count": self.findings_count,
            "severity_counts": self.severity_counts,
            "agreement_score": self.agreement_score,
            "evidence_excerpts": self.evidence_excerpts,
            "receipt_checksum": self.receipt_checksum,
        }


@dataclass
class DeltaSummary:
    """Paired baseline versus adversarial delta summary."""

    aragora_found_baseline_missed: list[str] = field(default_factory=list)
    both_found: list[str] = field(default_factory=list)
    baseline_only: list[str] = field(default_factory=list)
    neither_could_verify: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "aragora_found_baseline_missed": self.aragora_found_baseline_missed,
            "both_found": self.both_found,
            "baseline_only": self.baseline_only,
            "neither_could_verify": self.neither_could_verify,
        }


@dataclass
class PublicPRCaseStudyPacket:
    """One publication-safe case-study packet for a public PR."""

    case_id: str
    generated_at: str
    status: str
    reason: str | None
    pr_url: str
    repo: str | None
    owner: str | None
    pr_number: int | None
    title: str | None
    state: str | None
    base_ref: str | None
    base_sha: str | None
    head_ref: str | None
    head_sha: str | None
    baseline: ReviewPacketSummary
    adversarial: ReviewPacketSummary
    delta: DeltaSummary
    publication_safe: bool = True
    packet_type: str = "public_pr_case_study"

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_type": self.packet_type,
            "case_id": self.case_id,
            "generated_at": self.generated_at,
            "status": self.status,
            "reason": self.reason,
            "publication_safe": self.publication_safe,
            "target": {
                "pr_url": self.pr_url,
                "repo": self.repo,
                "owner": self.owner,
                "pr_number": self.pr_number,
                "title": self.title,
                "state": self.state,
                "base_ref": self.base_ref,
                "base_sha": self.base_sha,
                "head_ref": self.head_ref,
                "head_sha": self.head_sha,
            },
            "baseline": self.baseline.to_dict(),
            "adversarial": self.adversarial.to_dict(),
            "delta": self.delta.to_dict(),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json() + "\n", encoding="utf-8")
        return path


@dataclass
class PublicPRCaseStudyIndex:
    """Aggregate index for a batch of case-study packets."""

    generated_at: str
    source_manifest: str
    total_cases: int
    published: int
    skipped: int
    blocked: int
    cases: list[dict[str, Any]]
    packet_type: str = "public_pr_case_study_index"

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_type": self.packet_type,
            "generated_at": self.generated_at,
            "source_manifest": self.source_manifest,
            "total_cases": self.total_cases,
            "published": self.published,
            "skipped": self.skipped,
            "blocked": self.blocked,
            "cases": self.cases,
        }

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        return path


def summarize_review_result(
    mode: str,
    result: ReviewResult | None,
    *,
    fixture_only: bool = False,
) -> ReviewPacketSummary:
    """Convert a review result into a publication-safe summary."""
    if fixture_only:
        return ReviewPacketSummary(
            mode=mode,
            status="skipped",
            reason="fixture_only_mode",
        )
    if result is None:
        return ReviewPacketSummary(mode=mode, status="blocked", reason="missing_review_result")
    if result.error:
        return ReviewPacketSummary(mode=mode, status="blocked", reason=result.error)

    findings = result.findings
    severity_counts = {
        "critical": sum(1 for finding in findings if finding.severity == "critical"),
        "high": sum(1 for finding in findings if finding.severity == "high"),
        "medium": sum(1 for finding in findings if finding.severity == "medium"),
        "low": sum(1 for finding in findings if finding.severity == "low"),
    }
    excerpts = [finding_excerpt(finding) for finding in findings[:MAX_EXCERPTS]]

    return ReviewPacketSummary(
        mode=mode,
        status="completed",
        reason=None,
        findings_count=len(findings),
        severity_counts=severity_counts,
        agreement_score=result.agreement_score,
        evidence_excerpts=excerpts,
        receipt_checksum=result.receipt.checksum if result.receipt else None,
    )


def review_result_is_empty(result: ReviewResult | None) -> bool:
    """Return true when a review result lacks usable findings data."""
    if result is None or result.error:
        return False
    if result.findings:
        return False
    raw = result.raw_findings
    if not isinstance(raw, dict):
        return True
    for key in (
        "unanimous_critiques",
        "critical_issues",
        "high_issues",
        "medium_issues",
        "low_issues",
    ):
        value = raw.get(key)
        if isinstance(value, list) and value:
            return False
    return True


def build_delta_summary(
    baseline_result: ReviewResult | None,
    adversarial_result: ReviewResult | None,
    *,
    status: str,
    reason: str | None,
) -> DeltaSummary:
    """Compare baseline and adversarial findings."""
    if status != "published":
        note = sanitize_public_excerpt(reason or "comparison_not_available")
        return DeltaSummary(neither_could_verify=[note])

    baseline_map = {
        normalize_finding_key(finding): finding_excerpt(finding)
        for finding in (baseline_result.findings if baseline_result else [])
    }
    adversarial_map = {
        normalize_finding_key(finding): finding_excerpt(finding)
        for finding in (adversarial_result.findings if adversarial_result else [])
    }

    baseline_keys = set(baseline_map)
    adversarial_keys = set(adversarial_map)

    return DeltaSummary(
        aragora_found_baseline_missed=[
            adversarial_map[key] for key in sorted(adversarial_keys - baseline_keys)
        ][:MAX_EXCERPTS],
        both_found=[adversarial_map[key] for key in sorted(adversarial_keys & baseline_keys)][
            :MAX_EXCERPTS
        ],
        baseline_only=[baseline_map[key] for key in sorted(baseline_keys - adversarial_keys)][
            :MAX_EXCERPTS
        ],
        neither_could_verify=[],
    )


def build_case_study_packet(
    *,
    case_id: str,
    metadata: PRMetadata | None,
    pr_url: str,
    baseline_result: ReviewResult | None,
    adversarial_result: ReviewResult | None,
    fixture_only: bool = False,
    status: str | None = None,
    reason: str | None = None,
) -> PublicPRCaseStudyPacket:
    """Build one publication-safe case-study packet."""
    resolved_status = status or "published"
    resolved_reason = reason

    if fixture_only:
        resolved_status = "skipped"
        resolved_reason = "fixture_only_mode"
    elif baseline_result and baseline_result.error:
        resolved_status = "blocked"
        resolved_reason = f"baseline_review_failed: {baseline_result.error}"
    elif adversarial_result and adversarial_result.error:
        resolved_status = "blocked"
        resolved_reason = f"adversarial_review_failed: {adversarial_result.error}"
    elif review_result_is_empty(baseline_result):
        resolved_status = "blocked"
        resolved_reason = "baseline_review_empty_artifact"
    elif review_result_is_empty(adversarial_result):
        resolved_status = "blocked"
        resolved_reason = "adversarial_review_empty_artifact"

    owner = None
    repo = metadata.repo if metadata else None
    if repo and "/" in repo:
        owner, _ = repo.split("/", 1)

    baseline_summary = summarize_review_result(
        "baseline",
        baseline_result,
        fixture_only=fixture_only,
    )
    adversarial_summary = summarize_review_result(
        "aragora_adversarial",
        adversarial_result,
        fixture_only=fixture_only,
    )
    delta = build_delta_summary(
        baseline_result,
        adversarial_result,
        status=resolved_status,
        reason=resolved_reason,
    )

    return PublicPRCaseStudyPacket(
        case_id=case_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=resolved_status,
        reason=resolved_reason,
        pr_url=pr_url,
        repo=repo,
        owner=owner,
        pr_number=metadata.pr_number if metadata else None,
        title=metadata.title if metadata else None,
        state=metadata.state if metadata else None,
        base_ref=metadata.base_ref if metadata else None,
        base_sha=metadata.base_sha if metadata else None,
        head_ref=metadata.head_ref if metadata else None,
        head_sha=metadata.head_sha if metadata else None,
        baseline=baseline_summary,
        adversarial=adversarial_summary,
        delta=delta,
    )

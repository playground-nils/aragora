from __future__ import annotations

import asyncio
import json
from pathlib import Path

from aragora.compat.openclaw.pr_review_runner import (
    PRMetadata,
    ReviewFinding,
    ReviewReceipt,
    ReviewResult,
)
from scripts.generate_public_pr_case_studies import generate_case_studies, load_manifest


def _review_result(pr_url: str, repo: str, pr_number: int, *, title: str) -> ReviewResult:
    finding = ReviewFinding(severity="high", title=title, description=title)
    return ReviewResult(
        pr_url=pr_url,
        pr_number=pr_number,
        repo=repo,
        findings=[finding],
        agreement_score=0.75,
        agents_used=["anthropic-api", "openai-api"],
        comment_posted=False,
        comment_url=None,
        receipt=ReviewReceipt(
            review_id="receipt-1",
            pr_url=pr_url,
            started_at=1.0,
            completed_at=2.0,
            findings_count=1,
            critical_count=0,
            high_count=1,
            medium_count=0,
            low_count=0,
            agreement_score=0.75,
            agents_used=["anthropic-api", "openai-api"],
            policy_name="pr-reviewer",
            policy_violations=[],
            checksum="xyz",
        ),
        raw_findings={"high_issues": [title]},
    )


def test_load_manifest_reads_entries(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"cases": [{"id": "case-1", "pr_url": "https://github.com/o/r/pull/1"}]}),
        encoding="utf-8",
    )
    entries = load_manifest(manifest)
    assert len(entries) == 1
    assert entries[0].case_id == "case-1"


def test_generate_case_studies_fixture_only_writes_skipped_packet(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"cases": [{"id": "case-1", "pr_url": "https://github.com/o/r/pull/1"}]}),
        encoding="utf-8",
    )

    result = asyncio.run(
        generate_case_studies(
            manifest_path=manifest,
            out_dir=tmp_path / "out",
            limit=None,
            fixture_only=True,
        )
    )

    packet = json.loads((tmp_path / "out" / "cases" / "case-1.json").read_text(encoding="utf-8"))
    assert result["skipped"] == 1
    assert packet["status"] == "skipped"
    assert packet["reason"] == "fixture_only_mode"


def test_generate_case_studies_blocks_invalid_metadata(monkeypatch, tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"cases": [{"id": "case-1", "pr_url": "https://github.com/o/r/pull/404"}]}),
        encoding="utf-8",
    )

    from scripts import generate_public_pr_case_studies as module

    def _metadata(*args, **kwargs):
        return None, "not found"

    monkeypatch.setattr(module.PRReviewRunner, "fetch_pr_metadata", _metadata)

    result = asyncio.run(
        generate_case_studies(
            manifest_path=manifest,
            out_dir=tmp_path / "out",
            limit=None,
            fixture_only=False,
        )
    )

    packet = json.loads((tmp_path / "out" / "cases" / "case-1.json").read_text(encoding="utf-8"))
    assert result["blocked"] == 1
    assert packet["status"] == "blocked"
    assert "metadata_fetch_failed" in packet["reason"]


def test_generate_case_studies_publishes_case_with_paired_delta(
    monkeypatch, tmp_path: Path
) -> None:
    manifest = tmp_path / "manifest.json"
    pr_url = "https://github.com/o/r/pull/1"
    manifest.write_text(
        json.dumps({"cases": [{"id": "case-1", "pr_url": pr_url}]}),
        encoding="utf-8",
    )

    from scripts import generate_public_pr_case_studies as module

    def _metadata(self, url):
        return (
            PRMetadata(
                pr_url=url,
                repo="o/r",
                pr_number=1,
                title="Example PR",
                state="OPEN",
                base_ref="main",
                base_sha="base",
                head_ref="feature",
                head_sha="head",
            ),
            None,
        )

    async def _review_pr(self, url):
        if self.gauntlet:
            return _review_result(url, "o/r", 1, title="Aragora only")
        return _review_result(url, "o/r", 1, title="Shared")

    monkeypatch.setattr(module.PRReviewRunner, "fetch_pr_metadata", _metadata)
    monkeypatch.setattr(module.PRReviewRunner, "review_pr", _review_pr)

    result = asyncio.run(
        generate_case_studies(
            manifest_path=manifest,
            out_dir=tmp_path / "out",
            limit=None,
            fixture_only=False,
        )
    )

    index = json.loads((tmp_path / "out" / "index.json").read_text(encoding="utf-8"))
    packet = json.loads((tmp_path / "out" / "cases" / "case-1.json").read_text(encoding="utf-8"))
    assert result["published"] == 1
    assert index["published"] == 1
    assert packet["status"] == "published"
    assert packet["delta"]["aragora_found_baseline_missed"] == ["[high] Aragora only"]


def test_generate_case_studies_blocks_runtime_exception(monkeypatch, tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    pr_url = "https://github.com/o/r/pull/1"
    manifest.write_text(
        json.dumps({"cases": [{"id": "case-1", "pr_url": pr_url}]}),
        encoding="utf-8",
    )

    from scripts import generate_public_pr_case_studies as module

    def _metadata(self, url):
        return (
            PRMetadata(
                pr_url=url,
                repo="o/r",
                pr_number=1,
                title="Example PR",
                state="OPEN",
                base_ref="main",
                base_sha="base",
                head_ref="feature",
                head_sha="head",
            ),
            None,
        )

    async def _review_pr(self, url):
        raise RuntimeError("provider blew up")

    monkeypatch.setattr(module.PRReviewRunner, "fetch_pr_metadata", _metadata)
    monkeypatch.setattr(module.PRReviewRunner, "review_pr", _review_pr)

    result = asyncio.run(
        generate_case_studies(
            manifest_path=manifest,
            out_dir=tmp_path / "out",
            limit=None,
            fixture_only=False,
        )
    )

    packet = json.loads((tmp_path / "out" / "cases" / "case-1.json").read_text(encoding="utf-8"))
    assert result["blocked"] == 1
    assert packet["status"] == "blocked"
    assert "baseline_runtime_failure" in packet["reason"]

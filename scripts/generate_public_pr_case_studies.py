#!/usr/bin/env python3
"""Generate publication-safe public PR case-study packets."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aragora.compat.openclaw.pr_review_runner import PRReviewRunner
from aragora.export.case_study import PublicPRCaseStudyIndex, build_case_study_packet


@dataclass
class ManifestEntry:
    case_id: str
    pr_url: str


def load_manifest(path: Path) -> list[ManifestEntry]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError("manifest missing cases list")

    entries: list[ManifestEntry] = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"manifest case {index} must be an object")
        case_id = case.get("id")
        pr_url = case.get("pr_url")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"manifest case {index} missing id")
        if not isinstance(pr_url, str) or not pr_url:
            raise ValueError(f"manifest case {index} missing pr_url")
        entries.append(ManifestEntry(case_id=case_id, pr_url=pr_url))
    return entries


async def run_case(
    entry: ManifestEntry,
    *,
    baseline_runner: PRReviewRunner,
    adversarial_runner: PRReviewRunner,
    fixture_only: bool,
) -> tuple[dict[str, Any], Path]:
    metadata = None
    if not fixture_only:
        metadata, metadata_error = baseline_runner.fetch_pr_metadata(entry.pr_url)
        if metadata_error:
            packet = build_case_study_packet(
                case_id=entry.case_id,
                metadata=None,
                pr_url=entry.pr_url,
                baseline_result=None,
                adversarial_result=None,
                status="blocked",
                reason=f"metadata_fetch_failed: {metadata_error}",
            )
            return packet.to_dict(), Path(f"{entry.case_id}.json")
    baseline_result = None
    adversarial_result = None
    if not fixture_only:
        try:
            baseline_result = await baseline_runner.review_pr(entry.pr_url)
        except Exception as exc:  # noqa: BLE001 - fail closed into blocked packet
            packet = build_case_study_packet(
                case_id=entry.case_id,
                metadata=metadata,
                pr_url=entry.pr_url,
                baseline_result=None,
                adversarial_result=None,
                status="blocked",
                reason=f"baseline_runtime_failure: {exc}",
            )
            return packet.to_dict(), Path(f"{entry.case_id}.json")
        try:
            adversarial_result = await adversarial_runner.review_pr(entry.pr_url)
        except Exception as exc:  # noqa: BLE001 - fail closed into blocked packet
            packet = build_case_study_packet(
                case_id=entry.case_id,
                metadata=metadata,
                pr_url=entry.pr_url,
                baseline_result=baseline_result,
                adversarial_result=None,
                status="blocked",
                reason=f"adversarial_runtime_failure: {exc}",
            )
            return packet.to_dict(), Path(f"{entry.case_id}.json")

    packet = build_case_study_packet(
        case_id=entry.case_id,
        metadata=metadata,
        pr_url=entry.pr_url,
        baseline_result=baseline_result,
        adversarial_result=adversarial_result,
        fixture_only=fixture_only,
    )
    return packet.to_dict(), Path(f"{entry.case_id}.json")


async def generate_case_studies(
    *,
    manifest_path: Path,
    out_dir: Path,
    limit: int | None,
    fixture_only: bool,
) -> dict[str, Any]:
    entries = load_manifest(manifest_path)
    if limit is not None:
        entries = entries[:limit]

    out_dir.mkdir(parents=True, exist_ok=True)
    cases_dir = out_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    baseline_runner = PRReviewRunner(dry_run=True, gauntlet=False)
    adversarial_runner = PRReviewRunner(dry_run=True, gauntlet=True)

    index_cases: list[dict[str, Any]] = []
    published = 0
    skipped = 0
    blocked = 0

    for entry in entries:
        packet, rel_path = await run_case(
            entry,
            baseline_runner=baseline_runner,
            adversarial_runner=adversarial_runner,
            fixture_only=fixture_only,
        )
        packet_path = cases_dir / rel_path
        packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

        status = packet["status"]
        if status == "published":
            published += 1
        elif status == "skipped":
            skipped += 1
        else:
            blocked += 1

        index_cases.append(
            {
                "case_id": packet["case_id"],
                "pr_url": packet["target"]["pr_url"],
                "status": status,
                "reason": packet["reason"],
                "path": str(Path("cases") / rel_path),
            }
        )

    index = PublicPRCaseStudyIndex(
        generated_at=datetime.now(timezone.utc).isoformat(),
        source_manifest=str(manifest_path),
        total_cases=len(index_cases),
        published=published,
        skipped=skipped,
        blocked=blocked,
        cases=index_cases,
    )
    index_path = out_dir / "index.json"
    index.save(index_path)
    return index.to_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate public PR case-study packets")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to case-study manifest")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of cases")
    parser.add_argument(
        "--fixture-only",
        action="store_true",
        help="Emit deterministic skipped packets without live PR review execution",
    )
    args = parser.parse_args()

    asyncio.run(
        generate_case_studies(
            manifest_path=args.manifest,
            out_dir=args.out,
            limit=args.limit,
            fixture_only=args.fixture_only,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

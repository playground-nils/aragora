"""CLI command: aragora assess — run canonical repository assessment."""

from __future__ import annotations

import asyncio
import json
import sys


def cmd_assess(args) -> None:
    """Run canonical repo assessment."""
    asyncio.run(_run_assessment(args))


async def _run_assessment(args) -> None:
    from aragora.nomic.canonical_assessment import (
        CanonicalAssessmentCompiler,
        compute_delta,
        load_latest_assessment,
        save_assessment,
    )

    compiler = CanonicalAssessmentCompiler()
    assessment = await compiler.compile()

    if getattr(args, "save", False):
        aid = save_assessment(assessment)
        print(f"Saved: {aid}", file=sys.stderr)

    if getattr(args, "diff", False):
        previous = load_latest_assessment()
        if previous and previous.assessment_id != assessment.assessment_id:
            delta = compute_delta(assessment, previous)
            _print_delta(delta)
        elif previous is None:
            print("No previous assessment found for diff.", file=sys.stderr)

    fmt = getattr(args, "format", "text")
    if fmt == "json":
        print(json.dumps(assessment.to_dict(), indent=2, default=str))
    else:
        _print_summary(assessment)


def _print_summary(assessment) -> None:
    """Print a human-readable assessment summary."""
    health = assessment.health_report.get("health_score", "N/A")
    if isinstance(health, float):
        health = f"{health:.2f}"

    print(f"\nCanonical Repo Assessment: {assessment.assessment_id}")
    print("=" * 60)
    print(f"Timestamp:     {assessment.timestamp:.0f}")
    print(f"Health Score:  {health}")

    if assessment.scanner_metrics:
        m = assessment.scanner_metrics
        print(f"Total Modules: {m.get('total_modules', 'N/A')}")
        print(f"Test Files:    {m.get('total_test_files', 'N/A')}")
        print(f"Tested %:      {m.get('tested_pct', 'N/A')}")

    if assessment.feature_inventory:
        by_status: dict[str, int] = {}
        for f in assessment.feature_inventory:
            by_status[f.status] = by_status.get(f.status, 0) + 1
        print(f"\nFeatures ({len(assessment.feature_inventory)}):")
        for status, count in sorted(by_status.items()):
            print(f"  {status}: {count}")

    if assessment.improvement_candidates:
        print(f"\nTop Improvement Candidates ({len(assessment.improvement_candidates)}):")
        for c in assessment.improvement_candidates[:5]:
            desc = c.get("description", "")[:60]
            prio = c.get("priority", 0)
            print(f"  [{prio:.2f}] {desc}")

    if assessment.recurring_findings:
        print(f"\nRecurring Findings: {len(assessment.recurring_findings)}")

    if assessment.metadata.get("commit_sha"):
        sha = assessment.metadata["commit_sha"][:12]
        branch = assessment.metadata.get("branch", "?")
        dirty = " (dirty)" if assessment.metadata.get("dirty") else ""
        print(f"\nGit: {sha} on {branch}{dirty}")

    print()


def _print_delta(delta) -> None:
    """Print delta between two assessments."""
    print(f"\nDelta: {delta.previous_id} -> {delta.current_id}")
    print("-" * 50)
    hours = delta.time_elapsed_seconds / 3600
    print(f"Time elapsed:      {hours:.1f}h")
    sign = "+" if delta.health_score_change >= 0 else ""
    print(f"Health change:     {sign}{delta.health_score_change:.3f}")
    if delta.new_features:
        print(f"New features:      {', '.join(delta.new_features[:5])}")
    if delta.resolved_features:
        print(f"Resolved features: {', '.join(delta.resolved_features[:5])}")
    if delta.status_changes:
        for sc in delta.status_changes[:5]:
            print(f"  {sc['name']}: {sc['old_status']} -> {sc['new_status']}")
    print(f"New findings:      {delta.new_findings}")
    print(f"Resolved findings: {delta.resolved_findings}")
    print()

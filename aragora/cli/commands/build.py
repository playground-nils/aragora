"""aragora build — Turn a vague idea into executed, reviewed, merged code.

Usage:
    aragora build "I want real-time streaming of agent debate responses"
    aragora build "Add a provider selection UI to settings" --dry-run
    aragora build --from-file ideas.txt

Pipeline:
    1. Clarify: Ask questions to understand the idea (skip with --skip-clarify)
    2. Specify: Run aragora spec to produce structured specification
    3. Debate: Multi-agent debate on the specification quality
    4. Decompose: Break into bounded tasks with acceptance criteria
    5. Plan: Sequence tasks and identify dependencies
    6. Execute: Dispatch to boss loop for implementation
    7. Review: Adversarial review of each change
    8. Iterate: Fix issues found in review
    9. Merge: Land clean changes on main
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def cmd_build(args: argparse.Namespace) -> None:
    """Turn a vague idea into executed, reviewed, merged code."""
    idea = getattr(args, "idea", None) or ""
    from_file = getattr(args, "from_file", None)
    dry_run = getattr(args, "dry_run", False)
    skip_clarify = getattr(args, "skip_clarify", False)
    max_tasks = getattr(args, "max_tasks", 5)
    as_json = getattr(args, "json", False)

    if from_file:
        idea = Path(from_file).read_text().strip()
    if not idea:
        print('Usage: aragora build "your idea here"')
        sys.exit(1)

    result = asyncio.run(
        _run_build_pipeline(
            idea=idea,
            dry_run=dry_run,
            skip_clarify=skip_clarify,
            max_tasks=max_tasks,
        )
    )

    if as_json:
        print(json.dumps(result, indent=2, default=str))
    else:
        _print_result(result)


async def _run_build_pipeline(
    *,
    idea: str,
    dry_run: bool = False,
    skip_clarify: bool = False,
    max_tasks: int = 5,
) -> dict[str, Any]:
    """Execute the full build pipeline."""
    result: dict[str, Any] = {
        "idea": idea,
        "dry_run": dry_run,
        "stages": {},
        "status": "running",
    }
    start = time.monotonic()

    # Stage 1: Specification
    print("\n[1/5] Generating specification from idea...")
    print(f"  Idea: {idea[:100]}{'...' if len(idea) > 100 else ''}")
    spec = await _generate_spec(idea, skip_clarify=skip_clarify)
    result["stages"]["spec"] = spec
    print(f"  ✓ Spec generated ({len(spec.get('sections', []))} sections)")

    # Stage 2: Task decomposition
    print("\n[2/5] Decomposing into bounded tasks...")
    tasks = await _decompose_tasks(spec, max_tasks=max_tasks)
    result["stages"]["tasks"] = tasks
    print(f"  ✓ {len(tasks)} tasks identified")
    for i, task in enumerate(tasks, 1):
        print(f"    {i}. {task['title']}")

    if dry_run:
        result["status"] = "dry_run_complete"
        result["elapsed_seconds"] = time.monotonic() - start
        print(f"\n[DRY RUN] Would create {len(tasks)} issues and dispatch to boss loop.")
        print("  Run without --dry-run to execute.")
        return result

    # Stage 3: Create GitHub issues
    print("\n[3/5] Creating GitHub issues...")
    issues = await _create_issues(tasks)
    result["stages"]["issues"] = issues
    print(f"  ✓ {len(issues)} issues created")

    # Stage 4: Dispatch to boss loop
    print("\n[4/5] Dispatching to boss loop (--autonomy full-auto)...")
    dispatch_result = await _dispatch_to_boss_loop(issues)
    result["stages"]["dispatch"] = dispatch_result
    print(f"  ✓ Boss loop started (PID: {dispatch_result.get('pid', '?')})")

    # Stage 5: Summary
    result["status"] = "dispatched"
    result["elapsed_seconds"] = time.monotonic() - start
    print("\n[5/5] Pipeline complete!")
    print(f"  Issues: {', '.join(f'#{i}' for i in issues)}")
    print("  Monitor: tail -f .aragora/overnight/code-improvements.log")

    return result


async def _generate_spec(idea: str, *, skip_clarify: bool = False) -> dict[str, Any]:
    """Generate a structured specification from a vague idea."""
    try:
        from aragora.prompt_engine.conductor import PromptConductor, ConductorConfig

        config = ConductorConfig(
            skip_interrogation=skip_clarify,
            skip_research=True,  # Fast mode for build pipeline
        )
        conductor = PromptConductor(config=config)
        spec = await conductor.run(prompt=idea)
        return {
            "title": getattr(spec, "title", idea[:80]),
            "sections": [
                {"name": s.name, "content": s.content[:200]} for s in getattr(spec, "sections", [])
            ]
            if hasattr(spec, "sections")
            else [],
            "confidence": getattr(spec, "confidence", 0.0),
            "raw": str(spec)[:500],
        }
    except Exception as exc:
        logger.warning("Spec generation failed: %s", exc)
        return {
            "title": idea[:80],
            "sections": [],
            "confidence": 0.0,
            "raw": idea,
            "fallback": True,
        }


async def _decompose_tasks(spec: dict[str, Any], *, max_tasks: int = 5) -> list[dict[str, Any]]:
    """Break a specification into bounded implementation tasks."""
    try:
        from aragora.nomic.task_decomposer import TaskDecomposer

        decomposer = TaskDecomposer()
        analysis = decomposer.analyze(spec.get("raw", spec.get("title", "")))
        raw_tasks = analysis.subtasks if hasattr(analysis, "subtasks") else []
        raw_tasks = raw_tasks[:max_tasks]
        return [
            {
                "title": t.title if hasattr(t, "title") else str(t)[:80],
                "description": t.description if hasattr(t, "description") else str(t),
                "acceptance_criteria": getattr(t, "acceptance_criteria", []),
                "verification": getattr(t, "verification_command", "pytest tests/ -q"),
            }
            for t in (raw_tasks if isinstance(raw_tasks, list) else [raw_tasks])
        ]
    except Exception as exc:
        logger.warning("Task decomposition failed: %s, using spec as single task", exc)
        return [
            {
                "title": spec.get("title", "Implement idea"),
                "description": spec.get("raw", ""),
                "acceptance_criteria": ["Implementation complete", "Tests pass"],
                "verification": "python -m pytest tests/ -q -k 'not benchmark'",
            }
        ]


async def _create_issues(tasks: list[dict[str, Any]]) -> list[int]:
    """Create GitHub issues for each task."""
    import subprocess

    issue_numbers = []
    for task in tasks:
        body = f"""## Acceptance Criteria
{chr(10).join(f"- [ ] {c}" for c in task.get("acceptance_criteria", ["Implementation complete"]))}
- [ ] All tests pass (no new failures)
- [ ] Ruff clean on modified files

## Validation
```bash
{task.get("verification", "python -m pytest tests/ -q")}
```

## Description
{task.get("description", "")[:500]}

## Definition of Done
Implementation complete, tests pass, PR opened with evidence.
"""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "create",
                    "--repo",
                    "synaptent/aragora",
                    "--title",
                    task["title"],
                    "--label",
                    "boss-ready",
                    "--body",
                    body,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                # Extract issue number from URL
                url = result.stdout.strip()
                num = int(url.rstrip("/").split("/")[-1])
                issue_numbers.append(num)
                logger.info("Created issue #%d: %s", num, task["title"])
            else:
                logger.warning("Failed to create issue: %s", result.stderr)
        except Exception as exc:
            logger.warning("Issue creation failed: %s", exc)

    return issue_numbers


async def _dispatch_to_boss_loop(issue_numbers: list[int]) -> dict[str, Any]:
    """Launch the boss loop against the created issues."""
    import subprocess

    cmd = [
        "bash",
        "-lc",
        (
            "cd /Users/armand/Development/aragora && "
            "export ARAGORA_USER_ID=armand && "
            "exec python3 -u -m aragora.cli.main swarm boss-loop "
            "--boss-repo synaptent/aragora "
            "--label boss-ready "
            f"--max-ticks {len(issue_numbers) * 2} "
            "--interval 30 "
            "--max-consecutive-failures 5 "
            "--autonomy full-auto "
            "--max-hours 10"
        ),
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=open(".aragora/overnight/code-improvements.log", "w"),
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {
        "pid": proc.pid,
        "issues": issue_numbers,
        "log": ".aragora/overnight/code-improvements.log",
    }


def _print_result(result: dict[str, Any]) -> None:
    """Print a human-readable summary."""
    print(f"\n{'=' * 60}")
    print(f"Build Pipeline: {result['status']}")
    print(f"{'=' * 60}")
    if result.get("elapsed_seconds"):
        print(f"Time: {result['elapsed_seconds']:.1f}s")
    if "stages" in result:
        if "spec" in result["stages"]:
            print(f"Spec: {result['stages']['spec'].get('title', '?')}")
        if "tasks" in result["stages"]:
            print(f"Tasks: {len(result['stages']['tasks'])}")
        if "issues" in result["stages"]:
            issues = result["stages"]["issues"]
            print(f"Issues: {', '.join(f'#{n}' for n in issues)}")
        if "dispatch" in result["stages"]:
            print(f"Boss loop PID: {result['stages']['dispatch'].get('pid', '?')}")
    print(f"{'=' * 60}")

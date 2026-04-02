"""Micro-task decomposition for worker-friendly issue dispatch.

Claude Code workers in large repos (3000+ modules) succeed on small, focused
tasks but fail on broad ones — they spend all their time reading instead of
writing. This module decomposes broad issues into single-file, single-commit
micro-tasks with explicit instructions.

The key insight: workers need to know EXACTLY what file to edit, EXACTLY what
to change, and EXACTLY what test to run. Vague "analyze and implement" tasks
cause 60-minute timeouts with zero output.

Usage in boss_loop._dispatch_issue():
    spec.work_orders = build_micro_work_orders(
        goal=goal,
        file_scope_hints=scope_hints,
        acceptance_criteria=spec.acceptance_criteria,
        repo_root=Path.cwd(),
    )
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def build_micro_work_orders(
    *,
    goal: str,
    file_scope_hints: list[str],
    acceptance_criteria: list[str] | None = None,
    constraints: list[str] | None = None,
    repo_root: Path | None = None,
) -> list[dict[str, str | list[str] | dict[str, list[str]]]]:
    """Decompose a goal into single-file micro work orders.

    Strategy:
    1. If file_scope_hints contains specific files (with extensions),
       create one work order per file.
    2. If file_scope_hints contains directories, scan for relevant files
       and create one work order per file.
    3. Each work order gets an explicit, focused description that tells
       the worker exactly what to do in that file.
    4. A final work order runs the acceptance test.

    Returns empty list if decomposition isn't possible (caller falls back
    to normal decomposition).
    """
    root = repo_root or Path.cwd()
    if not file_scope_hints:
        return []

    # Resolve file hints to actual files
    resolved_files = _resolve_file_hints(file_scope_hints, root)
    if not resolved_files:
        return []

    # Separate implementation files from test files
    impl_files = [f for f in resolved_files if not _is_test_file(f)]
    test_files = [f for f in resolved_files if _is_test_file(f)]

    if not impl_files and not test_files:
        return []

    work_orders: list[dict] = []
    order_idx = 0

    # Create one work order per implementation file
    for filepath in impl_files[:5]:  # Cap at 5 files to avoid sprawl
        order_idx += 1
        wo = _build_file_work_order(
            index=order_idx,
            filepath=filepath,
            goal=goal,
            constraints=constraints,
            root=root,
        )
        work_orders.append(wo)

    # Create one work order for test files (grouped)
    if test_files:
        order_idx += 1
        test_wo = _build_test_work_order(
            index=order_idx,
            test_files=test_files,
            goal=goal,
            impl_files=impl_files,
            root=root,
        )
        work_orders.append(test_wo)

    # Final validation work order
    if acceptance_criteria:
        order_idx += 1
        validation_wo = _build_validation_work_order(
            index=order_idx,
            acceptance_criteria=acceptance_criteria,
            file_scope=file_scope_hints,
            dependency_ids=[wo["pipeline_task_id"] for wo in work_orders],
        )
        work_orders.append(validation_wo)

    if work_orders:
        logger.info(
            "Micro-decomposed into %d work orders for %d files",
            len(work_orders),
            len(resolved_files),
        )

    return work_orders


def _resolve_file_hints(hints: list[str], root: Path) -> list[str]:
    """Resolve file scope hints to actual file paths."""
    resolved: list[str] = []
    for hint in hints:
        hint = hint.strip().removeprefix("./")
        if not hint:
            continue
        path = root / hint
        if path.is_file():
            resolved.append(hint)
        elif path.is_dir():
            # Scan directory for Python files (limit to avoid explosion)
            for py_file in sorted(path.rglob("*.py"))[:20]:
                rel = str(py_file.relative_to(root))
                if "__pycache__" not in rel and not rel.endswith("__init__.py"):
                    resolved.append(rel)
    return resolved[:15]  # Hard cap


def _is_test_file(filepath: str) -> bool:
    """Check if a file is a test file."""
    name = filepath.rsplit("/", 1)[-1]
    return name.startswith("test_") or "/tests/" in filepath or "/test_" in filepath


def _build_file_work_order(
    *,
    index: int,
    filepath: str,
    goal: str,
    constraints: list[str] | None,
    root: Path,
) -> dict:
    """Build a focused work order for a single implementation file."""
    # Read the file to understand its structure (first 50 lines)
    file_preview = ""
    try:
        full_path = root / filepath
        if full_path.exists():
            lines = full_path.read_text(errors="replace").splitlines()[:50]
            file_preview = "\n".join(lines)
    except OSError:
        pass

    description = (
        f"Make the following change to `{filepath}`:\n\n"
        f"{goal}\n\n"
        f"IMPORTANT: Only modify this ONE file. Do not touch other files.\n"
        f"After making the change, immediately run:\n"
        f"  git add {filepath}\n"
        f"  git commit -m 'fix: update {filepath.rsplit('/', 1)[-1]}'\n"
    )
    if file_preview:
        description += (
            f"\nCurrent file structure (first 50 lines):\n```python\n{file_preview}\n```\n"
        )

    constraint_list = list(constraints or [])
    constraint_list.append(f"Only modify {filepath}")
    constraint_list.append("Commit immediately after making changes")

    return {
        "work_order_id": f"micro-{index}",
        "pipeline_task_id": f"micro-task-{index}",
        "title": f"Update {filepath.rsplit('/', 1)[-1]}",
        "description": description,
        "file_scope": [filepath],
        "target_agent": "claude",
        "estimated_complexity": "low",
        "approval_required": True,
        "metadata": {
            "source": "micro_decomposer",
            "constraints": constraint_list,
        },
    }


def _build_test_work_order(
    *,
    index: int,
    test_files: list[str],
    goal: str,
    impl_files: list[str],
    root: Path,
) -> dict:
    """Build a work order for creating/updating test files."""
    impl_names = ", ".join(f"`{f}`" for f in impl_files[:3])
    test_names = ", ".join(f"`{f}`" for f in test_files[:3])

    description = (
        f"Write or update tests in {test_names} for the changes made to {impl_names}.\n\n"
        f"Goal: {goal}\n\n"
        f"IMPORTANT: Only create/modify test files. Do not modify implementation files.\n"
        f"After writing tests, run:\n"
        f"  git add {' '.join(test_files[:3])}\n"
        f"  git commit -m 'test: add tests for {impl_files[0].rsplit('/', 1)[-1] if impl_files else 'changes'}'\n"
    )

    return {
        "work_order_id": f"micro-{index}",
        "pipeline_task_id": f"micro-task-{index}",
        "title": f"Write tests for {impl_files[0].rsplit('/', 1)[-1] if impl_files else 'changes'}",
        "description": description,
        "file_scope": test_files[:5],
        "target_agent": "claude",
        "estimated_complexity": "low",
        "approval_required": True,
        "dependency_ids": [f"micro-task-{i}" for i in range(1, index)],
        "metadata": {"source": "micro_decomposer"},
    }


def _build_validation_work_order(
    *,
    index: int,
    acceptance_criteria: list[str],
    file_scope: list[str],
    dependency_ids: list[str],
) -> dict:
    """Build a validation-only work order that runs acceptance tests."""
    criteria_text = "\n".join(f"  - {c}" for c in acceptance_criteria)

    return {
        "work_order_id": f"micro-{index}",
        "pipeline_task_id": f"micro-task-{index}",
        "title": "Run validation and fix failures",
        "description": (
            f"Run the following acceptance tests and fix any failures:\n\n"
            f"{criteria_text}\n\n"
            f"If tests fail, fix the issues and commit the fixes.\n"
            f"If tests pass, commit a no-op marker:\n"
            f"  git commit --allow-empty -m 'test: validation passed'\n"
        ),
        "file_scope": file_scope,
        "target_agent": "claude",
        "estimated_complexity": "low",
        "approval_required": True,
        "dependency_ids": dependency_ids,
        "metadata": {"source": "micro_decomposer"},
    }

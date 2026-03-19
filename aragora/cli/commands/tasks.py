"""CLI command for developer task queue management.

Usage::

    aragora tasks list [--status pending] [--format table|json]
    aragora tasks show <task_id>
    aragora tasks claim <task_id> [--worker <id>] [--ttl 8]
    aragora tasks release <task_id>
    aragora tasks complete <task_id>
    aragora tasks leases [--format table|json]
    aragora tasks salvage [--format table|json]
    aragora tasks stats
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import logging
import platform
import sys

logger = logging.getLogger(__name__)


def _resolve(result):
    """Resolve a potentially-async result to a sync value."""
    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


def add_tasks_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``tasks`` subcommand with its sub-subcommands."""
    parser = subparsers.add_parser(
        "tasks",
        help="Developer task queue: list, claim, release, complete work items",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="tasks_command")

    # --- list ---
    list_p = sub.add_parser("list", help="List queued work items")
    list_p.add_argument(
        "--status",
        choices=[
            "pending",
            "ready",
            "claimed",
            "in_progress",
            "completed",
            "failed",
            "blocked",
        ],
    )
    list_p.add_argument(
        "--format",
        dest="output_format",
        choices=["table", "json"],
        default="table",
    )
    list_p.add_argument("--limit", type=int, default=20)

    # --- show ---
    show_p = sub.add_parser("show", help="Show task details")
    show_p.add_argument("task_id")
    show_p.add_argument(
        "--format",
        dest="output_format",
        choices=["table", "json"],
        default="table",
    )

    # --- claim ---
    claim_p = sub.add_parser("claim", help="Claim a task")
    claim_p.add_argument("task_id")
    claim_p.add_argument("--worker", default=None, help="Worker identifier")
    claim_p.add_argument("--ttl", type=float, default=8.0, help="Lease TTL in hours")

    # --- release ---
    release_p = sub.add_parser("release", help="Release a claimed task")
    release_p.add_argument("task_id")

    # --- complete ---
    complete_p = sub.add_parser("complete", help="Mark task complete")
    complete_p.add_argument("task_id")

    # --- leases ---
    leases_p = sub.add_parser("leases", help="List active leases")
    leases_p.add_argument(
        "--format",
        dest="output_format",
        choices=["table", "json"],
        default="table",
    )

    # --- salvage ---
    salvage_p = sub.add_parser("salvage", help="List salvage candidates")
    salvage_p.add_argument(
        "--format",
        dest="output_format",
        choices=["table", "json"],
        default="table",
    )

    # --- stats ---
    sub.add_parser("stats", help="Show queue statistics")

    parser.set_defaults(func=cmd_tasks)


def cmd_tasks(args: argparse.Namespace) -> None:
    """Dispatch to the appropriate tasks subcommand."""
    command = getattr(args, "tasks_command", None)
    if not command:
        print(
            "Usage: aragora tasks {list|show|claim|release|complete|leases|salvage|stats}",
            file=sys.stderr,
        )
        sys.exit(1)

    dispatch = {
        "list": _cmd_list,
        "show": _cmd_show,
        "claim": _cmd_claim,
        "release": _cmd_release,
        "complete": _cmd_complete,
        "leases": _cmd_leases,
        "salvage": _cmd_salvage,
        "stats": _cmd_stats,
    }
    handler = dispatch.get(command)
    if handler is None:
        print(f"Unknown tasks subcommand: {command}", file=sys.stderr)
        sys.exit(1)
    handler(args)


# ------------------------------------------------------------------
# Subcommand implementations
# ------------------------------------------------------------------


def _cmd_list(args: argparse.Namespace) -> None:
    from aragora.nomic.global_work_queue import GlobalWorkQueue

    queue = GlobalWorkQueue()
    items = _resolve(
        queue.list_items(
            status=getattr(args, "status", None),
            work_type=None,
            limit=getattr(args, "limit", 20),
        )
    )
    fmt = getattr(args, "output_format", "table")
    if fmt == "json":
        serialized = [i.to_dict() if hasattr(i, "to_dict") else i for i in items]
        print(json.dumps(serialized, indent=2, default=str))
    else:
        print(f"{'ID':15s} {'Status':12s} {'Pri':>4s} Title")
        print("-" * 60)
        for item in items:
            item_d = item.to_dict() if hasattr(item, "to_dict") else item
            print(
                f"  {str(item_d.get('id', ''))[:13]:13s} "
                f"{str(item_d.get('status', ''))[:10]:10s} "
                f"P{item_d.get('computed_priority', item_d.get('base_priority', 0)):>3d} "
                f"{str(item_d.get('title', ''))[:40]}"
            )


def _cmd_show(args: argparse.Namespace) -> None:
    from aragora.nomic.global_work_queue import GlobalWorkQueue

    queue = GlobalWorkQueue()
    item = _resolve(queue.get(args.task_id))
    if item is None:
        print(f"Task {args.task_id} not found", file=sys.stderr)
        sys.exit(1)
    serialized = item.to_dict() if hasattr(item, "to_dict") else item
    print(json.dumps(serialized, indent=2, default=str))


def _cmd_claim(args: argparse.Namespace) -> None:
    import os

    from aragora.nomic.dev_coordination import DevCoordinationStore

    store = DevCoordinationStore()
    worker_id = args.worker or f"{platform.node()}-{os.getpid()}"
    lease = store.claim_lease(
        task_id=args.task_id,
        title=f"CLI claim for {args.task_id}",
        owner_agent=worker_id,
        owner_session_id="",
        branch="",
        worktree_path="",
        ttl_hours=args.ttl,
    )
    print(
        f"Claimed: lease_id={lease.lease_id} "
        f"owner_agent={lease.owner_agent} "
        f"expires={lease.expires_at}"
    )


def _cmd_release(args: argparse.Namespace) -> None:
    from aragora.nomic.dev_coordination import DevCoordinationStore

    store = DevCoordinationStore()
    lease = store.release_lease(args.task_id)
    print(f"Released: lease_id={lease.lease_id}")


def _cmd_complete(args: argparse.Namespace) -> None:
    from aragora.nomic.dev_coordination import DevCoordinationStore

    store = DevCoordinationStore()
    receipt = store.record_completion(
        lease_id=args.task_id,
        owner_agent="cli",
        owner_session_id="",
        branch="",
        worktree_path="",
        commit_shas=[],
        changed_paths=[],
        tests_run=[],
        assumptions=[],
        blockers=[],
        confidence=1.0,
    )
    print(f"Completed: receipt_id={receipt.receipt_id}")


def _cmd_leases(args: argparse.Namespace) -> None:
    from aragora.nomic.dev_coordination import DevCoordinationStore

    store = DevCoordinationStore()
    leases = store.list_active_leases()
    fmt = getattr(args, "output_format", "table")
    if fmt == "json":
        print(
            json.dumps(
                [
                    {
                        "lease_id": lease.lease_id,
                        "task_id": lease.task_id,
                        "owner_agent": lease.owner_agent,
                        "expires_at": lease.expires_at,
                    }
                    for lease in leases
                ],
                indent=2,
            )
        )
    else:
        print(f"{'Lease ID':20s} {'Agent':15s} {'Task':15s} Expires")
        print("-" * 70)
        for lease in leases:
            print(
                f"  {str(lease.lease_id)[:18]:18s} "
                f"{str(lease.owner_agent)[:13]:13s} "
                f"{str(lease.task_id)[:13]:13s} "
                f"{lease.expires_at}"
            )


def _cmd_salvage(args: argparse.Namespace) -> None:
    from aragora.nomic.dev_coordination import DevCoordinationStore

    store = DevCoordinationStore()
    candidates = store.list_salvage_candidates()
    fmt = getattr(args, "output_format", "table")
    if fmt == "json":
        print(
            json.dumps(
                [c.to_dict() for c in candidates],
                indent=2,
                default=str,
            )
        )
    else:
        print(f"{'Candidate ID':20s} {'Source':15s} Summary")
        print("-" * 60)
        for c in candidates:
            print(
                f"  {str(c.candidate_id)[:18]:18s} {str(c.source_kind)[:13]:13s} {c.summary[:40]}"
            )


def _cmd_stats(args: argparse.Namespace) -> None:
    from aragora.nomic.global_work_queue import GlobalWorkQueue

    queue = GlobalWorkQueue()
    stats = _resolve(queue.get_statistics())
    print(json.dumps(stats, indent=2, default=str))

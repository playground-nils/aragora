#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aragora.swarm.agent_bridge import AgentBridgeBroker
from aragora.swarm.agent_bridge import BridgeSession
from aragora.swarm.agent_bridge import HarnessKind


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _parse_agent_spec(raw: str) -> BridgeSession:
    # format: name=harness[:model]
    if "=" not in raw:
        raise ValueError(f"Invalid agent spec '{raw}'. Use name=harness[:model]")
    name, remainder = raw.split("=", 1)
    harness_value, _, model = remainder.partition(":")
    name = name.strip()
    harness_value = harness_value.strip()
    if not name or not harness_value:
        raise ValueError(f"Invalid agent spec '{raw}'. Use name=harness[:model]")
    return BridgeSession(
        name=name,
        harness=HarnessKind(harness_value),
        role=name,
        model=model.strip() or None,
    )


def _load_sessions(args: argparse.Namespace) -> list[BridgeSession]:
    if args.agents_file:
        payload = json.loads(Path(args.agents_file).read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("agents file must contain a JSON array")
        return [BridgeSession.from_dict(item) for item in payload if isinstance(item, dict)]
    if not args.agent:
        raise ValueError("Provide at least one --agent or --agents-file")
    return [_parse_agent_spec(item) for item in args.agent]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CLI-resume broker for heterogeneous agent sessions"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-run", help="Create a new bridge run")
    create.add_argument("--task", required=True)
    create.add_argument("--base", default="main")
    create.add_argument("--agent", action="append")
    create.add_argument("--agents-file")

    send = sub.add_parser("dispatch-turn", help="Dispatch a turn to one actor in an existing run")
    send.add_argument("--run-id", required=True)
    send.add_argument("--actor", required=True)
    prompt_group = send.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt")
    prompt_group.add_argument("--prompt-file")

    show = sub.add_parser("show-run", help="Show run detail with sessions")
    show.add_argument("--run-id", required=True)

    events = sub.add_parser("show-events", help="Show run events")
    events.add_argument("--run-id", required=True)
    events.add_argument("--limit", type=int, default=100)

    list_runs = sub.add_parser("list-runs", help="List bridge runs")
    list_runs.add_argument("--limit", type=int, default=50)

    sub.add_parser("healthcheck", help="Check installed harness CLIs")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    broker = AgentBridgeBroker(_repo_root())

    if args.command == "create-run":
        sessions = _load_sessions(args)
        run = broker.create_run(task=args.task, sessions=sessions, base_branch=args.base)
        _print_json(
            {
                "run": run.to_dict(),
                "sessions": [session.to_dict() for session in sessions],
            }
        )
        return 0

    if args.command == "dispatch-turn":
        prompt = args.prompt
        if args.prompt_file:
            prompt = Path(args.prompt_file).read_text(encoding="utf-8")
        if prompt is None:
            raise ValueError("prompt is required")
        result = broker.dispatch_turn(run_id=args.run_id, actor=args.actor, prompt=prompt)
        _print_json(result.to_dict())
        return 0

    if args.command == "show-run":
        run = broker.load_run(args.run_id)
        sessions = broker.load_sessions(args.run_id)
        _print_json({"run": run.to_dict(), "sessions": [session.to_dict() for session in sessions]})
        return 0

    if args.command == "show-events":
        _print_json({"events": broker.load_events(args.run_id, limit=args.limit)})
        return 0

    if args.command == "list-runs":
        _print_json({"runs": [run.to_dict() for run in broker.list_runs(limit=args.limit)]})
        return 0

    if args.command == "healthcheck":
        _print_json({"health": broker.healthcheck()})
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Print a JSON receipt for tmux prompt dispatch."""

from __future__ import annotations

import argparse
import json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dispatch", required=True, choices=("dry-run", "ok"))
    parser.add_argument("--name", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--prompt-id", required=True)
    parser.add_argument("--timestamp", required=True)
    parser.add_argument("--chars", required=True, type=int)
    parser.add_argument("--lines", required=True, type=int)
    parser.add_argument("--source", default="")
    parser.add_argument("--source-kind", required=True)
    parser.add_argument("--prompt-file", default="")
    parser.add_argument("--dispatch-method", default="")
    parser.add_argument("--audit-log", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = {
        "dispatch": args.dispatch,
        "name": args.name,
        "target": args.target,
        "prompt_id": args.prompt_id,
        "timestamp": args.timestamp,
        "chars": args.chars,
        "lines": args.lines,
        "source": args.source or None,
        "source_kind": args.source_kind,
        "prompt_file": args.prompt_file or None,
    }
    if args.dispatch_method:
        payload["dispatch_method"] = args.dispatch_method
    if args.audit_log:
        payload["audit_log"] = args.audit_log
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

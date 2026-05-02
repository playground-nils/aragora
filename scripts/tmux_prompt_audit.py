#!/usr/bin/env python3
"""Append a prompt dispatch audit record for tmux session launchers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-log", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--prompt-id", required=True)
    parser.add_argument("--timestamp", required=True)
    parser.add_argument("--chars", required=True, type=int)
    parser.add_argument("--lines", required=True, type=int)
    parser.add_argument("--source", default="")
    parser.add_argument("--source-kind", required=True)
    parser.add_argument("--prompt-file", default="")
    parser.add_argument("--dispatch-method", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--preview", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    record = {
        "prompt_id": args.prompt_id,
        "timestamp": args.timestamp,
        "name": args.name,
        "target": args.target,
        "chars": args.chars,
        "lines": args.lines,
        "source": args.source or None,
        "source_kind": args.source_kind,
        "prompt_file": args.prompt_file or None,
        "dispatch_method": args.dispatch_method,
        "preview": args.preview,
    }
    audit_log = Path(args.audit_log)
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    with audit_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

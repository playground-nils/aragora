#!/usr/bin/env python3
"""Write tmux launcher metadata and update the session mux registry."""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
from pathlib import Path
import sys


def _started_at() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _load_session_mux(repo_root: Path):
    module_path = repo_root / "aragora" / "swarm" / "session_mux.py"
    spec = importlib.util.spec_from_file_location("aragora_swarm_session_mux", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load session_mux module from {module_path}")
    session_mux = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = session_mux
    spec.loader.exec_module(session_mux)
    return session_mux


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--log-file", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--prompt-file", default="")
    parser.add_argument("--meta-file", required=True)
    parser.add_argument("--has-prompt", default="")
    parser.add_argument("--window-target", required=True)
    parser.add_argument("--tmux-session", required=True)
    parser.add_argument("--pane-index", default="0")
    parser.add_argument("--launch-command", required=True)
    parser.add_argument("--registry-repo-root", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root)
    started_at = _started_at()
    meta = {
        "name": args.name,
        "agent": args.agent,
        "started": started_at,
        "log_file": args.log_file,
        "repo_root": args.repo_root,
        "cwd": args.workdir,
        "worktree": args.workdir,
        "tmux_session": args.tmux_session,
        "tmux_window_target": args.window_target,
        "tmux_pane_index": args.pane_index,
        "prompt_file": args.prompt_file or None,
        "has_prompt": bool(args.has_prompt),
    }
    Path(args.meta_file).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    try:
        session_mux = _load_session_mux(repo_root)
        record = session_mux.SessionRecord(
            name=args.name,
            tmux_session=args.tmux_session,
            tmux_window=args.window_target,
            tmux_pane=args.pane_index or "0",
            launcher_command=args.launch_command,
            started_at=started_at,
            log_path=args.log_file,
            meta_path=args.meta_file,
        )
        session_mux.SessionMuxRegistry(Path(args.registry_repo_root)).upsert(record)
    except (
        Exception
    ) as exc:  # pragma: no cover - launcher should still succeed if registry sync fails
        print(f"warning: failed to register launcher session: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Small metadata helpers for tmux transport scripts."""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path


def _write_prompt_audit(argv: list[str]) -> int:
    (
        audit_log,
        name,
        prompt_id,
        timestamp,
        chars,
        lines,
        source_tag,
        source_kind,
        prompt_file,
        method,
        target,
        preview,
    ) = argv
    record = {
        "prompt_id": prompt_id,
        "timestamp": timestamp,
        "name": name,
        "target": target,
        "chars": int(chars),
        "lines": int(lines),
        "source": source_tag or None,
        "source_kind": source_kind,
        "prompt_file": prompt_file or None,
        "dispatch_method": method,
        "preview": preview,
    }
    with open(audit_log, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    return 0


def _write_session_meta(argv: list[str]) -> int:
    (
        name,
        agent,
        log_file,
        repo_root,
        workdir,
        prompt_file,
        meta_file,
        has_prompt,
        window_target,
        tmux_session,
        pane_index,
        launch_cmd,
        registry_repo_root,
    ) = argv
    started_at = (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    meta = {
        "name": name,
        "agent": agent,
        "started": started_at,
        "log_file": log_file,
        "repo_root": repo_root,
        "cwd": workdir,
        "worktree": workdir,
        "tmux_session": tmux_session,
        "tmux_window_target": window_target,
        "tmux_pane_index": pane_index,
        "prompt_file": prompt_file or None,
        "has_prompt": bool(has_prompt),
    }
    Path(meta_file).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    try:
        registry_path = Path(registry_repo_root) / ".aragora" / "session_mux" / "registry.json"
        if registry_path.exists():
            payload = json.loads(registry_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                payload = {}
        else:
            payload = {}
        payload.setdefault("schema_version", 1)
        sessions = payload.setdefault("sessions", {})
        if not isinstance(sessions, dict):
            sessions = {}
            payload["sessions"] = sessions
        sessions[name] = {
            "name": name,
            "tmux_session": tmux_session,
            "tmux_window": window_target,
            "tmux_pane": pane_index or "0",
            "launcher_command": launch_cmd,
            "started_at": started_at,
            "last_prompt_at": None,
            "last_prompt_id": None,
            "worktree_path": None,
            "branch": None,
            "log_path": log_file,
            "launcher_log_path": None,
            "meta_path": meta_file,
        }
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:  # pragma: no cover
        print(f"warning: failed to register launcher session: {exc}", file=sys.stderr)
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: tmux_launcher_metadata.py <prompt-audit|session-meta> ...", file=sys.stderr)
        return 2
    command = argv[1]
    rest = argv[2:]
    if command == "prompt-audit":
        if len(rest) != 12:
            print(f"prompt-audit expected 12 args, got {len(rest)}", file=sys.stderr)
            return 2
        return _write_prompt_audit(rest)
    if command == "session-meta":
        if len(rest) != 13:
            print(f"session-meta expected 13 args, got {len(rest)}", file=sys.stderr)
            return 2
        return _write_session_meta(rest)
    print(f"unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

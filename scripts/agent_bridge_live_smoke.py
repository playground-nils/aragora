#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aragora.swarm.agent_bridge.transport import ClaudeTransport
from aragora.swarm.agent_bridge.transport import CodexTransport
from aragora.swarm.agent_bridge.transport import DroidTransport
from aragora.swarm.agent_bridge.types import BridgeSession
from aragora.swarm.agent_bridge.types import HarnessKind
from aragora.swarm.agent_bridge.types import utc_now_iso


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Live smoke test for the CLI-resume agent bridge")
    parser.add_argument(
        "--repo", default=str(Path.cwd()), help="Repository root to use for artifacts"
    )
    parser.add_argument("--codex-model", default=None)
    parser.add_argument("--claude-model", default=None)
    parser.add_argument("--droid-model", default=None)
    parser.add_argument(
        "--artifact-dir",
        default=None,
        help="Optional artifact directory (defaults to .aragora/agent_bridge/live_smoke)",
    )
    return parser


def _require(binary: str) -> None:
    if shutil.which(binary):
        return
    raise SystemExit(f"Required binary not found on PATH: {binary}")


def _ensure_artifact_dir(repo_root: Path, override: str | None) -> Path:
    path = (
        Path(override).resolve()
        if override
        else repo_root / ".aragora" / "agent_bridge" / "live_smoke"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def _assert_contains(label: str, text: str, token: str) -> None:
    if token not in text:
        raise SystemExit(f"{label} did not preserve token {token!r}. Response: {text!r}")


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(args.repo).resolve()
    artifact_dir = _ensure_artifact_dir(repo_root, args.artifact_dir)

    _require("codex")
    _require("claude")
    _require("droid")

    with tempfile.TemporaryDirectory(prefix="agent-bridge-live-smoke-") as temp_dir:
        worktree = Path(temp_dir)
        shared_token = f"shared-{uuid.uuid4().hex[:10]}"
        codex_token = f"codex-{uuid.uuid4().hex[:8]}"
        droid_token = f"droid-{uuid.uuid4().hex[:8]}"
        claude_token = f"claude-{uuid.uuid4().hex[:8]}"

        codex_session = BridgeSession(
            name="codex-live-smoke",
            harness=HarnessKind.CODEX,
            worktree_path=str(worktree),
            model=args.codex_model,
        )
        droid_session = BridgeSession(
            name="droid-live-smoke",
            harness=HarnessKind.DROID,
            worktree_path=str(worktree),
            model=args.droid_model,
        )
        claude_session = BridgeSession(
            name="claude-live-smoke",
            harness=HarnessKind.CLAUDE,
            worktree_path=str(worktree),
            model=args.claude_model,
        )

        codex = CodexTransport()
        droid = DroidTransport()
        claude = ClaudeTransport()

        codex_first = codex.start_session(
            codex_session,
            f"Remember this token for the next turn: {codex_token}. Reply with exactly READY.",
        )
        codex_session.session_id = codex_first.session_id
        codex_second = codex.resume_turn(
            codex_session,
            "What token did I ask you to remember? Reply with the token only.",
        )
        _assert_contains("codex", codex_second.response_text, codex_token)

        droid_first = droid.start_session(
            droid_session,
            f"Remember this token for the next turn: {droid_token}. Reply with exactly READY.",
        )
        droid_session.session_id = droid_first.session_id
        droid_second = droid.resume_turn(
            droid_session,
            "What token did I ask you to remember? Reply with the token only.",
        )
        _assert_contains("droid", droid_second.response_text, droid_token)

        claude_first = claude.start_session(
            claude_session,
            f"Remember this token for the next turn: {claude_token}. Reply with exactly READY.",
        )
        claude_session.session_id = claude_first.session_id
        claude_second = claude.resume_turn(
            claude_session,
            "What token did I ask you to remember? Reply with the token only.",
        )
        _assert_contains("claude", claude_second.response_text, claude_token)

        codex_handoff = codex.resume_turn(
            codex_session,
            f"Create a handoff sentence containing the shared token {shared_token}. Reply in one sentence.",
        )
        droid_handoff = droid.resume_turn(
            droid_session,
            (
                "A peer agent handed you this sentence:\n"
                f"{codex_handoff.response_text}\n\n"
                f"Repeat the shared token {shared_token} exactly once in your response."
            ),
        )
        _assert_contains("droid handoff", droid_handoff.response_text, shared_token)
        claude_handoff = claude.resume_turn(
            claude_session,
            (
                "Two peer agents are coordinating on a shared token.\n"
                f"Codex said: {codex_handoff.response_text}\n"
                f"Droid said: {droid_handoff.response_text}\n\n"
                f"Confirm the shared token {shared_token} exactly once in your response."
            ),
        )
        _assert_contains("claude handoff", claude_handoff.response_text, shared_token)

        artifact = {
            "timestamp": utc_now_iso(),
            "repo_root": str(repo_root),
            "worktree": str(worktree),
            "shared_token": shared_token,
            "sessions": {
                "codex": codex_session.to_dict(),
                "droid": droid_session.to_dict(),
                "claude": claude_session.to_dict(),
            },
            "results": {
                "codex_recall": codex_second.to_dict(),
                "droid_recall": droid_second.to_dict(),
                "claude_recall": claude_second.to_dict(),
                "codex_handoff": codex_handoff.to_dict(),
                "droid_handoff": droid_handoff.to_dict(),
                "claude_handoff": claude_handoff.to_dict(),
            },
        }
        artifact_path = artifact_dir / f"live-smoke-{uuid.uuid4().hex[:12]}.json"
        artifact_path.write_text(
            json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(
            json.dumps({"ok": True, "artifact_path": str(artifact_path)}, indent=2, sort_keys=True)
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

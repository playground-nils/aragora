from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from aragora.swarm.agent_bridge.footer import build_footer_repair_prompt
from aragora.swarm.agent_bridge.footer import extract_footer
from aragora.swarm.agent_bridge.footer import footer_instructions
from aragora.swarm.agent_bridge.store import BridgeStore
from aragora.swarm.agent_bridge.transport import BridgeTransportError
from aragora.swarm.agent_bridge.transport import transport_for
from aragora.swarm.agent_bridge.types import BridgeRun
from aragora.swarm.agent_bridge.types import BridgeRunStatus
from aragora.swarm.agent_bridge.types import BridgeSession
from aragora.swarm.agent_bridge.types import BridgeTurnResult
from aragora.swarm.agent_bridge.types import HarnessKind
from aragora.swarm.agent_bridge.types import utc_now_iso


class AgentBridgeBroker:
    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        self.store = BridgeStore(self.repo_root)

    def create_run(
        self,
        *,
        task: str,
        sessions: list[BridgeSession],
        base_branch: str = "main",
        run_id: str | None = None,
    ) -> BridgeRun:
        normalized_run_id = run_id or uuid.uuid4().hex[:12]
        run = BridgeRun(
            run_id=normalized_run_id,
            task=task.strip(),
            repo_root=str(self.repo_root),
            base_branch=base_branch,
        )
        self.store.save_run(run)
        self.store.save_sessions(normalized_run_id, sessions)
        self.store.append_event(
            normalized_run_id,
            "run_created",
            task=run.task,
            base_branch=base_branch,
            sessions=[session.to_dict() for session in sessions],
        )
        return run

    def list_runs(self, *, limit: int | None = None) -> list[BridgeRun]:
        return self.store.list_runs(limit=limit)

    def load_run(self, run_id: str) -> BridgeRun:
        return self.store.load_run(run_id)

    def load_sessions(self, run_id: str) -> list[BridgeSession]:
        return self.store.load_sessions(run_id)

    def load_events(self, run_id: str, *, limit: int | None = None) -> list[dict]:
        return self.store.load_events(run_id, limit=limit)

    def dispatch_turn(self, *, run_id: str, actor: str, prompt: str) -> BridgeTurnResult:
        run = self.store.load_run(run_id)
        sessions = self.store.load_sessions(run_id)
        session = next((item for item in sessions if item.name == actor), None)
        if session is None:
            raise KeyError(f"Unknown actor '{actor}' for run {run_id}")

        self._ensure_worktree(session=session, base_branch=run.base_branch)
        transport = transport_for(session)
        prompt_text = f"{prompt.rstrip()}\n\n{footer_instructions()}"

        self.store.append_event(
            run_id,
            "turn_started",
            actor=actor,
            session_id=session.session_id,
            worktree_path=session.worktree_path,
            branch=session.branch,
        )

        result = (
            transport.resume_turn(session, prompt_text)
            if session.session_id
            else transport.start_session(session, prompt_text)
        )
        session.session_id = result.session_id
        session.turn_count += 1
        session.updated_at = utc_now_iso()

        footer, response_body = extract_footer(result.response_text)
        if footer is None:
            self.store.append_event(
                run_id,
                "footer_repair_requested",
                actor=actor,
                session_id=session.session_id,
            )
            repair = transport.resume_turn(
                session, build_footer_repair_prompt(result.response_text)
            )
            footer, _ = extract_footer(repair.response_text)
            repair_artifact = self.store.write_turn_artifact(
                run_id,
                turn_index=session.turn_count,
                actor=f"{actor}-repair",
                payload={
                    "actor": actor,
                    "repair": True,
                    "session_id": session.session_id,
                    "stdout": repair.raw_stdout,
                    "stderr": repair.raw_stderr,
                    "response_text": repair.response_text,
                },
            )
            self.store.append_event(
                run_id,
                "footer_repair_completed",
                actor=actor,
                session_id=session.session_id,
                artifact_path=str(repair_artifact),
                repaired=footer is not None,
            )
            if footer is None:
                self._save_sessions(run_id, sessions)
                run.status = BridgeRunStatus.FAILED
                run.updated_at = utc_now_iso()
                self.store.save_run(run)
                self.store.append_event(
                    run_id,
                    "turn_failed",
                    actor=actor,
                    reason="footer_missing_after_repair",
                )
                raise BridgeTransportError(
                    f"Agent '{actor}' did not return a valid bridge footer after repair"
                )

        result.footer = footer
        result.response_text = response_body
        artifact = self.store.write_turn_artifact(
            run_id,
            turn_index=session.turn_count,
            actor=actor,
            payload={
                "actor": actor,
                "session": session.to_dict(),
                "result": result.to_dict(),
            },
        )

        run.last_summary = footer.summary
        run.active_actor = footer.next_actor
        run.updated_at = utc_now_iso()
        if footer.done:
            run.status = BridgeRunStatus.COMPLETED
        elif footer.needs_human:
            run.status = BridgeRunStatus.WAITING_HUMAN
        else:
            run.status = BridgeRunStatus.RUNNING
        self.store.save_run(run)
        self._save_sessions(run_id, sessions)
        self.store.append_event(
            run_id,
            "turn_completed",
            actor=actor,
            session_id=session.session_id,
            artifact_path=str(artifact),
            footer=footer.to_dict(),
            active_actor=run.active_actor,
            run_status=run.status.value,
        )
        return result

    def healthcheck(self) -> dict[str, bool]:
        return {
            "claude": transport_for(
                BridgeSession(name="claude", harness=HarnessKind.CLAUDE)
            ).healthcheck(),
            "codex": transport_for(
                BridgeSession(name="codex", harness=HarnessKind.CODEX)
            ).healthcheck(),
            "droid": transport_for(
                BridgeSession(name="droid", harness=HarnessKind.DROID)
            ).healthcheck(),
        }

    def _save_sessions(self, run_id: str, sessions: list[BridgeSession]) -> None:
        self.store.save_sessions(run_id, sessions)

    def _ensure_worktree(self, *, session: BridgeSession, base_branch: str) -> None:
        if session.worktree_path and Path(session.worktree_path).exists():
            if not session.branch:
                session.branch = self._git_branch(Path(session.worktree_path))
            return

        cmd = [
            "python3",
            str(self.repo_root / "scripts" / "codex_worktree_autopilot.py"),
            "--repo",
            str(self.repo_root),
            "--managed-dir",
            ".worktrees/agent-bridge",
            "ensure",
            "--agent",
            session.name,
            "--base",
            base_branch,
            "--print-path",
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            cwd=self.repo_root,
        )
        if proc.returncode != 0:
            detail = proc.stderr.strip() or proc.stdout.strip() or "worktree ensure failed"
            raise RuntimeError(detail)
        worktree_path = proc.stdout.strip()
        if not worktree_path:
            raise RuntimeError("worktree ensure did not return a path")
        session.worktree_path = worktree_path
        session.branch = self._git_branch(Path(worktree_path))
        session.updated_at = utc_now_iso()

    def _git_branch(self, worktree: Path) -> str | None:
        proc = subprocess.run(
            ["git", "-C", str(worktree), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if proc.returncode != 0:
            return None
        branch = proc.stdout.strip()
        return branch or None


def default_sessions() -> list[BridgeSession]:
    return [
        BridgeSession(name="codex", harness=HarnessKind.CODEX),
        BridgeSession(name="claude", harness=HarnessKind.CLAUDE),
        BridgeSession(name="droid", harness=HarnessKind.DROID),
    ]

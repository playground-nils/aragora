from __future__ import annotations

import json
import subprocess
import tempfile
import uuid
from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Any

from aragora.swarm.agent_bridge.types import BridgeSession
from aragora.swarm.agent_bridge.types import BridgeTurnResult
from aragora.swarm.agent_bridge.types import HarnessKind


class BridgeTransportError(RuntimeError):
    pass


class MissingSessionIdentityError(BridgeTransportError):
    pass


class BaseTransport(ABC):
    binary_name: str

    def healthcheck(self) -> bool:
        result = subprocess.run(
            [self.binary_name, "--help"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return result.returncode == 0

    def _run(self, cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
                cwd=cwd,
            )
        except subprocess.TimeoutExpired as exc:  # pragma: no cover - exercised via live smoke
            raise BridgeTransportError(f"{self.binary_name} timed out: {exc}") from exc

    @abstractmethod
    def start_session(self, session: BridgeSession, prompt: str) -> BridgeTurnResult:
        raise NotImplementedError

    @abstractmethod
    def resume_turn(self, session: BridgeSession, prompt: str) -> BridgeTurnResult:
        raise NotImplementedError


class ClaudeTransport(BaseTransport):
    binary_name = "claude"

    def _build_cmd(
        self,
        session: BridgeSession,
        prompt: str,
        *,
        resume: bool,
    ) -> list[str]:
        cmd = [self.binary_name, "-p", prompt, "--output-format", "json"]
        if resume:
            if not session.session_id:
                raise MissingSessionIdentityError("Claude resume requested without session_id")
            cmd.extend(["--resume", session.session_id])
        else:
            session_id = session.session_id or str(uuid.uuid4())
            cmd.extend(["--session-id", session_id])
        if session.model:
            cmd.extend(["--model", session.model])
        if session.allow_dangerous:
            cmd.append("--dangerously-skip-permissions")
        return cmd

    def _parse(self, stdout: str, stderr: str) -> BridgeTurnResult:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise BridgeTransportError(f"Failed to parse Claude JSON output: {exc}") from exc
        if not isinstance(payload, dict):
            raise BridgeTransportError("Claude JSON output was not an object")
        session_id = str(payload.get("session_id", "") or "").strip()
        if not session_id:
            raise MissingSessionIdentityError("Claude output did not include session_id")
        response_text = str(payload.get("result", "") or "")
        return BridgeTurnResult(
            session_id=session_id,
            response_text=response_text,
            raw_stdout=stdout,
            raw_stderr=stderr,
            metadata={
                "subtype": payload.get("subtype"),
                "duration_ms": payload.get("duration_ms"),
                "num_turns": payload.get("num_turns"),
            },
        )

    def start_session(self, session: BridgeSession, prompt: str) -> BridgeTurnResult:
        cmd = self._build_cmd(session, prompt, resume=False)
        proc = self._run(cmd, cwd=session.worktree or Path.cwd())
        if proc.returncode != 0:
            raise BridgeTransportError(
                proc.stderr.strip() or proc.stdout.strip() or "Claude failed"
            )
        return self._parse(proc.stdout.strip(), proc.stderr.strip())

    def resume_turn(self, session: BridgeSession, prompt: str) -> BridgeTurnResult:
        cmd = self._build_cmd(session, prompt, resume=True)
        proc = self._run(cmd, cwd=session.worktree or Path.cwd())
        if proc.returncode != 0:
            raise BridgeTransportError(
                proc.stderr.strip() or proc.stdout.strip() or "Claude failed"
            )
        return self._parse(proc.stdout.strip(), proc.stderr.strip())


class CodexTransport(BaseTransport):
    binary_name = "codex"

    def _build_cmd(
        self,
        session: BridgeSession,
        prompt: str,
        *,
        resume: bool,
        output_file: Path,
    ) -> list[str]:
        base = [self.binary_name, "exec"]
        if resume:
            if not session.session_id:
                raise MissingSessionIdentityError("Codex resume requested without thread_id")
            base.extend(["resume", session.session_id])
        base.extend(
            [
                "--json",
                "-C",
                str(session.worktree or Path.cwd()),
                "-o",
                str(output_file),
            ]
        )
        if session.model:
            base.extend(["-m", session.model])
        if session.full_auto:
            base.append("--full-auto")
        if session.allow_dangerous:
            base.append("--dangerously-bypass-approvals-and-sandbox")
        base.append(prompt)
        return base

    def _parse(
        self,
        stdout: str,
        stderr: str,
        response_text: str,
        *,
        session_id_hint: str | None = None,
    ) -> BridgeTurnResult:
        thread_id = ""
        turn_metadata: dict[str, Any] = {}
        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            event_type = str(payload.get("type", "") or "")
            if event_type == "thread.started":
                thread_id = str(payload.get("thread_id", "") or "").strip()
            elif event_type == "turn.completed":
                turn_metadata["usage"] = payload.get("usage")
                turn_metadata["stop_reason"] = payload.get("stop_reason")
        if not thread_id and session_id_hint:
            thread_id = session_id_hint
        if not thread_id:
            raise MissingSessionIdentityError("Codex output did not include thread_id")
        return BridgeTurnResult(
            session_id=thread_id,
            response_text=response_text,
            raw_stdout=stdout,
            raw_stderr=stderr,
            metadata=turn_metadata,
        )

    def start_session(self, session: BridgeSession, prompt: str) -> BridgeTurnResult:
        with tempfile.NamedTemporaryFile(prefix="agent-bridge-codex-", suffix=".txt") as handle:
            cmd = self._build_cmd(session, prompt, resume=False, output_file=Path(handle.name))
            proc = self._run(cmd, cwd=session.worktree or Path.cwd())
            if proc.returncode != 0:
                raise BridgeTransportError(
                    proc.stderr.strip() or proc.stdout.strip() or "Codex failed"
                )
            response_text = Path(handle.name).read_text(encoding="utf-8").strip()
        return self._parse(proc.stdout, proc.stderr, response_text)

    def resume_turn(self, session: BridgeSession, prompt: str) -> BridgeTurnResult:
        with tempfile.NamedTemporaryFile(prefix="agent-bridge-codex-", suffix=".txt") as handle:
            cmd = self._build_cmd(session, prompt, resume=True, output_file=Path(handle.name))
            proc = self._run(cmd, cwd=session.worktree or Path.cwd())
            if proc.returncode != 0:
                raise BridgeTransportError(
                    proc.stderr.strip() or proc.stdout.strip() or "Codex failed"
                )
            response_text = Path(handle.name).read_text(encoding="utf-8").strip()
        return self._parse(
            proc.stdout,
            proc.stderr,
            response_text,
            session_id_hint=session.session_id,
        )


class DroidTransport(BaseTransport):
    binary_name = "droid"

    def _build_cmd(self, session: BridgeSession, prompt: str, *, resume: bool) -> list[str]:
        cmd = [
            self.binary_name,
            "exec",
            "--output-format",
            "json",
            "--cwd",
            str(session.worktree or Path.cwd()),
        ]
        if resume:
            if not session.session_id:
                raise MissingSessionIdentityError("Droid resume requested without session_id")
            cmd.extend(["-s", session.session_id])
        if session.model:
            cmd.extend(["-m", session.model])
        if session.droid_auto:
            cmd.extend(["--auto", session.droid_auto])
        cmd.append(prompt)
        return cmd

    def _parse(self, stdout: str, stderr: str) -> BridgeTurnResult:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise BridgeTransportError(f"Failed to parse Droid JSON output: {exc}") from exc
        if not isinstance(payload, dict):
            raise BridgeTransportError("Droid JSON output was not an object")
        session_id = str(payload.get("session_id", "") or "").strip()
        if not session_id:
            raise MissingSessionIdentityError("Droid output did not include session_id")
        return BridgeTurnResult(
            session_id=session_id,
            response_text=str(payload.get("result", "") or ""),
            raw_stdout=stdout,
            raw_stderr=stderr,
            metadata={
                "duration_ms": payload.get("duration_ms"),
                "num_turns": payload.get("num_turns"),
            },
        )

    def start_session(self, session: BridgeSession, prompt: str) -> BridgeTurnResult:
        cmd = self._build_cmd(session, prompt, resume=False)
        proc = self._run(cmd, cwd=session.worktree or Path.cwd())
        if proc.returncode != 0:
            raise BridgeTransportError(proc.stderr.strip() or proc.stdout.strip() or "Droid failed")
        return self._parse(proc.stdout.strip(), proc.stderr.strip())

    def resume_turn(self, session: BridgeSession, prompt: str) -> BridgeTurnResult:
        cmd = self._build_cmd(session, prompt, resume=True)
        proc = self._run(cmd, cwd=session.worktree or Path.cwd())
        if proc.returncode != 0:
            raise BridgeTransportError(proc.stderr.strip() or proc.stdout.strip() or "Droid failed")
        return self._parse(proc.stdout.strip(), proc.stderr.strip())


def transport_for(session: BridgeSession) -> BaseTransport:
    if session.harness is HarnessKind.CLAUDE:
        return ClaudeTransport()
    if session.harness is HarnessKind.CODEX:
        return CodexTransport()
    if session.harness is HarnessKind.DROID:
        return DroidTransport()
    raise BridgeTransportError(f"Unsupported harness: {session.harness.value}")

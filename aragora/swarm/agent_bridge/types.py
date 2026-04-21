from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class HarnessKind(str, Enum):
    CLAUDE = "claude"
    CODEX = "codex"
    DROID = "droid"


class BridgeRunStatus(str, Enum):
    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class BridgeFooter:
    summary: str
    next_actor: str | None
    needs_human: bool
    done: bool
    artifacts: list[str] = field(default_factory=list)
    tests_run: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "next_actor": self.next_actor,
            "needs_human": self.needs_human,
            "done": self.done,
            "artifacts": list(self.artifacts),
            "tests_run": list(self.tests_run),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BridgeFooter":
        return cls(
            summary=str(payload.get("summary", "") or "").strip(),
            next_actor=(
                str(payload.get("next_actor", "")).strip()
                if payload.get("next_actor") not in (None, "")
                else None
            ),
            needs_human=bool(payload.get("needs_human", False)),
            done=bool(payload.get("done", False)),
            artifacts=[
                str(item).strip()
                for item in list(payload.get("artifacts", []) or [])
                if str(item).strip()
            ],
            tests_run=[
                str(item).strip()
                for item in list(payload.get("tests_run", []) or [])
                if str(item).strip()
            ],
        )


@dataclass(slots=True)
class BridgeSession:
    name: str
    harness: HarnessKind
    role: str = ""
    model: str | None = None
    session_id: str | None = None
    worktree_path: str | None = None
    branch: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    turn_count: int = 0
    full_auto: bool = False
    allow_dangerous: bool = False
    droid_auto: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "harness": self.harness.value,
            "role": self.role,
            "model": self.model,
            "session_id": self.session_id,
            "worktree_path": self.worktree_path,
            "branch": self.branch,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "turn_count": self.turn_count,
            "full_auto": self.full_auto,
            "allow_dangerous": self.allow_dangerous,
            "droid_auto": self.droid_auto,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BridgeSession":
        return cls(
            name=str(payload.get("name", "") or ""),
            harness=HarnessKind(str(payload.get("harness", HarnessKind.CODEX.value))),
            role=str(payload.get("role", "") or ""),
            model=str(payload.get("model")) if payload.get("model") else None,
            session_id=str(payload.get("session_id")) if payload.get("session_id") else None,
            worktree_path=(
                str(payload.get("worktree_path")) if payload.get("worktree_path") else None
            ),
            branch=str(payload.get("branch")) if payload.get("branch") else None,
            created_at=str(payload.get("created_at", utc_now_iso()) or utc_now_iso()),
            updated_at=str(payload.get("updated_at", utc_now_iso()) or utc_now_iso()),
            turn_count=int(payload.get("turn_count", 0) or 0),
            full_auto=bool(payload.get("full_auto", False)),
            allow_dangerous=bool(payload.get("allow_dangerous", False)),
            droid_auto=str(payload.get("droid_auto")) if payload.get("droid_auto") else None,
        )

    @property
    def worktree(self) -> Path | None:
        if not self.worktree_path:
            return None
        return Path(self.worktree_path)


@dataclass(slots=True)
class BridgeRun:
    run_id: str
    task: str
    repo_root: str
    base_branch: str = "main"
    status: BridgeRunStatus = BridgeRunStatus.RUNNING
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    active_actor: str | None = None
    last_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task": self.task,
            "repo_root": self.repo_root,
            "base_branch": self.base_branch,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "active_actor": self.active_actor,
            "last_summary": self.last_summary,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BridgeRun":
        return cls(
            run_id=str(payload.get("run_id", "") or ""),
            task=str(payload.get("task", "") or ""),
            repo_root=str(payload.get("repo_root", "") or ""),
            base_branch=str(payload.get("base_branch", "main") or "main"),
            status=BridgeRunStatus(str(payload.get("status", BridgeRunStatus.RUNNING.value))),
            created_at=str(payload.get("created_at", utc_now_iso()) or utc_now_iso()),
            updated_at=str(payload.get("updated_at", utc_now_iso()) or utc_now_iso()),
            active_actor=(
                str(payload.get("active_actor", "")).strip()
                if payload.get("active_actor") not in (None, "")
                else None
            ),
            last_summary=str(payload.get("last_summary", "") or ""),
        )


@dataclass(slots=True)
class BridgeTurnResult:
    session_id: str
    response_text: str
    raw_stdout: str
    raw_stderr: str
    footer: BridgeFooter | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "response_text": self.response_text,
            "raw_stdout": self.raw_stdout,
            "raw_stderr": self.raw_stderr,
            "footer": self.footer.to_dict() if self.footer is not None else None,
            "metadata": dict(self.metadata),
        }

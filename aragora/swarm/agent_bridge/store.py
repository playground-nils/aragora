from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aragora.swarm.agent_bridge.types import BridgeRun
from aragora.swarm.agent_bridge.types import BridgeSession
from aragora.swarm.agent_bridge.types import utc_now_iso


class BridgeStore:
    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        self.root = self.repo_root / ".aragora" / "agent_bridge" / "runs"

    def runs_dir(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    def run_dir(self, run_id: str) -> Path:
        path = self.runs_dir() / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def run_file(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "run.json"

    def sessions_file(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "sessions.json"

    def events_file(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "events.jsonl"

    def turns_dir(self, run_id: str) -> Path:
        path = self.run_dir(run_id) / "turns"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_run(self, run: BridgeRun) -> None:
        self.run_file(run.run_id).write_text(
            json.dumps(run.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def load_run(self, run_id: str) -> BridgeRun:
        payload = json.loads(self.run_file(run_id).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid run payload for {run_id}")
        return BridgeRun.from_dict(payload)

    def save_sessions(self, run_id: str, sessions: list[BridgeSession]) -> None:
        payload = {"sessions": [session.to_dict() for session in sessions]}
        self.sessions_file(run_id).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def load_sessions(self, run_id: str) -> list[BridgeSession]:
        path = self.sessions_file(run_id)
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid sessions payload for {run_id}")
        raw_sessions = payload.get("sessions", [])
        if not isinstance(raw_sessions, list):
            raise ValueError(f"Invalid sessions list for {run_id}")
        return [BridgeSession.from_dict(item) for item in raw_sessions if isinstance(item, dict)]

    def append_event(self, run_id: str, event_type: str, **data: Any) -> None:
        event = {
            "timestamp": utc_now_iso(),
            "type": event_type,
            "run_id": run_id,
            **data,
        }
        with self.events_file(run_id).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    def load_events(self, run_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
        path = self.events_file(run_id)
        if not path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                events.append(payload)
        if limit is not None and limit > 0:
            return events[-limit:]
        return events

    def write_turn_artifact(
        self,
        run_id: str,
        *,
        turn_index: int,
        actor: str,
        payload: dict[str, Any],
    ) -> Path:
        safe_actor = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in actor)
        path = self.turns_dir(run_id) / f"{turn_index:04d}-{safe_actor}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def list_runs(self, *, limit: int | None = None) -> list[BridgeRun]:
        runs: list[BridgeRun] = []
        for run_path in self.runs_dir().glob("*/run.json"):
            try:
                payload = json.loads(run_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                try:
                    runs.append(BridgeRun.from_dict(payload))
                except (TypeError, ValueError):
                    continue
        runs.sort(key=lambda item: item.updated_at, reverse=True)
        if limit is not None and limit > 0:
            return runs[:limit]
        return runs

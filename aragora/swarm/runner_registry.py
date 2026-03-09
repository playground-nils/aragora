"""Local Codex runner inspection and registration for supervised swarm routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
from typing import Any

from aragora.rbac.models import AuthorizationContext
from aragora.swarm.worker_launcher import LaunchConfig

UTC = timezone.utc


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _env_flag_int(env: dict[str, str], key: str, default: int) -> int:
    raw = str(env.get(key, "")).strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


@dataclass(slots=True)
class CodexRunnerInspection:
    runner_id: str
    runner_type: str
    availability: str
    available: bool
    auth_mode: str
    codex_path: str | None
    version: str | None
    status_summary: str | None
    capabilities: dict[str, Any] = field(default_factory=dict)
    owner_binding: dict[str, Any] = field(default_factory=dict)
    registered: bool = False
    registry_path: str | None = None
    registered_at: str | None = None
    next_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "runner_id": self.runner_id,
            "runner_type": self.runner_type,
            "availability": self.availability,
            "available": self.available,
            "auth_mode": self.auth_mode,
            "codex_path": self.codex_path,
            "version": self.version,
            "status_summary": self.status_summary,
            "capabilities": dict(self.capabilities),
            "owner_binding": dict(self.owner_binding),
            "registered": self.registered,
            "registry_path": self.registry_path,
            "registered_at": self.registered_at,
            "next_action": self.next_action,
        }


class CodexRunnerInspector:
    """Inspect local Codex CLI availability and auth state truthfully."""

    def __init__(
        self,
        *,
        config: LaunchConfig | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.config = config or LaunchConfig()
        self.env = dict(os.environ if env is None else env)

    def inspect(self) -> CodexRunnerInspection:
        codex_path = shutil.which(self.config.codex_path)
        runner_id = self._runner_id(codex_path)
        owner = owner_binding_from_env(self.env)

        if not codex_path:
            return CodexRunnerInspection(
                runner_id=runner_id,
                runner_type="codex",
                availability="unavailable",
                available=False,
                auth_mode="unavailable",
                codex_path=None,
                version=None,
                status_summary=None,
                capabilities=self._capabilities(False, None),
                owner_binding=owner,
                next_action="Install the Codex CLI or add `codex` to PATH before registering this runner.",
            )

        version_result = self._run_command([codex_path, "--version"])
        help_result = self._run_command([codex_path, "--help"])
        login_result = self._run_command([codex_path, "login", "status"])

        help_text = "\n".join(
            part for part in (help_result.get("stdout", ""), help_result.get("stderr", "")) if part
        ).strip()
        login_text = "\n".join(
            part
            for part in (login_result.get("stdout", ""), login_result.get("stderr", ""))
            if part
        ).strip()

        available = bool(
            help_result.get("returncode") == 0
            or version_result.get("returncode") == 0
            or help_text
            or version_result.get("stdout")
            or version_result.get("stderr")
        )
        if not available:
            return CodexRunnerInspection(
                runner_id=runner_id,
                runner_type="codex",
                availability="unavailable",
                available=False,
                auth_mode="unavailable",
                codex_path=codex_path,
                version=None,
                status_summary=None,
                capabilities=self._capabilities(False, None),
                owner_binding=owner,
                next_action="The local `codex` binary exists but did not respond truthfully; fix the CLI installation before registering this runner.",
            )

        auth_mode = self._classify_auth_mode(login_text)
        version = self._first_line(
            version_result.get("stdout") or version_result.get("stderr") or ""
        )
        availability = "available"
        next_action = self._next_action(
            available=available, auth_mode=auth_mode, owner_binding=owner
        )

        return CodexRunnerInspection(
            runner_id=runner_id,
            runner_type="codex",
            availability=availability,
            available=available,
            auth_mode=auth_mode,
            codex_path=codex_path,
            version=version or None,
            status_summary=self._first_line(login_text) or None,
            capabilities=self._capabilities(True, help_text),
            owner_binding=owner,
            next_action=next_action,
        )

    def _capabilities(self, available: bool, help_text: str | None) -> dict[str, Any]:
        text = (help_text or "").lower()
        return {
            "supports_exec": available and "exec" in text,
            "supports_review": available and "review" in text,
            "supports_login_status": available and "login" in text,
            "max_parallel_lanes": _env_flag_int(
                self.env, "ARAGORA_CODEX_RUNNER_MAX_CONCURRENCY", 1
            ),
        }

    def _classify_auth_mode(self, login_text: str) -> str:
        lowered = login_text.lower()
        if "chatgpt" in lowered and "logged in" in lowered:
            return "chatgpt_login"
        if "api key" in lowered and "logged in" in lowered:
            return "api_key"
        return "unknown"

    @staticmethod
    def _first_line(text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return ""

    def _runner_id(self, codex_path: str | None) -> str:
        identity = f"codex:{platform.node()}:{codex_path or self.config.codex_path}"
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
        return f"codex-runner-{digest}"

    @staticmethod
    def _run_command(command: list[str]) -> dict[str, Any]:
        try:
            proc = subprocess.run(
                command,
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            return {"returncode": 1, "stdout": "", "stderr": ""}
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    @staticmethod
    def _next_action(*, available: bool, auth_mode: str, owner_binding: dict[str, Any]) -> str:
        if not available:
            return "Install the Codex CLI or add `codex` to PATH before registering this runner."
        if auth_mode == "unknown":
            return (
                "Confirm the local Codex CLI login state with `codex login status` or set "
                "`OPENAI_API_KEY` before relying on this runner for routed work."
            )
        if not owner_binding.get("user_id"):
            return (
                "Set `ARAGORA_USER_ID` and optional `ARAGORA_WORKSPACE_ID` before registering this "
                "runner to an Aragora owner context."
            )
        return (
            "Runner is eligible for future Boss-mode routing under the bound Aragora owner context."
        )


class LocalRunnerRegistry:
    """Minimal local registry for user-owned Codex runners."""

    def __init__(self, *, path: str | Path | None = None) -> None:
        raw = (
            path
            or os.environ.get("ARAGORA_RUNNER_REGISTRY_PATH")
            or "~/.aragora/swarm_runners.json"
        )
        self.path = Path(raw).expanduser()

    def register(
        self,
        inspection: CodexRunnerInspection,
        *,
        owner_context: AuthorizationContext | None,
    ) -> CodexRunnerInspection:
        registry_path = str(self.path)
        if not inspection.available:
            inspection.registered = False
            inspection.registry_path = registry_path
            inspection.next_action = inspection.next_action or (
                "Restore local Codex runner availability before registering this runner."
            )
            return inspection
        if owner_context is None:
            inspection.registered = False
            inspection.registry_path = registry_path
            inspection.next_action = (
                "Set `ARAGORA_USER_ID` and optional `ARAGORA_WORKSPACE_ID` before registering this "
                "runner to an Aragora owner context."
            )
            return inspection

        records = self._load()
        now = _utcnow()
        entry = {
            **inspection.to_dict(),
            "owner_binding": owner_binding_from_context(owner_context),
            "registered": True,
            "registered_at": now,
            "updated_at": now,
        }
        records["registrations"] = [
            item
            for item in records.get("registrations", [])
            if isinstance(item, dict) and item.get("runner_id") != inspection.runner_id
        ]
        records["registrations"].append(entry)
        self._save(records)

        inspection.owner_binding = owner_binding_from_context(owner_context)
        inspection.registered = True
        inspection.registry_path = registry_path
        inspection.registered_at = now
        if inspection.auth_mode == "unknown":
            inspection.next_action = (
                "Runner registered to the owner context, but auth mode is still unknown. "
                "Confirm the local Codex login state before Boss-mode routing relies on this runner."
            )
        else:
            inspection.next_action = "Runner registered. Future Boss-mode routing can target this owner-bound Codex runner."
        return inspection

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"registrations": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"registrations": []}
        registrations = data.get("registrations", [])
        if not isinstance(registrations, list):
            registrations = []
        return {"registrations": registrations}

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(self.path)


def authorization_context_from_env(
    env: dict[str, str] | None = None,
) -> AuthorizationContext | None:
    values = dict(env or os.environ)
    user_id = str(values.get("ARAGORA_USER_ID") or values.get("ARAGORA_ACTOR_ID") or "").strip()
    if not user_id:
        return None
    workspace_id = (
        str(values.get("ARAGORA_WORKSPACE_ID") or values.get("ARAGORA_WORKSPACE") or "").strip()
        or None
    )
    org_id = str(values.get("ARAGORA_ORG_ID", "")).strip() or None
    email = str(values.get("ARAGORA_USER_EMAIL", "")).strip() or None
    role = str(values.get("ARAGORA_ROLE", "")).strip()
    roles = {role} if role else set()
    return AuthorizationContext(
        user_id=user_id,
        user_email=email,
        org_id=org_id,
        workspace_id=workspace_id,
        roles=roles,
    )


def owner_binding_from_context(context: AuthorizationContext | None) -> dict[str, Any]:
    if context is None:
        return {"user_id": None, "workspace_id": None, "org_id": None}
    return {
        "user_id": context.user_id,
        "workspace_id": context.workspace_id,
        "org_id": context.org_id,
    }


def owner_binding_from_env(env: dict[str, str] | None = None) -> dict[str, Any]:
    return owner_binding_from_context(authorization_context_from_env(env))

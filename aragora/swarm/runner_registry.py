"""Local Codex runner registration and Boss routing eligibility helpers."""

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
VERIFIED_AUTH_MODES = {"chatgpt_login", "api_key"}


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


def _text(value: Any) -> str:
    return str(value or "").strip()


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


@dataclass(slots=True)
class BossRoutingDecision:
    owner_binding: dict[str, Any]
    selected_runner_ids: list[str] = field(default_factory=list)
    selected_runners: list[dict[str, Any]] = field(default_factory=list)
    selection_basis: str = ""
    blocked_reason: str | None = None
    next_action: str | None = None

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocked_reason)

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner_binding": dict(self.owner_binding),
            "selected_runner_ids": list(self.selected_runner_ids),
            "selected_runners": [dict(item) for item in self.selected_runners],
            "selection_basis": self.selection_basis,
            "blocked_reason": self.blocked_reason,
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
        return CodexRunnerInspection(
            runner_id=runner_id,
            runner_type="codex",
            availability="available",
            available=True,
            auth_mode=auth_mode,
            codex_path=codex_path,
            version=version or None,
            status_summary=self._first_line(login_text) or None,
            capabilities=self._capabilities(True, help_text),
            owner_binding=owner,
            next_action=self._next_action(available=True, auth_mode=auth_mode, owner_binding=owner),
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
            return "Confirm the local Codex CLI login state before relying on this runner for routed work."
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
        if inspection.auth_mode == "unknown":
            inspection.registered = False
            inspection.registry_path = registry_path
            inspection.next_action = (
                "Registration blocked: Codex auth mode is unknown. Confirm the local Codex login state "
                "before registering this runner for Boss-mode routing."
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
        inspection.next_action = (
            "Runner registered. Future Boss-mode routing can target this owner-bound Codex runner."
        )
        return inspection

    def list_registrations(self) -> list[dict[str, Any]]:
        return [
            dict(item) for item in self._load().get("registrations", []) if isinstance(item, dict)
        ]

    def resolve_boss_routing(
        self,
        *,
        owner_context: AuthorizationContext | None,
    ) -> BossRoutingDecision:
        owner_binding = owner_binding_from_context(owner_context)
        selection_basis = (
            "registered=true, availability=available, auth_mode in {chatgpt_login, api_key}, "
            "owner_binding user/workspace compatible with current Aragora context"
        )
        if owner_context is None or not _text(owner_context.user_id):
            return BossRoutingDecision(
                owner_binding=owner_binding,
                selection_basis=selection_basis,
                blocked_reason="missing_owner_context",
                next_action=(
                    "Set `ARAGORA_USER_ID` and `ARAGORA_WORKSPACE_ID` before running Boss mode so "
                    "Aragora can route only onto authorized registered Codex runners."
                ),
            )

        eligible: list[dict[str, Any]] = []
        for runner in self.list_registrations():
            if not self._is_runner_eligible(runner, owner_context=owner_context):
                continue
            eligible.append(
                {
                    "runner_id": _text(runner.get("runner_id")),
                    "auth_mode": _text(runner.get("auth_mode")),
                    "owner_binding": dict(runner.get("owner_binding") or {}),
                    "capabilities": dict(runner.get("capabilities") or {}),
                }
            )

        if not eligible:
            return BossRoutingDecision(
                owner_binding=owner_binding,
                selection_basis=selection_basis,
                blocked_reason="no_eligible_registered_runners",
                next_action=(
                    "Register an available Codex runner for this exact Aragora user/workspace "
                    "context before running Boss mode."
                ),
            )

        return BossRoutingDecision(
            owner_binding=owner_binding,
            selected_runner_ids=[item["runner_id"] for item in eligible],
            selected_runners=eligible,
            selection_basis=selection_basis,
            next_action="Boss mode will route only through the selected registered Codex runner set.",
        )

    @staticmethod
    def _is_runner_eligible(
        runner: dict[str, Any],
        *,
        owner_context: AuthorizationContext,
    ) -> bool:
        if _text(runner.get("runner_type")) != "codex":
            return False
        if not bool(runner.get("registered")):
            return False
        if _text(runner.get("availability")) != "available" or not bool(
            runner.get("available", True)
        ):
            return False
        if _text(runner.get("auth_mode")) not in VERIFIED_AUTH_MODES:
            return False

        owner_binding = dict(runner.get("owner_binding") or {})
        if _text(owner_binding.get("user_id")) != _text(owner_context.user_id):
            return False

        runner_workspace = _text(owner_binding.get("workspace_id"))
        context_workspace = _text(owner_context.workspace_id)
        if runner_workspace != context_workspace:
            return False

        runner_org = _text(owner_binding.get("org_id"))
        context_org = _text(owner_context.org_id)
        if runner_org and context_org and runner_org != context_org:
            return False

        return True

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
    values = dict(os.environ if env is None else env)
    user_id = _text(values.get("ARAGORA_USER_ID") or values.get("ARAGORA_ACTOR_ID"))
    if not user_id:
        return None
    workspace_id = (
        _text(values.get("ARAGORA_WORKSPACE_ID") or values.get("ARAGORA_WORKSPACE")) or None
    )
    org_id = _text(values.get("ARAGORA_ORG_ID")) or None
    email = _text(values.get("ARAGORA_USER_EMAIL")) or None
    role = _text(values.get("ARAGORA_ROLE"))
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

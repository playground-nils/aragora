from __future__ import annotations

import json
from pathlib import Path

from aragora.swarm.runner_registry import (
    CodexRunnerInspection,
    CodexRunnerInspector,
    LocalRunnerRegistry,
    authorization_context_from_env,
)


class TestCodexRunnerInspector:
    def test_codex_unavailable(self, monkeypatch):
        monkeypatch.setattr("aragora.swarm.runner_registry.shutil.which", lambda _name: None)
        inspection = CodexRunnerInspector(env={}).inspect()

        assert inspection.available is False
        assert inspection.availability == "unavailable"
        assert inspection.auth_mode == "unavailable"
        assert "Install the Codex CLI" in str(inspection.next_action)

    def test_api_key_runner_detected_from_login_status(self, monkeypatch):
        monkeypatch.setattr(
            "aragora.swarm.runner_registry.shutil.which",
            lambda _name: "/usr/local/bin/codex",
        )

        def _run(command: list[str]) -> dict[str, object]:
            joined = " ".join(command)
            if joined.endswith("--version"):
                return {"returncode": 0, "stdout": "codex 1.2.3\n", "stderr": ""}
            if joined.endswith("--help"):
                return {
                    "returncode": 0,
                    "stdout": "Commands:\n  exec\n  review\n  login\n",
                    "stderr": "",
                }
            return {"returncode": 0, "stdout": "Logged in using API key\n", "stderr": ""}

        monkeypatch.setattr(CodexRunnerInspector, "_run_command", staticmethod(_run))
        inspection = CodexRunnerInspector(env={}).inspect()

        assert inspection.available is True
        assert inspection.auth_mode == "api_key"
        assert inspection.capabilities["supports_exec"] is True
        assert inspection.capabilities["supports_review"] is True

    def test_chatgpt_login_runner_detected(self, monkeypatch):
        monkeypatch.setattr(
            "aragora.swarm.runner_registry.shutil.which",
            lambda _name: "/usr/local/bin/codex",
        )

        def _run(command: list[str]) -> dict[str, object]:
            joined = " ".join(command)
            if joined.endswith("--help"):
                return {
                    "returncode": 0,
                    "stdout": "Commands:\n  exec\n  review\n  login\n",
                    "stderr": "",
                }
            return {"returncode": 0, "stdout": "Logged in using ChatGPT\n", "stderr": ""}

        monkeypatch.setattr(CodexRunnerInspector, "_run_command", staticmethod(_run))
        inspection = CodexRunnerInspector(env={}).inspect()

        assert inspection.auth_mode == "chatgpt_login"
        assert inspection.available is True

    def test_ambiguous_state_returns_unknown(self, monkeypatch):
        monkeypatch.setattr(
            "aragora.swarm.runner_registry.shutil.which",
            lambda _name: "/usr/local/bin/codex",
        )

        def _run(command: list[str]) -> dict[str, object]:
            joined = " ".join(command)
            if joined.endswith("--help"):
                return {"returncode": 0, "stdout": "Commands:\n  exec\n", "stderr": ""}
            return {"returncode": 0, "stdout": "Authentication status unavailable\n", "stderr": ""}

        monkeypatch.setattr(CodexRunnerInspector, "_run_command", staticmethod(_run))
        inspection = CodexRunnerInspector(env={}).inspect()

        assert inspection.auth_mode == "unknown"
        assert "Confirm the local Codex CLI login state" in str(inspection.next_action)


class TestLocalRunnerRegistry:
    def test_registration_persists_owner_binding_and_payload_shape(self, tmp_path: Path) -> None:
        registry_path = tmp_path / "swarm-runners.json"
        registry = LocalRunnerRegistry(path=registry_path)
        owner_context = authorization_context_from_env(
            {
                "ARAGORA_USER_ID": "user-123",
                "ARAGORA_WORKSPACE_ID": "ws-456",
                "ARAGORA_ORG_ID": "org-789",
            }
        )
        inspection = CodexRunnerInspection(
            runner_id="codex-runner-123",
            runner_type="codex",
            availability="available",
            available=True,
            auth_mode="chatgpt_login",
            codex_path="/usr/local/bin/codex",
            version="codex 1.2.3",
            status_summary="Logged in using ChatGPT",
            capabilities={"supports_exec": True, "supports_review": True, "max_parallel_lanes": 2},
            owner_binding={},
        )

        registered = registry.register(inspection, owner_context=owner_context)

        assert registered.registered is True
        assert registered.owner_binding["user_id"] == "user-123"
        assert registered.owner_binding["workspace_id"] == "ws-456"
        assert registry_path.exists()

        stored = json.loads(registry_path.read_text(encoding="utf-8"))
        assert stored["registrations"][0]["runner_id"] == "codex-runner-123"
        assert stored["registrations"][0]["auth_mode"] == "chatgpt_login"
        assert stored["registrations"][0]["owner_binding"]["org_id"] == "org-789"

    def test_registration_without_owner_context_fails_closed(self, tmp_path: Path) -> None:
        registry = LocalRunnerRegistry(path=tmp_path / "swarm-runners.json")
        inspection = CodexRunnerInspection(
            runner_id="codex-runner-123",
            runner_type="codex",
            availability="available",
            available=True,
            auth_mode="unknown",
            codex_path="/usr/local/bin/codex",
            version=None,
            status_summary=None,
            capabilities={},
            owner_binding={},
        )

        registered = registry.register(inspection, owner_context=None)

        assert registered.registered is False
        assert registered.registry_path is not None
        assert "ARAGORA_USER_ID" in str(registered.next_action)

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from aragora.swarm.runner_registry import (
    BossRoutingDecision,
    CodexRunnerInspection,
    CodexRunnerInspector,
    LocalRunnerRegistry,
    authorization_context_from_env,
)

UTC = timezone.utc


class TestCodexRunnerInspector:
    def test_codex_unavailable(self, monkeypatch):
        monkeypatch.setattr("aragora.swarm.runner_registry.shutil.which", lambda _name: None)
        inspection = CodexRunnerInspector(env={}).inspect()

        assert inspection.available is False
        assert inspection.availability == "unavailable"
        assert inspection.auth_mode == "unavailable"
        assert inspection.freshness_status == "unavailable"
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
        assert inspection.freshness_status == "fresh"
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
        assert inspection.freshness_status == "fresh"

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
        assert inspection.freshness_status == "unknown"
        assert "Confirm the local Codex CLI login state" in str(inspection.next_action)

    def test_openai_api_key_env_alone_does_not_prove_api_key_auth(self, monkeypatch):
        monkeypatch.setattr(
            "aragora.swarm.runner_registry.shutil.which",
            lambda _name: "/usr/local/bin/codex",
        )

        def _run(command: list[str]) -> dict[str, object]:
            joined = " ".join(command)
            if joined.endswith("--help"):
                return {
                    "returncode": 0,
                    "stdout": "Commands:\n  exec\n  review\n",
                    "stderr": "",
                }
            return {"returncode": 0, "stdout": "Authentication status unavailable\n", "stderr": ""}

        monkeypatch.setattr(CodexRunnerInspector, "_run_command", staticmethod(_run))
        inspection = CodexRunnerInspector(env={"OPENAI_API_KEY": "sk-test"}).inspect()

        assert inspection.auth_mode == "unknown"
        assert inspection.freshness_status == "unknown"


class TestLocalRunnerRegistry:
    def test_registration_persists_owner_binding_and_freshness(self, tmp_path: Path) -> None:
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
            freshness_status="fresh",
        )

        registered = registry.register(inspection, owner_context=owner_context)

        assert registered.registered is True
        assert registered.owner_binding["user_id"] == "user-123"
        assert registered.owner_binding["workspace_id"] == "ws-456"
        assert registered.freshness_status == "fresh"
        assert registered.heartbeat_at is not None
        assert registry_path.exists()

        stored = json.loads(registry_path.read_text(encoding="utf-8"))
        assert stored["registrations"][0]["runner_id"] == "codex-runner-123"
        assert stored["registrations"][0]["auth_mode"] == "chatgpt_login"
        assert stored["registrations"][0]["owner_binding"]["org_id"] == "org-789"
        assert stored["registrations"][0]["freshness_status"] == "fresh"
        assert stored["registrations"][0]["heartbeat_at"]

    def test_registration_of_unknown_auth_runner_fails_closed(self, tmp_path: Path) -> None:
        registry = LocalRunnerRegistry(path=tmp_path / "swarm-runners.json")
        owner_context = authorization_context_from_env(
            {
                "ARAGORA_USER_ID": "user-123",
                "ARAGORA_WORKSPACE_ID": "ws-456",
            }
        )
        inspection = CodexRunnerInspection(
            runner_id="codex-runner-unknown",
            runner_type="codex",
            availability="available",
            available=True,
            auth_mode="unknown",
            codex_path="/usr/local/bin/codex",
            version="codex 1.2.3",
            status_summary="Authentication status unavailable",
            capabilities={"supports_exec": True},
            owner_binding={},
            freshness_status="unknown",
        )

        registered = registry.register(inspection, owner_context=owner_context)

        assert registered.registered is False
        assert registered.registry_path is not None
        assert registered.registered_at is None
        assert "Registration blocked: Codex auth mode is unknown" in str(registered.next_action)
        assert not (tmp_path / "swarm-runners.json").exists()

    def test_heartbeat_refreshes_registered_runner(self, tmp_path: Path) -> None:
        registry_path = tmp_path / "swarm-runners.json"
        registry_path.write_text(
            json.dumps(
                {
                    "registrations": [
                        {
                            "runner_id": "codex-runner-1",
                            "runner_type": "codex",
                            "registered": True,
                            "availability": "available",
                            "available": True,
                            "auth_mode": "chatgpt_login",
                            "owner_binding": {"user_id": "user-123", "workspace_id": "ws-456"},
                            "registered_at": "2026-03-09T00:00:00+00:00",
                            "heartbeat_at": "2026-03-09T00:00:00+00:00",
                            "freshness_status": "stale",
                            "stale_after_seconds": 3600,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        registry = LocalRunnerRegistry(path=registry_path)
        owner_context = authorization_context_from_env(
            {"ARAGORA_USER_ID": "user-123", "ARAGORA_WORKSPACE_ID": "ws-456"}
        )
        inspection = CodexRunnerInspection(
            runner_id="codex-runner-1",
            runner_type="codex",
            availability="available",
            available=True,
            auth_mode="chatgpt_login",
            codex_path="/usr/local/bin/codex",
            version="codex 1.2.3",
            status_summary="Logged in using ChatGPT",
            capabilities={"supports_exec": True},
            owner_binding={},
            freshness_status="fresh",
        )

        heartbeated = registry.heartbeat(inspection, owner_context=owner_context)

        assert heartbeated.registered is True
        assert heartbeated.freshness_status == "fresh"
        assert heartbeated.heartbeat_at is not None
        stored = json.loads(registry_path.read_text(encoding="utf-8"))
        assert stored["registrations"][0]["freshness_status"] == "fresh"
        assert stored["registrations"][0]["heartbeat_at"]

    def test_missing_heartbeat_is_treated_as_stale(self, tmp_path: Path) -> None:
        registry_path = tmp_path / "swarm-runners.json"
        registry_path.write_text(
            json.dumps(
                {
                    "registrations": [
                        {
                            "runner_id": "codex-runner-1",
                            "runner_type": "codex",
                            "registered": True,
                            "availability": "available",
                            "available": True,
                            "auth_mode": "chatgpt_login",
                            "owner_binding": {"user_id": "user-123", "workspace_id": "ws-456"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        decision = LocalRunnerRegistry(path=registry_path).resolve_boss_routing(
            owner_context=authorization_context_from_env(
                {"ARAGORA_USER_ID": "user-123", "ARAGORA_WORKSPACE_ID": "ws-456"}
            )
        )

        assert decision.is_blocked is True
        assert decision.blocked_reason == "no_fresh_registered_runners"

    def test_resolve_boss_routing_selects_fresh_runner(self, tmp_path: Path) -> None:
        fresh_heartbeat = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
        registry_path = tmp_path / "swarm-runners.json"
        registry_path.write_text(
            json.dumps(
                {
                    "registrations": [
                        {
                            "runner_id": "codex-runner-1",
                            "runner_type": "codex",
                            "registered": True,
                            "availability": "available",
                            "available": True,
                            "auth_mode": "chatgpt_login",
                            "owner_binding": {"user_id": "user-123", "workspace_id": "ws-456"},
                            "capabilities": {"max_parallel_lanes": 2},
                            "heartbeat_at": fresh_heartbeat,
                            "stale_after_seconds": 3600,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        decision = LocalRunnerRegistry(path=registry_path).resolve_boss_routing(
            owner_context=authorization_context_from_env(
                {"ARAGORA_USER_ID": "user-123", "ARAGORA_WORKSPACE_ID": "ws-456"}
            )
        )

        assert decision.is_blocked is False
        assert decision.selected_runner_ids == ["codex-runner-1"]
        assert decision.selected_runners[0]["freshness_status"] == "fresh"

    def test_resolve_boss_routing_rejects_stale_runner(self, tmp_path: Path) -> None:
        stale_heartbeat = (datetime.now(UTC) - timedelta(hours=3)).isoformat()
        registry_path = tmp_path / "swarm-runners.json"
        registry_path.write_text(
            json.dumps(
                {
                    "registrations": [
                        {
                            "runner_id": "codex-runner-stale",
                            "runner_type": "codex",
                            "registered": True,
                            "availability": "available",
                            "available": True,
                            "auth_mode": "chatgpt_login",
                            "owner_binding": {"user_id": "user-123", "workspace_id": "ws-456"},
                            "heartbeat_at": stale_heartbeat,
                            "stale_after_seconds": 3600,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        decision = LocalRunnerRegistry(path=registry_path).resolve_boss_routing(
            owner_context=authorization_context_from_env(
                {"ARAGORA_USER_ID": "user-123", "ARAGORA_WORKSPACE_ID": "ws-456"}
            )
        )

        assert decision.is_blocked is True
        assert decision.blocked_reason == "no_fresh_registered_runners"
        assert "codex-runner-stale" in decision.rejected_runner_ids

    def test_resolve_boss_routing_rejects_wrong_workspace(self, tmp_path: Path) -> None:
        registry_path = tmp_path / "swarm-runners.json"
        registry_path.write_text(
            json.dumps(
                {
                    "registrations": [
                        {
                            "runner_id": "codex-runner-1",
                            "runner_type": "codex",
                            "registered": True,
                            "availability": "available",
                            "available": True,
                            "auth_mode": "chatgpt_login",
                            "owner_binding": {"user_id": "user-123", "workspace_id": "ws-other"},
                            "heartbeat_at": datetime.now(UTC).isoformat(),
                            "stale_after_seconds": 3600,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        decision = LocalRunnerRegistry(path=registry_path).resolve_boss_routing(
            owner_context=authorization_context_from_env(
                {"ARAGORA_USER_ID": "user-123", "ARAGORA_WORKSPACE_ID": "ws-456"}
            )
        )

        assert decision.is_blocked is True
        assert decision.blocked_reason == "no_eligible_registered_runners"

    def test_resolve_boss_routing_blocks_without_owner_context(self, tmp_path: Path) -> None:
        decision = LocalRunnerRegistry(path=tmp_path / "swarm-runners.json").resolve_boss_routing(
            owner_context=None
        )

        assert decision == BossRoutingDecision(
            owner_binding={"user_id": None, "workspace_id": None, "org_id": None},
            selection_basis=(
                "registered=true, freshness_status=fresh, availability=available, auth_mode in "
                "{chatgpt_login, api_key}, owner_binding user/workspace compatible with current "
                "Aragora context"
            ),
            blocked_reason="missing_owner_context",
            next_action=(
                "Set `ARAGORA_USER_ID` and `ARAGORA_WORKSPACE_ID` before running Boss mode so "
                "Aragora can route only onto authorized registered Codex runners."
            ),
        )

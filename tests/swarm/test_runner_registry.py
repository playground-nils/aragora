from __future__ import annotations

import json
from pathlib import Path

from aragora.swarm.runner_registry import (
    BossRoutingDecision,
    CodexRunnerInspection,
    CodexRunnerInspector,
    LocalRunnerRegistry,
    authorization_context_from_env,
)


class TestCodexRunnerInspector:
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


class TestLocalRunnerRegistry:
    def test_register_persists_verified_runner(self, tmp_path: Path) -> None:
        registry = LocalRunnerRegistry(path=tmp_path / "swarm-runners.json")
        inspection = CodexRunnerInspection(
            runner_id="codex-runner-1",
            runner_type="codex",
            availability="available",
            available=True,
            auth_mode="chatgpt_login",
            codex_path="/usr/local/bin/codex",
            version="codex 1.2.3",
            status_summary="Logged in using ChatGPT",
            capabilities={"max_parallel_lanes": 2},
            owner_binding={},
        )
        owner_context = authorization_context_from_env(
            {"ARAGORA_USER_ID": "user-123", "ARAGORA_WORKSPACE_ID": "ws-456"}
        )

        registered = registry.register(inspection, owner_context=owner_context)

        assert registered.registered is True
        stored = json.loads((tmp_path / "swarm-runners.json").read_text(encoding="utf-8"))
        assert stored["registrations"][0]["owner_binding"]["user_id"] == "user-123"

    def test_resolve_boss_routing_selects_eligible_runner(self, tmp_path: Path) -> None:
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

    def test_resolve_boss_routing_rejects_unregistered_unknown_and_unavailable(
        self, tmp_path: Path
    ) -> None:
        registry_path = tmp_path / "swarm-runners.json"
        registry_path.write_text(
            json.dumps(
                {
                    "registrations": [
                        {
                            "runner_id": "codex-runner-unregistered",
                            "runner_type": "codex",
                            "registered": False,
                            "availability": "available",
                            "available": True,
                            "auth_mode": "chatgpt_login",
                            "owner_binding": {"user_id": "user-123", "workspace_id": "ws-456"},
                        },
                        {
                            "runner_id": "codex-runner-unknown",
                            "runner_type": "codex",
                            "registered": True,
                            "availability": "available",
                            "available": True,
                            "auth_mode": "unknown",
                            "owner_binding": {"user_id": "user-123", "workspace_id": "ws-456"},
                        },
                        {
                            "runner_id": "codex-runner-down",
                            "runner_type": "codex",
                            "registered": True,
                            "availability": "unavailable",
                            "available": False,
                            "auth_mode": "chatgpt_login",
                            "owner_binding": {"user_id": "user-123", "workspace_id": "ws-456"},
                        },
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
        assert decision.selected_runner_ids == []

    def test_resolve_boss_routing_blocks_without_owner_context(self, tmp_path: Path) -> None:
        decision = LocalRunnerRegistry(path=tmp_path / "swarm-runners.json").resolve_boss_routing(
            owner_context=None
        )

        assert decision == BossRoutingDecision(
            owner_binding={"user_id": None, "workspace_id": None, "org_id": None},
            selection_basis=(
                "registered=true, availability=available, auth_mode in {chatgpt_login, api_key}, "
                "owner_binding user/workspace compatible with current Aragora context"
            ),
            blocked_reason="missing_owner_context",
            next_action=(
                "Set `ARAGORA_USER_ID` and `ARAGORA_WORKSPACE_ID` before running Boss mode so "
                "Aragora can route only onto authorized registered Codex runners."
            ),
        )

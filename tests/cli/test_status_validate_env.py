"""Tests for environment validation provider readiness."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from aragora.cli.commands.status import cmd_validate_env


def test_validate_env_fails_when_configured_provider_rejects_key(monkeypatch, capsys):
    """validate-env should not report readiness for an expired configured provider."""

    async def ok_connectivity(timeout_seconds: float) -> tuple[bool, str]:
        del timeout_seconds
        return True, "ok"

    def fake_secret_presence(name: str, strict: bool | None = None) -> SimpleNamespace:
        del strict
        return SimpleNamespace(source="env" if name == "GEMINI_API_KEY" else "missing")

    def fake_validate_provider_key(provider: str) -> SimpleNamespace:
        assert provider == "gemini"
        return SimpleNamespace(
            remote_status="invalid",
            is_valid=False,
            message="Provider rejected the API key",
        )

    monkeypatch.setattr(
        "aragora.server.startup.validate_redis_connectivity",
        ok_connectivity,
    )
    monkeypatch.setattr(
        "aragora.server.startup.validate_database_connectivity",
        ok_connectivity,
    )
    monkeypatch.setattr("aragora.cli.commands.status.get_secret_presence", fake_secret_presence)
    monkeypatch.setattr(
        "aragora.cli.api_keys.validate_provider_key",
        fake_validate_provider_key,
    )

    args = SimpleNamespace(verbose=False, json=True, strict=False)
    with pytest.raises(SystemExit) as exc_info:
        cmd_validate_env(args)

    assert exc_info.value.code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["checks"]["ai_providers"]["status"] == "error"
    assert payload["checks"]["ai_providers"]["configured"] == ["gemini"]
    assert payload["checks"]["ai_providers"]["validation"] == [
        {
            "provider": "gemini",
            "remote_status": "invalid",
            "is_valid": False,
            "message": "Provider rejected the API key",
        }
    ]
    assert payload["errors"] == ["gemini: Provider rejected the API key"]

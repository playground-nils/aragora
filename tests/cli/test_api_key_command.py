"""Tests for secure CLI LLM API key management."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from aragora.cli.api_keys import (
    get_provider_key,
    hydrate_env_from_secure_store,
    list_provider_statuses,
)
from aragora.cli.commands.api_key import cmd_api_key
from aragora.cli.parser import build_parser


def _file_store_env(tmp_path: Path) -> dict[str, str]:
    return {
        "ARAGORA_API_KEY_BACKEND": "file",
        "HOME": str(tmp_path),
    }


class TestApiKeyParser:
    def test_set_parses(self):
        args = build_parser().parse_args(["api-key", "set", "openai", "sk-test-1234"])
        assert args.command == "api-key"
        assert args.api_key_command == "set"
        assert args.provider == "openai"
        assert args.key == "sk-test-1234"

    def test_list_parses(self):
        args = build_parser().parse_args(["api-key", "list"])
        assert args.command == "api-key"
        assert args.api_key_command == "list"

    def test_validate_parses(self):
        args = build_parser().parse_args(["api-key", "validate", "anthropic"])
        assert args.command == "api-key"
        assert args.api_key_command == "validate"
        assert args.provider == "anthropic"


class TestApiKeyCommands:
    def test_set_stores_key_in_encrypted_file_backend(self, tmp_path, monkeypatch, capsys):
        for key, value in _file_store_env(tmp_path).items():
            monkeypatch.setenv(key, value)

        args = SimpleNamespace(api_key_command="set", provider="openai", key="sk-test-1234")
        cmd_api_key(args)

        store_path = tmp_path / ".aragora" / "api_keys.json"
        store_contents = store_path.read_text(encoding="utf-8")
        assert "sk-test-1234" not in store_contents
        assert '"backend": "file"' in store_contents

        resolved_key, source = get_provider_key("openai")
        assert resolved_key == "sk-test-1234"
        assert source == "secure-store"

        output = capsys.readouterr().out
        assert "Stored OpenAI API key" in output
        assert "Backend:  file" in output

    def test_list_includes_secure_store_and_env_override(self, tmp_path, monkeypatch, capsys):
        for key, value in _file_store_env(tmp_path).items():
            monkeypatch.setenv(key, value)

        cmd_api_key(SimpleNamespace(api_key_command="set", provider="openai", key="sk-test-1234"))
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-override")

        cmd_api_key(SimpleNamespace(api_key_command="list"))

        output = capsys.readouterr().out
        assert "openai" in output
        assert "environment override (OPENAI_API_KEY)" in output
        assert "sk-e...ride" in output

    def test_hydrate_env_from_secure_store_preserves_existing_env(self, tmp_path, monkeypatch):
        for key, value in _file_store_env(tmp_path).items():
            monkeypatch.setenv(key, value)

        cmd_api_key(SimpleNamespace(api_key_command="set", provider="anthropic", key="sk-ant-1234"))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env-override")

        hydrated = hydrate_env_from_secure_store()

        assert hydrated == {}
        assert os.environ["ANTHROPIC_API_KEY"] == "sk-ant-env-override"

    def test_validate_uses_stored_key(self, tmp_path, monkeypatch, capsys):
        for key, value in _file_store_env(tmp_path).items():
            monkeypatch.setenv(key, value)

        cmd_api_key(SimpleNamespace(api_key_command="set", provider="openai", key="sk-test-1234"))
        response = MagicMock(status_code=200)

        with patch("aragora.security.safe_http.safe_get", return_value=response):
            with pytest.raises(SystemExit) as exc_info:
                cmd_api_key(SimpleNamespace(api_key_command="validate", provider="openai"))

        assert exc_info.value.code == 0
        output = capsys.readouterr().out
        assert "OpenAI API key validation" in output
        assert "Remote check: valid" in output
        assert "API key is valid" in output

    def test_validate_fails_for_missing_key(self, tmp_path, monkeypatch, capsys):
        for key, value in _file_store_env(tmp_path).items():
            monkeypatch.setenv(key, value)

        with pytest.raises(SystemExit) as exc_info:
            cmd_api_key(SimpleNamespace(api_key_command="validate", provider="mistral"))

        assert exc_info.value.code == 1
        output = capsys.readouterr().out
        assert "No API key configured for Mistral" in output

    def test_list_provider_statuses_shows_environment_alias(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("GOOGLE_API_KEY", "google-test-key")

        statuses = {status.provider: status for status in list_provider_statuses()}

        assert statuses["gemini"].configured is True
        assert statuses["gemini"].source == "environment (GOOGLE_API_KEY)"
        assert statuses["gemini"].masked_value == "goog...-key"

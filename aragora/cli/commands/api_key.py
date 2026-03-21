"""
CLI commands for secure LLM API key management.
"""

from __future__ import annotations

import argparse
import getpass

from aragora.cli.api_keys import (
    get_supported_provider_names,
    list_provider_statuses,
    resolve_provider,
    set_provider_key,
    validate_provider_key,
)


def cmd_api_key(args: argparse.Namespace) -> None:
    """Dispatch `aragora api-key` subcommands."""
    subcommand = getattr(args, "api_key_command", None)

    if subcommand == "set":
        _cmd_set(args)
        return
    if subcommand == "list":
        _cmd_list(args)
        return
    if subcommand == "validate":
        _cmd_validate(args)
        return

    print("\nUsage: aragora api-key <command>")
    print("\nCommands:")
    print("  set <provider> <key>    Store an LLM API key securely")
    print("  list                    List configured LLM API keys")
    print("  validate <provider>     Validate a configured provider key")
    print(f"\nSupported providers: {', '.join(get_supported_provider_names())}")


def _cmd_set(args: argparse.Namespace) -> None:
    """Store an LLM API key for a provider."""
    try:
        spec = resolve_provider(args.provider)
        key = getattr(args, "key", None)
        if not key:
            key = getpass.getpass(f"{spec.display_name} API key: ")
        stored = set_provider_key(spec.name, key)
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc

    print(f"\nStored {spec.display_name} API key.")
    print(f"  Provider: {stored.provider}")
    print(f"  Env var:  {stored.env_var}")
    print(f"  Backend:  {stored.backend}")
    print(f"  Key:      {stored.masked_value}")


def _cmd_list(_: argparse.Namespace) -> None:
    """List configured LLM API key status for supported providers."""
    statuses = list_provider_statuses()

    print("\nConfigured LLM API keys\n")
    print(f"{'Provider':<12} {'Status':<12} {'Source':<34} {'Key'}")
    print("-" * 78)
    for status in statuses:
        print(
            f"{status.provider:<12} "
            f"{('configured' if status.configured else 'not set'):<12} "
            f"{status.source:<34} "
            f"{status.masked_value}"
        )


def _cmd_validate(args: argparse.Namespace) -> None:
    """Validate a configured LLM API key."""
    try:
        report = validate_provider_key(args.provider)
    except ValueError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc

    print(f"\n{report.display_name} API key validation")
    print(f"  Provider:     {report.provider}")
    print(f"  Env var:      {report.env_var}")
    print(f"  Source:       {report.source}")
    print(f"  Key:          {report.masked_value}")
    print(f"  Format:       {'ok' if report.format_valid else 'invalid'}")
    print(f"  Remote check: {report.remote_status}")
    print(f"  Result:       {report.message}")

    raise SystemExit(0 if report.is_valid else 1)


__all__ = ["cmd_api_key"]

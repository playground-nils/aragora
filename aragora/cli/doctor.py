"""
Doctor command - Comprehensive health checks for Aragora.

Checks:
- Python version and required packages
- API key configuration
- Database connectivity
- Redis availability
- Storage backends
- Server endpoints (if running)
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from aragora.config.secrets import get_secret_presence


_AI_PROVIDER_KEYS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ANTHROPIC_API_KEY", ("ANTHROPIC_API_KEY",)),
    ("OPENAI_API_KEY", ("OPENAI_API_KEY",)),
    ("OPENROUTER_API_KEY", ("OPENROUTER_API_KEY",)),
    ("GEMINI_API_KEY", ("GEMINI_API_KEY", "GOOGLE_API_KEY")),
    ("MISTRAL_API_KEY", ("MISTRAL_API_KEY",)),
    ("XAI_API_KEY", ("XAI_API_KEY", "GROK_API_KEY")),
    ("DEEPSEEK_API_KEY", ("DEEPSEEK_API_KEY",)),
)

_VALIDATION_PROVIDER_BY_DISPLAY_KEY: dict[str, str] = {
    "ANTHROPIC_API_KEY": "anthropic",
    "OPENAI_API_KEY": "openai",
    "OPENROUTER_API_KEY": "openrouter",
    "GEMINI_API_KEY": "gemini",
    "MISTRAL_API_KEY": "mistral",
    "XAI_API_KEY": "grok",
    "DEEPSEEK_API_KEY": "deepseek",
}


def _configured_secret_var(env_vars: tuple[str, ...]) -> str | None:
    """Return the first usable secret variable name from env/AWS-backed discovery."""
    for env_var in env_vars:
        if get_secret_presence(env_var).source in {"aws", "env"}:
            return env_var
    return None


def check_icon(ok: bool | None) -> str:
    """Return status icon."""
    if ok is True:
        return "\033[92m✓\033[0m"  # Green checkmark
    elif ok is False:
        return "\033[91m✗\033[0m"  # Red X
    return "\033[93m○\033[0m"  # Yellow circle (optional)


def print_section(title: str) -> None:
    """Print section header."""
    print(f"\n\033[1m{title}\033[0m")
    print("-" * 40)


def check_packages() -> list[tuple[str, str, bool | None]]:
    """Check required and optional packages."""
    checks = []

    # Required packages
    required = ["aiohttp", "pydantic", "sqlite3", "asyncio"]
    for pkg in required:
        try:
            __import__(pkg)
            checks.append((pkg, "installed", True))
        except Exception as exc:  # noqa: BLE001 - doctor should surface broken imports, not crash
            checks.append((pkg, f"MISSING ({type(exc).__name__})", False))

    # Optional ML packages
    optional_ml = ["torch", "transformers", "sentence_transformers"]
    for pkg in optional_ml:
        try:
            __import__(pkg)
            checks.append((f"{pkg} (ML)", "installed", True))
        except Exception as exc:  # noqa: BLE001 - optional imports may fail due broken transitive deps
            checks.append((f"{pkg} (ML)", f"not installed ({type(exc).__name__})", None))

    # Optional integrations
    optional_int = ["redis", "asyncpg", "boto3", "opentelemetry"]
    for pkg in optional_int:
        try:
            __import__(pkg)
            checks.append((f"{pkg} (integration)", "installed", True))
        except Exception as exc:  # noqa: BLE001 - doctor should not crash on broken optional deps
            checks.append((f"{pkg} (integration)", f"not installed ({type(exc).__name__})", None))

    return checks


def check_api_keys(validate_live: bool = False) -> list[tuple[str, str, bool | None]]:
    """Check API key configuration."""
    checks = []

    # At least one real provider is required. Keep this in sync with validate-env:
    # env vars, .env hydration, AWS Secrets Manager, and provider aliases all count.
    configured_providers = []
    invalid_providers = []
    for display_key, env_vars in _AI_PROVIDER_KEYS:
        configured_var = _configured_secret_var(env_vars)
        if configured_var:
            configured_providers.append(display_key)
            status = (
                "configured"
                if configured_var == display_key
                else f"configured via {configured_var}"
            )
            ok = True
            if validate_live:
                provider_name = _VALIDATION_PROVIDER_BY_DISPLAY_KEY[display_key]
                from aragora.cli.api_keys import validate_provider_key

                report = validate_provider_key(provider_name)
                status = f"{status}; live {report.remote_status}"
                if not report.is_valid:
                    status = f"{status}: {report.message}"
                    invalid_providers.append(display_key)
                    ok = False
            checks.append((display_key, status, ok))
        else:
            checks.append((display_key, "not set", None))

    if invalid_providers:
        checks.append(
            ("LLM Provider", f"invalid provider(s): {', '.join(invalid_providers)}", False)
        )
    elif configured_providers:
        checks.append(("LLM Provider", ", ".join(configured_providers), True))
    else:
        checks.append(("LLM Provider", "NO API KEY SET", False))

    return checks


def check_storage() -> list[tuple[str, str, bool | None]]:
    """Check storage backends."""
    checks = []

    # Check data directory
    data_dir = Path.home() / ".aragora"
    if data_dir.exists():
        checks.append(("Data directory", str(data_dir), True))
    else:
        checks.append(("Data directory", "will be created", None))

    # Check SQLite
    try:
        import sqlite3

        conn = sqlite3.connect(":memory:")
        conn.execute("SELECT 1")
        conn.close()
        checks.append(("SQLite", "working", True))
    except (OSError, RuntimeError) as e:
        checks.append(("SQLite", f"error: {e}", False))

    # Check PostgreSQL
    try:
        import asyncpg  # noqa: F401

        checks.append(("PostgreSQL driver", "available", True))
        if os.getenv("DATABASE_URL"):
            checks.append(("DATABASE_URL", "configured", True))
        else:
            checks.append(("DATABASE_URL", "not set (using SQLite)", None))
    except ImportError:
        checks.append(("PostgreSQL driver", "not installed", None))

    # Check Redis
    try:
        import redis  # noqa: F401

        checks.append(("Redis driver", "available", True))
        if os.getenv("ARAGORA_REDIS_URL"):
            checks.append(("ARAGORA_REDIS_URL", "configured", True))
        else:
            checks.append(("ARAGORA_REDIS_URL", "not set (using memory)", None))
    except ImportError:
        checks.append(("Redis driver", "not installed", None))

    return checks


async def check_server() -> list[tuple[str, str, bool | None]]:
    """Check if server is running and responsive."""
    checks = []

    try:
        from aragora.server.http_client_pool import get_http_pool

        pool = get_http_pool()
        try:
            async with pool.get_session("health_check") as client:
                resp = await client.get("http://localhost:8080/health", timeout=5)
                if resp.status_code == 200:
                    checks.append(("Server (localhost:8080)", "running", True))
                else:
                    checks.append(
                        ("Server (localhost:8080)", f"unhealthy ({resp.status_code})", False)
                    )
        except Exception:  # noqa: BLE001 — diagnostic tool must never crash
            checks.append(("Server (localhost:8080)", "not running", None))
    except ImportError:
        checks.append(("Server check", "http pool not available", None))

    return checks


def check_environment() -> list[tuple[str, str, bool | None]]:
    """Check environment configuration."""
    checks = []

    # Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append(("Python", py_ver, sys.version_info >= (3, 10)))

    # Environment
    env = os.getenv("ARAGORA_ENV", "development")
    checks.append(("Environment", env, True))

    # Debug mode
    debug = os.getenv("ARAGORA_DEBUG", "false").lower() == "true"
    checks.append(("Debug mode", "enabled" if debug else "disabled", True))

    return checks


def main(validate_keys: bool = False) -> int:
    """Run comprehensive health checks."""
    print("\n\033[1;36m" + "=" * 50 + "\033[0m")
    print("\033[1;36m       ARAGORA HEALTH CHECK\033[0m")
    print("\033[1;36m" + "=" * 50 + "\033[0m")

    all_ok = True
    all_checks = []

    # Environment
    print_section("Environment")
    env_checks = check_environment()
    all_checks.extend(env_checks)
    for name, status, ok in env_checks:
        print(f"  {check_icon(ok)} {name}: {status}")
        if ok is False:
            all_ok = False

    # Packages
    print_section("Packages")
    pkg_checks = check_packages()
    all_checks.extend(pkg_checks)
    for name, status, ok in pkg_checks:
        print(f"  {check_icon(ok)} {name}: {status}")
        if ok is False:
            all_ok = False

    # API Keys
    print_section("API Keys")
    key_checks = check_api_keys(validate_live=validate_keys)
    all_checks.extend(key_checks)
    for name, status, ok in key_checks:
        print(f"  {check_icon(ok)} {name}: {status}")
        if ok is False:
            all_ok = False

    # Storage
    print_section("Storage")
    storage_checks = check_storage()
    all_checks.extend(storage_checks)
    for name, status, ok in storage_checks:
        print(f"  {check_icon(ok)} {name}: {status}")
        if ok is False:
            all_ok = False

    # Server
    print_section("Server")
    try:
        server_checks = asyncio.run(check_server())
        all_checks.extend(server_checks)
        for name, status, ok in server_checks:
            print(f"  {check_icon(ok)} {name}: {status}")
            if ok is False:
                all_ok = False
    except Exception as e:  # noqa: BLE001 — doctor must never crash
        print(f"  {check_icon(None)} Server check: skipped ({type(e).__name__}: {e})")

    # Summary
    passed = sum(1 for _, _, ok in all_checks if ok is True)
    failed = sum(1 for _, _, ok in all_checks if ok is False)
    optional = sum(1 for _, _, ok in all_checks if ok is None)

    print("\n" + "=" * 50)
    print(f"\033[1mSummary:\033[0m {passed} passed, {failed} failed, {optional} optional")

    if all_ok:
        print("\n\033[92m✓ Aragora is ready to use!\033[0m\n")
    else:
        print("\n\033[91m✗ Some required checks failed. Please fix the issues above.\033[0m\n")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

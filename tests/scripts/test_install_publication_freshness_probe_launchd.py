"""Tests for the publication-freshness probe LaunchAgent template and installer."""

from __future__ import annotations

import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALLER = REPO_ROOT / "scripts" / "install_publication_freshness_probe_launchd.sh"
TEMPLATE = REPO_ROOT / "scripts" / "launch_agents" / "com.aragora.publication-freshness-probe.plist"
LABEL = "com.aragora.publication-freshness-probe"


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(INSTALLER), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env if env is not None else os.environ.copy(),
    )


def test_template_exists_and_is_xml_plist() -> None:
    assert TEMPLATE.is_file(), TEMPLATE
    text = TEMPLATE.read_text(encoding="utf-8")
    assert text.lstrip().startswith("<?xml"), "template must declare XML prolog"
    assert "DOCTYPE plist" in text
    assert '<plist version="1.0">' in text
    assert "</plist>" in text


def test_template_uses_placeholders_only() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "__ARAGORA_REPO_ROOT__" in text, "template must keep repo-root placeholder"
    assert "__ARAGORA_PYTHON__" in text, "template must keep python placeholder"
    # No absolute armand-specific paths in the template.
    assert "/Users/armand" not in text, "template must stay path-agnostic"


def test_template_label_matches_filename() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert f"<string>{LABEL}</string>" in text
    assert TEMPLATE.name == f"{LABEL}.plist"


def test_template_runs_the_freshness_probe_with_render_markdown() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "scripts/publish_publication_freshness_probe.py" in text
    assert "--render-markdown" in text


def test_template_has_default_interval_4h() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "<integer>14400</integer>" in text, "default StartInterval should be 4h"


def test_installer_help_exits_zero() -> None:
    cp = _run(["--help"])
    assert cp.returncode == 0, (cp.stdout, cp.stderr)
    assert "Usage" in cp.stdout
    assert "--dry-run" in cp.stdout
    assert "--uninstall" in cp.stdout


def test_installer_unknown_flag_exits_two() -> None:
    cp = _run(["--definitely-not-a-flag"])
    assert cp.returncode == 2, (cp.stdout, cp.stderr)
    assert "Unknown option" in cp.stderr


def test_installer_non_numeric_interval_rejected() -> None:
    cp = _run(["--interval-seconds", "abc", "--dry-run"])
    assert cp.returncode == 2, (cp.stdout, cp.stderr)
    assert "numeric" in cp.stderr.lower()


def test_installer_dry_run_substitutes_repo_root_and_python(tmp_path: Path) -> None:
    fake_py = tmp_path / "python3"
    fake_py.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    fake_py.chmod(0o755)

    cp = _run(["--dry-run", "--python", str(fake_py)])
    assert cp.returncode == 0, (cp.stdout, cp.stderr)
    out = cp.stdout

    assert "__ARAGORA_REPO_ROOT__" not in out, "placeholder must be substituted"
    assert "__ARAGORA_PYTHON__" not in out, "placeholder must be substituted"
    assert str(REPO_ROOT) in out
    assert str(fake_py) in out
    assert "scripts/publish_publication_freshness_probe.py" in out
    assert "--render-markdown" in out


def test_installer_dry_run_changes_interval(tmp_path: Path) -> None:
    fake_py = tmp_path / "python3"
    fake_py.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    fake_py.chmod(0o755)

    cp = _run(["--dry-run", "--python", str(fake_py), "--interval-seconds", "3600"])
    assert cp.returncode == 0, (cp.stdout, cp.stderr)
    assert "<integer>3600</integer>" in cp.stdout
    assert "<integer>14400</integer>" not in cp.stdout


def test_installer_dry_run_output_is_valid_plist_xml(tmp_path: Path) -> None:
    fake_py = tmp_path / "python3"
    fake_py.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    fake_py.chmod(0o755)

    cp = _run(["--dry-run", "--python", str(fake_py)])
    assert cp.returncode == 0, (cp.stdout, cp.stderr)
    # Strip the XML+DOCTYPE prologue and parse just the <plist>...</plist> block,
    # because ElementTree refuses external DTD references.
    plist_match = re.search(r"<plist .*?</plist>", cp.stdout, re.DOTALL)
    assert plist_match is not None, "rendered output must contain a <plist> element"
    root = ET.fromstring(plist_match.group(0))
    assert root.tag == "plist"
    # Label key must be present.
    found_label = False
    for elem in root.iter("string"):
        if elem.text == LABEL:
            found_label = True
            break
    assert found_label, "rendered plist must contain the LaunchAgent label"


def test_installer_does_not_write_anywhere_when_dry_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(fake_home)

    fake_py = tmp_path / "python3"
    fake_py.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    fake_py.chmod(0o755)

    cp = _run(["--dry-run", "--python", str(fake_py)], env=env)
    assert cp.returncode == 0, (cp.stdout, cp.stderr)
    assert not (fake_home / "Library" / "LaunchAgents" / f"{LABEL}.plist").exists()


def test_installer_uninstall_is_idempotent(tmp_path: Path) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(fake_home)

    cp = _run(["--uninstall"], env=env)
    assert cp.returncode == 0, (cp.stdout, cp.stderr)
    assert "Nothing to uninstall" in cp.stdout
    assert not (fake_home / "Library" / "LaunchAgents" / f"{LABEL}.plist").exists()


def test_installer_no_automation_invokes_it() -> None:
    """The installer must remain strictly opt-in: no executable script in the
    repo should call it automatically. We grep all `.sh` and `.py` files
    under scripts/ for invocations and require zero hits outside the
    installer itself. Documentation strings inside the template plist or
    inside the installer are not considered invocations."""

    scripts_dir = REPO_ROOT / "scripts"
    needle = "install_publication_freshness_probe_launchd.sh"
    hits: list[Path] = []
    for path in scripts_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".sh", ".py"}:
            continue
        if path.name == "install_publication_freshness_probe_launchd.sh":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        if needle in text:
            hits.append(path)
    assert hits == [], f"installer must not be auto-invoked, but found: {hits}"


def test_installer_makes_executable_with_shebang() -> None:
    text = INSTALLER.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash") or text.startswith("#!/bin/bash")
    assert os.access(INSTALLER, os.X_OK), "installer must be marked executable"

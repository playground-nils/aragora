"""Tests for scripts/check_codex_desktop_automations.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


@pytest.fixture(autouse=True)
def _setup_path():
    sys.path.insert(0, str(SCRIPTS_DIR))
    yield
    sys.path.remove(str(SCRIPTS_DIR))


def _write_automation(
    root: Path,
    automation_id: str,
    *,
    name: str,
    prompt: str,
    byminute: int,
    status: str = "ACTIVE",
) -> None:
    path = root / automation_id
    path.mkdir(parents=True)
    (path / "automation.toml").write_text(
        "\n".join(
            [
                "version = 1",
                f'id = "{automation_id}"',
                'kind = "cron"',
                f'name = "{name}"',
                f'prompt = "{prompt}"',
                f'status = "{status}"',
                f'rrule = "FREQ=HOURLY;INTERVAL=1;BYMINUTE={byminute}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_audit_detects_paused_core_writer(tmp_path: Path) -> None:
    import check_codex_desktop_automations as mod

    for automation_id, minute in mod.CORE_WRITERS.items():
        _write_automation(
            tmp_path,
            automation_id,
            name=f"{automation_id} Writer",
            prompt="Paused during queue drain.",
            byminute=minute,
        )

    payload = mod.build_payload(tmp_path)

    codes = {issue["code"] for issue in payload["issues"]}
    assert "active_paused_prompt" in codes
    assert "missing_prompt_word_outbox" in codes


def test_audit_accepts_staggered_writer_contracts(tmp_path: Path) -> None:
    import check_codex_desktop_automations as mod

    prompt = "Read memory, repair one branch, validate locally, then refresh outbox."
    for automation_id, minute in mod.CORE_WRITERS.items():
        _write_automation(
            tmp_path,
            automation_id,
            name=f"{automation_id} Writer",
            prompt=prompt,
            byminute=minute,
        )

    payload = mod.build_payload(tmp_path)

    assert payload["summary"] == {"active_count": 4, "error_count": 0, "warning_count": 0}


def test_audit_warns_duplicate_writer_minutes(tmp_path: Path) -> None:
    import check_codex_desktop_automations as mod

    prompt = "Read memory, repair one branch, validate locally, then refresh outbox."
    for automation_id in mod.CORE_WRITERS:
        _write_automation(
            tmp_path,
            automation_id,
            name=f"{automation_id} Writer",
            prompt=prompt,
            byminute=5,
        )

    payload = mod.build_payload(tmp_path)

    assert any(issue["code"] == "duplicate_writer_minute" for issue in payload["issues"])
    assert any(issue["code"] == "writer_not_staggered" for issue in payload["issues"])


def test_build_payload_reports_invalid_automation_toml_and_continues(
    tmp_path: Path,
) -> None:
    import check_codex_desktop_automations as mod

    prompt = "Read memory, repair one branch, validate locally, then refresh outbox."
    for automation_id, minute in mod.CORE_WRITERS.items():
        _write_automation(
            tmp_path,
            automation_id,
            name=f"{automation_id} Writer",
            prompt=prompt,
            byminute=minute,
        )
    broken = tmp_path / "broken-writer"
    broken.mkdir()
    (broken / "automation.toml").write_text(
        'id = "broken-writer"\nprompt = "unterminated\n',
        encoding="utf-8",
    )

    payload = mod.build_payload(tmp_path)

    assert payload["summary"] == {"active_count": 4, "error_count": 1, "warning_count": 0}
    assert payload["automation_count"] == 4
    assert payload["issues"] == [
        {
            "automation_id": "broken-writer",
            "severity": "error",
            "code": "invalid_automation_definition",
            "message": (
                f"failed to load {broken / 'automation.toml'}: "
                "Illegal character '\\n' (at line 2, column 23)"
            ),
        }
    ]

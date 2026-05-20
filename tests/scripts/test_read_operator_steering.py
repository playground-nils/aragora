"""Fixture tests for ``scripts/read_operator_steering.py``."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest


def _load_script(name: str) -> Any:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / f"{name}.py"
    scripts_dir = str(script_path.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(f"{name}_under_test", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load spec for {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sos = _load_script("send_operator_steering")
ros = _load_script("read_operator_steering")


def _write_message(root: Path, recipient: str, body: str) -> Path:
    message = sos.build_message(
        to_session=recipient,
        body=body,
        from_label="operator-test",
        lane_id_hint="Q-test",
        pr_hint=7373,
        priority="blocking",
        sent_at_utc="2026-05-19T22:00:00.000Z",
    )
    return sos.write_message(message, steering_inbox_root=root)


def test_reads_only_selected_owner_and_writes_bound_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target_message = _write_message(tmp_path, "codex-target", "continue the target lane")
    other_message = _write_message(tmp_path, "codex-other", "do not read this")

    rc = ros.main(
        [
            "--to",
            "codex-target",
            "--read-by-session",
            "codex-reader",
            "--outcome",
            "obeyed",
            "--json",
            "--steering-inbox-root",
            str(tmp_path),
        ]
    )

    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["owner_session"] == "codex-target"
    assert data["message_count"] == 1
    assert data["receipt_count"] == 1
    assert data["messages"][0]["filename"] == target_message.name
    assert data["messages"][0]["sha256_valid"] is True

    receipts = sorted((tmp_path / "codex-target" / "_read_receipts").glob("*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
    original = json.loads(target_message.read_text(encoding="utf-8"))
    assert receipt["schema_version"] == "aragora-operator-steering-read-receipt/1.0"
    assert receipt["owner_session"] == "codex-target"
    assert receipt["read_by_session"] == "codex-reader"
    assert receipt["message_filename"] == target_message.name
    assert receipt["message_sha256"] == original["message_sha256"]
    assert receipt["priority"] == "blocking"
    assert receipt["lane_id_hint"] == "Q-test"
    assert receipt["pr_hint"] == 7373
    assert receipt["outcome"] == "obeyed"
    assert target_message.exists()
    assert other_message.exists()
    assert not (tmp_path / "codex-other" / "_read_receipts").exists()


def test_no_receipt_lists_messages_without_writing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_message(tmp_path, "codex-target", "read-only inspection")

    rc = ros.main(
        [
            "--to",
            "codex-target",
            "--no-receipt",
            "--json",
            "--steering-inbox-root",
            str(tmp_path),
        ]
    )

    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["message_count"] == 1
    assert data["receipt_count"] == 0
    assert data["no_receipt"] is True
    assert not (tmp_path / "codex-target" / "_read_receipts").exists()


def test_rejects_unsafe_session_before_reading(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = ros.main(["--to", "../escape", "--json", "--steering-inbox-root", str(tmp_path)])

    assert rc == 2
    assert "path separators" in capsys.readouterr().err


def test_resolves_owner_by_lane_id(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_message(tmp_path, "codex-lane-owner", "lane-routed message")
    registry = tmp_path / "lanes.json"
    registry.write_text(
        json.dumps(
            [
                {
                    "lane_id": "Q-lane",
                    "owner_session": "codex-lane-owner",
                    "status": "active",
                    "branch": "codex/test",
                    "pr_number": 7373,
                }
            ]
        ),
        encoding="utf-8",
    )

    rc = ros.main(
        [
            "--lane-id",
            "Q-lane",
            "--json",
            "--registry-path",
            str(registry),
            "--steering-inbox-root",
            str(tmp_path),
        ]
    )

    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["owner_session"] == "codex-lane-owner"
    assert data["resolved_via"] == "lane-id"
    assert data["lane_id"] == "Q-lane"
    assert data["pr_number"] == 7373
    assert data["receipt_count"] == 1

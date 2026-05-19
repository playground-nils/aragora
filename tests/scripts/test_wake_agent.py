"""Tests for ``scripts/wake_agent.sh`` (R02 — reach plan Phase 2).

Pattern mirrors ``tests/scripts/test_tmux_transport_scripts.py`` — invoke
the bash script with subprocess against a tmp HOME / repo-root scaffold,
and assert on dispatch receipts + exit codes.

R02 depends on R01's `contact_method` field but degrades gracefully when
the field is absent (falls back to mailbox-only by default), so these
tests do not require R01 to be on main.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WAKE_SCRIPT = REPO_ROOT / "scripts" / "wake_agent.sh"


def _make_fake_repo(tmp_path: Path) -> Path:
    """Build a minimal repo skeleton that mirrors what wake_agent.sh expects."""
    fake_repo = tmp_path / "fake_repo"
    (fake_repo / "scripts").mkdir(parents=True)
    (fake_repo / ".aragora" / "agent-bridge").mkdir(parents=True)
    (fake_repo / ".aragora" / "dispatch-receipts").mkdir(parents=True)

    # Copy the script under test into the fake repo so REPO_ROOT resolves correctly.
    target_script = fake_repo / "scripts" / "wake_agent.sh"
    target_script.write_bytes(WAKE_SCRIPT.read_bytes())
    target_script.chmod(target_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return fake_repo


def _write_lane(
    fake_repo: Path, lane_id: str, *, owner: str, contact_method: str | None = None
) -> None:
    registry = fake_repo / ".aragora" / "agent-bridge" / "lanes.json"
    row: dict[str, object] = {"lane_id": lane_id, "owner_session": owner, "status": "active"}
    if contact_method is not None:
        row["contact_method"] = contact_method
    registry.write_text(json.dumps([row]), encoding="utf-8")


def _write_fake_backend(fake_repo: Path, name: str, log_file: Path, *, exit_code: int = 0) -> None:
    """Drop a fake backend script under the fake repo's scripts/ dir."""
    script = fake_repo / "scripts" / name
    script.write_text(
        f"""#!/usr/bin/env bash
echo "$@" >> "{log_file}"
exit {exit_code}
"""
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _run(fake_repo: Path, *args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HOME"] = str(fake_repo.parent)  # so the user-registry fallback uses tmp
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(fake_repo / "scripts" / "wake_agent.sh"), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(fake_repo),
        check=False,
    )


# ----- usage / arg validation -----


def test_no_lane_flag_errors(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    result = _run(fake_repo, "--prompt", "hi")
    assert result.returncode == 1
    assert "--lane is required" in result.stderr


def test_no_prompt_errors(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    result = _run(fake_repo, "--lane", "L1")
    assert result.returncode == 1
    assert "--prompt or --prompt-file is required" in result.stderr


def test_both_prompt_forms_errors(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    pf = tmp_path / "p.txt"
    pf.write_text("hi")
    result = _run(fake_repo, "--lane", "L1", "--prompt", "x", "--prompt-file", str(pf))
    assert result.returncode == 1
    assert "mutually exclusive" in result.stderr


def test_invalid_priority_errors(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi", "--priority", "bogus")
    assert result.returncode == 1
    assert "must be one of low|normal|high|blocking" in result.stderr


def test_invalid_fallback_errors(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi", "--fallback", "bogus")
    assert result.returncode == 1
    assert "must be one of mailbox-only|fail" in result.stderr


# ----- lane resolution -----


def test_lane_not_found_exits_2(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    # No lanes.json written.
    result = _run(fake_repo, "--lane", "missing", "--prompt", "hi")
    assert result.returncode == 2
    assert "lane not found" in result.stderr


# ----- dispatch backend selection -----


def test_tmux_backend_dry_run_writes_receipt(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(fake_repo, "L1", owner="claude-A", contact_method="tmux:claude-p52")
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi", "--json")
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["chosen_backend"] == "tmux"
    assert receipt["backend_target"] == "claude-p52"
    assert receipt["mode"] == "dry-run"
    assert receipt["dispatch_attempted"] is False
    assert receipt["dispatch_outcome"] == "dry-run-only"


def test_mailbox_backend_dry_run_uses_owner(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(fake_repo, "L1", owner="droid-X", contact_method="mailbox-only")
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi", "--json")
    assert result.returncode == 0
    receipt = json.loads(result.stdout)
    assert receipt["chosen_backend"] == "mailbox-only"
    assert receipt["backend_target"] == "droid-X"


def test_missing_contact_method_defaults_to_mailbox(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(fake_repo, "L1", owner="codex-Y", contact_method=None)
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi", "--json")
    assert result.returncode == 0
    receipt = json.loads(result.stdout)
    assert receipt["chosen_backend"] == "mailbox-only"
    assert receipt["backend_target"] == "codex-Y"


def test_missing_contact_method_with_fail_fallback_exits_3(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(fake_repo, "L1", owner="codex-Y", contact_method=None)
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi", "--fallback", "fail")
    assert result.returncode == 3
    assert "no contact_method" in result.stderr


def test_unknown_backend_falls_back_to_mailbox(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(
        fake_repo, "L1", owner="codex-Z", contact_method="osascript:codex-desktop:thread-abc"
    )
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi", "--json")
    assert result.returncode == 0
    receipt = json.loads(result.stdout)
    assert receipt["chosen_backend"] == "mailbox-only"
    assert receipt["backend_target"] == "codex-Z"


def test_unknown_backend_with_fail_fallback_exits_3(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(fake_repo, "L1", owner="codex-Z", contact_method="factory-api:sess-1")
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi", "--fallback", "fail")
    assert result.returncode == 3
    assert "not implemented" in result.stderr


# ----- receipt schema -----


def test_receipt_includes_sha256_of_prompt(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(fake_repo, "L1", owner="claude-A", contact_method="tmux:claude-p52")
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi", "--json")
    receipt = json.loads(result.stdout)
    # SHA256 of "hi" with no trailing newline
    assert (
        receipt["prompt_sha256"]
        == "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4"
    )


def test_receipt_schema_version(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(fake_repo, "L1", owner="claude-A", contact_method="tmux:claude-p52")
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi", "--json")
    receipt = json.loads(result.stdout)
    assert receipt["schema_version"] == "aragora-wake-agent-receipt/1.0"


def test_receipt_persisted_to_dispatch_receipts_dir(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(fake_repo, "L1", owner="claude-A", contact_method="tmux:claude-p52")
    _run(fake_repo, "--lane", "L1", "--prompt", "hi")
    receipts = list((fake_repo / ".aragora" / "dispatch-receipts").iterdir())
    assert len(receipts) == 1
    data = json.loads(receipts[0].read_text())
    assert data["lane_id"] == "L1"


# ----- apply mode (with fake backends) -----


def test_apply_mode_invokes_tmux_backend(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(fake_repo, "L1", owner="claude-A", contact_method="tmux:claude-p52")
    log = tmp_path / "tmux.log"
    _write_fake_backend(fake_repo, "tmux_send_prompt.sh", log)
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi", "--apply", "--json")
    assert result.returncode == 0
    receipt = json.loads(result.stdout)
    assert receipt["mode"] == "apply"
    assert receipt["dispatch_attempted"] is True
    assert receipt["dispatch_outcome"] == "dispatched"
    assert log.read_text().strip()  # backend was called with some args


def test_apply_mode_records_backend_failure(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(fake_repo, "L1", owner="claude-A", contact_method="tmux:claude-p52")
    log = tmp_path / "tmux.log"
    _write_fake_backend(fake_repo, "tmux_send_prompt.sh", log, exit_code=7)
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi", "--apply", "--json")
    assert result.returncode == 4
    receipt = json.loads(result.stdout)
    assert receipt["dispatch_outcome"] == "failed"
    assert "non-zero" in (receipt.get("dispatch_error") or "")


def test_apply_mode_invokes_mailbox_backend(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(fake_repo, "L1", owner="droid-X", contact_method="mailbox-only")
    log = tmp_path / "mailbox.log"
    # send_operator_steering.py is a Python script; emulate by writing a bash
    # shim with the same name. wake_agent.sh shells out via `python3` so we
    # need a real .py — instead make the .py file invoke a logger.
    py_script = fake_repo / "scripts" / "send_operator_steering.py"
    py_script.write_text(
        f"""#!/usr/bin/env python3
import sys
with open("{log}", "a") as fh:
    fh.write(" ".join(sys.argv[1:]) + "\\n")
sys.exit(0)
"""
    )
    py_script.chmod(py_script.stat().st_mode | stat.S_IXUSR)
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi", "--apply", "--json")
    assert result.returncode == 0
    receipt = json.loads(result.stdout)
    assert receipt["chosen_backend"] == "mailbox-only"
    assert receipt["dispatch_outcome"] == "dispatched"
    assert "droid-X" in log.read_text()


# ----- priority + json wiring -----


@pytest.mark.parametrize("priority", ["low", "normal", "high", "blocking"])
def test_priority_round_trips(tmp_path: Path, priority: str) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(fake_repo, "L1", owner="claude-A", contact_method="tmux:claude-p52")
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi", "--priority", priority, "--json")
    receipt = json.loads(result.stdout)
    assert receipt["priority"] == priority


def test_non_json_output_is_human_readable(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(fake_repo, "L1", owner="claude-A", contact_method="tmux:claude-p52")
    result = _run(fake_repo, "--lane", "L1", "--prompt", "hi")
    assert result.returncode == 0
    assert "wake_agent:" in result.stdout
    assert "lane=L1" in result.stdout
    assert "backend=tmux" in result.stdout


# ----- prompt-file path -----


def test_prompt_file_is_read(tmp_path: Path) -> None:
    fake_repo = _make_fake_repo(tmp_path)
    _write_lane(fake_repo, "L1", owner="claude-A", contact_method="tmux:claude-p52")
    pf = tmp_path / "prompt.txt"
    pf.write_text("hello from file\nsecond line")
    result = _run(fake_repo, "--lane", "L1", "--prompt-file", str(pf), "--json")
    receipt = json.loads(result.stdout)
    # SHA256 of "hello from file\nsecond line" (no trailing newline)
    import hashlib

    expected = hashlib.sha256(b"hello from file\nsecond line").hexdigest()
    assert receipt["prompt_sha256"] == expected

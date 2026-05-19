"""Subprocess-style tests for ``scripts/sign_delegation_contract.py``.

The CLI is a thin shim around ``aragora.policy.contract_signing``; these
tests exercise the script via the same Python interpreter to keep the
suite hermetic and fast.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "sign_delegation_contract.py"


def _sample_contract_json(tmp_path: Path) -> Path:
    """Write a minimal valid unsigned contract to ``tmp_path/contract.json``."""
    # Pull the canonical encoding from the live module so we don't drift.
    from aragora.policy import make_root_contract
    from aragora.policy.contract_signing import canonical_contract_payload

    contract = make_root_contract(
        contract_id="cli-test-1",
        root_intent_id="intent-cli-1",
        delegator="operator",
        delegatee="droid-cli",
        goal_id="G-cli",
        allowed_actions=("read:*",),
        duration_minutes=60,
    )
    payload = canonical_contract_payload(contract)
    raw_obj = json.loads(payload.decode("utf-8"))
    raw_obj["signature"] = None  # make the unsigned mode explicit on disk
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(raw_obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _run(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), *args]
    merged_env = os.environ.copy()
    # Default to a hermetic env that does NOT carry the user's signing key.
    merged_env.pop("ARAGORA_CONTEXT_SIGNING_KEY", None)
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
        env=merged_env,
    )


def _fixture_hmac_material() -> str:
    """Synthetic test-only HMAC fixture: 32 deterministic bytes,
    base64-encoded. Not a real secret — just exercises the signer."""
    return base64.b64encode(b"\x11" * 32).decode()


# ---------------------------------------------------------------------------
# 1. Sign a valid unsigned contract.
# ---------------------------------------------------------------------------


def test_signs_unsigned_contract_with_env_key(tmp_path: Path) -> None:
    contract_path = _sample_contract_json(tmp_path)
    out_path = tmp_path / "signed.json"

    result = _run(
        ["--in", str(contract_path), "--out", str(out_path)],
        env={"ARAGORA_CONTEXT_SIGNING_KEY": _fixture_hmac_material()},
    )
    assert result.returncode == 0, result.stderr
    assert out_path.exists()

    signed = json.loads(out_path.read_text(encoding="utf-8"))
    assert isinstance(signed.get("signature"), str)
    assert len(signed["signature"]) == 64  # SHA-256 hex digest


# ---------------------------------------------------------------------------
# 2. Verify a signed contract.
# ---------------------------------------------------------------------------


def test_verify_only_succeeds_on_signed_contract(tmp_path: Path) -> None:
    contract_path = _sample_contract_json(tmp_path)
    out_path = tmp_path / "signed.json"

    # Sign first.
    sign_res = _run(
        ["--in", str(contract_path), "--out", str(out_path)],
        env={"ARAGORA_CONTEXT_SIGNING_KEY": _fixture_hmac_material()},
    )
    assert sign_res.returncode == 0, sign_res.stderr

    # Verify.
    verify_res = _run(
        ["--in", str(out_path), "--verify-only"],
        env={"ARAGORA_CONTEXT_SIGNING_KEY": _fixture_hmac_material()},
    )
    assert verify_res.returncode == 0, verify_res.stderr
    assert "OK" in verify_res.stdout


# ---------------------------------------------------------------------------
# 3. --require-signed without a key fails clearly.
# ---------------------------------------------------------------------------


def test_require_signed_without_key_fails(tmp_path: Path) -> None:
    contract_path = _sample_contract_json(tmp_path)
    out_path = tmp_path / "should-not-exist.json"

    result = _run(
        ["--in", str(contract_path), "--out", str(out_path), "--require-signed"],
    )
    assert result.returncode == 2, result.stderr
    assert "no signing key" in result.stderr.lower()
    assert not out_path.exists()


# ---------------------------------------------------------------------------
# 4. --verify-only against tampered contract exits non-zero.
# ---------------------------------------------------------------------------


def test_verify_only_detects_tamper(tmp_path: Path) -> None:
    contract_path = _sample_contract_json(tmp_path)
    out_path = tmp_path / "signed.json"

    sign_res = _run(
        ["--in", str(contract_path), "--out", str(out_path)],
        env={"ARAGORA_CONTEXT_SIGNING_KEY": _fixture_hmac_material()},
    )
    assert sign_res.returncode == 0, sign_res.stderr

    # Tamper: mutate delegatee while keeping the signature intact.
    signed_obj = json.loads(out_path.read_text(encoding="utf-8"))
    signed_obj["delegatee"] = "evil-agent"
    tampered_path = tmp_path / "tampered.json"
    tampered_path.write_text(json.dumps(signed_obj, indent=2, sort_keys=True), encoding="utf-8")

    verify_res = _run(
        ["--in", str(tampered_path), "--verify-only"],
        env={"ARAGORA_CONTEXT_SIGNING_KEY": _fixture_hmac_material()},
    )
    assert verify_res.returncode == 3, (verify_res.returncode, verify_res.stderr)
    assert "VERIFY-FAILED" in verify_res.stderr


# ---------------------------------------------------------------------------
# 5. --verify-only against unsigned contract exits 4.
# ---------------------------------------------------------------------------


def test_verify_only_on_unsigned_returns_exit_4(tmp_path: Path) -> None:
    contract_path = _sample_contract_json(tmp_path)
    verify_res = _run(
        ["--in", str(contract_path), "--verify-only"],
        env={"ARAGORA_CONTEXT_SIGNING_KEY": _fixture_hmac_material()},
    )
    assert verify_res.returncode == 4
    assert "UNSIGNED" in verify_res.stderr


# ---------------------------------------------------------------------------
# 6. Sign via --key-b64 instead of env var.
# ---------------------------------------------------------------------------


def test_sign_with_explicit_key_b64(tmp_path: Path) -> None:
    contract_path = _sample_contract_json(tmp_path)
    out_path = tmp_path / "signed.json"
    result = _run(
        [
            "--in",
            str(contract_path),
            "--out",
            str(out_path),
            "--key-b64",
            _fixture_hmac_material(),
        ],
    )
    assert result.returncode == 0, result.stderr
    signed = json.loads(out_path.read_text(encoding="utf-8"))
    assert signed.get("signature")

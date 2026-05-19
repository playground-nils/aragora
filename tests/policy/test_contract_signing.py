"""Tests for ``aragora.policy.contract_signing`` — Delegation Contract v0.4.

Covers:
- canonical_contract_payload is deterministic, omits the signature field,
  and is stable across frozenset / dict ordering
- sign_contract → verify_contract round-trip
- tamper detection (mutated field → verification fails)
- unsigned-mode verification (signed=False, ok=False, no error)
- key resolution (explicit > env > missing-raises)
- sign_receipt → verify_receipt round-trip
- cross-key incompatibility (key A signs, key B fails)
- parent → child narrowing preserves signature semantics
"""

from __future__ import annotations

import base64
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from aragora.policy import (
    ContractBudget,
    ContractValidationError,
    DelegationContract,
    RiskBudget,
    SigningError,
    canonical_contract_payload,
    is_contract_signed,
    make_root_contract,
    narrow_for_child,
    sign_contract,
    sign_receipt,
    signing_key_available,
    verify_contract,
    verify_receipt,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso(offset_minutes: int = 0) -> str:
    return (datetime.now(UTC) + timedelta(minutes=offset_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_parent() -> DelegationContract:
    return make_root_contract(
        contract_id="root-1",
        root_intent_id="intent-1",
        delegator="an0mium",
        delegatee="claude-A",
        goal_id="G-foo",
        allowed_actions=("read:*", "write:branch:claude/*", "spawn:subagent"),
        max_depth=3,
        duration_minutes=120,
        stale_threshold_minutes=30,
        destructive_action_policy="deny",
    )


KEY_A = b"\x01" * 32
KEY_B = b"\x02" * 32


@pytest.fixture(autouse=True)
def _clean_signing_env(monkeypatch):
    """Ensure tests start with no env-backed signing key."""
    monkeypatch.delenv("ARAGORA_CONTEXT_SIGNING_KEY", raising=False)
    yield


# ---------------------------------------------------------------------------
# 1-3. Canonicalization properties
# ---------------------------------------------------------------------------


def test_canonical_payload_is_deterministic() -> None:
    """Same contract → same canonical bytes across two calls."""
    contract = _make_parent()
    assert canonical_contract_payload(contract) == canonical_contract_payload(contract)


def test_canonical_payload_omits_signature_field() -> None:
    """The signing payload must not include the `signature` key."""
    contract = _make_parent()
    payload = canonical_contract_payload(contract)
    decoded = json.loads(payload.decode("utf-8"))
    assert "signature" not in decoded
    # And a signed contract produces the same payload as its unsigned form.
    signed = sign_contract(contract, key=KEY_A)
    assert canonical_contract_payload(signed) == payload


def test_canonical_payload_stable_under_field_order_changes() -> None:
    """Frozenset / dict order must not change the canonical bytes.

    We rebuild the same logical contract twice with different iteration-order
    seeds and confirm the canonical bytes match.
    """
    c1 = _make_parent()
    # Rebuild with the same logical content but reversed iteration order for
    # the allowed_actions set. frozenset already has unspecified order, but
    # canonical_contract_payload must sort it before serializing.
    c2 = replace(
        c1,
        allowed_actions=frozenset(sorted(c1.allowed_actions, reverse=True)),
        denied_actions=frozenset(sorted(c1.denied_actions, reverse=True)),
    )
    assert canonical_contract_payload(c1) == canonical_contract_payload(c2)


# ---------------------------------------------------------------------------
# 4-5. Sign / verify round-trip
# ---------------------------------------------------------------------------


def test_sign_then_verify_round_trip() -> None:
    contract = _make_parent()
    signed = sign_contract(contract, key=KEY_A)
    assert signed.signature is not None
    assert is_contract_signed(signed)
    result = verify_contract(signed, key=KEY_A)
    assert result.ok is True
    assert result.signed is True


def test_verify_detects_tamper() -> None:
    """Mutating any signed field must invalidate the signature."""
    contract = _make_parent()
    signed = sign_contract(contract, key=KEY_A)
    # Tamper: change the delegatee.
    tampered = replace(signed, delegatee="evil-agent")
    result = verify_contract(tampered, key=KEY_A)
    assert result.ok is False
    assert result.signed is True
    assert "tampered" in result.reason or "match" in result.reason


# ---------------------------------------------------------------------------
# 6. Unsigned-mode behavior
# ---------------------------------------------------------------------------


def test_verify_unsigned_returns_signed_false_without_raising() -> None:
    contract = _make_parent()
    assert contract.signature is None
    result = verify_contract(contract, key=KEY_A)
    assert result.ok is False
    assert result.signed is False
    # Reason must explain it's an unsigned-mode result, not a verify failure.
    assert "unsigned" in result.reason.lower()


# ---------------------------------------------------------------------------
# 7. Key resolution
# ---------------------------------------------------------------------------


def test_signing_requires_key_explicit_or_env(monkeypatch) -> None:
    """Without an explicit key AND without env var, signing must raise."""
    contract = _make_parent()
    monkeypatch.delenv("ARAGORA_CONTEXT_SIGNING_KEY", raising=False)
    with pytest.raises(SigningError, match="no signing key"):
        sign_contract(contract)

    # Setting the env var resolves the key (base64-encoded).
    monkeypatch.setenv("ARAGORA_CONTEXT_SIGNING_KEY", base64.b64encode(KEY_A).decode())
    signed = sign_contract(contract)
    assert signed.signature is not None
    assert verify_contract(signed).ok is True
    assert signing_key_available() is True


# ---------------------------------------------------------------------------
# 8. Receipt round-trip
# ---------------------------------------------------------------------------


def test_sign_receipt_then_verify_round_trip() -> None:
    receipt = {
        "lane_id": "ADC-v0.4-hmac-signing",
        "session_id": "droid-FAKE",
        "outcome": "shipped",
        "pr_number": 9999,
        "nested": {"a": 1, "b": [3, 1, 2]},
    }
    signed = sign_receipt(receipt, key=KEY_A)
    assert "signature" in signed
    assert signed["signature"] is not None
    # Original receipt unchanged (sign_receipt is non-mutating).
    assert "signature" not in receipt

    result = verify_receipt(signed, key=KEY_A)
    assert result.ok is True
    assert result.signed is True

    # Tamper detection: change a field.
    tampered = dict(signed)
    tampered["outcome"] = "fraudulent-shipped"
    assert verify_receipt(tampered, key=KEY_A).ok is False


def test_sign_receipt_idempotent_with_same_key() -> None:
    """Signing a receipt twice with the same key produces the same digest."""
    receipt = {"lane_id": "X", "n": 1}
    s1 = sign_receipt(receipt, key=KEY_A)
    s2 = sign_receipt(s1, key=KEY_A)
    assert s1["signature"] == s2["signature"]


# ---------------------------------------------------------------------------
# 9. Cross-key incompatibility
# ---------------------------------------------------------------------------


def test_contract_signed_with_key_a_fails_under_key_b() -> None:
    contract = _make_parent()
    signed_a = sign_contract(contract, key=KEY_A)
    result = verify_contract(signed_a, key=KEY_B)
    assert result.ok is False
    assert result.signed is True


def test_receipt_signed_with_key_a_fails_under_key_b() -> None:
    receipt = {"k": "v"}
    signed_a = sign_receipt(receipt, key=KEY_A)
    assert verify_receipt(signed_a, key=KEY_B).ok is False


# ---------------------------------------------------------------------------
# 10. Parent → child narrowing preserves signature semantics
# ---------------------------------------------------------------------------


def test_child_carries_own_signature_not_parent_transcription() -> None:
    """``narrow_for_child`` mints a child with its own (None at issue time)
    signature; the parent's signature is referenced via parent_contract_id
    in the authority chain, not copied into the child's signature field.
    """
    parent = _make_parent()
    signed_parent = sign_contract(parent, key=KEY_A)
    child = narrow_for_child(
        signed_parent,
        child_contract_id="child-1",
        child_delegatee="claude-B",
        child_allowed_actions=frozenset({"read:*"}),
        child_budget=ContractBudget(risk_budget=RiskBudget()),
        child_stale_threshold_minutes=15,
        child_expires_at=_now_iso(60),
    )
    # Child starts unsigned and references the signed parent by id.
    assert child.signature is None
    assert child.is_signed is False
    assert child.parent_contract_id == signed_parent.contract_id
    # Parent's signature is intact; not consumed by the narrowing step.
    assert signed_parent.signature is not None
    assert verify_contract(signed_parent, key=KEY_A).ok is True

    # Signing the child independently works and remains independent of parent.
    signed_child = sign_contract(child, key=KEY_A)
    assert signed_child.signature != signed_parent.signature
    assert verify_contract(signed_child, key=KEY_A).ok is True


# ---------------------------------------------------------------------------
# Bonus: validation of populated signatures
# ---------------------------------------------------------------------------


def test_contract_validate_accepts_hex_signature_without_env_key(monkeypatch) -> None:
    """With no env-backed key, validate() accepts a well-shaped signature
    (hex string) without cryptographic verification."""
    monkeypatch.delenv("ARAGORA_CONTEXT_SIGNING_KEY", raising=False)
    parent = _make_parent()
    signed = sign_contract(parent, key=KEY_A)
    # Should not raise even though the env key is absent.
    signed.validate()


def test_contract_validate_rejects_non_hex_signature() -> None:
    parent = _make_parent()
    forged = replace(parent, signature="not-hex-content!!")
    with pytest.raises(ContractValidationError, match="hex"):
        forged.validate()


def test_contract_validate_with_env_key_verifies_signature(monkeypatch) -> None:
    """When the env key is set, validate() cryptographically verifies."""
    monkeypatch.setenv("ARAGORA_CONTEXT_SIGNING_KEY", base64.b64encode(KEY_A).decode())
    contract = _make_parent()
    signed = sign_contract(contract)  # picks up env key
    signed.validate()
    # Now flip a field; signature no longer matches → validate raises.
    tampered = replace(signed, delegatee="evil")
    with pytest.raises(ContractValidationError, match="fails verification"):
        tampered.validate()


def test_canonical_payload_is_pure_json_bytes() -> None:
    """Canonical payload must be valid UTF-8 JSON (no surprises)."""
    contract = _make_parent()
    payload = canonical_contract_payload(contract)
    decoded = json.loads(payload.decode("utf-8"))
    assert isinstance(decoded, dict)
    # Allowed_actions / surfaces become sorted lists (canonical encoding).
    assert decoded["allowed_actions"] == sorted(contract.allowed_actions)
    assert decoded["allowed_surfaces"]["pr_numbers"] == []

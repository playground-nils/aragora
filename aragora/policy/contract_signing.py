"""HMAC-SHA256 signing for Aragora Delegation Contracts (v0.4).

Companion to ``aragora.policy.delegation_contract`` — turns a v0.1 contract
(which carries a nullable ``signature`` field) into a signed artifact whose
authority chain is cryptographically unforgeable, not just typed.

Design choices
--------------
- **HMAC-SHA256** over a canonical JSON serialization. ed25519 (asymmetric
  signing with a public-key directory) is a v1.0 hardening item; for v0.4
  HMAC is sufficient because the verifier is always a process that already
  shares the shared secret. The same primitive backs
  ``aragora.security.context_signing`` and is well-trodden in the codebase.
- **Canonical JSON**: ``sort_keys=True`` + ``separators=(",",":")`` +
  the ``signature`` field omitted. This guarantees the same contract
  serializes byte-identically across Python versions, dict insertion
  orders, and whether the caller round-tripped through JSON before
  signing.
- **Key resolution**: explicit ``key`` kwarg wins; otherwise we fall back
  to ``ARAGORA_CONTEXT_SIGNING_KEY`` via
  ``aragora.security.context_signing.get_signing_key()`` so v0.4 inherits
  the same env contract as G1 manifest signing. Missing key + no explicit
  key + signing mode raises ``SigningError``.
- **Schema-additive**: the contract dataclass is unchanged. We bump only
  a *signing* schema version (``SIGNING_SCHEMA_VERSION``) so v0.1
  contracts remain parsable; the v0.1 ``validate()`` rule is relaxed
  separately in ``delegation_contract.py`` to allow either ``None``
  (unsigned mode) or a populated signature that verifies.

Out of scope for v0.4
---------------------
- ed25519 / public-key signing (v1.0)
- key rotation / public-key infrastructure (v1.0)
- lane-registry enforcement at claim time (v0.5, depends on lane-registry
  hookup v0.2 first)
- re-signing previously-emitted receipts retroactively

Pure stdlib. No new pip deps.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from typing import Any, Mapping

from aragora.security.context_signing import get_signing_key

from .delegation_contract import (
    AllowedSurfaces,
    ContractBudget,
    DelegationContract,
)

SIGNING_SCHEMA_VERSION = "aragora-contract-signing/0.4"

# Field carrying the signature on both contracts and receipts. Centralized
# so canonicalization and verification stay in lock-step.
_SIGNATURE_FIELD = "signature"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SigningError(RuntimeError):
    """Raised when signing cannot proceed (e.g. no key available)."""


class VerificationError(RuntimeError):
    """Raised on unrecoverable verification problems (malformed input)."""


# ---------------------------------------------------------------------------
# Verification result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of a contract or receipt signature check.

    Attributes:
        ok: True iff a signature was present AND verified against ``key``.
        signed: True iff the artifact carried a non-empty ``signature``
            field. ``signed=False`` is not an error — it just means the
            artifact is in "unsigned mode".
        reason: Human-readable summary.
    """

    ok: bool
    signed: bool
    reason: str


# ---------------------------------------------------------------------------
# Canonicalization
# ---------------------------------------------------------------------------


def _contract_to_plain(contract: DelegationContract) -> dict[str, Any]:
    """Serialize a ``DelegationContract`` into a dict of JSON-native types.

    frozensets become sorted lists; nested dataclasses are unrolled. The
    ``signature`` field is INCLUDED at this layer — the canonicalizer is
    responsible for omitting it when computing the signing payload.
    """
    surfaces: AllowedSurfaces = contract.allowed_surfaces
    budget: ContractBudget = contract.budget
    return {
        "contract_id": contract.contract_id,
        "schema_version": contract.schema_version,
        "root_intent_id": contract.root_intent_id,
        "parent_contract_id": contract.parent_contract_id,
        "delegator": contract.delegator,
        "delegatee": contract.delegatee,
        "max_depth": contract.max_depth,
        "goal_id": contract.goal_id,
        "allowed_actions": sorted(contract.allowed_actions),
        "denied_actions": sorted(contract.denied_actions),
        "allowed_surfaces": {
            "pr_numbers": sorted(surfaces.pr_numbers),
            "branch_globs": sorted(surfaces.branch_globs),
            "worktree_globs": sorted(surfaces.worktree_globs),
            "file_globs": sorted(surfaces.file_globs),
            "deny_file_globs": sorted(surfaces.deny_file_globs),
        },
        "destructive_action_policy": contract.destructive_action_policy,
        "budget": {
            "risk_budget": {
                "total": budget.risk_budget.total,
                "spent": budget.risk_budget.spent,
            },
            "max_wall_clock_minutes": budget.max_wall_clock_minutes,
            "max_subagents_spawned": budget.max_subagents_spawned,
            "max_prs_opened": budget.max_prs_opened,
            "max_commits_to_main": budget.max_commits_to_main,
            "max_api_dollars": budget.max_api_dollars,
            "max_lane_claims": budget.max_lane_claims,
        },
        "issued_at": contract.issued_at,
        "expires_at": contract.expires_at,
        "revocation_check_uri": contract.revocation_check_uri,
        "progress_predicates": list(contract.progress_predicates),
        "stale_threshold_minutes": contract.stale_threshold_minutes,
        _SIGNATURE_FIELD: contract.signature,
    }


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    """Deterministic JSON encoding with ``signature`` omitted.

    Same rules as RFC 8785 (JSON Canonicalization Scheme) at the level
    we need:
    - sorted keys at every depth
    - no extra whitespace
    - UTF-8 bytes
    - the ``signature`` field is removed before hashing so a signed
      contract and its pre-signing form hash identically.
    """

    def _strip(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _strip(v) for k, v in obj.items() if k != _SIGNATURE_FIELD}
        if isinstance(obj, list):
            return [_strip(item) for item in obj]
        return obj

    stripped = _strip(dict(payload))
    return json.dumps(stripped, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def canonical_contract_payload(contract: DelegationContract) -> bytes:
    """Return the deterministic JSON byte string for ``contract``.

    The bytes are identical regardless of:
    - whether ``contract.signature`` is ``None`` or populated (the field
      is omitted before hashing)
    - dict insertion order (sorted keys at every depth)
    - frozenset iteration order (we sort first)
    - whitespace formatting

    This is the input to HMAC-SHA256.
    """
    return _canonical_bytes(_contract_to_plain(contract))


# ---------------------------------------------------------------------------
# Key resolution
# ---------------------------------------------------------------------------


def _resolve_key(
    key: bytes | None,
    *,
    required: bool,
) -> bytes | None:
    """Resolve an HMAC key. Explicit > env > None.

    When ``required`` is True and no key is available, raises
    ``SigningError``.
    """
    if key is not None:
        if not key:
            raise SigningError("explicit signing key is empty")
        return key
    env_key = get_signing_key()
    if env_key:
        return env_key
    if required:
        raise SigningError(
            "no signing key available: pass ``key=`` explicitly or set the "
            "ARAGORA_CONTEXT_SIGNING_KEY env var (base64-encoded)"
        )
    return None


# ---------------------------------------------------------------------------
# Contract signing / verification
# ---------------------------------------------------------------------------


def _hmac_hex(payload: bytes, key: bytes) -> str:
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def sign_contract(
    contract: DelegationContract,
    *,
    key: bytes | None = None,
) -> DelegationContract:
    """Return a NEW ``DelegationContract`` with ``signature`` populated.

    The signature is HMAC-SHA256 over ``canonical_contract_payload(contract)``.
    Because the canonical payload omits the ``signature`` field, signing an
    already-signed contract is idempotent in the sense that the resulting
    signature value matches the original (assuming the key is the same).

    Raises:
        SigningError: when no key is available.
    """
    resolved = _resolve_key(key, required=True)
    if resolved is None:  # pragma: no cover — _resolve_key would have raised
        raise SigningError("internal: key resolution returned None despite required=True")
    payload = canonical_contract_payload(contract)
    signature = _hmac_hex(payload, resolved)
    # Use dataclasses.replace to avoid duplicating field plumbing.
    from dataclasses import replace

    return replace(contract, signature=signature)


def verify_contract(
    contract: DelegationContract,
    *,
    key: bytes | None = None,
) -> VerificationResult:
    """Verify the signature on ``contract``.

    Returns a ``VerificationResult``. ``ok`` is True only when a signature
    was present and successfully verified. ``signed=False`` for contracts
    with ``signature=None`` is not an error.

    Verification never raises on tampered input — only on missing key
    when one is required by the artifact itself.
    """
    if not contract.signature:
        return VerificationResult(
            ok=False,
            signed=False,
            reason="contract is unsigned (signature field is None or empty)",
        )
    resolved = _resolve_key(key, required=False)
    if resolved is None:
        return VerificationResult(
            ok=False,
            signed=True,
            reason=(
                "contract is signed but no verification key is available; "
                "pass key= or set ARAGORA_CONTEXT_SIGNING_KEY"
            ),
        )
    payload = canonical_contract_payload(contract)
    expected = _hmac_hex(payload, resolved)
    if hmac.compare_digest(expected, contract.signature):
        return VerificationResult(ok=True, signed=True, reason="signature verified")
    return VerificationResult(
        ok=False,
        signed=True,
        reason="signature does not match canonical payload (tampered or wrong key)",
    )


# ---------------------------------------------------------------------------
# Receipt signing / verification
# ---------------------------------------------------------------------------


def sign_receipt(
    receipt: Mapping[str, Any],
    *,
    key: bytes | None = None,
) -> dict[str, Any]:
    """Return a NEW receipt dict with a ``signature`` field added.

    Idempotent: signing an already-signed receipt with the same key
    produces the same signature because the canonical payload omits the
    ``signature`` field before hashing.

    Receipts are arbitrary JSON-serializable mappings. The signature is
    HMAC-SHA256 over the canonical-JSON-without-signature bytes.
    """
    resolved = _resolve_key(key, required=True)
    if resolved is None:  # pragma: no cover
        raise SigningError("internal: key resolution returned None despite required=True")
    payload_bytes = _canonical_bytes(dict(receipt))
    signature = _hmac_hex(payload_bytes, resolved)
    signed: dict[str, Any] = dict(receipt)
    signed[_SIGNATURE_FIELD] = signature
    return signed


def verify_receipt(
    receipt: Mapping[str, Any],
    *,
    key: bytes | None = None,
) -> VerificationResult:
    """Verify a signed receipt dict. Mirrors ``verify_contract`` semantics."""
    sig = receipt.get(_SIGNATURE_FIELD)
    if not sig or not isinstance(sig, str):
        return VerificationResult(
            ok=False,
            signed=False,
            reason="receipt is unsigned (no `signature` field)",
        )
    resolved = _resolve_key(key, required=False)
    if resolved is None:
        return VerificationResult(
            ok=False,
            signed=True,
            reason=(
                "receipt is signed but no verification key is available; "
                "pass key= or set ARAGORA_CONTEXT_SIGNING_KEY"
            ),
        )
    payload_bytes = _canonical_bytes(dict(receipt))
    expected = _hmac_hex(payload_bytes, resolved)
    if hmac.compare_digest(expected, sig):
        return VerificationResult(ok=True, signed=True, reason="signature verified")
    return VerificationResult(
        ok=False,
        signed=True,
        reason="signature does not match canonical payload (tampered or wrong key)",
    )


# ---------------------------------------------------------------------------
# Helpers exposed for the CLI tool / external callers
# ---------------------------------------------------------------------------


def is_contract_signed(contract: DelegationContract) -> bool:
    """Convenience: True iff the contract carries a non-empty signature."""
    return bool(contract.signature)


def signing_key_available(key: bytes | None = None) -> bool:
    """True iff a signing key is resolvable from explicit arg or env."""
    if key:
        return True
    return bool(os.environ.get("ARAGORA_CONTEXT_SIGNING_KEY"))


__all__ = [
    "SIGNING_SCHEMA_VERSION",
    "SigningError",
    "VerificationError",
    "VerificationResult",
    "canonical_contract_payload",
    "is_contract_signed",
    "sign_contract",
    "sign_receipt",
    "signing_key_available",
    "verify_contract",
    "verify_receipt",
]

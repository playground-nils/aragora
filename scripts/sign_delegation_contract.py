#!/usr/bin/env python3
"""Sign or verify a Delegation Contract JSON file.

Companion CLI for ``aragora.policy.contract_signing`` (v0.4). Reads a
contract JSON file produced by the contract issuance pipeline, signs it
with HMAC-SHA256, and writes the signed contract back out.

Usage
-----

Sign an unsigned contract::

    python3 scripts/sign_delegation_contract.py \\
        --in unsigned.json --out signed.json

Verify a signed contract (read-only)::

    python3 scripts/sign_delegation_contract.py \\
        --in signed.json --verify-only

Sign with an explicit base64-encoded key (instead of env var)::

    python3 scripts/sign_delegation_contract.py \\
        --in unsigned.json --out signed.json --key-b64 BASE64=

Exit codes
----------
- 0    success (signed or verified)
- 1    generic error (file missing, malformed JSON, etc.)
- 2    no signing key available and --require-signed was passed
       (or verification key missing in --verify-only mode)
- 3    signature is present but does NOT verify (tamper / wrong key)
- 4    --verify-only and contract is unsigned

Pure stdlib. No new pip deps. Lane: ADC-v0.4-hmac-signing.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

# Allow running directly from a checkout without installing the package.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aragora.policy.contract_signing import (  # noqa: E402
    SigningError,
    canonical_contract_payload,
    sign_contract,
    signing_key_available,
    verify_contract,
)
from aragora.policy.delegation_contract import (  # noqa: E402
    AllowedSurfaces,
    ContractBudget,
    ContractValidationError,
    DelegationContract,
)
from aragora.policy.risk import RiskBudget  # noqa: E402


def _load_contract(path: Path) -> DelegationContract:
    """Load a contract JSON file into a ``DelegationContract`` dataclass.

    The on-disk JSON shape is the one produced by
    ``aragora.policy.contract_signing._contract_to_plain`` (sorted-list
    encoding of frozensets, nested objects for surfaces/budget).
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    surfaces_raw: dict[str, Any] = raw.get("allowed_surfaces", {})
    budget_raw: dict[str, Any] = raw.get("budget", {})
    risk_raw: dict[str, Any] = budget_raw.get("risk_budget", {})

    surfaces = AllowedSurfaces(
        pr_numbers=frozenset(surfaces_raw.get("pr_numbers", []) or []),
        branch_globs=frozenset(surfaces_raw.get("branch_globs", []) or []),
        worktree_globs=frozenset(surfaces_raw.get("worktree_globs", []) or []),
        file_globs=frozenset(surfaces_raw.get("file_globs", []) or []),
        deny_file_globs=frozenset(surfaces_raw.get("deny_file_globs", []) or []),
    )
    budget = ContractBudget(
        risk_budget=RiskBudget(
            total=risk_raw.get("total", 100),
            spent=risk_raw.get("spent", 0),
        ),
        max_wall_clock_minutes=budget_raw.get("max_wall_clock_minutes", 60),
        max_subagents_spawned=budget_raw.get("max_subagents_spawned", 0),
        max_prs_opened=budget_raw.get("max_prs_opened", 1),
        max_commits_to_main=budget_raw.get("max_commits_to_main", 0),
        max_api_dollars=budget_raw.get("max_api_dollars", 1.0),
        max_lane_claims=budget_raw.get("max_lane_claims", 1),
    )
    return DelegationContract(
        contract_id=raw["contract_id"],
        schema_version=raw["schema_version"],
        root_intent_id=raw["root_intent_id"],
        parent_contract_id=raw.get("parent_contract_id"),
        delegator=raw["delegator"],
        delegatee=raw["delegatee"],
        max_depth=raw["max_depth"],
        goal_id=raw["goal_id"],
        allowed_actions=frozenset(raw.get("allowed_actions", [])),
        denied_actions=frozenset(raw.get("denied_actions", [])),
        allowed_surfaces=surfaces,
        destructive_action_policy=raw.get("destructive_action_policy", "deny"),
        budget=budget,
        issued_at=raw["issued_at"],
        expires_at=raw["expires_at"],
        revocation_check_uri=raw.get("revocation_check_uri"),
        progress_predicates=list(raw.get("progress_predicates", [])),
        stale_threshold_minutes=raw.get("stale_threshold_minutes", 30),
        signature=raw.get("signature"),
    )


def _dump_contract(contract: DelegationContract, path: Path) -> None:
    """Write the contract JSON to ``path`` in canonical-ish form.

    We use indent=2 for the on-disk artifact (humans need to diff it);
    the signing payload itself uses canonical compact JSON via
    ``canonical_contract_payload``.
    """
    # Reuse the canonicalizer to derive the dict shape, then re-decode
    # so we can re-emit with indentation.
    payload_bytes = canonical_contract_payload(contract)
    obj = json.loads(payload_bytes.decode("utf-8"))
    if contract.signature:
        obj["signature"] = contract.signature
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve_explicit_key(args: argparse.Namespace) -> bytes | None:
    if args.key_b64:
        try:
            return base64.b64decode(args.key_b64)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: --key-b64 is not valid base64: {exc}", file=sys.stderr)
            sys.exit(1)
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sign_delegation_contract.py",
        description=("Sign or verify an Aragora Delegation Contract JSON file (v0.4 HMAC-SHA256)."),
    )
    parser.add_argument(
        "--in",
        dest="in_path",
        required=True,
        type=Path,
        help="path to contract JSON file to sign or verify",
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        type=Path,
        default=None,
        help="path to write the signed contract (required unless --verify-only)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="do not sign; just verify the signature on the input file",
    )
    parser.add_argument(
        "--require-signed",
        action="store_true",
        help=(
            "fail (exit 2) when no signing key is available, rather than "
            "writing an unsigned contract"
        ),
    )
    parser.add_argument(
        "--key-b64",
        dest="key_b64",
        default=None,
        help=(
            "base64-encoded HMAC key, overriding ARAGORA_CONTEXT_SIGNING_KEY. "
            "Useful for tests; production paths should rely on the env var."
        ),
    )
    args = parser.parse_args(argv)

    in_path: Path = args.in_path
    if not in_path.exists():
        print(f"ERROR: input file does not exist: {in_path}", file=sys.stderr)
        return 1

    try:
        contract = _load_contract(in_path)
    except (KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: failed to parse contract JSON at {in_path}: {exc}", file=sys.stderr)
        return 1
    except ContractValidationError as exc:
        print(f"ERROR: contract validation failed at {in_path}: {exc}", file=sys.stderr)
        return 1

    explicit_key = _resolve_explicit_key(args)

    if args.verify_only:
        result = verify_contract(contract, key=explicit_key)
        if not result.signed:
            print(f"UNSIGNED: {result.reason}", file=sys.stderr)
            return 4
        if not result.ok:
            print(f"VERIFY-FAILED: {result.reason}", file=sys.stderr)
            return 3
        print(f"OK: {result.reason}")
        return 0

    # Signing mode
    if args.out_path is None:
        print("ERROR: --out is required when not using --verify-only", file=sys.stderr)
        return 1

    if not signing_key_available(explicit_key):
        if args.require_signed:
            print(
                "ERROR: --require-signed was passed but no signing key is "
                "available (set ARAGORA_CONTEXT_SIGNING_KEY or pass --key-b64)",
                file=sys.stderr,
            )
            return 2
        # No key + not required → just copy through (still valid v0.4
        # unsigned mode). We re-emit via _dump_contract so the on-disk
        # JSON gets canonical key ordering.
        _dump_contract(contract, args.out_path)
        print(f"WROTE (unsigned): {args.out_path}")
        return 0

    try:
        signed = sign_contract(contract, key=explicit_key)
    except SigningError as exc:
        print(f"ERROR: signing failed: {exc}", file=sys.stderr)
        return 2

    _dump_contract(signed, args.out_path)
    print(f"WROTE (signed): {args.out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

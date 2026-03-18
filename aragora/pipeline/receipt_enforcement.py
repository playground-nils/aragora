"""Canonical receipt enforcement for all write-action paths.

Provides a single ``require_receipt_gate()`` function that any domain
(openclaw, canvas, computer_use, inbox, shared_inbox) can call before
executing a write action.  Enforcement is controlled per-domain via
feature flags so rollout can be gradual.

The function delegates to the existing ``gauntlet.receipt_store`` state
machine for all persistence and verification logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aragora.gauntlet.receipt_store import StoredReceipt

logger = logging.getLogger(__name__)


class ReceiptEnforcementError(RuntimeError):
    """Raised when a write action is attempted without a valid receipt."""


@dataclass(frozen=True)
class ReceiptExemption:
    """Documented exemption from receipt enforcement.

    Used for operations that legitimately bypass the receipt gate,
    such as read-only queries, metadata-only updates, or legacy
    admin operations during migration.
    """

    reason: str
    approved_by: str
    category: str  # "read_only", "metadata_only", "legacy_admin", "system_internal"


def is_receipt_enforcement_enabled(domain: str) -> bool:
    """Check whether receipt enforcement is active for *domain*.

    Resolution order:
    1. Environment variable ``ARAGORA_RECEIPT_ENFORCEMENT_{DOMAIN}``
    2. Feature flag ``receipt_enforcement_{domain}``

    Returns ``False`` when the flag is not set (safe default — enforcement
    must be opted-in per domain).
    """
    from aragora.config.feature_flags import is_enabled

    flag_name = f"receipt_enforcement_{domain}"
    return is_enabled(flag_name)


def require_receipt_gate(
    *,
    action_domain: str,
    action_type: str,
    actor_id: str,
    resource_id: str,
    receipt_id: str | None = None,
    exempt: ReceiptExemption | None = None,
) -> StoredReceipt | None:
    """Canonical enforcement function for write-action paths.

    Call this before any mutating operation.  Behaviour:

    * If enforcement is **disabled** for *action_domain*: returns ``None``
      (no-op — domain not yet enrolled).
    * If *exempt* is provided: logs the exemption and returns ``None``.
    * If *receipt_id* is provided: validates that the receipt exists, is
      in the ``APPROVED`` state, and has a valid signature.  Returns the
      ``StoredReceipt`` on success.
    * Otherwise: raises ``ReceiptEnforcementError``.

    All calls (including no-ops and exemptions) emit structured audit
    log entries so the enforcement surface can be observed.
    """
    if not is_receipt_enforcement_enabled(action_domain):
        logger.debug(
            "receipt_enforcement_skip domain=%s action=%s actor=%s resource=%s "
            "reason=domain_not_enrolled",
            action_domain,
            action_type,
            actor_id,
            resource_id,
        )
        return None

    if exempt is not None:
        logger.info(
            "receipt_enforcement_exempt domain=%s action=%s actor=%s resource=%s "
            "category=%s reason=%s approved_by=%s",
            action_domain,
            action_type,
            actor_id,
            resource_id,
            exempt.category,
            exempt.reason,
            exempt.approved_by,
        )
        return None

    if receipt_id is None:
        logger.warning(
            "receipt_enforcement_denied domain=%s action=%s actor=%s resource=%s "
            "reason=no_receipt_id",
            action_domain,
            action_type,
            actor_id,
            resource_id,
        )
        raise ReceiptEnforcementError(
            f"Write action {action_type} on {action_domain} requires a receipt"
        )

    # Lazy import to stay consistent with project conventions
    from aragora.gauntlet.receipt_store import ReceiptState, get_receipt_store

    store = get_receipt_store()
    stored = store.get(receipt_id)

    if stored is None:
        logger.warning(
            "receipt_enforcement_denied domain=%s action=%s actor=%s resource=%s "
            "receipt=%s reason=not_found",
            action_domain,
            action_type,
            actor_id,
            resource_id,
            receipt_id,
        )
        raise ReceiptEnforcementError(f"Receipt {receipt_id} not found")

    if stored.state != ReceiptState.APPROVED:
        logger.warning(
            "receipt_enforcement_denied domain=%s action=%s actor=%s resource=%s "
            "receipt=%s reason=wrong_state state=%s",
            action_domain,
            action_type,
            actor_id,
            resource_id,
            receipt_id,
            stored.state.value,
        )
        raise ReceiptEnforcementError(
            f"Receipt {receipt_id} is in state {stored.state.value}, expected APPROVED"
        )

    if not store.verify_receipt(receipt_id):
        logger.warning(
            "receipt_enforcement_denied domain=%s action=%s actor=%s resource=%s "
            "receipt=%s reason=invalid_signature",
            action_domain,
            action_type,
            actor_id,
            resource_id,
            receipt_id,
        )
        raise ReceiptEnforcementError(f"Receipt {receipt_id} failed signature verification")

    logger.info(
        "receipt_enforcement_passed domain=%s action=%s actor=%s resource=%s receipt=%s",
        action_domain,
        action_type,
        actor_id,
        resource_id,
        receipt_id,
    )
    return stored


def transition_receipt_executed(receipt_id: str) -> StoredReceipt:
    """Transition a receipt to EXECUTED after a successful write action.

    Should be called immediately after the gated action completes
    successfully.  Raises ``ReceiptStateError`` if the transition is
    invalid (e.g. receipt is not in APPROVED state).
    """
    from aragora.gauntlet.receipt_store import ReceiptState, get_receipt_store

    store = get_receipt_store()
    stored = store.transition(receipt_id, ReceiptState.EXECUTED)
    logger.info(
        "receipt_transition_executed receipt=%s",
        receipt_id,
    )
    return stored


__all__ = [
    "ReceiptEnforcementError",
    "ReceiptExemption",
    "is_receipt_enforcement_enabled",
    "require_receipt_gate",
    "transition_receipt_executed",
]

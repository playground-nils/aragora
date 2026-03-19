"""Best-effort receipt emission for autonomous loops.

All functions are fire-and-forget: they log failures but never raise,
so callers don't need try/except wrappers.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _get_facade() -> Any | None:
    try:
        from aragora.pipeline.receipt_store_facade import get_receipt_store_facade

        return get_receipt_store_facade()
    except (ImportError, RuntimeError):
        return None


def _get_signer() -> Any | None:
    try:
        from aragora.gauntlet.signing import get_default_signer

        return get_default_signer()
    except (ImportError, RuntimeError, ValueError, TypeError):
        return None


def emit_operational_receipt(
    *,
    source: str,
    action: str,
    actor: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    verdict: str,
    confidence: float = 0.0,
    duration_seconds: float = 0.0,
    receipt_id: str | None = None,
) -> str | None:
    """Persist an operational receipt. Returns receipt_id on success, None on failure."""
    receipt_id = receipt_id or f"op-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    receipt_data = {
        "receipt_id": receipt_id,
        "source": source,
        "action": action,
        "actor": actor,
        "inputs": inputs,
        "outputs": outputs,
        "verdict": verdict,
        "confidence": confidence,
        "duration_seconds": duration_seconds,
        "generated_at": now,
        "content_hash": _content_hash(receipt_id, source, action, inputs, outputs),
    }

    facade = _get_facade()
    if facade is None:
        logger.debug("Receipt facade unavailable; skipping %s", receipt_id)
        return None

    signature = signature_key_id = signed_at = signature_algorithm = None
    signer = _get_signer()
    if signer is not None:
        try:
            signed = signer.sign(receipt_data)
            signature = signed.signature
            signature_key_id = signed.signature_metadata.key_id
            signed_at = signed.signature_metadata.timestamp
            signature_algorithm = signed.signature_metadata.algorithm
        except (RuntimeError, ValueError, TypeError, AttributeError):
            pass

    try:
        facade.persist_and_save(
            receipt_id,
            receipt_data,
            signature=signature,
            signature_key_id=signature_key_id,
            signed_at=signed_at,
            signature_algorithm=signature_algorithm,
            state="CREATED",
        )
        logger.info("Operational receipt emitted: %s (%s/%s)", receipt_id, source, action)
        return receipt_id
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        logger.debug("Receipt emission failed for %s: %s", receipt_id, exc)
        return None


def _content_hash(
    receipt_id: str,
    source: str,
    action: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
) -> str:
    content = json.dumps(
        {
            "receipt_id": receipt_id,
            "source": source,
            "action": action,
            "inputs": inputs,
            "outputs": outputs,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(content.encode()).hexdigest()

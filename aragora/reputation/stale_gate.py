"""AGT-05 stale-policy gate for PendingPrediction batches (AGT-05 / #6066).

Classifies prediction objects through :mod:`aragora.reputation.stale_policy`
so the Manifold Brier bridge can discard or annotate predictions whose
information value has decayed past the configured threshold.

Gating
------
``ARAGORA_STALE_POLICY_ENABLED`` (default OFF). When not set,
:func:`apply_stale_gate` returns all predictions in the ``fresh`` bucket —
the production Brier path is unchanged.

Out of scope
------------
- Wiring into ``settle_claim`` or the calibration leaderboard (separate PRs
  per the note in stale_policy.py).
- Persistence of gate decisions to an audit JSONL.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Sequence

from aragora.reputation.stale_policy import StaleDecision, StalePolicy, is_stale

_ENV_FLAG = "ARAGORA_STALE_POLICY_ENABLED"
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def stale_policy_enabled() -> bool:
    """Return True when the stale-gate filtering surface is enabled."""
    return os.environ.get(_ENV_FLAG, "").strip().lower() in _TRUTHY


def _to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat().replace("+00:00", "Z")


@dataclass
class StaleGateResult:
    """Classification result from :func:`apply_stale_gate`.

    Attributes:
        fresh: Predictions within the policy's ``fresh_days`` threshold.
        stale: Predictions older than ``stale_days`` but within ``hard_limit_days``.
        expired: Predictions older than ``hard_limit_days``; should not be settled.
        decisions: Parallel list of :class:`~aragora.reputation.stale_policy.StaleDecision`
            objects; empty when the flag is off (pass-through mode).
        policy_fingerprint: Stable hash of the :class:`StalePolicy` used.
    """

    fresh: list[Any] = field(default_factory=list)
    stale: list[Any] = field(default_factory=list)
    expired: list[Any] = field(default_factory=list)
    decisions: list[StaleDecision] = field(default_factory=list)
    policy_fingerprint: str = ""

    @property
    def total(self) -> int:
        return len(self.fresh) + len(self.stale) + len(self.expired)

    def summary(self) -> dict[str, Any]:
        return {
            "fresh": len(self.fresh),
            "stale": len(self.stale),
            "expired": len(self.expired),
            "total": self.total,
            "policy_fingerprint": self.policy_fingerprint,
        }


def apply_stale_gate(
    predictions: Sequence[Any],
    *,
    policy: StalePolicy | None = None,
    now: datetime | None = None,
) -> StaleGateResult:
    """Apply stale-policy filtering to a list of PendingPredictions.

    When ``ARAGORA_STALE_POLICY_ENABLED`` is not set all predictions are
    returned in the ``fresh`` bucket with no filtering applied.

    Each prediction must have a ``predicted_at: datetime`` attribute.
    """
    effective_policy = policy or StalePolicy()
    now_iso = _to_iso(now or datetime.now(UTC))

    if not stale_policy_enabled():
        return StaleGateResult(
            fresh=list(predictions),
            policy_fingerprint=effective_policy.fingerprint(),
        )

    fresh: list[Any] = []
    stale: list[Any] = []
    expired: list[Any] = []
    decisions: list[StaleDecision] = []

    for pred in predictions:
        decision = is_stale(
            claim_iso=_to_iso(pred.predicted_at),
            now_iso=now_iso,
            policy=effective_policy,
        )
        decisions.append(decision)
        if decision.is_expired:
            expired.append(pred)
        elif decision.is_stale:
            stale.append(pred)
        else:
            fresh.append(pred)

    return StaleGateResult(
        fresh=fresh,
        stale=stale,
        expired=expired,
        decisions=decisions,
        policy_fingerprint=effective_policy.fingerprint(),
    )


__all__ = [
    "StaleGateResult",
    "apply_stale_gate",
    "stale_policy_enabled",
]

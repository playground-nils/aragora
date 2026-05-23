"""AGT-05 stale-policy seed (shadow only).

A *stale* claim is one whose resolution would still type-check but whose
information value has decayed past a threshold. The settlement module
already supports time-decay via ``decay_half_life_days``. This module
adds an *explicit, named* policy surface that future settlement,
leaderboard, and audit code can call without each call site rolling its
own age math.

This is shadow-only:

- It defines :class:`StalePolicy` with conservative defaults that match
  the existing 30-day settlement half-life.
- It exposes :func:`is_stale` as the public predicate.
- It returns a :class:`StaleDecision` carrying the reason, the age in
  days, and the policy fingerprint, so audit trails are
  machine-greppable.
- No production code path calls into this module yet.

**Three-axis extension (AGT-05 sub-deliverable — plan:**
``docs/plans/2026-04-29-agt-05-stale-claim-policy.md``):

When a ``STALE`` verdict is produced by the settlement path the simple
``is_stale`` predicate does not tell the caller *what to do about it*.
Treating every stale claim identically as a calibration miss creates a
false-decay-penalty pathology over time (see plan for full analysis).

:func:`evaluate_stale_axis` introduces a three-band decision based on
``evidence_age_at_resolution_days`` vs ``half_life_used_days``:

- ``DECAY_PENALTY`` — age < 0.5 × half_life → premature staleness,
  treat as calibration miss (existing −2 delta)
- ``RENEWAL_REQUIRED`` — 0.5 ≤ age/half_life < 1.5 → mid-band, issue
  renewal; delta abstains at 0
- ``ABSTAIN`` — age ≥ 1.5 × half_life → structural staleness; delta
  abstains at 0, no penalty

No production code path calls into this yet; wiring into ``settle_claim``
is a follow-up PR.
"""

from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final

# Default tuning. These mirror the half-life used in
# ``aragora.reputation.settlement.settle_claim`` so a claim that is
# materially decayed under the existing scoring rule is also flagged
# stale by this predicate.
DEFAULT_FRESH_DAYS: Final[float] = 7.0
DEFAULT_STALE_DAYS: Final[float] = 30.0
DEFAULT_HARD_LIMIT_DAYS: Final[float] = 180.0


@dataclass(frozen=True)
class StalePolicy:
    """Bounds for the stale-claim predicate.

    Attributes:
        fresh_days: Claims younger than this are always fresh.
        stale_days: Claims older than this are always stale.
        hard_limit_days: Claims older than this are *expired* and
            should not even be settled.
    """

    fresh_days: float = DEFAULT_FRESH_DAYS
    stale_days: float = DEFAULT_STALE_DAYS
    hard_limit_days: float = DEFAULT_HARD_LIMIT_DAYS

    def __post_init__(self) -> None:
        if not (0 < self.fresh_days <= self.stale_days <= self.hard_limit_days):
            raise ValueError(
                "StalePolicy bounds must satisfy "
                "0 < fresh_days <= stale_days <= hard_limit_days; got "
                f"fresh={self.fresh_days}, stale={self.stale_days}, "
                f"hard_limit={self.hard_limit_days}"
            )

    def fingerprint(self) -> str:
        """Stable 12-char hash of the policy parameters.

        Useful for tagging audit rows so a future change in defaults can
        be tracked in receipts without a schema migration.
        """
        material = json.dumps(
            {
                "fresh_days": self.fresh_days,
                "stale_days": self.stale_days,
                "hard_limit_days": self.hard_limit_days,
            },
            sort_keys=True,
        )
        return f"sp_{hashlib.sha256(material.encode('utf-8')).hexdigest()[:12]}"


@dataclass(frozen=True)
class StaleDecision:
    """The outcome of a stale-policy evaluation.

    Attributes:
        is_stale: True iff the claim should be treated as stale.
        is_expired: True iff the claim is past the hard-limit and
            should not be settled at all.
        age_days: Age of the claim in days at the evaluation moment.
        bucket: One of ``"fresh"``, ``"stale"``, ``"expired"``.
        policy_fingerprint: Stable hash of the policy parameters.
    """

    is_stale: bool
    is_expired: bool
    age_days: float
    bucket: str
    policy_fingerprint: str


def _age_days(claim_iso: str, now_iso: str) -> float:
    claim_at = datetime.fromisoformat(claim_iso.replace("Z", "+00:00"))
    if claim_at.tzinfo is None:
        claim_at = claim_at.replace(tzinfo=timezone.utc)
    now = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    delta = (now - claim_at).total_seconds() / 86400.0
    if delta < 0:
        # Future-dated claims are treated as fresh; we never lie about age.
        return 0.0
    return delta


def is_stale(
    *,
    claim_iso: str,
    now_iso: str | None = None,
    policy: StalePolicy | None = None,
) -> StaleDecision:
    """Decide whether a claim is fresh, stale, or expired.

    Args:
        claim_iso: ISO-8601 timestamp at which the claim was made.
        now_iso: Optional override for the evaluation moment; defaults
            to ``datetime.now(timezone.utc)``.
        policy: Optional :class:`StalePolicy`; defaults to the
            conservative module-level defaults.

    Returns:
        A :class:`StaleDecision`. The decision is *advisory* — call
        sites are responsible for whatever action it implies (skip
        settlement, mark a leaderboard cell, append to an audit row).
    """
    if not claim_iso:
        raise ValueError("claim_iso must be a non-empty ISO-8601 string")
    if now_iso is None:
        now_iso = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
    p = policy or StalePolicy()
    age = _age_days(claim_iso, now_iso)
    if age > p.hard_limit_days:
        return StaleDecision(
            is_stale=True,
            is_expired=True,
            age_days=age,
            bucket="expired",
            policy_fingerprint=p.fingerprint(),
        )
    if age >= p.stale_days:
        return StaleDecision(
            is_stale=True,
            is_expired=False,
            age_days=age,
            bucket="stale",
            policy_fingerprint=p.fingerprint(),
        )
    return StaleDecision(
        is_stale=False,
        is_expired=False,
        age_days=age,
        bucket="fresh",
        policy_fingerprint=p.fingerprint(),
    )


# ---------------------------------------------------------------------------
# Three-axis stale policy (AGT-05 sub-deliverable)
# ---------------------------------------------------------------------------

# Band boundaries expressed as multiples of half_life_used_days (see plan).
_DECAY_PENALTY_UPPER = 0.5  # age < 0.5 × half_life → decay penalty
_ABSTAIN_LOWER = 1.5        # age ≥ 1.5 × half_life → abstain


class StaleAxis(str, enum.Enum):
    """Resolution axis for a STALE claim under the three-band policy.

    Attributes:
        DECAY_PENALTY: Premature staleness — treat as calibration miss
            (same −2 delta as an outright failure).
        RENEWAL_REQUIRED: Mid-band staleness — abstain from delta but
            record a ``claim_renewal_id`` for downstream re-evidencing.
        ABSTAIN: Structural staleness — evidence so old that penalising
            the agent would be unfair; no delta, no renewal obligation.
    """

    DECAY_PENALTY = "decay_penalty"
    RENEWAL_REQUIRED = "renewal_required"
    ABSTAIN = "abstain"


@dataclass(frozen=True)
class StaleAxisDecision:
    """Outcome of :func:`evaluate_stale_axis`.

    Attributes:
        axis: One of the three :class:`StaleAxis` values.
        evidence_age_days: Age of the evidence at resolution time.
        half_life_used_days: The half-life value used in this evaluation.
        calibration_delta: Recommended delta (−2 for DECAY_PENALTY, 0
            for RENEWAL_REQUIRED and ABSTAIN).  Advisory only — callers
            decide whether to apply it.
        ratio: ``evidence_age_days / half_life_used_days`` for audit
            logging; None when ``half_life_used_days`` is zero.
    """

    axis: StaleAxis
    evidence_age_days: float
    half_life_used_days: float
    calibration_delta: int
    ratio: float | None


def evaluate_stale_axis(
    evidence_age_days: float,
    half_life_used_days: float,
) -> StaleAxisDecision:
    """Classify a STALE verdict into one of three policy bands.

    Args:
        evidence_age_days: Age of the underlying evidence at the moment
            of resolution, expressed in days.  Must be non-negative.
        half_life_used_days: The half-life the settlement path used when
            producing the STALE verdict.  Must be positive.

    Returns:
        A :class:`StaleAxisDecision`.  The decision is advisory; callers
        are responsible for applying (or ignoring) ``calibration_delta``.

    Raises:
        ValueError: If ``evidence_age_days`` is negative or
            ``half_life_used_days`` is non-positive.
    """
    if evidence_age_days < 0:
        raise ValueError(
            f"evidence_age_days must be non-negative; got {evidence_age_days}"
        )
    if half_life_used_days <= 0:
        raise ValueError(
            f"half_life_used_days must be positive; got {half_life_used_days}"
        )

    ratio = evidence_age_days / half_life_used_days

    if ratio < _DECAY_PENALTY_UPPER:
        return StaleAxisDecision(
            axis=StaleAxis.DECAY_PENALTY,
            evidence_age_days=evidence_age_days,
            half_life_used_days=half_life_used_days,
            calibration_delta=-2,
            ratio=ratio,
        )
    if ratio < _ABSTAIN_LOWER:
        return StaleAxisDecision(
            axis=StaleAxis.RENEWAL_REQUIRED,
            evidence_age_days=evidence_age_days,
            half_life_used_days=half_life_used_days,
            calibration_delta=0,
            ratio=ratio,
        )
    return StaleAxisDecision(
        axis=StaleAxis.ABSTAIN,
        evidence_age_days=evidence_age_days,
        half_life_used_days=half_life_used_days,
        calibration_delta=0,
        ratio=ratio,
    )


__all__ = [
    "DEFAULT_FRESH_DAYS",
    "DEFAULT_STALE_DAYS",
    "DEFAULT_HARD_LIMIT_DAYS",
    "StalePolicy",
    "StaleDecision",
    "is_stale",
    # Three-axis extension
    "StaleAxis",
    "StaleAxisDecision",
    "evaluate_stale_axis",
]

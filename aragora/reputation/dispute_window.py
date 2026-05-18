"""AGT-05 dispute-window gate — settlement step 4 (issue #6066).

Per-domain dispute windows control when an agent may file a counter-attestation
against a resolved claim.  Filings inside the window produce a
:class:`DisputeRecord`; filings outside are rejected (settlement is final).

Default windows (hours): prediction_market 72 | debate_position 48 | code_pr 24
  crux_resolution 48 | km_contribution 24 | epistemic_claim 48

Gate: ``ARAGORA_DISPUTE_WINDOW_ENABLED`` (default OFF).  No queue mutation.
Advances: AGT-05 #6066 SD-4.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from aragora.reputation.types import (
    DOMAIN_CODE_PR,
    DOMAIN_CRUX_RESOLUTION,
    DOMAIN_DEBATE_POSITION,
    DOMAIN_EPISTEMIC_CLAIM,
    DOMAIN_KM_CONTRIBUTION,
    DOMAIN_PREDICTION_MARKET,
    KNOWN_DOMAINS,
)

_FLAG = "ARAGORA_DISPUTE_WINDOW_ENABLED"
_TRUTHY = frozenset({"1", "true", "yes", "on"})

DEFAULT_WINDOW_HOURS: dict[str, float] = {
    DOMAIN_PREDICTION_MARKET: 72.0,
    DOMAIN_DEBATE_POSITION: 48.0,
    DOMAIN_CODE_PR: 24.0,
    DOMAIN_CRUX_RESOLUTION: 48.0,
    DOMAIN_KM_CONTRIBUTION: 24.0,
    DOMAIN_EPISTEMIC_CLAIM: 48.0,
}


class DisputeWindowGateDisabledError(RuntimeError):
    """Raised when the feature flag is off."""


class UnknownDomainError(ValueError):
    """Raised for domain strings not in :data:`~aragora.reputation.types.KNOWN_DOMAINS`."""


@dataclass(frozen=True)
class DisputeWindowPolicy:
    """Per-domain window configuration; absent domains fall back to defaults."""

    windows_hours: dict[str, float] = field(default_factory=dict)

    def window_for(self, domain: str) -> float:
        if domain not in KNOWN_DOMAINS:
            raise UnknownDomainError(
                f"unknown domain: {domain!r}; expected one of {sorted(KNOWN_DOMAINS)}"
            )
        return self.windows_hours.get(domain, DEFAULT_WINDOW_HOURS[domain])

    @classmethod
    def default(cls) -> "DisputeWindowPolicy":
        return cls()


@dataclass(frozen=True)
class DisputeRecord:
    """Eligibility result.  ``within_window=True`` → eligible for reversal path."""

    claim_id: str
    domain: str
    resolved_at: str
    filed_at: str
    window_hours: float
    elapsed_hours: float
    within_window: bool
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "domain": self.domain,
            "resolved_at": self.resolved_at,
            "filed_at": self.filed_at,
            "window_hours": round(self.window_hours, 4),
            "elapsed_hours": round(self.elapsed_hours, 4),
            "within_window": self.within_window,
            "evidence": dict(self.evidence),
        }


def dispute_window_enabled() -> bool:
    return os.environ.get(_FLAG, "").strip().lower() in _TRUTHY


def _parse_iso(ts: str) -> datetime:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"cannot parse timestamp {ts!r}: {exc}") from exc
    return dt.astimezone(UTC)


class DisputeWindowGate:
    """Flag-gated gate: checks whether a dispute filing is within the allowed window."""

    def __init__(self, policy: DisputeWindowPolicy | None = None) -> None:
        self._policy = policy or DisputeWindowPolicy.default()

    def check(
        self,
        *,
        claim_id: str,
        domain: str,
        resolved_at: str,
        filed_at: str,
        evidence: dict[str, Any] | None = None,
    ) -> DisputeRecord:
        if not dispute_window_enabled():
            raise DisputeWindowGateDisabledError(
                f"dispute window gate is disabled; set {_FLAG}=1 to enable"
            )
        window_hours = self._policy.window_for(domain)
        resolved_dt = _parse_iso(resolved_at)
        filed_dt = _parse_iso(filed_at)
        elapsed = (filed_dt - resolved_dt) / timedelta(hours=1)
        return DisputeRecord(
            claim_id=claim_id,
            domain=domain,
            resolved_at=resolved_at,
            filed_at=filed_at,
            window_hours=window_hours,
            elapsed_hours=elapsed,
            within_window=elapsed <= window_hours,
            evidence=dict(evidence or {}),
        )


__all__ = [
    "DEFAULT_WINDOW_HOURS",
    "DisputeRecord",
    "DisputeWindowGate",
    "DisputeWindowGateDisabledError",
    "DisputeWindowPolicy",
    "UnknownDomainError",
    "dispute_window_enabled",
]

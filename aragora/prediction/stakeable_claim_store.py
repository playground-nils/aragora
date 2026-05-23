"""JSONL-backed StakeableClaim store — AGT-04, sub-deliverable 3.

Durable counterpart to :class:`~aragora.prediction.stakeable_claim.InMemoryStakeableClaimStore`.
Each mutation is appended as one JSON line; on reload the newest line per
``claim_id`` wins (append-only audit log).

Flag: ``ARAGORA_PREDICTION_MARKETS_ENABLED`` (default OFF).
Advances: issue #6065 (AGT-04).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aragora.prediction.stakeable_claim import (
    QuestionType,
    ResolutionStatus,
    StakeableClaim,
    _require_enabled,
)

__all__ = ["JsonlStakeableClaimStore"]


class JsonlStakeableClaimStore:
    """JSONL-backed store for :class:`StakeableClaim` objects.

    The file format is one JSON object per line.  On reload the last
    occurrence of each ``claim_id`` wins so the file is a replayable log.
    All methods raise :exc:`RuntimeError` when the feature flag is unset.

    Parameters
    ----------
    path: Path to the ``.jsonl`` file.  Created on first write; replayed on
        ``__init__`` if it already exists.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._claims: dict[str, StakeableClaim] = {}
        if path.exists():
            self._load()

    def _load(self) -> None:
        latest: dict[str, dict[str, Any]] = {}
        with open(self._path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    latest[d["claim_id"]] = d
                except (json.JSONDecodeError, KeyError):
                    pass
        self._claims = {k: StakeableClaim.from_dict(v) for k, v in latest.items()}

    def _persist(self, claim: StakeableClaim) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as fh:
            fh.write(json.dumps(claim.to_dict()) + "\n")

    def _get_open(self, claim_id: str) -> StakeableClaim:
        claim = self._claims.get(claim_id)
        if claim is None:
            raise KeyError(f"Unknown claim {claim_id!r}")
        if not claim.is_open():
            raise ValueError(f"Claim {claim_id!r} is already {claim.resolution_status.value}.")
        return claim

    def add(self, claim: StakeableClaim) -> None:
        _require_enabled()
        if claim.claim_id in self._claims:
            raise ValueError(f"Claim {claim.claim_id!r} already exists.")
        self._claims[claim.claim_id] = claim
        self._persist(claim)

    def record_position(self, claim_id: str, agent_id: str, probability: float) -> None:
        _require_enabled()
        if not 0.0 <= probability <= 1.0:
            raise ValueError(f"probability must be in [0, 1], got {probability!r}")
        claim = self._get_open(claim_id)
        claim.positions[agent_id] = probability
        self._persist(claim)

    def resolve(self, claim_id: str, value: bool, evidence: str = "") -> StakeableClaim:
        _require_enabled()
        claim = self._get_open(claim_id)
        claim.resolution_status = (
            ResolutionStatus.RESOLVED_YES if value else ResolutionStatus.RESOLVED_NO
        )
        claim.resolution_value = value
        claim.resolution_evidence = evidence
        self._persist(claim)
        return claim

    def expire_stale(self, before_dt: datetime | None = None) -> list[str]:
        _require_enabled()
        cutoff = before_dt or datetime.now(tz=UTC)
        expired_ids: list[str] = []
        for claim in self._claims.values():
            if claim.resolution_status != ResolutionStatus.OPEN:
                continue
            try:
                exp_dt = datetime.fromisoformat(claim.expiry)
            except ValueError:
                continue
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=UTC)
            if exp_dt < cutoff:
                claim.resolution_status = ResolutionStatus.EXPIRED
                expired_ids.append(claim.claim_id)
                self._persist(claim)
        return expired_ids

    def get(self, claim_id: str) -> StakeableClaim:
        _require_enabled()
        try:
            return self._claims[claim_id]
        except KeyError:
            raise KeyError(f"Unknown claim {claim_id!r}") from None

    def list_open(self) -> list[StakeableClaim]:
        _require_enabled()
        return [c for c in self._claims.values() if c.is_open()]

    def list_by_type(self, question_type: QuestionType) -> list[StakeableClaim]:
        _require_enabled()
        return [c for c in self._claims.values() if c.question_type == question_type]

    def all(self) -> list[StakeableClaim]:
        _require_enabled()
        return list(self._claims.values())

    def __len__(self) -> int:
        _require_enabled()
        return len(self._claims)

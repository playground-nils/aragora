"""Prediction markets — AGT-04 synthetic GitHub prediction substrate.

All public symbols are importable regardless of the feature flag.
The flag (``ARAGORA_PREDICTION_MARKETS_ENABLED``) only gates the runtime
behaviour of the store classes and the resolution adapter.
"""

from aragora.prediction.stakeable_claim import (
    GithubResolutionAdapterStub,
    InMemoryStakeableClaimStore,
    QuestionType,
    ResolutionStatus,
    StakeableClaim,
)
from aragora.prediction.stakeable_claim_store import JsonlStakeableClaimStore

__all__ = [
    "GithubResolutionAdapterStub",
    "InMemoryStakeableClaimStore",
    "JsonlStakeableClaimStore",
    "QuestionType",
    "ResolutionStatus",
    "StakeableClaim",
]

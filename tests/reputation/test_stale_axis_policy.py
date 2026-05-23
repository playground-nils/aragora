"""Tests for the AGT-05 three-axis stale-claim policy.

Covers evaluate_stale_axis() across all three bands (DECAY_PENALTY,
RENEWAL_REQUIRED, ABSTAIN), boundary conditions, and invalid inputs.

Shadow-only: no production wiring, no live queue effect.
Advances: AGT-05 (#6066), docs/plans/2026-04-29-agt-05-stale-claim-policy.md
"""

from __future__ import annotations

import pytest

from aragora.reputation.stale_policy import (
    StaleAxis,
    StaleAxisDecision,
    evaluate_stale_axis,
)


def _call(age: float, half_life: float = 30.0) -> StaleAxisDecision:
    return evaluate_stale_axis(age, half_life)


# ---------------------------------------------------------------------------
# DECAY_PENALTY band  (age < 0.5 × half_life)
# ---------------------------------------------------------------------------


class TestDecayPenaltyBand:
    def test_zero_age_is_decay_penalty(self) -> None:
        assert _call(age=0.0).axis is StaleAxis.DECAY_PENALTY

    def test_calibration_delta_is_minus_two(self) -> None:
        assert _call(age=5.0).calibration_delta == -2

    def test_just_below_boundary_is_decay_penalty(self) -> None:
        assert _call(age=14.999).axis is StaleAxis.DECAY_PENALTY

    def test_ratio_stored_correctly(self) -> None:
        assert _call(age=6.0).ratio == pytest.approx(6.0 / 30.0)

    def test_fields_round_trip(self) -> None:
        d = _call(age=7.5)
        assert d.evidence_age_days == 7.5
        assert d.half_life_used_days == 30.0


# ---------------------------------------------------------------------------
# RENEWAL_REQUIRED band  (0.5 × half_life ≤ age < 1.5 × half_life)
# ---------------------------------------------------------------------------


class TestRenewalRequiredBand:
    def test_at_lower_boundary(self) -> None:
        assert _call(age=15.0).axis is StaleAxis.RENEWAL_REQUIRED

    def test_midband(self) -> None:
        assert _call(age=25.0).axis is StaleAxis.RENEWAL_REQUIRED

    def test_just_below_upper_boundary(self) -> None:
        assert _call(age=44.999).axis is StaleAxis.RENEWAL_REQUIRED

    def test_calibration_delta_is_zero(self) -> None:
        assert _call(age=20.0).calibration_delta == 0

    def test_ratio_at_lower_boundary(self) -> None:
        assert _call(age=15.0).ratio == pytest.approx(0.5)

    def test_non_default_half_life(self) -> None:
        assert _call(age=7.0, half_life=7.0).axis is StaleAxis.RENEWAL_REQUIRED


# ---------------------------------------------------------------------------
# ABSTAIN band  (age ≥ 1.5 × half_life)
# ---------------------------------------------------------------------------


class TestAbstainBand:
    def test_at_lower_boundary(self) -> None:
        assert _call(age=45.0).axis is StaleAxis.ABSTAIN

    def test_well_above_boundary(self) -> None:
        assert _call(age=180.0).axis is StaleAxis.ABSTAIN

    def test_calibration_delta_is_zero(self) -> None:
        assert _call(age=90.0).calibration_delta == 0

    def test_ratio_at_boundary(self) -> None:
        assert _call(age=45.0).ratio == pytest.approx(1.5)

    def test_short_half_life_abstain(self) -> None:
        assert _call(age=4.0, half_life=2.0).axis is StaleAxis.ABSTAIN


# ---------------------------------------------------------------------------
# Boundary contiguity — bands are contiguous and non-overlapping
# ---------------------------------------------------------------------------


class TestBandContiguity:
    @pytest.mark.parametrize("half_life", [7.0, 14.0, 30.0, 90.0])
    def test_lower_boundary_is_renewal_not_decay(self, half_life: float) -> None:
        assert _call(0.5 * half_life, half_life).axis is StaleAxis.RENEWAL_REQUIRED

    @pytest.mark.parametrize("half_life", [7.0, 14.0, 30.0, 90.0])
    def test_upper_boundary_is_abstain_not_renewal(self, half_life: float) -> None:
        assert _call(1.5 * half_life, half_life).axis is StaleAxis.ABSTAIN

    def test_three_adjacent_samples(self) -> None:
        hl = 20.0
        assert _call(9.0, hl).axis is StaleAxis.DECAY_PENALTY
        assert _call(10.0, hl).axis is StaleAxis.RENEWAL_REQUIRED
        assert _call(30.0, hl).axis is StaleAxis.ABSTAIN


# ---------------------------------------------------------------------------
# Full field verification
# ---------------------------------------------------------------------------


class TestDecisionFields:
    def test_decay_penalty_all_fields(self) -> None:
        d = evaluate_stale_axis(evidence_age_days=5.0, half_life_used_days=30.0)
        assert d.axis is StaleAxis.DECAY_PENALTY
        assert d.evidence_age_days == 5.0
        assert d.half_life_used_days == 30.0
        assert d.calibration_delta == -2
        assert d.ratio == pytest.approx(5.0 / 30.0)

    def test_abstain_all_fields(self) -> None:
        d = evaluate_stale_axis(evidence_age_days=60.0, half_life_used_days=30.0)
        assert d.axis is StaleAxis.ABSTAIN
        assert d.calibration_delta == 0
        assert d.ratio == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Invalid inputs
# ---------------------------------------------------------------------------


class TestInvalidInputs:
    def test_negative_age_raises(self) -> None:
        with pytest.raises(ValueError, match="evidence_age_days"):
            evaluate_stale_axis(-1.0, 30.0)

    def test_zero_half_life_raises(self) -> None:
        with pytest.raises(ValueError, match="half_life_used_days"):
            evaluate_stale_axis(10.0, 0.0)

    def test_negative_half_life_raises(self) -> None:
        with pytest.raises(ValueError, match="half_life_used_days"):
            evaluate_stale_axis(10.0, -5.0)

    def test_zero_age_is_valid(self) -> None:
        assert evaluate_stale_axis(0.0, 30.0).axis is StaleAxis.DECAY_PENALTY

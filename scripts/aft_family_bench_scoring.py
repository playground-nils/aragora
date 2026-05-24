"""Pure-function scoring helpers for the model-family bench (PR-B).

All helpers in this module are deterministic and have no side effects —
they take in-memory data and return in-memory data. They are unit-tested
in `tests/scripts/test_aft_family_bench.py` without any network, model
loading, or subprocess invocations.

The helpers compose with the AFT statistical primitives already on main:
- `scripts.aft_harness.brier_score`
- `scripts.aft_harness.accuracy`
- `scripts.aft_harness.mcnemar_p`

Three things this module adds:

1. `pareto_frontier(points)` — given `(cost, quality, label)` points,
   return the labels that are not strictly dominated by any other.
2. `jaccard_distance(set_a, set_b)` — for H4 (non-redundant findings).
3. `cost_quality_table(per_family_summaries)` — build a sortable table
   from per-family aggregate stats.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypedDict


class FamilyPoint(TypedDict):
    """One family's aggregated cost/quality position on a task class."""

    family: str
    cost_usd: float
    accuracy: float
    brier: float


class ParetoPoint(TypedDict):
    """A family that sits on the cost/quality Pareto frontier."""

    family: str
    cost_usd: float
    accuracy: float


def pareto_frontier(points: Iterable[FamilyPoint]) -> list[ParetoPoint]:
    """Return families on the cost/quality Pareto frontier.

    A family is on the frontier if no other family has *both* equal-or-
    lower cost AND strictly higher accuracy, OR equal-or-higher accuracy
    AND strictly lower cost.

    Ties (same cost AND same accuracy) keep all tied families on the
    frontier — we don't break ties arbitrarily because at this scale of
    measurement noise, calling one of them "better" would be false
    precision.
    """
    pts = list(points)
    frontier: list[ParetoPoint] = []
    for candidate in pts:
        dominated = False
        for other in pts:
            if other["family"] == candidate["family"]:
                continue
            # `other` dominates `candidate` if it is at least as good on
            # both dimensions and strictly better on at least one.
            if (
                other["cost_usd"] <= candidate["cost_usd"]
                and other["accuracy"] >= candidate["accuracy"]
                and (
                    other["cost_usd"] < candidate["cost_usd"]
                    or other["accuracy"] > candidate["accuracy"]
                )
            ):
                dominated = True
                break
        if not dominated:
            frontier.append(
                ParetoPoint(
                    family=candidate["family"],
                    cost_usd=candidate["cost_usd"],
                    accuracy=candidate["accuracy"],
                )
            )
    # Stable, deterministic order: by cost ascending, then accuracy descending.
    frontier.sort(key=lambda p: (p["cost_usd"], -p["accuracy"]))
    return frontier


def jaccard_distance(set_a: Iterable[str], set_b: Iterable[str]) -> float:
    """Jaccard distance between two finding-sets: 1 - |A∩B| / |A∪B|.

    Returns 0.0 if both sets are empty (treat as identical).
    """
    a = set(set_a)
    b = set(set_b)
    union = a | b
    if not union:
        return 0.0
    intersection = a & b
    return 1.0 - (len(intersection) / len(union))


def cost_quality_table(
    per_family: dict[str, FamilyPoint],
    *,
    sort_by: str = "cost_per_correct",
) -> list[dict[str, float | str]]:
    """Build a sortable cost/quality table from per-family aggregates.

    Adds a derived `cost_per_correct` column that is `cost_usd / n_correct`
    where `n_correct = accuracy * n`. For the bench's small-n regime we
    don't know `n` per family from this signature, so the derived column
    is `cost_usd / max(accuracy, 1e-9)` instead — a normalized cost-per-
    accuracy-point metric.

    `sort_by` may be any of `cost_per_correct`, `accuracy`, `brier`, or
    `cost_usd`. Default sorts cheapest-correct-per-dollar first.
    """
    rows: list[dict[str, float | str]] = []
    for family, point in per_family.items():
        cost_per_correct = (
            point["cost_usd"] / max(point["accuracy"], 1e-9)
            if point["accuracy"] > 0
            else float("inf")
        )
        rows.append(
            {
                "family": family,
                "accuracy": point["accuracy"],
                "brier": point["brier"],
                "cost_usd": point["cost_usd"],
                "cost_per_correct": cost_per_correct,
            }
        )
    valid_keys = {"cost_per_correct", "accuracy", "brier", "cost_usd"}
    if sort_by not in valid_keys:
        raise ValueError(f"sort_by must be one of {sorted(valid_keys)}; got {sort_by!r}")
    reverse = sort_by in {"accuracy"}  # bigger is better for accuracy
    rows.sort(key=lambda r: r[sort_by], reverse=reverse)
    return rows


def small_n_warning(
    pairwise_disagreement_counts: dict[str, int], *, threshold: int = 15
) -> list[str]:
    """Return a list of human-readable warnings for under-powered pairs.

    A McNemar test on paired binary outcomes needs roughly `threshold`
    disagreement pairs to detect a 10-accuracy-point gap at p<0.05.
    Below that we should refuse to make significance claims.
    """
    warnings: list[str] = []
    for pair, count in sorted(pairwise_disagreement_counts.items()):
        if count < threshold:
            warnings.append(
                f"{pair}: only {count} disagreement pair(s); "
                f"need ≥{threshold} for p<0.05 detection of a 10-point gap. "
                f"Treat as directional, not conclusive."
            )
    return warnings

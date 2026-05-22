#!/usr/bin/env python3
"""Run the Advocate Feasibility Test on a PR-decision corpus."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import time
from typing import Any

from aragora.advocates import (
    AdvocateInput,
    LocalMockUserInterestAdvocate,
    RulesUserInterestAdvocate,
)


SCHEMA_VERSION = "aft.result.v1"
DECISIONS = {"accept", "challenge", "ask_user", "block"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _advocate_input(example: dict[str, Any]) -> AdvocateInput:
    return AdvocateInput(
        task_type=str(example.get("task_type") or "pr_triage"),
        artifact_summary=str(example.get("artifact_summary") or ""),
        proposed_action=str(example.get("proposed_action") or "merge"),
        context_features=dict(example.get("context_features") or {}),
    )


def _rules_prediction(example: dict[str, Any]) -> dict[str, Any]:
    advocate = RulesUserInterestAdvocate()
    output = advocate.evaluate(_advocate_input(example))
    return {
        "decision": output.decision,
        "confidence": output.confidence,
        "rationale": output.rationale,
        "cited_features": list(output.cited_features),
        "cost_usd": 0.0,
        "mock": False,
    }


def _local_advocate_prediction(example: dict[str, Any]) -> dict[str, Any]:
    advocate = LocalMockUserInterestAdvocate()
    output = advocate.evaluate(_advocate_input(example))
    return {
        "decision": output.decision,
        "confidence": output.confidence,
        "rationale": output.rationale,
        "cited_features": list(output.cited_features),
        "cost_usd": 0.0,
        "mock": True,
    }


def _load_frontier_fixture(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(
            "--frontier-fixture must be a JSON object keyed by artifact_id or pr_number"
        )
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def _frontier_prediction(
    example: dict[str, Any],
    fixture: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    keys = [str(example.get("artifact_id") or ""), str(example.get("pr_number") or "")]
    for key in keys:
        if key in fixture:
            raw = fixture[key]
            decision = str(raw.get("decision") or "ask_user")
            return {
                "decision": decision if decision in DECISIONS else "ask_user",
                "confidence": float(raw.get("confidence", 0.5)),
                "rationale": str(raw.get("rationale") or "frontier fixture prediction"),
                "cited_features": list(raw.get("cited_features") or []),
                "cost_usd": float(raw.get("cost_usd", 0.0)),
                "mock": False,
            }
    return {
        "decision": "ask_user",
        "confidence": 0.0,
        "rationale": "frontier model not configured; deterministic unavailable prediction",
        "cited_features": [],
        "cost_usd": 0.0,
        "mock": True,
    }


def _predict(
    arm: str,
    example: dict[str, Any],
    frontier_fixture: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    start = time.perf_counter()
    if arm == "rules":
        prediction = _rules_prediction(example)
    elif arm == "local_advocate":
        prediction = _local_advocate_prediction(example)
    elif arm == "frontier_prompt":
        prediction = _frontier_prediction(example, frontier_fixture)
    else:
        raise ValueError(f"Unknown arm: {arm}")
    prediction["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
    return prediction


def summarize(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in predictions:
        by_arm[str(row["arm"])].append(row)

    arms: dict[str, dict[str, Any]] = {}
    for arm, rows in sorted(by_arm.items()):
        total = len(rows)
        correct = sum(1 for row in rows if row["prediction"]["decision"] == row["label"])
        confusion = Counter(f"{row['label']}->{row['prediction']['decision']}" for row in rows)
        arms[arm] = {
            "examples": total,
            "accuracy": correct / total if total else 0.0,
            "correct": correct,
            "avg_confidence": (
                sum(float(row["prediction"]["confidence"]) for row in rows) / total
                if total
                else 0.0
            ),
            "avg_latency_ms": (
                sum(float(row["prediction"]["latency_ms"]) for row in rows) / total
                if total
                else 0.0
            ),
            "total_cost_usd": sum(float(row["prediction"].get("cost_usd", 0.0)) for row in rows),
            "confusion": dict(sorted(confusion.items())),
        }

    rules_accuracy = arms.get("rules", {}).get("accuracy")
    local_accuracy = arms.get("local_advocate", {}).get("accuracy")
    frontier_accuracy = arms.get("frontier_prompt", {}).get("accuracy")
    deltas = {}
    if isinstance(rules_accuracy, float) and isinstance(local_accuracy, float):
        deltas["local_advocate_minus_rules"] = local_accuracy - rules_accuracy
    if isinstance(frontier_accuracy, float) and isinstance(local_accuracy, float):
        deltas["local_advocate_minus_frontier_prompt"] = local_accuracy - frontier_accuracy

    return {
        "schema_version": SCHEMA_VERSION,
        "examples": len({row["artifact_id"] for row in predictions}),
        "predictions": len(predictions),
        "arms": arms,
        "deltas": deltas,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--arms",
        default="rules,frontier_prompt,local_advocate",
        help="Comma-separated arms: rules, frontier_prompt, local_advocate",
    )
    parser.add_argument("--split", choices=["train", "holdout", "all"], default="holdout")
    parser.add_argument("--frontier-fixture", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    arms = [arm.strip() for arm in args.arms.split(",") if arm.strip()]
    unknown = sorted(set(arms) - {"rules", "frontier_prompt", "local_advocate"})
    if unknown:
        raise SystemExit(f"Unknown arms: {', '.join(unknown)}")

    examples = load_jsonl(args.corpus)
    if args.split != "all":
        examples = [example for example in examples if example.get("split") == args.split]
    frontier_fixture = _load_frontier_fixture(args.frontier_fixture)

    predictions: list[dict[str, Any]] = []
    for example in examples:
        for arm in arms:
            predictions.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_id": example.get("artifact_id"),
                    "pr_number": example.get("pr_number"),
                    "split": example.get("split"),
                    "label": example.get("label"),
                    "arm": arm,
                    "prediction": _predict(arm, example, frontier_fixture),
                }
            )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = args.output_dir / "predictions.jsonl"
    with predictions_path.open("w", encoding="utf-8") as handle:
        for row in predictions:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    summary = summarize(predictions)
    summary["corpus"] = str(args.corpus)
    summary["split"] = args.split
    summary["predictions_path"] = str(predictions_path)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from pathlib import Path

import scripts.aft_harness as mod


def _write_corpus(path: Path) -> None:
    rows = [
        {
            "schema_version": "aft.pr_decision.v1",
            "task_type": "pr_triage",
            "artifact_id": "pr-1",
            "pr_number": 1,
            "artifact_summary": "PR #1 docs-only",
            "proposed_action": "merge",
            "context_features": {"tier": 0, "failing_checks": 0},
            "label": "accept",
            "split": "holdout",
        },
        {
            "schema_version": "aft.pr_decision.v1",
            "task_type": "pr_triage",
            "artifact_id": "pr-2",
            "pr_number": 2,
            "artifact_summary": "PR #2 workflow policy",
            "proposed_action": "merge",
            "context_features": {"tier": 4, "requires_human_risk_settlement": True},
            "label": "block",
            "split": "holdout",
        },
    ]
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_harness_writes_predictions_and_summary(tmp_path: Path, capsys) -> None:
    corpus = tmp_path / "corpus.jsonl"
    output_dir = tmp_path / "results"
    fixture = tmp_path / "frontier.json"
    _write_corpus(corpus)
    fixture.write_text(
        json.dumps(
            {
                "pr-1": {"decision": "accept", "confidence": 0.7, "rationale": "docs-only"},
                "pr-2": {"decision": "challenge", "confidence": 0.6, "rationale": "risky"},
            }
        ),
        encoding="utf-8",
    )

    rc = mod.main(
        [
            "--corpus",
            str(corpus),
            "--output-dir",
            str(output_dir),
            "--frontier-fixture",
            str(fixture),
        ]
    )

    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["examples"] == 2
    assert set(summary["arms"]) == {"rules", "frontier_prompt", "local_advocate"}
    assert summary["arms"]["frontier_prompt"]["mock_predictions"] == 0
    assert summary["arms"]["frontier_prompt"]["stubbed"] is False
    assert summary["arms"]["local_advocate"]["mock_predictions"] == 2
    assert summary["arms"]["local_advocate"]["stubbed"] is True
    assert (output_dir / "predictions.jsonl").exists()
    assert (output_dir / "summary.json").exists()


def test_summarize_reports_accuracy() -> None:
    predictions = [
        {
            "artifact_id": "pr-1",
            "arm": "rules",
            "label": "accept",
            "prediction": {"decision": "accept", "confidence": 0.9, "latency_ms": 1, "cost_usd": 0},
        },
        {
            "artifact_id": "pr-2",
            "arm": "rules",
            "label": "block",
            "prediction": {"decision": "accept", "confidence": 0.2, "latency_ms": 1, "cost_usd": 0},
        },
    ]

    summary = mod.summarize(predictions)

    assert summary["arms"]["rules"]["accuracy"] == 0.5
    assert summary["arms"]["rules"]["mock_predictions"] == 0
    assert summary["arms"]["rules"]["real_predictions"] == 2
    assert summary["arms"]["rules"]["stubbed"] is False
    assert summary["arms"]["rules"]["confusion"] == {"accept->accept": 1, "block->accept": 1}

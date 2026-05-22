from __future__ import annotations

import json
from pathlib import Path

import scripts.extract_pr_decision_corpus as mod


def _sample_prs() -> list[dict]:
    return [
        {
            "number": 1,
            "title": "docs: safe update",
            "state": "MERGED",
            "isDraft": False,
            "mergeStateStatus": "CLEAN",
            "mergedAt": "2026-05-22T00:00:00Z",
            "additions": 3,
            "deletions": 1,
            "changedFiles": 1,
            "files": [{"path": "docs/example.md"}],
            "author": {"login": "alice"},
            "labels": [{"name": "docs"}],
            "url": "https://github.example/pr/1",
        },
        {
            "number": 2,
            "title": "fix: do not leak token=sk-ant-secretsecretsecret",
            "state": "OPEN",
            "isDraft": True,
            "mergeStateStatus": "CLEAN",
            "additions": 5,
            "deletions": 2,
            "changedFiles": 1,
            "files": [{"path": "scripts/example.py"}],
            "author": {"login": "bob"},
            "labels": [],
            "url": "https://github.example/pr/2",
        },
    ]


def test_pr_to_example_redacts_and_labels() -> None:
    example = mod.pr_to_example(
        _sample_prs()[1],
        seed="test",
        holdout_ratio=0.2,
        packet={"pr_number": 2, "tier": 2, "requires_human_risk_settlement": False},
    )

    blob = json.dumps(example)
    assert "sk-ant" not in blob
    assert "[REDACTED_SECRET]" in blob
    assert example["label"] == "ask_user"
    assert example["context_features"]["tier"] == 2
    assert example["schema_version"] == mod.SCHEMA_VERSION


def test_extractor_writes_deterministic_jsonl(tmp_path: Path, capsys) -> None:
    source = tmp_path / "prs.json"
    output = tmp_path / "corpus.jsonl"
    source.write_text(json.dumps(_sample_prs()), encoding="utf-8")

    rc = mod.main(
        [
            "--source-json",
            str(source),
            "--output",
            str(output),
            "--seed",
            "fixed",
            "--holdout-ratio",
            "0.5",
        ]
    )

    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert summary["examples"] == 2
    assert [row["pr_number"] for row in rows] == [1, 2]
    assert {row["split"] for row in rows} <= {"train", "holdout"}

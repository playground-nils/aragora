from __future__ import annotations

from pathlib import Path

from scripts.check_aragora_review_gate_policy import (
    check_repo,
    find_review_gate_policy_violations,
)


def _valid_gate_data() -> dict:
    return {
        "on": {
            "pull_request": {
                "types": ["opened", "synchronize", "reopened", "ready_for_review"],
            },
            "workflow_dispatch": {},
        },
        "jobs": {
            "changes": {},
            "review": {
                "steps": [
                    {
                        "name": "Run Aragora Review",
                        "run": """
if [[ ! -s /tmp/pr.diff ]]; then
  echo "skip=true" >> "$GITHUB_OUTPUT"
  exit 0
fi
cat /tmp/pr.diff | python -m aragora.cli.review --output /tmp/review.json
if [[ ! -f /tmp/review.json ]]; then
  exit 1
fi
""",
                    }
                ]
            },
            "aragora-review": {
                "if": "always()",
                "needs": ["changes", "review"],
            },
        },
    }


def _valid_gate_text() -> str:
    return """
jobs:
  review:
    steps:
      - name: Run Aragora Review
        run: |
          if [[ ! -s /tmp/pr.diff ]]; then
            echo "skip=true" >> "$GITHUB_OUTPUT"
            exit 0
          fi
          cat /tmp/pr.diff | python -m aragora.cli.review --output /tmp/review.json
          if [[ ! -f /tmp/review.json ]]; then
            exit 1
          fi
  aragora-review:
    if: always()
    needs: [changes, review]
    steps:
      - run: |
          if [[ "$SHOULD_REVIEW" != "true" ]]; then
            exit 0
          fi
          if [[ "$REVIEW_RESULT" != "success" ]]; then
            exit 1
          fi
"""


def _valid_manual_data() -> dict:
    return {"on": {"workflow_dispatch": {}}}


def test_policy_accepts_valid_review_gate_configuration() -> None:
    violations = find_review_gate_policy_violations(
        _valid_gate_data(),
        _valid_gate_text(),
        _valid_manual_data(),
    )
    assert violations == []


def test_policy_rejects_pull_request_paths_filter() -> None:
    gate = _valid_gate_data()
    gate["on"]["pull_request"]["paths"] = ["aragora/**"]
    violations = find_review_gate_policy_violations(gate, _valid_gate_text(), _valid_manual_data())
    assert "review gate pull_request trigger must not define paths filters" in violations


def test_policy_rejects_fail_open_review_execution() -> None:
    gate = _valid_gate_data()
    gate["jobs"]["review"]["steps"][0]["run"] = gate["jobs"]["review"]["steps"][0]["run"].replace(
        "python -m aragora.cli.review --output /tmp/review.json",
        "python -m aragora.cli.review --output /tmp/review.json || true",
    )
    text = _valid_gate_text().replace(
        "python -m aragora.cli.review --output /tmp/review.json",
        "python -m aragora.cli.review --output /tmp/review.json || true",
    )
    violations = find_review_gate_policy_violations(
        gate,
        text,
        _valid_manual_data(),
    )
    assert "review execution must not use || true" in violations


def test_policy_rejects_manual_workflow_pull_request_trigger() -> None:
    manual = {"on": {"pull_request": {"types": ["opened"]}}}
    violations = find_review_gate_policy_violations(
        _valid_gate_data(),
        _valid_gate_text(),
        manual,
    )
    assert "manual Aragora review workflow must not trigger on pull_request" in violations


def test_repo_review_gate_policy_passes_for_current_tree() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    assert check_repo(repo_root) == []

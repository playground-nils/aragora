"""Tests for ralph blocker classification."""

from __future__ import annotations

import pytest

from aragora.ralph.classifier import BlockerKind, classify_blocker


class TestBlockerKindEnum:
    def test_deterministic_kinds(self) -> None:
        assert BlockerKind.REVIEWER_MISSING_DIFF.is_deterministic
        assert BlockerKind.SCOPE_FALSE_POSITIVE.is_deterministic
        assert BlockerKind.WORKER_CLEAN_EXIT_NO_EFFECT.is_deterministic
        assert BlockerKind.MANIFEST_IDENTIFIER_COLLISION.is_deterministic
        assert BlockerKind.RUNTIME_TIMEOUT_CONFIG.is_deterministic
        assert BlockerKind.RECEIPT_EMISSION_GAP.is_deterministic

    def test_escalation_kinds(self) -> None:
        assert not BlockerKind.REVIEWER_AUTH_OR_BILLING.is_deterministic
        assert not BlockerKind.BUDGET_EXHAUSTION.is_deterministic
        assert not BlockerKind.INFRA_FAILURE.is_deterministic
        assert not BlockerKind.UNKNOWN.is_deterministic


class TestClassifyBlocker:
    def test_still_running_returns_none(self) -> None:
        assert classify_blocker(stop_reason="still_running", manifest_dict={}) is None

    def test_campaign_complete_returns_none(self) -> None:
        assert classify_blocker(stop_reason="campaign_complete", manifest_dict={}) is None

    def test_budget_exhausted(self) -> None:
        result = classify_blocker(stop_reason="budget_exhausted", manifest_dict={})
        assert result == BlockerKind.BUDGET_EXHAUSTION

    def test_time_limit_with_progress(self) -> None:
        manifest = {
            "execution_state": {"completed_projects": ["proj-001"]},
            "projects": [],
        }
        result = classify_blocker(stop_reason="time_limit_exceeded", manifest_dict=manifest)
        assert result == BlockerKind.RUNTIME_TIMEOUT_CONFIG

    def test_time_limit_no_progress(self) -> None:
        manifest = {
            "execution_state": {"completed_projects": []},
            "projects": [],
        }
        result = classify_blocker(stop_reason="time_limit_exceeded", manifest_dict=manifest)
        assert result == BlockerKind.INFRA_FAILURE

    def test_blocked_with_deliverable_and_review_rejection(self) -> None:
        manifest = {
            "projects": [
                {
                    "project_id": "p1",
                    "status": "blocked",
                    "last_run_outcome": "deliverable_created",
                    "review": {
                        "status": "changes_requested",
                        "findings": ["needs more detail"],
                    },
                }
            ]
        }
        result = classify_blocker(stop_reason="campaign_blocked", manifest_dict=manifest)
        assert result == BlockerKind.REVIEWER_MISSING_DIFF

    def test_blocked_with_scope_violation_finding(self) -> None:
        manifest = {
            "projects": [
                {
                    "project_id": "p1",
                    "status": "blocked",
                    "last_run_outcome": "deliverable_created",
                    "review": {
                        "status": "blocked_nonreviewable",
                        "findings": ["scope violation: file outside declared scope"],
                    },
                }
            ]
        }
        result = classify_blocker(stop_reason="campaign_blocked", manifest_dict=manifest)
        assert result == BlockerKind.SCOPE_FALSE_POSITIVE

    def test_blocked_with_billing_finding_escalates(self) -> None:
        manifest = {
            "projects": [
                {
                    "project_id": "p1",
                    "status": "blocked",
                    "last_run_outcome": "deliverable_created",
                    "review": {
                        "status": "blocked_nonreviewable",
                        "findings": ["Review blocked (billing): Credit balance is too low"],
                    },
                }
            ]
        }
        result = classify_blocker(stop_reason="campaign_blocked", manifest_dict=manifest)
        assert result == BlockerKind.REVIEWER_AUTH_OR_BILLING

    def test_blocked_with_auth_subprocess_finding_escalates(self) -> None:
        manifest = {
            "projects": [
                {
                    "project_id": "p1",
                    "status": "blocked",
                    "last_run_outcome": "deliverable_created",
                    "review": {
                        "status": "blocked_nonreviewable",
                        "findings": ["Review failed: CLISubprocessError. Run claude auth login."],
                    },
                }
            ]
        }
        result = classify_blocker(stop_reason="campaign_blocked", manifest_dict=manifest)
        assert result == BlockerKind.REVIEWER_AUTH_OR_BILLING

    def test_blocked_with_review_connection_error_escalates_infra(self) -> None:
        manifest = {
            "projects": [
                {
                    "project_id": "p1",
                    "status": "blocked",
                    "last_run_outcome": "deliverable_created",
                    "review": {
                        "status": "blocked_nonreviewable",
                        "findings": ["Review failed: AgentConnectionError"],
                        "raw_review": {"error": "AgentConnectionError"},
                    },
                }
            ]
        }
        result = classify_blocker(stop_reason="campaign_blocked", manifest_dict=manifest)
        assert result == BlockerKind.INFRA_FAILURE

    def test_blocked_with_verification_exec_format_error_escalates_infra(self) -> None:
        manifest = {
            "projects": [
                {
                    "project_id": "p1",
                    "status": "blocked",
                    "last_run_outcome": "deliverable_created",
                    "review": {
                        "status": "blocked_nonreviewable",
                        "findings": [],
                    },
                    "attempt_history": [
                        {
                            "failure_detail": (
                                "merge gate blocked: verification failed: "
                                "python -m pytest tests/ralph/test_classifier.py -q "
                                "(exit 126) - /bin/bash: "
                                "/Users/armand/local/aws-cli/python: cannot execute "
                                "binary file: Exec format error"
                            ),
                            "blockers": [
                                "merge gate blocked: verification failed: python -m pytest "
                                "tests/ralph/test_classifier.py -q (exit 126)"
                            ],
                        }
                    ],
                }
            ]
        }
        result = classify_blocker(stop_reason="campaign_blocked", manifest_dict=manifest)
        assert result == BlockerKind.INFRA_FAILURE

    def test_blocked_with_true_diff_missing_still_maps_to_reviewer_missing_diff(self) -> None:
        manifest = {
            "projects": [
                {
                    "project_id": "p1",
                    "status": "blocked",
                    "last_run_outcome": "deliverable_created",
                    "review": {
                        "status": "blocked_nonreviewable",
                        "findings": ["Reviewer could not verify acceptance criteria without diff."],
                    },
                }
            ]
        }
        result = classify_blocker(stop_reason="campaign_blocked", manifest_dict=manifest)
        assert result == BlockerKind.REVIEWER_MISSING_DIFF

    def test_blocked_with_repeated_clean_exit(self) -> None:
        manifest = {
            "projects": [
                {
                    "project_id": "p1",
                    "status": "failed",
                    "last_run_outcome": "clean_exit_no_deliverable",
                },
                {
                    "project_id": "p2",
                    "status": "skipped",
                    "last_run_outcome": "clean_exit_no_deliverable",
                },
            ]
        }
        result = classify_blocker(stop_reason="campaign_blocked", manifest_dict=manifest)
        assert result == BlockerKind.WORKER_CLEAN_EXIT_NO_EFFECT

    def test_blocked_with_repeated_needs_human(self) -> None:
        manifest = {
            "projects": [
                {
                    "project_id": "p1",
                    "status": "blocked",
                    "last_run_outcome": "needs_human",
                },
                {
                    "project_id": "p2",
                    "status": "blocked",
                    "last_run_outcome": "needs_human",
                },
            ]
        }
        result = classify_blocker(stop_reason="campaign_blocked", manifest_dict=manifest)
        assert result == BlockerKind.WORKER_CLEAN_EXIT_NO_EFFECT

    def test_blocked_with_mixed_stall_outcomes(self) -> None:
        manifest = {
            "projects": [
                {
                    "project_id": "p1",
                    "status": "blocked",
                    "last_run_outcome": "needs_human",
                },
                {
                    "project_id": "p2",
                    "status": "failed",
                    "last_run_outcome": "clean_exit_no_deliverable",
                },
            ]
        }
        result = classify_blocker(stop_reason="campaign_blocked", manifest_dict=manifest)
        assert result == BlockerKind.WORKER_CLEAN_EXIT_NO_EFFECT

    def test_blocked_with_single_needs_human(self) -> None:
        manifest = {
            "projects": [
                {
                    "project_id": "p1",
                    "status": "blocked",
                    "last_run_outcome": "needs_human",
                    "receipt_id": "r1",
                },
            ]
        }
        result = classify_blocker(stop_reason="campaign_blocked", manifest_dict=manifest)
        assert result == BlockerKind.WORKER_CLEAN_EXIT_NO_EFFECT

    def test_blocked_with_receipt_gap(self) -> None:
        manifest = {
            "projects": [
                {
                    "project_id": "p1",
                    "status": "completed",
                    "last_run_outcome": "deliverable_created",
                    "receipt_id": "path/to/receipt.yaml",
                    "review": {"status": "passed", "findings": []},
                },
                {
                    "project_id": "p2",
                    "status": "failed",
                    "last_run_outcome": "crash",
                    # No receipt_id — gap!
                },
            ]
        }
        result = classify_blocker(stop_reason="campaign_blocked", manifest_dict=manifest)
        assert result == BlockerKind.RECEIPT_EMISSION_GAP

    def test_blocked_with_duplicate_file_scope_hints(self) -> None:
        manifest = {
            "projects": [
                {
                    "project_id": "p1",
                    "status": "completed",
                    "receipt_id": "r1",
                    "file_scope_hints": ["docs/ADR/019.md"],
                },
                {
                    "project_id": "p2",
                    "status": "blocked",
                    "last_run_outcome": "blocked",
                    "receipt_id": "r2",
                    "file_scope_hints": ["docs/ADR/019.md"],
                },
            ]
        }
        result = classify_blocker(stop_reason="campaign_blocked", manifest_dict=manifest)
        assert result == BlockerKind.MANIFEST_IDENTIFIER_COLLISION

    def test_unknown_stop_reason(self) -> None:
        result = classify_blocker(stop_reason="something_new", manifest_dict={})
        assert result == BlockerKind.UNKNOWN

    def test_blocked_with_no_projects(self) -> None:
        result = classify_blocker(stop_reason="campaign_blocked", manifest_dict={"projects": []})
        assert result == BlockerKind.UNKNOWN

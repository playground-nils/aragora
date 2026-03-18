"""Tests for LLM-powered blocker classification."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from aragora.ralph.classifier import BlockerKind
from aragora.ralph.llm_classifier import (
    ClassificationVerdict,
    LLMBlockerClassifier,
    MergeVerdict,
    ScopeVerdict,
)


class TestClassificationVerdict:
    def test_verdict_fields(self) -> None:
        v = ClassificationVerdict(
            kind=BlockerKind.SCOPE_FALSE_POSITIVE,
            confidence=0.95,
            reasoning="Test file edits are expected companions.",
        )
        assert v.kind == BlockerKind.SCOPE_FALSE_POSITIVE
        assert v.confidence == 0.95
        assert "companions" in v.reasoning


class TestScopeVerdict:
    def test_verdict_fields(self) -> None:
        v = ScopeVerdict(
            justified_paths=["tests/test_foo.py"],
            rejected_paths=[],
            reasoning="Test file corresponds to implementation.",
        )
        assert v.justified_paths == ["tests/test_foo.py"]
        assert v.rejected_paths == []


class TestMergeVerdict:
    def test_verdict_fields(self) -> None:
        v = MergeVerdict(
            ready=True,
            blocking_issues=[],
            advisory_issues=["Consider adding docstring"],
            reasoning="All acceptance criteria met.",
        )
        assert v.ready is True
        assert len(v.advisory_issues) == 1


class TestLLMClassifyBlocker:
    @pytest.mark.asyncio
    async def test_classify_scope_false_positive(self) -> None:
        llm_response = json.dumps(
            {
                "kind": "scope_false_positive",
                "confidence": 0.92,
                "reasoning": "Worker edited test files that correspond to implementation scope.",
            }
        )
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(return_value=llm_response)

        with patch("aragora.agents.base.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.classify_blocker(
                manifest_dict={
                    "projects": [
                        {
                            "project_id": "B-3",
                            "status": "blocked",
                            "last_run_outcome": "needs_human",
                            "review": {
                                "status": "changes_requested",
                                "findings": [
                                    "scope violation: tests/swarm/test_campaign.py outside declared scope"
                                ],
                            },
                            "attempt_history": [
                                {
                                    "failure_detail": "worker edited files outside permitted scope: tests/swarm/test_campaign.py"
                                }
                            ],
                        }
                    ]
                },
                stop_reason="campaign_blocked",
            )
        assert verdict.kind == BlockerKind.SCOPE_FALSE_POSITIVE
        assert verdict.confidence > 0.8

    @pytest.mark.asyncio
    async def test_classify_auth_failure(self) -> None:
        llm_response = json.dumps(
            {
                "kind": "reviewer_auth_or_billing_failure",
                "confidence": 0.99,
                "reasoning": "Credit balance exhausted.",
            }
        )
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(return_value=llm_response)

        with patch("aragora.agents.base.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.classify_blocker(
                manifest_dict={
                    "projects": [
                        {
                            "project_id": "B-1",
                            "status": "blocked",
                            "last_run_outcome": "deliverable_created",
                            "review": {
                                "status": "blocked_nonreviewable",
                                "findings": ["Credit balance is too low"],
                            },
                        }
                    ]
                },
                stop_reason="campaign_blocked",
            )
        assert verdict.kind == BlockerKind.REVIEWER_AUTH_OR_BILLING

    @pytest.mark.asyncio
    async def test_classify_falls_back_on_malformed_response(self) -> None:
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(return_value="not json at all")

        with patch("aragora.agents.base.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.classify_blocker(
                manifest_dict={"projects": []},
                stop_reason="campaign_blocked",
            )
        # Should return UNKNOWN with low confidence on parse failure
        assert verdict.kind == BlockerKind.UNKNOWN
        assert verdict.confidence < 0.5

    @pytest.mark.asyncio
    async def test_classify_falls_back_on_agent_error(self) -> None:
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(side_effect=RuntimeError("API down"))

        with patch("aragora.agents.base.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.classify_blocker(
                manifest_dict={"projects": []},
                stop_reason="campaign_blocked",
            )
        assert verdict.kind == BlockerKind.UNKNOWN
        assert verdict.confidence == 0.0


class TestLLMAdjudicateScope:
    @pytest.mark.asyncio
    async def test_justifies_test_file_companion(self) -> None:
        llm_response = json.dumps(
            {
                "justified_paths": ["tests/swarm/test_campaign.py"],
                "rejected_paths": [],
                "reasoning": "Test file directly tests the implementation in declared scope.",
            }
        )
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(return_value=llm_response)

        with patch("aragora.agents.base.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.adjudicate_scope(
                task_description="Implement budget cap validation in campaign executor",
                declared_scope=["aragora/swarm/campaign.py"],
                changed_paths=["aragora/swarm/campaign.py", "tests/swarm/test_campaign.py"],
                violations=[
                    {
                        "type": "out_of_scope",
                        "path": "tests/swarm/test_campaign.py",
                        "allowed_scope": ["aragora/swarm/campaign.py"],
                    }
                ],
            )
        assert "tests/swarm/test_campaign.py" in verdict.justified_paths
        assert verdict.rejected_paths == []

    @pytest.mark.asyncio
    async def test_rejects_unrelated_file(self) -> None:
        llm_response = json.dumps(
            {
                "justified_paths": [],
                "rejected_paths": ["aragora/billing/cost_tracker.py"],
                "reasoning": "Billing module is unrelated to swarm campaign work.",
            }
        )
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(return_value=llm_response)

        with patch("aragora.agents.base.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.adjudicate_scope(
                task_description="Fix campaign reviewer diff",
                declared_scope=["aragora/swarm/campaign.py"],
                changed_paths=["aragora/swarm/campaign.py", "aragora/billing/cost_tracker.py"],
                violations=[
                    {
                        "type": "out_of_scope",
                        "path": "aragora/billing/cost_tracker.py",
                        "allowed_scope": ["aragora/swarm/campaign.py"],
                    }
                ],
            )
        assert verdict.rejected_paths == ["aragora/billing/cost_tracker.py"]

    @pytest.mark.asyncio
    async def test_fail_closed_on_error(self) -> None:
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(side_effect=RuntimeError("timeout"))

        with patch("aragora.agents.base.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.adjudicate_scope(
                task_description="Any task",
                declared_scope=["src/foo.py"],
                changed_paths=["src/foo.py", "src/bar.py"],
                violations=[
                    {"type": "out_of_scope", "path": "src/bar.py", "allowed_scope": ["src/foo.py"]}
                ],
            )
        # Fail closed: all violation paths stay rejected
        assert verdict.rejected_paths == ["src/bar.py"]
        assert verdict.justified_paths == []


class TestLLMEvaluateMergeReadiness:
    @pytest.mark.asyncio
    async def test_ready_despite_cosmetic_test_noise(self) -> None:
        llm_response = json.dumps(
            {
                "ready": True,
                "blocking_issues": [],
                "advisory_issues": ["Test output includes deprecation warning"],
                "reasoning": "All acceptance criteria met. Test failure is a pre-existing deprecation warning, not caused by this change.",
            }
        )
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(return_value=llm_response)

        with patch("aragora.agents.base.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.evaluate_merge_readiness(
                acceptance_criteria=["Budget caps enforced", "Tests pass"],
                verification_results=[
                    {
                        "command": "pytest tests/swarm -q",
                        "passed": False,
                        "exit_code": 1,
                        "stderr": "DeprecationWarning: old API",
                    },
                ],
                changed_paths=["aragora/swarm/campaign.py"],
                diff_summary="Added budget cap validation to campaign executor",
            )
        assert verdict.ready is True
        assert len(verdict.advisory_issues) > 0

    @pytest.mark.asyncio
    async def test_not_ready_real_failure(self) -> None:
        llm_response = json.dumps(
            {
                "ready": False,
                "blocking_issues": ["Test assertion failure in budget validation"],
                "advisory_issues": [],
                "reasoning": "The budget cap test fails with AssertionError, indicating the implementation has a bug.",
            }
        )
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(return_value=llm_response)

        with patch("aragora.agents.base.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.evaluate_merge_readiness(
                acceptance_criteria=["Budget caps enforced"],
                verification_results=[
                    {
                        "command": "pytest tests/swarm -q",
                        "passed": False,
                        "exit_code": 1,
                        "stderr": "AssertionError: expected 75.0 got None",
                    },
                ],
                changed_paths=["aragora/swarm/campaign.py"],
                diff_summary="Added budget cap field",
            )
        assert verdict.ready is False
        assert len(verdict.blocking_issues) > 0

    @pytest.mark.asyncio
    async def test_fail_closed_on_error(self) -> None:
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(side_effect=RuntimeError("timeout"))

        with patch("aragora.agents.base.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.evaluate_merge_readiness(
                acceptance_criteria=["Tests pass"],
                verification_results=[{"command": "pytest", "passed": False, "exit_code": 1}],
                changed_paths=["src/foo.py"],
                diff_summary="changes",
            )
        # Fail closed: not ready
        assert verdict.ready is False

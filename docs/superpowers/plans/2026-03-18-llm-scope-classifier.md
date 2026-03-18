# LLM-Powered Scope Validation & Blocker Classification Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all regex/keyword-based classification in the Ralph pipeline with frontier LLM calls, keeping existing keyword logic as degraded-mode fallback.

**Architecture:** New `aragora/ralph/llm_classifier.py` module with `LLMBlockerClassifier` class containing three async methods: `classify_blocker()`, `adjudicate_scope()`, and `evaluate_merge_readiness()`. Each uses `create_agent()` from `aragora.agents.base` to call Claude/OpenRouter, returning structured dataclass verdicts. Existing keyword classifier preserved as fallback when LLM is unavailable.

**Tech Stack:** Python 3.11+, `aragora.agents.base.create_agent()`, `asyncio`, `json`, `dataclasses`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `aragora/ralph/llm_classifier.py` | **New** — `LLMBlockerClassifier` with three LLM-powered methods + verdict dataclasses |
| `aragora/ralph/classifier.py` | Modified — async entry point delegates to LLM, keyword logic renamed as `_keyword_classify_campaign_blocked()` fallback |
| `aragora/swarm/supervisor.py` | Modified — wire scope adjudicator into `_apply_worker_result()`, merge gate evaluator after gate failure |
| `tests/ralph/test_llm_classifier.py` | **New** — unit tests for all LLM classification paths with mocked agents |
| `tests/ralph/test_classifier.py` | Modified — verify LLM-first with keyword fallback behavior |

---

## Chunk 1: LLM Blocker Classifier

### Task 1: Create verdict dataclasses and LLMBlockerClassifier skeleton

**Files:**
- Create: `aragora/ralph/llm_classifier.py`
- Test: `tests/ralph/test_llm_classifier.py`

- [ ] **Step 1: Write the failing test for ClassificationVerdict**

Create `tests/ralph/test_llm_classifier.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ralph/test_llm_classifier.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'aragora.ralph.llm_classifier'`

- [ ] **Step 3: Create llm_classifier.py with dataclasses and class skeleton**

Create `aragora/ralph/llm_classifier.py`:

```python
"""LLM-powered blocker classification for campaign supervision.

Replaces keyword/regex matching with frontier LLM calls for nuanced
classification of campaign blockers, scope violations, and merge readiness.
Falls back to keyword-based classification on LLM failure.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from aragora.ralph.classifier import BlockerKind

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ClassificationVerdict:
    """Result of LLM blocker classification."""

    kind: BlockerKind
    confidence: float
    reasoning: str


@dataclass(frozen=True, slots=True)
class ScopeVerdict:
    """Result of LLM scope adjudication."""

    justified_paths: list[str]
    rejected_paths: list[str]
    reasoning: str


@dataclass(frozen=True, slots=True)
class MergeVerdict:
    """Result of LLM merge readiness evaluation."""

    ready: bool
    blocking_issues: list[str]
    advisory_issues: list[str]
    reasoning: str


class LLMBlockerClassifier:
    """Frontier-LLM-powered blocker classification.

    Uses ``create_agent()`` from ``aragora.agents.base`` to invoke Claude
    or OpenRouter for nuanced classification that keyword matching cannot
    provide.  Each method returns a structured verdict dataclass.  On LLM
    failure, callers fall back to existing keyword-based logic.
    """

    def __init__(self, *, model: str = "anthropic", timeout: float = 30.0) -> None:
        self.model = model
        self.timeout = timeout
```

- [ ] **Step 4: Run test to verify dataclass tests pass**

Run: `pytest tests/ralph/test_llm_classifier.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add aragora/ralph/llm_classifier.py tests/ralph/test_llm_classifier.py
git commit -m "feat(ralph): add LLM classifier skeleton with verdict dataclasses"
```

---

### Task 2: Implement classify_blocker() LLM method

**Files:**
- Modify: `aragora/ralph/llm_classifier.py`
- Test: `tests/ralph/test_llm_classifier.py`

- [ ] **Step 1: Write the failing test for classify_blocker**

Append to `tests/ralph/test_llm_classifier.py`:

```python
class TestLLMClassifyBlocker:
    @pytest.mark.asyncio
    async def test_classify_scope_false_positive(self) -> None:
        llm_response = json.dumps({
            "kind": "scope_false_positive",
            "confidence": 0.92,
            "reasoning": "Worker edited test files that correspond to implementation scope.",
        })
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(return_value=llm_response)

        with patch("aragora.ralph.llm_classifier.create_agent", return_value=mock_agent):
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
                                "findings": ["scope violation: tests/swarm/test_campaign.py outside declared scope"],
                            },
                            "attempt_history": [
                                {"failure_detail": "worker edited files outside permitted scope: tests/swarm/test_campaign.py"}
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
        llm_response = json.dumps({
            "kind": "reviewer_auth_or_billing_failure",
            "confidence": 0.99,
            "reasoning": "Credit balance exhausted.",
        })
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(return_value=llm_response)

        with patch("aragora.ralph.llm_classifier.create_agent", return_value=mock_agent):
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

        with patch("aragora.ralph.llm_classifier.create_agent", return_value=mock_agent):
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

        with patch("aragora.ralph.llm_classifier.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.classify_blocker(
                manifest_dict={"projects": []},
                stop_reason="campaign_blocked",
            )
        assert verdict.kind == BlockerKind.UNKNOWN
        assert verdict.confidence == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ralph/test_llm_classifier.py::TestLLMClassifyBlocker -v`
Expected: FAIL — `classify_blocker` not implemented

- [ ] **Step 3: Implement classify_blocker()**

Add to `LLMBlockerClassifier` in `aragora/ralph/llm_classifier.py`:

```python
    async def classify_blocker(
        self,
        manifest_dict: dict[str, Any],
        stop_reason: str,
    ) -> ClassificationVerdict:
        """Classify a campaign blocker using frontier LLM reasoning.

        Builds a diagnostic prompt from the manifest state and asks the LLM
        to return a structured ``BlockerKind`` with confidence and reasoning.
        On any failure, returns ``UNKNOWN`` at zero confidence so the caller
        can fall back to keyword classification.
        """
        prompt = self._build_classify_prompt(manifest_dict, stop_reason)
        try:
            from aragora.agents.base import create_agent

            agent = create_agent(
                self.model, name="ralph-blocker-classifier", role="critic"
            )
            raw = await agent.generate(prompt)
            return self._parse_classify_response(raw)
        except Exception:
            logger.debug("LLM classify_blocker failed, returning UNKNOWN", exc_info=True)
            return ClassificationVerdict(
                kind=BlockerKind.UNKNOWN, confidence=0.0, reasoning="LLM call failed"
            )

    def _build_classify_prompt(
        self, manifest_dict: dict[str, Any], stop_reason: str
    ) -> str:
        kind_descriptions = "\n".join(
            f"- {k.value}: deterministic={k.is_deterministic}" for k in BlockerKind
        )
        projects = manifest_dict.get("projects", [])
        diagnostics: list[str] = []
        for proj in projects:
            status = proj.get("status", "unknown")
            outcome = proj.get("last_run_outcome", "unknown")
            pid = proj.get("project_id", "?")
            diagnostics.append(f"Project {pid}: status={status}, outcome={outcome}")
            review = proj.get("review", {})
            if isinstance(review, dict):
                for finding in review.get("findings", []):
                    diagnostics.append(f"  finding: {str(finding)[:300]}")
                raw = review.get("raw_review", {})
                if isinstance(raw, dict):
                    for k, v in raw.items():
                        if v:
                            diagnostics.append(f"  raw_review.{k}: {str(v)[:200]}")
            for attempt in proj.get("attempt_history", []):
                if not isinstance(attempt, dict):
                    continue
                fd = attempt.get("failure_detail")
                if fd:
                    diagnostics.append(f"  failure_detail: {str(fd)[:300]}")
                for b in attempt.get("blockers", []):
                    if str(b).strip():
                        diagnostics.append(f"  blocker: {str(b)[:200]}")
        diag_text = "\n".join(diagnostics) if diagnostics else "(no project diagnostics)"

        return f"""You are a campaign diagnostics classifier for an AI development orchestration system.

Given the campaign state below, classify the root-cause blocker into exactly ONE of these kinds:

{kind_descriptions}

Campaign stop_reason: {stop_reason}

Project diagnostics:
{diag_text}

Return ONLY a JSON object (no markdown fences):
{{"kind": "<BlockerKind value>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}

Rules:
- scope_false_positive: Worker edited files that are semantically related to the task (test files, __init__.py, config) but weren't in declared scope. The planner's scope was too narrow, not a real violation.
- reviewer_auth_or_billing_failure: Review failed due to billing, credits, auth, rate limits, or API key issues.
- infra_failure: Network errors, SSL failures, binary exec errors, permission denied.
- worker_context_overflow: Context length exceeded, prompt too long.
- reviewer_missing_diff_context: Deliverable created but reviewer couldn't verify because diff was missing or review was blocked.
- worker_clean_exit_no_effect: Worker exited but produced no useful deliverable (stall pattern).
- budget_exhaustion: Campaign ran out of budget.
- campaign_runtime_timeout_config: Timeout but some progress was made.
- receipt_emission_gap: Terminal project without receipt.
- manifest_identifier_collision: Duplicate file scope hints.
- unknown: Cannot determine root cause."""

    @staticmethod
    def _parse_classify_response(raw: str) -> ClassificationVerdict:
        text = str(raw or "").strip()
        parsed: dict[str, Any] = {}
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end > start:
                try:
                    parsed = json.loads(text[start : end + 1])
                except (json.JSONDecodeError, ValueError):
                    pass
        if not isinstance(parsed, dict) or "kind" not in parsed:
            return ClassificationVerdict(
                kind=BlockerKind.UNKNOWN,
                confidence=0.1,
                reasoning=f"Could not parse LLM response: {text[:200]}",
            )
        kind_str = str(parsed["kind"]).strip()
        try:
            kind = BlockerKind(kind_str)
        except ValueError:
            return ClassificationVerdict(
                kind=BlockerKind.UNKNOWN,
                confidence=0.1,
                reasoning=f"Unknown blocker kind from LLM: {kind_str}",
            )
        confidence = max(0.0, min(1.0, float(parsed.get("confidence", 0.5))))
        reasoning = str(parsed.get("reasoning", ""))
        return ClassificationVerdict(kind=kind, confidence=confidence, reasoning=reasoning)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/ralph/test_llm_classifier.py -v`
Expected: 7 PASS (3 dataclass + 4 classify_blocker)

- [ ] **Step 5: Commit**

```bash
git add aragora/ralph/llm_classifier.py tests/ralph/test_llm_classifier.py
git commit -m "feat(ralph): implement LLM-powered classify_blocker with prompt and parsing"
```

---

### Task 3: Implement adjudicate_scope() LLM method

**Files:**
- Modify: `aragora/ralph/llm_classifier.py`
- Test: `tests/ralph/test_llm_classifier.py`

- [ ] **Step 1: Write the failing test for adjudicate_scope**

Append to `tests/ralph/test_llm_classifier.py`:

```python
class TestLLMAdjudicateScope:
    @pytest.mark.asyncio
    async def test_justifies_test_file_companion(self) -> None:
        llm_response = json.dumps({
            "justified_paths": ["tests/swarm/test_campaign.py"],
            "rejected_paths": [],
            "reasoning": "Test file directly tests the implementation in declared scope.",
        })
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(return_value=llm_response)

        with patch("aragora.ralph.llm_classifier.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.adjudicate_scope(
                task_description="Implement budget cap validation in campaign executor",
                declared_scope=["aragora/swarm/campaign.py"],
                changed_paths=["aragora/swarm/campaign.py", "tests/swarm/test_campaign.py"],
                violations=[{"type": "out_of_scope", "path": "tests/swarm/test_campaign.py", "allowed_scope": ["aragora/swarm/campaign.py"]}],
            )
        assert "tests/swarm/test_campaign.py" in verdict.justified_paths
        assert verdict.rejected_paths == []

    @pytest.mark.asyncio
    async def test_rejects_unrelated_file(self) -> None:
        llm_response = json.dumps({
            "justified_paths": [],
            "rejected_paths": ["aragora/billing/cost_tracker.py"],
            "reasoning": "Billing module is unrelated to swarm campaign work.",
        })
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(return_value=llm_response)

        with patch("aragora.ralph.llm_classifier.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.adjudicate_scope(
                task_description="Fix campaign reviewer diff",
                declared_scope=["aragora/swarm/campaign.py"],
                changed_paths=["aragora/swarm/campaign.py", "aragora/billing/cost_tracker.py"],
                violations=[{"type": "out_of_scope", "path": "aragora/billing/cost_tracker.py", "allowed_scope": ["aragora/swarm/campaign.py"]}],
            )
        assert verdict.rejected_paths == ["aragora/billing/cost_tracker.py"]

    @pytest.mark.asyncio
    async def test_fail_closed_on_error(self) -> None:
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(side_effect=RuntimeError("timeout"))

        with patch("aragora.ralph.llm_classifier.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.adjudicate_scope(
                task_description="Any task",
                declared_scope=["src/foo.py"],
                changed_paths=["src/foo.py", "src/bar.py"],
                violations=[{"type": "out_of_scope", "path": "src/bar.py", "allowed_scope": ["src/foo.py"]}],
            )
        # Fail closed: all violation paths stay rejected
        assert verdict.rejected_paths == ["src/bar.py"]
        assert verdict.justified_paths == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ralph/test_llm_classifier.py::TestLLMAdjudicateScope -v`
Expected: FAIL — `adjudicate_scope` not implemented

- [ ] **Step 3: Implement adjudicate_scope()**

Add to `LLMBlockerClassifier` in `aragora/ralph/llm_classifier.py`:

```python
    async def adjudicate_scope(
        self,
        task_description: str,
        declared_scope: list[str],
        changed_paths: list[str],
        violations: list[dict[str, Any]],
    ) -> ScopeVerdict:
        """Adjudicate whether out-of-scope file edits are semantically justified.

        Called after glob matching finds violations.  The LLM sees the task
        context and decides if each violation is a genuine scope breach or a
        planner oversight (e.g., test companion files, __init__.py updates).

        Fail-closed: on any error, all violations stand.
        """
        out_of_scope_paths = [
            str(v.get("path", "")) for v in violations if str(v.get("path", "")).strip()
        ]
        if not out_of_scope_paths:
            return ScopeVerdict(justified_paths=[], rejected_paths=[], reasoning="no violations")

        prompt = self._build_scope_prompt(
            task_description, declared_scope, changed_paths, out_of_scope_paths
        )
        try:
            from aragora.agents.base import create_agent

            agent = create_agent(
                self.model, name="ralph-scope-adjudicator", role="critic"
            )
            raw = await agent.generate(prompt)
            return self._parse_scope_response(raw, out_of_scope_paths)
        except Exception:
            logger.debug("LLM adjudicate_scope failed, fail-closed", exc_info=True)
            return ScopeVerdict(
                justified_paths=[],
                rejected_paths=list(out_of_scope_paths),
                reasoning="LLM call failed — fail-closed, all violations stand",
            )

    @staticmethod
    def _build_scope_prompt(
        task_description: str,
        declared_scope: list[str],
        changed_paths: list[str],
        out_of_scope_paths: list[str],
    ) -> str:
        return f"""You are a file-scope adjudicator for an AI development orchestration system.

A worker was given this task:
{task_description}

Declared file scope (glob patterns the worker was allowed to edit):
{json.dumps(declared_scope)}

All files the worker actually changed:
{json.dumps(changed_paths)}

Files flagged as OUT OF SCOPE by glob matching:
{json.dumps(out_of_scope_paths)}

For each out-of-scope file, decide if the edit is JUSTIFIED or REJECTED.

Justified means: the file is semantically related to the task even though it wasn't in the declared scope. Common justified cases:
- Test files that correspond to implementation files (tests/foo/test_bar.py for foo/bar.py)
- __init__.py files that need export updates
- Configuration files that the implementation depends on
- Documentation files directly related to the change

Rejected means: the file is genuinely unrelated to the declared task scope.

Return ONLY a JSON object (no markdown fences):
{{"justified_paths": ["path1", ...], "rejected_paths": ["path2", ...], "reasoning": "explanation"}}

Every path from the out-of-scope list must appear in exactly one of justified_paths or rejected_paths."""

    @staticmethod
    def _parse_scope_response(raw: str, fallback_rejected: list[str]) -> ScopeVerdict:
        text = str(raw or "").strip()
        parsed: dict[str, Any] = {}
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end > start:
                try:
                    parsed = json.loads(text[start : end + 1])
                except (json.JSONDecodeError, ValueError):
                    pass
        if not isinstance(parsed, dict):
            return ScopeVerdict(
                justified_paths=[],
                rejected_paths=list(fallback_rejected),
                reasoning=f"Could not parse LLM scope response: {text[:200]}",
            )
        justified = [str(p) for p in parsed.get("justified_paths", []) if str(p).strip()]
        rejected = [str(p) for p in parsed.get("rejected_paths", []) if str(p).strip()]
        reasoning = str(parsed.get("reasoning", ""))
        # Any path not in either list → rejected (fail-closed)
        accounted = set(justified) | set(rejected)
        for path in fallback_rejected:
            if path not in accounted:
                rejected.append(path)
        return ScopeVerdict(
            justified_paths=justified, rejected_paths=rejected, reasoning=reasoning
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/ralph/test_llm_classifier.py -v`
Expected: 10 PASS

- [ ] **Step 5: Commit**

```bash
git add aragora/ralph/llm_classifier.py tests/ralph/test_llm_classifier.py
git commit -m "feat(ralph): implement LLM scope adjudicator with fail-closed semantics"
```

---

### Task 4: Implement evaluate_merge_readiness() LLM method

**Files:**
- Modify: `aragora/ralph/llm_classifier.py`
- Test: `tests/ralph/test_llm_classifier.py`

- [ ] **Step 1: Write the failing test for evaluate_merge_readiness**

Append to `tests/ralph/test_llm_classifier.py`:

```python
class TestLLMEvaluateMergeReadiness:
    @pytest.mark.asyncio
    async def test_ready_despite_cosmetic_test_noise(self) -> None:
        llm_response = json.dumps({
            "ready": True,
            "blocking_issues": [],
            "advisory_issues": ["Test output includes deprecation warning"],
            "reasoning": "All acceptance criteria met. Test failure is a pre-existing deprecation warning, not caused by this change.",
        })
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(return_value=llm_response)

        with patch("aragora.ralph.llm_classifier.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.evaluate_merge_readiness(
                acceptance_criteria=["Budget caps enforced", "Tests pass"],
                verification_results=[
                    {"command": "pytest tests/swarm -q", "passed": False, "exit_code": 1, "stderr": "DeprecationWarning: old API"},
                ],
                changed_paths=["aragora/swarm/campaign.py"],
                diff_summary="Added budget cap validation to campaign executor",
            )
        assert verdict.ready is True
        assert len(verdict.advisory_issues) > 0

    @pytest.mark.asyncio
    async def test_not_ready_real_failure(self) -> None:
        llm_response = json.dumps({
            "ready": False,
            "blocking_issues": ["Test assertion failure in budget validation"],
            "advisory_issues": [],
            "reasoning": "The budget cap test fails with AssertionError, indicating the implementation has a bug.",
        })
        mock_agent = AsyncMock()
        mock_agent.generate = AsyncMock(return_value=llm_response)

        with patch("aragora.ralph.llm_classifier.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.evaluate_merge_readiness(
                acceptance_criteria=["Budget caps enforced"],
                verification_results=[
                    {"command": "pytest tests/swarm -q", "passed": False, "exit_code": 1, "stderr": "AssertionError: expected 75.0 got None"},
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

        with patch("aragora.ralph.llm_classifier.create_agent", return_value=mock_agent):
            classifier = LLMBlockerClassifier()
            verdict = await classifier.evaluate_merge_readiness(
                acceptance_criteria=["Tests pass"],
                verification_results=[{"command": "pytest", "passed": False, "exit_code": 1}],
                changed_paths=["src/foo.py"],
                diff_summary="changes",
            )
        # Fail closed: not ready
        assert verdict.ready is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ralph/test_llm_classifier.py::TestLLMEvaluateMergeReadiness -v`
Expected: FAIL — `evaluate_merge_readiness` not implemented

- [ ] **Step 3: Implement evaluate_merge_readiness()**

Add to `LLMBlockerClassifier` in `aragora/ralph/llm_classifier.py`:

```python
    async def evaluate_merge_readiness(
        self,
        acceptance_criteria: list[str],
        verification_results: list[dict[str, Any]],
        changed_paths: list[str],
        diff_summary: str,
    ) -> MergeVerdict:
        """Evaluate whether a deliverable is ready to merge.

        Called after the deterministic merge gate fails.  The LLM evaluates
        whether the failure is a genuine blocking issue or cosmetic noise
        (pre-existing test failures, deprecation warnings, etc.).

        Fail-closed: on any error, returns not-ready.
        """
        prompt = self._build_merge_prompt(
            acceptance_criteria, verification_results, changed_paths, diff_summary
        )
        try:
            from aragora.agents.base import create_agent

            agent = create_agent(
                self.model, name="ralph-merge-evaluator", role="critic"
            )
            raw = await agent.generate(prompt)
            return self._parse_merge_response(raw)
        except Exception:
            logger.debug("LLM evaluate_merge_readiness failed, fail-closed", exc_info=True)
            return MergeVerdict(
                ready=False,
                blocking_issues=["LLM evaluation failed — fail-closed"],
                advisory_issues=[],
                reasoning="LLM call failed",
            )

    @staticmethod
    def _build_merge_prompt(
        acceptance_criteria: list[str],
        verification_results: list[dict[str, Any]],
        changed_paths: list[str],
        diff_summary: str,
    ) -> str:
        criteria_text = "\n".join(f"- {c}" for c in acceptance_criteria) or "(none specified)"
        results_text = json.dumps(verification_results, indent=2, default=str)
        paths_text = "\n".join(f"- {p}" for p in changed_paths) or "(none)"
        return f"""You are a merge readiness evaluator for an AI development orchestration system.

A worker completed a task. The deterministic merge gate flagged issues. Evaluate whether the deliverable is actually ready to merge or has genuine blocking problems.

Acceptance criteria:
{criteria_text}

Verification results (test commands and their outcomes):
{results_text}

Changed files:
{paths_text}

Diff summary:
{diff_summary[:2000]}

Distinguish between:
- BLOCKING issues: Real test failures caused by this change, missing acceptance criteria, broken functionality
- ADVISORY issues: Pre-existing failures, deprecation warnings, cosmetic issues, unrelated test noise

Return ONLY a JSON object (no markdown fences):
{{"ready": true/false, "blocking_issues": ["..."], "advisory_issues": ["..."], "reasoning": "explanation"}}

Set ready=true ONLY if there are zero blocking issues."""

    @staticmethod
    def _parse_merge_response(raw: str) -> MergeVerdict:
        text = str(raw or "").strip()
        parsed: dict[str, Any] = {}
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end > start:
                try:
                    parsed = json.loads(text[start : end + 1])
                except (json.JSONDecodeError, ValueError):
                    pass
        if not isinstance(parsed, dict):
            return MergeVerdict(
                ready=False,
                blocking_issues=[f"Could not parse LLM merge response: {text[:200]}"],
                advisory_issues=[],
                reasoning="Parse failure",
            )
        return MergeVerdict(
            ready=bool(parsed.get("ready", False)),
            blocking_issues=[str(i) for i in parsed.get("blocking_issues", []) if str(i).strip()],
            advisory_issues=[str(i) for i in parsed.get("advisory_issues", []) if str(i).strip()],
            reasoning=str(parsed.get("reasoning", "")),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/ralph/test_llm_classifier.py -v`
Expected: 13 PASS

- [ ] **Step 5: Commit**

```bash
git add aragora/ralph/llm_classifier.py tests/ralph/test_llm_classifier.py
git commit -m "feat(ralph): implement LLM merge readiness evaluator with fail-closed semantics"
```

---

## Chunk 2: Integration Wiring

### Task 5: Wire LLM classifier into classifier.py (blocker classification)

**Files:**
- Modify: `aragora/ralph/classifier.py`
- Modify: `tests/ralph/test_classifier.py`

- [ ] **Step 1: Write the failing test for LLM-first classification**

Append to `tests/ralph/test_classifier.py`:

```python
import asyncio
from unittest.mock import AsyncMock, patch

from aragora.ralph.llm_classifier import ClassificationVerdict


class TestLLMFirstClassification:
    def test_llm_classify_used_when_available(self) -> None:
        """classify_blocker delegates to LLM when campaign_blocked."""
        verdict = ClassificationVerdict(
            kind=BlockerKind.SCOPE_FALSE_POSITIVE,
            confidence=0.95,
            reasoning="Test companion file.",
        )
        mock_classifier = AsyncMock()
        mock_classifier.classify_blocker = AsyncMock(return_value=verdict)

        with patch("aragora.ralph.classifier._get_llm_classifier", return_value=mock_classifier):
            result = classify_blocker(
                stop_reason="campaign_blocked",
                manifest_dict={
                    "projects": [
                        {
                            "project_id": "p1",
                            "status": "blocked",
                            "review": {"status": "changes_requested", "findings": ["scope issue"]},
                        }
                    ]
                },
            )
        assert result == BlockerKind.SCOPE_FALSE_POSITIVE

    def test_keyword_fallback_on_llm_failure(self) -> None:
        """Falls back to keyword classifier when LLM returns UNKNOWN at low confidence."""
        verdict = ClassificationVerdict(
            kind=BlockerKind.UNKNOWN,
            confidence=0.0,
            reasoning="LLM call failed",
        )
        mock_classifier = AsyncMock()
        mock_classifier.classify_blocker = AsyncMock(return_value=verdict)

        with patch("aragora.ralph.classifier._get_llm_classifier", return_value=mock_classifier):
            result = classify_blocker(
                stop_reason="campaign_blocked",
                manifest_dict={
                    "projects": [
                        {
                            "project_id": "p1",
                            "status": "blocked",
                            "last_run_outcome": "deliverable_created",
                            "review": {
                                "status": "blocked_nonreviewable",
                                "findings": ["Credit balance is too low"],
                            },
                        }
                    ]
                },
            )
        # Keyword fallback should catch the billing pattern
        assert result == BlockerKind.REVIEWER_AUTH_OR_BILLING
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ralph/test_classifier.py::TestLLMFirstClassification -v`
Expected: FAIL — `_get_llm_classifier` not found

- [ ] **Step 3: Modify classifier.py to use LLM-first with keyword fallback**

In `aragora/ralph/classifier.py`, rename `_classify_campaign_blocked` to `_keyword_classify_campaign_blocked` and add LLM orchestration:

```python
# Add at top of file after existing imports:
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aragora.ralph.llm_classifier import LLMBlockerClassifier

_LLM_CONFIDENCE_THRESHOLD = 0.3


def _get_llm_classifier() -> "LLMBlockerClassifier | None":
    """Lazy-load the LLM classifier. Returns None if unavailable."""
    try:
        from aragora.ralph.llm_classifier import LLMBlockerClassifier
        return LLMBlockerClassifier()
    except Exception:
        logger.debug("LLM classifier unavailable, using keyword fallback", exc_info=True)
        return None


# Replace the existing _classify_campaign_blocked call in classify_blocker:
def classify_blocker(
    *,
    stop_reason: str,
    manifest_dict: dict[str, Any],
) -> BlockerKind | None:
    """Classify a campaign blocker from its stop reason and manifest state."""
    if stop_reason in ("still_running", "campaign_complete"):
        return None
    if stop_reason == "budget_exhausted":
        return BlockerKind.BUDGET_EXHAUSTION
    if stop_reason == "time_limit_exceeded":
        return _classify_time_limit(manifest_dict)
    if stop_reason in ("campaign_blocked", "campaign_stalled"):
        return _classify_with_llm_fallback(manifest_dict, stop_reason)
    return BlockerKind.UNKNOWN


def _classify_with_llm_fallback(
    manifest_dict: dict[str, Any], stop_reason: str
) -> BlockerKind:
    """Try LLM classification first, fall back to keyword matching."""
    llm = _get_llm_classifier()
    if llm is not None:
        try:
            verdict = asyncio.run(
                llm.classify_blocker(manifest_dict=manifest_dict, stop_reason=stop_reason)
            )
            logger.info(
                "LLM blocker classification: kind=%s confidence=%.2f reasoning=%s",
                verdict.kind.value,
                verdict.confidence,
                verdict.reasoning,
            )
            if verdict.confidence >= _LLM_CONFIDENCE_THRESHOLD:
                return verdict.kind
            logger.info(
                "LLM confidence %.2f below threshold %.2f, falling back to keyword",
                verdict.confidence,
                _LLM_CONFIDENCE_THRESHOLD,
            )
        except Exception:
            logger.debug("LLM classification failed, using keyword fallback", exc_info=True)
    return _keyword_classify_campaign_blocked(manifest_dict)
```

Then rename `_classify_campaign_blocked` → `_keyword_classify_campaign_blocked` (no other changes to that function).

- [ ] **Step 4: Run all classifier tests to verify they pass**

Run: `pytest tests/ralph/test_classifier.py -v`
Expected: ALL PASS (existing tests still pass via keyword fallback, new tests pass via LLM mock)

- [ ] **Step 5: Commit**

```bash
git add aragora/ralph/classifier.py tests/ralph/test_classifier.py
git commit -m "feat(ralph): wire LLM-first blocker classification with keyword fallback"
```

---

### Task 6: Wire LLM scope adjudicator into supervisor.py

**Files:**
- Modify: `aragora/swarm/supervisor.py`

- [ ] **Step 1: Read the current scope violation handling in _apply_worker_result**

The relevant code in `supervisor.py` around line 1169:

```python
scope_violations = self._check_file_scope_violations(item, clean_paths)
if scope_violations:
    self._mark_scope_violation(item, scope_violations)
    ...
    return
```

- [ ] **Step 2: Add LLM adjudication between scope check and marking**

Modify `_apply_worker_result()` in `supervisor.py`. After `scope_violations = self._check_file_scope_violations(item, clean_paths)` and before `if scope_violations:`, add LLM adjudication:

```python
        scope_violations = self._check_file_scope_violations(item, clean_paths)
        if scope_violations:
            # LLM adjudication: ask frontier model if violations are justified
            scope_violations = await self._llm_adjudicate_scope(item, scope_violations)

        if scope_violations:
            self._mark_scope_violation(item, scope_violations)
```

Add the new method to the `SwarmSupervisor` class:

```python
    async def _llm_adjudicate_scope(
        self,
        item: dict[str, Any],
        violations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Use LLM to filter false-positive scope violations.

        Returns the reduced list of violations (may be empty if all justified).
        On any failure, returns the original violations unchanged (fail-closed).
        """
        try:
            from aragora.ralph.llm_classifier import LLMBlockerClassifier

            classifier = LLMBlockerClassifier()
            task_desc = str(item.get("task_description", item.get("title", "")))
            declared_scope = [
                str(s).strip()
                for s in item.get("file_scope", [])
                if str(s).strip()
            ]
            changed_paths = [str(p) for p in item.get("changed_paths", [])]
            verdict = await classifier.adjudicate_scope(
                task_description=task_desc,
                declared_scope=declared_scope,
                changed_paths=changed_paths,
                violations=violations,
            )
            if verdict.justified_paths:
                logger.info(
                    "LLM scope adjudicator justified %d paths: %s (%s)",
                    len(verdict.justified_paths),
                    verdict.justified_paths,
                    verdict.reasoning,
                )
            justified_set = set(verdict.justified_paths)
            remaining = [
                v for v in violations
                if str(v.get("path", "")) not in justified_set
            ]
            return remaining
        except Exception:
            logger.debug("LLM scope adjudication failed, keeping all violations", exc_info=True)
            return violations
```

- [ ] **Step 3: Run existing swarm tests to verify no regressions**

Run: `pytest tests/swarm/test_supervisor.py -q --tb=short -x`
Expected: PASS (LLM import fails gracefully, fallback preserves original violations)

- [ ] **Step 4: Commit**

```bash
git add aragora/swarm/supervisor.py
git commit -m "feat(swarm): wire LLM scope adjudicator into worker result handling"
```

---

### Task 7: Wire LLM merge gate evaluator into supervisor.py

**Files:**
- Modify: `aragora/swarm/supervisor.py`

- [ ] **Step 1: Add LLM override after merge gate failure**

In `_apply_worker_result()`, around line 1224, after the merge gate fails:

```python
            if not bool(merge_gate.get("checks_passed")):
                # LLM second opinion: is the merge gate failure genuine?
                if await self._llm_override_merge_gate(item, merge_gate):
                    # LLM says deliverable is ready despite gate failure
                    merge_gate["checks_passed"] = True
                    merge_gate["llm_override"] = True
                    item["merge_gate"] = merge_gate
                else:
                    self._mark_needs_human(item, self._merge_gate_failure_reason(merge_gate))
                    item["review_status"] = "changes_requested"
                    ...
```

Add the new method:

```python
    async def _llm_override_merge_gate(
        self,
        item: dict[str, Any],
        merge_gate: dict[str, Any],
    ) -> bool:
        """Ask LLM if merge gate failure is cosmetic or genuine.

        Returns True if the LLM says the deliverable is ready despite the
        gate failure.  Returns False on any error (fail-closed).
        """
        try:
            from aragora.ralph.llm_classifier import LLMBlockerClassifier

            classifier = LLMBlockerClassifier()
            acceptance_criteria = [
                str(c).strip()
                for c in item.get("acceptance_criteria", [])
                if str(c).strip()
            ]
            verification_results = merge_gate.get("verification_results", [])
            changed_paths = [str(p) for p in item.get("changed_paths", [])]
            diff_summary = str(item.get("diff_summary", ""))[:2000]

            verdict = await classifier.evaluate_merge_readiness(
                acceptance_criteria=acceptance_criteria,
                verification_results=verification_results,
                changed_paths=changed_paths,
                diff_summary=diff_summary,
            )
            logger.info(
                "LLM merge evaluation: ready=%s blocking=%s advisory=%s (%s)",
                verdict.ready,
                verdict.blocking_issues,
                verdict.advisory_issues,
                verdict.reasoning,
            )
            return verdict.ready
        except Exception:
            logger.debug("LLM merge evaluation failed, fail-closed", exc_info=True)
            return False
```

- [ ] **Step 2: Run existing tests to verify no regressions**

Run: `pytest tests/swarm/test_supervisor.py -q --tb=short -x`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add aragora/swarm/supervisor.py
git commit -m "feat(swarm): wire LLM merge gate evaluator as second opinion on failures"
```

---

## Chunk 3: Final Integration & PR

### Task 8: Run full test suite and create PR

- [ ] **Step 1: Run all Ralph tests**

Run: `pytest tests/ralph/ -v --tb=short`
Expected: ALL PASS

- [ ] **Step 2: Run all swarm tests**

Run: `pytest tests/swarm/ -v --tb=short -x`
Expected: ALL PASS (1 pre-existing failure in test_session_artifact_prevention is acceptable)

- [ ] **Step 3: Syntax check all modified files**

Run: `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['aragora/ralph/llm_classifier.py', 'aragora/ralph/classifier.py', 'aragora/swarm/supervisor.py']]"`
Expected: No errors

- [ ] **Step 4: Push branch and create PR**

```bash
git push origin HEAD
gh pr create --title "feat(ralph): LLM-powered scope validation and blocker classification" --body "..."
```

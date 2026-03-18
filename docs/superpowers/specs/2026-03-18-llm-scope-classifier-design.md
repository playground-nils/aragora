# LLM-Powered Scope Validation & Blocker Classification

**Date:** 2026-03-18
**Status:** Approved
**Problem:** Ralph campaign loop stalls on `scope_false_positive` because the blocker classifier uses keyword matching and the scope validator uses strict glob matching, both producing false positives that block valid worker deliverables.

## Problem Analysis

Three regex/keyword-based systems cause cascading false positives:

1. **File scope enforcement** (`supervisor.py:_check_file_scope_violations`): Strict glob matching rejects workers that edit test files corresponding to their implementation files, because the planner didn't include test paths in `file_scope_hints`.

2. **Blocker classifier** (`classifier.py:_classify_campaign_blocked`): Uses `"scope" in detail_lower and ("violation" in detail_lower or "outside" in detail_lower)` to classify blockers. Cannot distinguish genuine scope violations from planner-generated false positives.

3. **Merge gate** (`supervisor.py:_merge_gate_state`): Keyword-based verification assessment that can't evaluate whether verification failures are blocking or cosmetic.

## Design

### 1. LLM Blocker Classifier

**Replaces:** `_classify_campaign_blocked()` in `aragora/ralph/classifier.py` (~80 lines of keyword matching).

**New module:** `aragora/ralph/llm_classifier.py`

```python
@dataclass
class ClassificationVerdict:
    kind: BlockerKind
    confidence: float  # 0.0-1.0
    reasoning: str

class LLMBlockerClassifier:
    async def classify_blocker(
        self, manifest_dict: dict, stop_reason: str
    ) -> ClassificationVerdict:
        # Build prompt with full diagnostic context:
        # - All blocked/failed project statuses
        # - Attempt histories with failure details
        # - Review findings and raw review text
        # - Budget state
        # Returns structured BlockerKind with reasoning
```

**Prompt structure:**
- System: "You are a campaign diagnostics classifier. Given campaign state, classify the blocker into exactly one of: [enum values with descriptions]."
- User: Full diagnostic context (project statuses, attempt histories, review findings, failure details)
- Output: JSON `{"kind": "<BlockerKind>", "confidence": 0.0-1.0, "reasoning": "..."}`

**Fallback:** If LLM call fails (timeout, auth, malformed response), fall back to existing keyword classifier. The keyword classifier becomes the degraded-mode backup, not the primary path.

**Integration:** `classify_blocker()` in `classifier.py` gains an `async` variant that tries LLM first, falls back to keyword. The sync entry point uses `asyncio.run()` bridge.

### 2. LLM Scope Adjudicator

**Replaces:** Hard rejection in `_check_file_scope_violations()` for borderline cases.

**Flow:**
1. Glob matching runs first (fast, deterministic)
2. If violations found, invoke LLM adjudicator before marking scope_violation
3. LLM sees: task description, declared scope patterns, out-of-scope paths, brief diff summary
4. LLM returns: `{justified: bool, reasoning: str}` per path
5. Justified paths are removed from violations list
6. Remaining violations (if any) proceed to `_mark_scope_violation()`

```python
@dataclass
class ScopeVerdict:
    justified_paths: list[str]   # Paths the LLM considers valid
    rejected_paths: list[str]    # Paths that are genuinely out of scope
    reasoning: str

class LLMBlockerClassifier:
    async def adjudicate_scope(
        self, task_description: str, declared_scope: list[str],
        changed_paths: list[str], violations: list[dict]
    ) -> ScopeVerdict:
        # Prompt: "A worker was tasked with [description] and declared
        # scope [patterns]. It also edited [paths]. For each out-of-scope
        # path, decide if the edit is semantically justified (e.g., test
        # file for implementation, __init__.py update, config change)."
```

**Fail-closed:** LLM errors → all violations stand (current behavior preserved).

### 3. LLM Merge Gate Evaluator

**Replaces:** Keyword-based `_merge_gate_state()` assessment.

```python
@dataclass
class MergeVerdict:
    ready: bool
    blocking_issues: list[str]
    advisory_issues: list[str]  # Non-blocking observations
    reasoning: str

class LLMBlockerClassifier:
    async def evaluate_merge_readiness(
        self, acceptance_criteria: list[str],
        verification_results: list[dict],
        changed_paths: list[str],
        diff_summary: str,
    ) -> MergeVerdict:
        # Prompt: "Given acceptance criteria [list] and verification
        # results [list], is this deliverable ready to merge? Distinguish
        # blocking issues from advisory observations."
```

**Integration:** Called from `_apply_worker_result()` after existing merge gate checks fail. If LLM says "ready despite test noise", the merge gate passes. If LLM confirms blocking, `_mark_needs_human()` proceeds.

## Agent Selection

Uses existing `aragora.agents` infrastructure:
- Primary: `create_agent("claude")` via Anthropic API (same as CampaignReviewer)
- Fallback: OpenRouter (same fallback chain as existing review)
- Model: Haiku for scope adjudication (fast, cheap), Sonnet for blocker classification (needs more reasoning)

## Cost & Latency

- **Blocker classification:** ~1 call per campaign stall. Campaign stalls are rare (once per ~5-10 steps). Cost: ~$0.01/call with Haiku.
- **Scope adjudication:** ~1 call per scope violation. Only when glob matching fails. Cost: ~$0.005/call.
- **Merge gate evaluation:** ~1 call per merge gate failure. Cost: ~$0.01/call.
- **Total added cost per campaign:** ~$0.05-0.10 (negligible vs. $8/step worker cost)

## Testing Strategy

- Unit tests with mocked LLM responses for each verdict type
- Integration test: real campaign manifest with known false-positive scenario → verify LLM correctly overrides
- Regression: existing keyword classifier becomes fallback; all current tests must still pass
- Prompt regression: golden-file tests with known inputs → expected BlockerKind outputs

## Files Modified

| File | Change |
|------|--------|
| `aragora/ralph/llm_classifier.py` | **New** — LLMBlockerClassifier with all three methods |
| `aragora/ralph/classifier.py` | Add async classify path, delegate to LLM with keyword fallback |
| `aragora/swarm/supervisor.py` | Wire scope adjudicator into `_apply_worker_result()`, merge gate evaluator into gate failures |
| `tests/ralph/test_llm_classifier.py` | **New** — unit tests for all LLM classification paths |
| `tests/ralph/test_classifier.py` | Update to verify LLM-first with keyword fallback |

## Rollout

1. LLM classifier behind `use_llm_classifier: bool` config flag (default: True)
2. Keyword classifier preserved as fallback
3. Logging: all LLM verdicts logged at INFO with reasoning for observability
4. Metrics: track LLM vs keyword agreement rate to validate quality

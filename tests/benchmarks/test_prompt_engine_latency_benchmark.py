"""Benchmark-style latency baselines for the prompt-engine pipeline."""

from __future__ import annotations

import asyncio
import json
import statistics
from collections import Counter

import pytest

from aragora.prompt_engine.conductor import ConductorConfig, PromptConductor
from aragora.prompt_engine.types import AutonomyLevel

pytestmark = pytest.mark.benchmark

_DECOMPOSE_RESPONSE = json.dumps(
    {
        "intent_type": "improvement",
        "summary": "Improve the onboarding flow",
        "domains": ["frontend"],
        "ambiguities": [
            {
                "description": "Which onboarding flow?",
                "impact": "Changes implementation scope",
                "options": ["web", "mobile"],
                "recommended": "web",
            }
        ],
        "assumptions": [],
        "scope_estimate": "medium",
    }
)

_INTERROGATE_RESPONSE = json.dumps(
    {
        "questions": [
            {
                "question": "Should this focus on the web flow?",
                "why_it_matters": "Determines the initial rollout target",
                "options": [
                    {"label": "Yes", "description": "Optimize the web onboarding flow first"},
                    {"label": "No", "description": "Cover multiple onboarding entry points"},
                ],
                "default": "Yes",
            }
        ]
    }
)

_RESEARCH_RESPONSE = json.dumps(
    {
        "summary": "Research complete",
        "current_state": "Current onboarding is a three-step web flow.",
        "related_decisions": [],
        "recommendations": ["Reduce the number of decisions in the first session"],
    }
)

_SPEC_RESPONSE = json.dumps(
    {
        "title": "Onboarding Latency Baseline",
        "problem_statement": "Users drop before completing the onboarding flow.",
        "proposed_solution": "Reduce the flow to two steps with clearer defaults.",
        "alternatives_considered": [],
        "file_changes": [],
        "dependencies": [],
        "risks": [],
        "success_criteria": [],
        "estimated_effort": "medium",
        "confidence": 0.9,
    }
)


class _TimedPromptAgent:
    """Deterministic agent that simulates stage-specific latency."""

    def __init__(self, delays: dict[str, float]) -> None:
        self._delays = delays

    async def generate(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "technical researcher" in prompt_lower:
            stage = "research"
            response = _RESEARCH_RESPONSE
        elif "software architect" in prompt_lower or "specification" in prompt_lower:
            stage = "specify"
            response = _SPEC_RESPONSE
        elif "clarifying" in prompt_lower:
            stage = "interrogate"
            response = _INTERROGATE_RESPONSE
        else:
            stage = "decompose"
            response = _DECOMPOSE_RESPONSE

        await asyncio.sleep(self._delays[stage])
        return response


def _percentile(values: list[float], percentile: float) -> float:
    """Return the requested percentile for a non-empty value list."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * (percentile / 100.0)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


async def _collect_latency_baseline(
    *,
    samples: int = 6,
    skip_research: bool = False,
) -> dict[str, object]:
    delays = {
        "decompose": 0.004,
        "interrogate": 0.008,
        "research": 0.018,
        "specify": 0.025,
    }
    timings = []

    for _ in range(samples):
        agent = _TimedPromptAgent(delays)
        config = ConductorConfig(
            autonomy=AutonomyLevel.FULL_AUTO,
            skip_research=skip_research,
        )
        conductor = PromptConductor(config=config, agent=agent)
        result = await conductor.run("Improve onboarding conversion")
        timings.append(result.timing)

    total_durations = [timing.total_duration_ms for timing in timings]
    stage_names = sorted({stage for timing in timings for stage in timing.stage_durations_ms})
    stage_mean_ms = {
        stage: statistics.mean(timing.stage_durations_ms[stage] for timing in timings)
        for stage in stage_names
    }
    slowest_stage_counts = Counter(timing.slowest_stage_name for timing in timings)
    slowest_operation_counts = Counter(
        timing.top_operations(limit=1)[0].operation
        for timing in timings
        if timing.top_operations(1)
    )

    return {
        "samples": samples,
        "total_ms": {
            "mean": statistics.mean(total_durations),
            "p95": _percentile(total_durations, 95),
        },
        "stage_mean_ms": stage_mean_ms,
        "dominant_stage": slowest_stage_counts.most_common(1)[0][0]
        if slowest_stage_counts
        else None,
        "dominant_operation": slowest_operation_counts.most_common(1)[0][0]
        if slowest_operation_counts
        else None,
    }


class TestPromptEngineLatencyBenchmark:
    @pytest.mark.asyncio
    async def test_full_pipeline_benchmark_establishes_baseline(self) -> None:
        metrics = await _collect_latency_baseline(samples=6)

        assert metrics["samples"] == 6
        assert metrics["total_ms"]["p95"] < 150.0
        assert metrics["dominant_stage"] == "specify"
        assert metrics["dominant_operation"] == "specify.agent_generate"
        assert metrics["stage_mean_ms"]["specify"] > metrics["stage_mean_ms"]["research"]

    @pytest.mark.asyncio
    async def test_skip_research_benchmark_reduces_total_latency(self) -> None:
        full_metrics = await _collect_latency_baseline(samples=4, skip_research=False)
        reduced_metrics = await _collect_latency_baseline(samples=4, skip_research=True)

        assert "research" in full_metrics["stage_mean_ms"]
        assert "research" not in reduced_metrics["stage_mean_ms"]
        assert reduced_metrics["total_ms"]["mean"] < full_metrics["total_ms"]["mean"]

"""Tests for EssayRefinementPipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aragora.essay.pipeline import EssayRefinementPipeline
from aragora.essay.rubric import EssayScore


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def test_pipeline_config_defaults() -> None:
    """Verify sensible defaults on a bare pipeline instance."""
    pipe = EssayRefinementPipeline()
    assert pipe.target_words == 1200
    assert pipe.max_rounds == 3
    assert pipe.quality_threshold == 0.8
    assert pipe.models == ["anthropic-api", "openai-api", "gemini"]
    assert pipe.voice_notes == ""
    assert pipe.rubric_path is None


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_dry_run_returns_thesis_and_outline() -> None:
    """dry_run=True should return extraction result without drafting."""
    pipe = EssayRefinementPipeline()

    extraction = {
        "thesis": "AI will reshape education.",
        "outline": "1. Intro\n2. Body\n3. Conclusion",
        "raw_extraction": "full text...",
    }

    with patch.object(pipe, "_extract_ideas", new_callable=AsyncMock, return_value=extraction):
        result = await pipe.run("some raw notes", dry_run=True)

    assert result["thesis"] == "AI will reshape education."
    assert result["outline"] == "1. Intro\n2. Body\n3. Conclusion"
    # dry_run must NOT produce a final essay
    assert "final_essay" not in result


# ---------------------------------------------------------------------------
# Full run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_full_run_produces_essay_and_score() -> None:
    """Full run should yield final_essay, final_score, and metadata."""
    pipe = EssayRefinementPipeline()

    extraction = {
        "thesis": "Remote work boosts productivity.",
        "outline": "1. Stats\n2. Culture\n3. Conclusion",
        "raw_extraction": "...",
    }

    draft_dicts = [
        {"text": "Draft A text", "model": "anthropic-api", "model_index": 0},
        {"text": "Draft B text", "model": "openai-api", "model_index": 1},
        {"text": "Draft C text", "model": "gemini", "model_index": 2},
    ]

    score_good = EssayScore(
        thesis_clarity=0.9,
        argument_coherence=0.85,
        evidence_grounding=0.8,
        rhetorical_force=0.8,
        concision=0.9,
        factual_accuracy=0.85,
        originality=0.8,
    )
    scores = [score_good, score_good, score_good]
    critiques: list[dict[str, str]] = [
        {"evaluator": "anthropic-api", "text": "Critique A"},
        {"evaluator": "openai-api", "text": "Critique B"},
        {"evaluator": "gemini", "text": "Critique C"},
    ]
    raw_scores: list[dict] = [
        {"draft_index": 0, "evaluator": "anthropic-api", "score": score_good},
        {"draft_index": 1, "evaluator": "openai-api", "score": score_good},
        {"draft_index": 2, "evaluator": "gemini", "score": score_good},
    ]

    final_score = EssayScore(
        thesis_clarity=0.95,
        argument_coherence=0.9,
        evidence_grounding=0.85,
        rhetorical_force=0.85,
        concision=0.9,
        factual_accuracy=0.9,
        originality=0.85,
    )

    with (
        patch.object(pipe, "_extract_ideas", new_callable=AsyncMock, return_value=extraction),
        patch.object(pipe, "_parallel_draft", new_callable=AsyncMock, return_value=draft_dicts),
        patch.object(
            pipe,
            "_evaluate_drafts",
            new_callable=AsyncMock,
            return_value=(scores, critiques, raw_scores),
        ),
        patch.object(
            pipe, "_synthesize", new_callable=AsyncMock, return_value="Synthesized essay text"
        ),
        patch.object(pipe, "_polish", new_callable=AsyncMock, return_value="Polished essay text"),
        patch.object(pipe, "_final_score", new_callable=AsyncMock, return_value=final_score),
    ):
        result = await pipe.run("raw ideas")

    assert result["final_essay"] == "Polished essay text"
    assert result["final_score"] is final_score
    assert result["thesis"] == "Remote work boosts productivity."
    assert result["outline"] == "1. Stats\n2. Culture\n3. Conclusion"
    assert result["rounds_used"] >= 1
    assert isinstance(result["critique_history"], list)
    # New fields
    assert "drafts" in result
    assert "all_scores" in result
    assert "all_critiques" in result
    assert "round_details" in result
    assert len(result["drafts"]) == 3
    assert result["drafts"][0]["model"] == "anthropic-api"


# ---------------------------------------------------------------------------
# End-to-end integration with mocked agents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_end_to_end_with_mocked_agents():
    with patch("aragora.essay.pipeline.create_agent") as mock_create:
        mock_agent = AsyncMock()

        # Build a JSON score response helper
        def _score_json(tc=0.7, ac=0.7, eg=0.7, rf=0.7, co=0.7, fa=0.7, og=0.5, **extra):
            import json

            d = {
                "thesis_clarity": tc,
                "argument_coherence": ac,
                "evidence_grounding": eg,
                "rhetorical_force": rf,
                "concision": co,
                "factual_accuracy": fa,
                "originality": og,
            }
            d.update(extra)
            return json.dumps(d)

        responses = [
            # Extraction
            "**Thesis:** AI needs testing\n**Outline:**\n1. Problem\n2. Solution",
            # Draft 1, 2, 3
            "Draft about AI testing. " * 80,
            "Alternative AI draft. " * 80,
            "Third perspective. " * 80,
            # Evaluation: 3 models x 3 drafts = 9 scores
            _score_json(
                0.8, 0.7, 0.6, 0.7, 0.8, 0.9, 0.5, severity_notes=["weak"], suggestions=["add data"]
            ),
            _score_json(0.7, 0.8, 0.7, 0.6, 0.7, 0.8, 0.6),
            _score_json(0.6, 0.6, 0.8, 0.5, 0.6, 0.7, 0.7),
            _score_json(0.75, 0.72, 0.65, 0.68, 0.75, 0.85, 0.55),
            _score_json(0.72, 0.78, 0.72, 0.62, 0.72, 0.82, 0.62),
            _score_json(0.62, 0.62, 0.78, 0.52, 0.62, 0.72, 0.68),
            _score_json(0.78, 0.74, 0.64, 0.72, 0.78, 0.88, 0.52),
            _score_json(0.74, 0.76, 0.74, 0.64, 0.74, 0.84, 0.64),
            _score_json(0.64, 0.64, 0.76, 0.54, 0.64, 0.74, 0.66),
            # Synthesis
            "Synthesized essay. " * 80,
            # Polish
            "Polished final. " * 80,
            # Final score
            _score_json(0.85, 0.82, 0.78, 0.80, 0.85, 0.90, 0.70),
        ]

        mock_agent.generate.side_effect = responses
        mock_create.return_value = mock_agent

        pipeline = EssayRefinementPipeline(
            models=["anthropic-api", "openai-api", "gemini"],
            target_words=1000,
            max_rounds=1,
        )
        result = await pipeline.run("Raw ideas about AI testing")

        assert "final_essay" in result
        assert "final_score" in result
        assert result["final_score"].overall > 0
        assert result["thesis"]
        assert result["rounds_used"] >= 1
        # New fields
        assert "drafts" in result
        assert "all_scores" in result
        assert "all_critiques" in result
        assert "round_details" in result


# ---------------------------------------------------------------------------
# Draft and score preservation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_preserves_all_drafts_and_scores() -> None:
    """Pipeline result should include all drafts with model attribution and scores."""
    pipe = EssayRefinementPipeline(models=["model-a", "model-b"])

    extraction = {
        "thesis": "Testing matters.",
        "outline": "1. Why\n2. How",
        "raw_extraction": "...",
    }

    draft_dicts = [
        {"text": "Draft from model-a", "model": "model-a", "model_index": 0},
        {"text": "Draft from model-b", "model": "model-b", "model_index": 1},
    ]

    score_a = EssayScore(thesis_clarity=0.9, argument_coherence=0.8)
    score_b = EssayScore(thesis_clarity=0.7, argument_coherence=0.75)
    scores = [score_a, score_b]
    critiques: list[dict[str, str]] = [
        {"evaluator": "model-a", "text": "Needs more evidence"},
    ]
    raw_scores: list[dict] = [
        {"draft_index": 0, "evaluator": "model-a", "score": score_a},
        {"draft_index": 1, "evaluator": "model-b", "score": score_b},
    ]

    final_score = EssayScore(thesis_clarity=0.95, argument_coherence=0.9)

    with (
        patch.object(pipe, "_extract_ideas", new_callable=AsyncMock, return_value=extraction),
        patch.object(pipe, "_parallel_draft", new_callable=AsyncMock, return_value=draft_dicts),
        patch.object(
            pipe,
            "_evaluate_drafts",
            new_callable=AsyncMock,
            return_value=(scores, critiques, raw_scores),
        ),
        patch.object(pipe, "_synthesize", new_callable=AsyncMock, return_value="Merged essay"),
        patch.object(pipe, "_polish", new_callable=AsyncMock, return_value="Polished essay"),
        patch.object(pipe, "_final_score", new_callable=AsyncMock, return_value=final_score),
    ):
        result = await pipe.run("ideas", max_rounds=1)

    # Drafts preserve model attribution
    assert len(result["drafts"]) == 2
    assert result["drafts"][0]["model"] == "model-a"
    assert result["drafts"][1]["model"] == "model-b"
    assert result["drafts"][0]["text"] == "Draft from model-a"

    # Per-draft scores are attached
    assert len(result["drafts"][0]["scores"]) == 1
    assert result["drafts"][0]["scores"][0].thesis_clarity == 0.9

    # All raw scores preserved
    assert len(result["all_scores"]) == 2
    assert result["all_scores"][0]["evaluator"] == "model-a"

    # Critiques with attribution
    assert len(result["all_critiques"]) >= 1
    assert result["all_critiques"][0]["evaluator"] == "model-a"

    # Round details
    assert len(result["round_details"]) == 1
    assert result["round_details"][0]["round"] == 1

    # Backward compat fields still present
    assert result["final_essay"] == "Polished essay"
    assert result["final_score"] is final_score
    assert result["thesis"] == "Testing matters."
    assert isinstance(result["critique_history"], list)

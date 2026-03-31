"""EssaySynthesizer — merges ranked drafts into a single best-in-class essay."""

from __future__ import annotations

from typing import Any

from aragora.essay.prompts import build_synthesis_prompt
from aragora.essay.rubric import EssayScore


class EssaySynthesizer:
    """Merge multiple essay drafts into a single synthesised essay.

    Parameters
    ----------
    agent:
        Any object with an async ``.generate(prompt: str) -> str`` method.
    """

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def synthesize(
        self,
        drafts: list[str],
        scores: list[EssayScore],
        critiques: list[str],
        *,
        target_words: int = 1200,
        voice_notes: str = "",
        model_names: list[str] | None = None,
    ) -> str:
        """Synthesise *drafts* into one best-in-class essay.

        Parameters
        ----------
        drafts:
            Raw essay draft strings (parallel to *scores*).
        scores:
            ``EssayScore`` instances corresponding to each draft.
        critiques:
            Critique strings (one per draft, or a shared pool).
        target_words:
            Desired word count for the synthesised output.
        voice_notes:
            Optional stylistic guidance forwarded to the prompt.
        model_names:
            Optional list of model names parallel to *drafts*.  When provided,
            model attribution is included in the synthesis prompt.

        Returns
        -------
        str
            The synthesised essay text returned by the agent.
        """
        names = model_names or [""] * len(drafts)

        # Pair each draft with its overall score and model name then sort best-first
        paired = list(zip(drafts, scores, names))
        paired.sort(key=lambda item: item[1].overall, reverse=True)

        ranked_with_scores: list[tuple[str, float, str]] = [
            (draft, score.overall, name) for draft, score, name in paired
        ]

        prompt = build_synthesis_prompt(
            ranked_with_scores,
            critiques,
            target_word_count=target_words,
            voice_notes=voice_notes,
        )

        response: str = await self.agent.generate(prompt)
        return response

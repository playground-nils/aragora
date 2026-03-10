"""Regression tests for bounded dependency/update issue decomposition (#889).

Covers the bug where bounded dependency issues like Dependabot bumps were
decomposed into irrelevant generic subtasks (Performance Review, SOC2 Audit,
Citation Verification, Improve Developer Track) instead of producing
semantically relevant subtasks that match the actual task.

Root cause: _is_specific_goal() failed to recognize dependency bump goals
as specific, causing _expand_vague_goal() to generate generic track/template
subtasks. The LLM-based extraction path now handles decomposition with
a structured prompt and OpenRouter fallback.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aragora.nomic.task_decomposer import DecomposerConfig, SubTask, TaskDecomposer


# -- Forensic issue #873 task text (exact shape from live Boss-loop run) -------
ISSUE_873_TASK = (
    "[Issue #873] Bump @eslint/eslintrc from 3.2.0 to 3.3.0 in /aragora/live\n\n"
    "Bumps @eslint/eslintrc from 3.2.0 to 3.3.0.\n"
    "--- updated-dependencies:\n"
    "- dependency-name: @eslint/eslintrc\n"
    "  dependency-type: indirect\n"
    "  update-type: version-update:semver-minor\n"
    "...\n"
    "Signed-off-by: dependabot[bot] <support@github.com>"
)

ISSUE_873_HINTS = ["aragora/live", "@eslint/eslintrc", "/aragora/live"]


class TestIsSpecificGoal:
    """Verify _is_specific_goal recognizes bounded dependency issues."""

    def test_dependency_bump_with_path_is_specific(self) -> None:
        decomposer = TaskDecomposer()
        assert decomposer._is_specific_goal(ISSUE_873_TASK) is True

    def test_bump_verb_with_technical_term_is_specific(self) -> None:
        decomposer = TaskDecomposer()
        assert decomposer._is_specific_goal("bump eslintrc dependency") is True

    def test_upgrade_verb_with_technical_term_is_specific(self) -> None:
        decomposer = TaskDecomposer()
        assert decomposer._is_specific_goal("upgrade webpack to v5") is True

    def test_pin_verb_with_technical_term_is_specific(self) -> None:
        decomposer = TaskDecomposer()
        assert decomposer._is_specific_goal("pin react version to 18.3.0") is True

    def test_vague_goal_still_not_specific(self) -> None:
        decomposer = TaskDecomposer()
        assert decomposer._is_specific_goal("improve the platform") is False

    def test_path_reference_makes_any_goal_specific(self) -> None:
        decomposer = TaskDecomposer()
        assert decomposer._is_specific_goal("do something in aragora/live") is True


class TestBoundedIssueNoVagueExpansion:
    """Verify bounded issues skip vague-goal expansion entirely."""

    def test_issue_873_not_expanded_into_generic_tracks(self) -> None:
        """The exact #873 task text must NOT produce generic track subtasks."""
        decomposer = TaskDecomposer()
        result = decomposer.analyze(ISSUE_873_TASK)

        # Should either not decompose, or produce relevant subtasks
        for subtask in result.subtasks:
            title_lower = subtask.title.lower()
            assert "performance review" not in title_lower, (
                "Generic 'Performance Review' subtask produced for dependency bump"
            )
            assert "soc2 audit" not in title_lower, (
                "Generic 'SOC2 Audit' subtask produced for dependency bump"
            )
            assert "citation verification" not in title_lower, (
                "Generic 'Citation Verification' subtask produced for dependency bump"
            )
            assert "improve developer track" not in title_lower, (
                "Generic 'Improve Developer Track' subtask produced for dependency bump"
            )

    def test_vague_goal_still_expands(self) -> None:
        """Genuinely vague goals should still get template-based expansion."""
        decomposer = TaskDecomposer()
        result = decomposer.analyze("maximize utility for SME businesses")

        # Vague goal should produce subtasks from track/template expansion
        assert result.should_decompose or len(result.subtasks) > 0


class TestScopeOverlapsHints:
    """Unit tests for the _scope_overlaps_hints static method."""

    def test_exact_match(self) -> None:
        assert TaskDecomposer._scope_overlaps_hints(["aragora/live"], ["aragora/live"]) is True

    def test_scope_under_hint(self) -> None:
        assert (
            TaskDecomposer._scope_overlaps_hints(["aragora/live/package.json"], ["aragora/live"])
            is True
        )

    def test_hint_under_scope(self) -> None:
        assert TaskDecomposer._scope_overlaps_hints(["aragora"], ["aragora/live"]) is True

    def test_no_overlap(self) -> None:
        assert (
            TaskDecomposer._scope_overlaps_hints(
                ["aragora/audit/", "aragora/compliance/"], ["aragora/live"]
            )
            is False
        )

    def test_empty_scope(self) -> None:
        assert TaskDecomposer._scope_overlaps_hints([], ["aragora/live"]) is False

    def test_empty_hints(self) -> None:
        assert TaskDecomposer._scope_overlaps_hints(["aragora/live"], []) is False

    def test_leading_dot_slash_stripped(self) -> None:
        assert TaskDecomposer._scope_overlaps_hints(["./aragora/live"], ["aragora/live"]) is True

    def test_trailing_slash_stripped(self) -> None:
        assert TaskDecomposer._scope_overlaps_hints(["aragora/live/"], ["aragora/live"]) is True


class TestConstrainScopesToHints:
    """Unit tests for the _constrain_scopes_to_hints method."""

    def test_empty_scope_backfilled(self) -> None:
        decomposer = TaskDecomposer()
        subtasks = [SubTask(id="s1", title="t", description="d", file_scope=[])]
        result = decomposer._constrain_scopes_to_hints(subtasks, ["aragora/live"])
        assert result[0].file_scope == ["aragora/live"]

    def test_overlapping_scope_preserved(self) -> None:
        decomposer = TaskDecomposer()
        subtasks = [
            SubTask(id="s1", title="t", description="d", file_scope=["aragora/live/foo.py"])
        ]
        result = decomposer._constrain_scopes_to_hints(subtasks, ["aragora/live"])
        assert result[0].file_scope == ["aragora/live/foo.py"]

    def test_non_overlapping_scope_overridden(self) -> None:
        decomposer = TaskDecomposer()
        subtasks = [
            SubTask(
                id="s1",
                title="t",
                description="d",
                file_scope=["aragora/audit/", "aragora/compliance/"],
            )
        ]
        result = decomposer._constrain_scopes_to_hints(subtasks, ["aragora/live"])
        assert result[0].file_scope == ["aragora/live"]

    def test_mixed_subtasks(self) -> None:
        decomposer = TaskDecomposer()
        subtasks = [
            SubTask(id="s1", title="ok", description="d", file_scope=["aragora/live/a.py"]),
            SubTask(id="s2", title="wrong", description="d", file_scope=["aragora/audit/"]),
            SubTask(id="s3", title="empty", description="d", file_scope=[]),
        ]
        result = decomposer._constrain_scopes_to_hints(subtasks, ["aragora/live"])
        assert result[0].file_scope == ["aragora/live/a.py"]
        assert result[1].file_scope == ["aragora/live"]
        assert result[2].file_scope == ["aragora/live"]

    def test_no_hints_passthrough(self) -> None:
        """Without hints, scopes pass through unchanged."""
        decomposer = TaskDecomposer()
        subtasks = [SubTask(id="s1", title="t", description="d", file_scope=["aragora/audit/"])]
        # _constrain_scopes_to_hints is only called when hints exist,
        # but if called with empty list, nothing should change
        result = decomposer._constrain_scopes_to_hints(subtasks, [])
        assert result[0].file_scope == ["aragora/audit/"]


class TestAnalyzeWithFileScopeHints:
    """Integration tests for analyze() with file_scope_hints parameter."""

    def test_hints_constrain_vague_expansion(self) -> None:
        """file_scope_hints override non-overlapping scopes from vague expansion."""
        decomposer = TaskDecomposer()
        result = decomposer.analyze(
            "improve the security and compliance",
            file_scope_hints=["aragora/live"],
        )
        for subtask in result.subtasks:
            if subtask.file_scope:
                # Every scope should overlap with the hint
                assert TaskDecomposer._scope_overlaps_hints(subtask.file_scope, ["aragora/live"]), (
                    f"Subtask {subtask.id} scope {subtask.file_scope} doesn't overlap hint"
                )

    def test_issue_873_with_hints(self) -> None:
        """Forensic: #873 task with file_scope_hints must not produce irrelevant subtasks."""
        decomposer = TaskDecomposer()
        result = decomposer.analyze(ISSUE_873_TASK, file_scope_hints=ISSUE_873_HINTS)

        for subtask in result.subtasks:
            title_lower = subtask.title.lower()
            assert "performance review" not in title_lower
            assert "soc2 audit" not in title_lower
            assert "citation verification" not in title_lower


class TestBuildDecompositionPrompt:
    """Test the structured decomposition prompt construction."""

    def test_prompt_includes_task(self) -> None:
        decomposer = TaskDecomposer()
        prompt = decomposer._build_decomposition_prompt("Fix the widget")
        assert "Fix the widget" in prompt

    def test_prompt_includes_scope_constraints(self) -> None:
        decomposer = TaskDecomposer()
        prompt = decomposer._build_decomposition_prompt(
            "Fix the widget", ["aragora/live", "tests/"]
        )
        assert "`aragora/live`" in prompt
        assert "`tests/`" in prompt
        assert "Scope Constraints" in prompt

    def test_prompt_no_scope_section_without_hints(self) -> None:
        decomposer = TaskDecomposer()
        prompt = decomposer._build_decomposition_prompt("Fix the widget")
        assert "Scope Constraints" not in prompt

    def test_prompt_includes_anti_patterns(self) -> None:
        decomposer = TaskDecomposer()
        prompt = decomposer._build_decomposition_prompt("bump eslintrc")
        assert "Performance Review" in prompt
        assert "Anti-patterns" in prompt

    def test_prompt_includes_classification_rules(self) -> None:
        decomposer = TaskDecomposer()
        prompt = decomposer._build_decomposition_prompt("bump eslintrc")
        assert "Bounded operations" in prompt
        assert "Multi-file changes" in prompt


class TestLLMProviderFallback:
    """Test the Anthropic → OpenRouter fallback chain."""

    def test_anthropic_skipped_without_key(self) -> None:
        decomposer = TaskDecomposer()
        with patch.dict("os.environ", {}, clear=True):
            result = decomposer._call_anthropic("test prompt")
        assert result is None

    def test_openrouter_skipped_without_key(self) -> None:
        decomposer = TaskDecomposer()
        with patch.dict("os.environ", {}, clear=True):
            result = decomposer._call_openrouter("test prompt")
        assert result is None

    @patch("aragora.nomic.task_decomposer.TaskDecomposer._call_anthropic")
    @patch("aragora.nomic.task_decomposer.TaskDecomposer._call_openrouter")
    def test_falls_back_to_openrouter_on_anthropic_failure(
        self, mock_openrouter: MagicMock, mock_anthropic: MagicMock
    ) -> None:
        mock_anthropic.return_value = None
        mock_openrouter.return_value = '[{"title":"Bump dep","description":"bump","file_scope":[],"estimated_complexity":"low"}]'
        decomposer = TaskDecomposer()
        result = decomposer._llm_extract_subtasks("bump eslintrc")
        assert len(result) == 1
        assert result[0].title == "Bump dep"
        mock_anthropic.assert_called_once()
        mock_openrouter.assert_called_once()

    @patch("aragora.nomic.task_decomposer.TaskDecomposer._call_anthropic")
    @patch("aragora.nomic.task_decomposer.TaskDecomposer._call_openrouter")
    def test_uses_anthropic_when_available(
        self, mock_openrouter: MagicMock, mock_anthropic: MagicMock
    ) -> None:
        mock_anthropic.return_value = '[{"title":"Bump dep","description":"bump","file_scope":[],"estimated_complexity":"low"}]'
        decomposer = TaskDecomposer()
        result = decomposer._llm_extract_subtasks("bump eslintrc")
        assert len(result) == 1
        mock_anthropic.assert_called_once()
        mock_openrouter.assert_not_called()

    @patch("aragora.nomic.task_decomposer.TaskDecomposer._call_anthropic")
    @patch("aragora.nomic.task_decomposer.TaskDecomposer._call_openrouter")
    def test_both_fail_returns_empty(
        self, mock_openrouter: MagicMock, mock_anthropic: MagicMock
    ) -> None:
        mock_anthropic.return_value = None
        mock_openrouter.return_value = None
        decomposer = TaskDecomposer()
        result = decomposer._llm_extract_subtasks("bump eslintrc")
        assert result == []


class TestExtractorOverridePrecedence:
    """Verify extract_subtasks_fn remains authoritative over LLM and heuristic.

    The caller-supplied extract_subtasks_fn is an explicit override that must
    take priority.  The LLM path is a fallback for when no extractor is
    supplied.
    """

    @patch("aragora.nomic.task_decomposer.TaskDecomposer._call_anthropic")
    def test_extract_fn_takes_priority_over_llm(self, mock_anthropic: MagicMock) -> None:
        """When extract_subtasks_fn is provided, LLM is NOT called."""
        mock_anthropic.return_value = (
            '[{"title":"LLM Step","description":"from llm",'
            '"file_scope":[],"estimated_complexity":"low"}]'
        )
        extracted = [
            {"title": "Fn Step", "description": "from fn", "complexity": "low"},
        ]
        decomposer = TaskDecomposer(
            config=DecomposerConfig(complexity_threshold=1),
            extract_subtasks_fn=lambda task: extracted,
        )
        result = decomposer.analyze("Refactor the database and security and api layers system-wide")
        if result.should_decompose:
            assert any("Fn Step" in st.title for st in result.subtasks)
            assert not any("LLM Step" in st.title for st in result.subtasks)
            mock_anthropic.assert_not_called()

    @patch("aragora.nomic.task_decomposer.TaskDecomposer._call_anthropic")
    def test_llm_used_when_no_extract_fn(self, mock_anthropic: MagicMock) -> None:
        """Without extract_subtasks_fn, LLM is the primary decomposition path."""
        mock_anthropic.return_value = (
            '[{"title":"LLM Step","description":"from llm",'
            '"file_scope":[],"estimated_complexity":"low"}]'
        )
        decomposer = TaskDecomposer(
            config=DecomposerConfig(complexity_threshold=1),
        )
        result = decomposer.analyze("Refactor the database and security and api layers system-wide")
        if result.should_decompose:
            assert any("LLM Step" in st.title for st in result.subtasks)
            mock_anthropic.assert_called_once()


class TestParseJsonArray:
    """Test JSON array extraction from LLM responses."""

    def test_clean_array(self) -> None:
        result = TaskDecomposer._parse_json_array('[{"title": "foo"}]')
        assert result == [{"title": "foo"}]

    def test_array_with_preamble(self) -> None:
        result = TaskDecomposer._parse_json_array('Here is the result:\n[{"title": "foo"}]')
        assert result == [{"title": "foo"}]

    def test_no_array(self) -> None:
        result = TaskDecomposer._parse_json_array("no json here")
        assert result == []

    def test_malformed_json(self) -> None:
        result = TaskDecomposer._parse_json_array("[{broken]")
        assert result == []

    def test_nested_arrays(self) -> None:
        result = TaskDecomposer._parse_json_array('[{"files": ["a.py", "b.py"]}]')
        assert result == [{"files": ["a.py", "b.py"]}]

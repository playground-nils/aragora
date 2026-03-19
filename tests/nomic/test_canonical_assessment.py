"""Tests for the Canonical Repo Assessment Compiler."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aragora.nomic.canonical_assessment import (
    AssessmentDelta,
    CanonicalAssessmentCompiler,
    CanonicalRepoAssessment,
    FeatureEntry,
    compute_delta,
    load_assessment,
    load_latest_assessment,
    save_assessment,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_assessment(
    assessment_id: str = "ca-test123",
    timestamp: float = 1000.0,
    health_score: float = 0.85,
    features: list[FeatureEntry] | None = None,
    candidates: list[dict] | None = None,
    recurring: list[dict] | None = None,
) -> CanonicalRepoAssessment:
    return CanonicalRepoAssessment(
        assessment_id=assessment_id,
        timestamp=timestamp,
        health_report={"health_score": health_score},
        scanner_metrics={"total_modules": 100, "tested_pct": 80.0},
        feature_inventory=features or [],
        improvement_candidates=candidates or [],
        recurring_findings=recurring or [],
        audit_results={"todo_count": 5},
        metadata={"commit_sha": "abc123", "branch": "main", "dirty": False},
    )


# ---------------------------------------------------------------------------
# Serialization round-trips
# ---------------------------------------------------------------------------


class TestFeatureEntrySerialization:
    def test_round_trip(self):
        entry = FeatureEntry(
            name="Blockchain receipts",
            status="scaffolding",
            evidence=["file:aragora/blockchain/receipt.py", "issue:#42"],
            priority="P2",
            notes="Needs mainnet deploy",
        )
        d = entry.to_dict()
        restored = FeatureEntry.from_dict(d)
        assert restored.name == entry.name
        assert restored.status == entry.status
        assert restored.evidence == entry.evidence
        assert restored.priority == entry.priority
        assert restored.notes == entry.notes

    def test_minimal_from_dict(self):
        entry = FeatureEntry.from_dict({"name": "X", "status": "gap"})
        assert entry.name == "X"
        assert entry.priority == "P3"  # default
        assert entry.evidence == []


class TestAssessmentRoundTrip:
    def test_full_round_trip(self):
        features = [
            FeatureEntry(name="Widget", status="shipped", priority="P1"),
            FeatureEntry(name="Gadget", status="scaffolding", priority="P2"),
        ]
        original = _make_assessment(
            features=features, candidates=[{"description": "Fix X", "priority": 0.8}]
        )
        d = original.to_dict()
        restored = CanonicalRepoAssessment.from_dict(d)
        assert restored.assessment_id == original.assessment_id
        assert restored.timestamp == original.timestamp
        assert restored.health_report == original.health_report
        assert len(restored.feature_inventory) == 2
        assert restored.feature_inventory[0].name == "Widget"
        assert restored.feature_inventory[1].status == "scaffolding"
        assert restored.improvement_candidates == original.improvement_candidates
        assert restored.metadata == original.metadata


# ---------------------------------------------------------------------------
# Compiler with mocked sources
# ---------------------------------------------------------------------------


class TestCompileWithMockedSources:
    def test_compile_aggregates_all_sources(self, tmp_path):
        # Set up a mock repo with a feature gap list
        (tmp_path / "aragora").mkdir()
        (tmp_path / "aragora" / "__init__.py").write_text("")
        (tmp_path / "tests").mkdir()
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "FEATURE_GAP_LIST.md").write_text(
            "## P1 — GTM\n\n| Feature | Status | Notes |\n|---|---|---|\n| Widget | **Shipped** | Done |\n"
        )

        # Mock health report
        mock_report = MagicMock()
        mock_report.to_dict.return_value = {"health_score": 0.9}
        mock_report.improvement_candidates = []

        mock_engine = MagicMock()
        mock_engine.assess = AsyncMock(return_value=mock_report)

        # Mock scanner
        mock_finding = MagicMock()
        mock_finding.file_path = "aragora/core.py"
        mock_scanner_instance = MagicMock()
        mock_scanner_instance.scan.return_value = MagicMock(
            metrics={"total_modules": 50}, findings=[mock_finding]
        )

        # Mock memory store
        mock_store_instance = MagicMock()
        mock_store_instance.get_recurring_findings.return_value = []

        with (
            patch(
                "aragora.nomic.canonical_assessment.CanonicalAssessmentCompiler._collect_git_metadata",
                return_value={"commit_sha": "deadbeef", "branch": "main", "dirty": False},
            ),
            patch.dict(os.environ, {"ARAGORA_DATA_DIR": str(tmp_path)}),
        ):
            compiler = CanonicalAssessmentCompiler(repo_path=tmp_path)

            # Patch lazy imports inside methods
            with (
                patch(
                    "aragora.nomic.assessment_engine.AutonomousAssessmentEngine",
                    return_value=mock_engine,
                ),
                patch(
                    "aragora.nomic.strategic_scanner.StrategicScanner",
                    return_value=mock_scanner_instance,
                ),
                patch(
                    "aragora.nomic.strategic_memory.StrategicMemoryStore",
                    return_value=mock_store_instance,
                ),
            ):
                assessment = asyncio.run(compiler.compile())

        assert assessment.assessment_id.startswith("ca-")
        assert assessment.timestamp > 0
        assert isinstance(assessment.feature_inventory, list)
        assert isinstance(assessment.audit_results, dict)
        assert assessment.metadata.get("commit_sha") == "deadbeef"


# ---------------------------------------------------------------------------
# Feature classification
# ---------------------------------------------------------------------------


class TestClassifyFeatures:
    def _make_compiler(self, tmp_path, gap_content=""):
        (tmp_path / "aragora").mkdir(exist_ok=True)
        (tmp_path / "docs").mkdir(exist_ok=True)
        if gap_content:
            (tmp_path / "docs" / "FEATURE_GAP_LIST.md").write_text(gap_content)
        return CanonicalAssessmentCompiler(repo_path=tmp_path)

    def test_shipped_feature(self, tmp_path):
        content = (
            "## P1 — GTM\n\n"
            "| Feature | Status | Notes |\n"
            "|---|---|---|\n"
            "| Auth system | **Shipped and verified** | All tests pass |\n"
        )
        compiler = self._make_compiler(tmp_path, content)
        features = compiler._classify_features([], {})
        assert len(features) == 1
        assert features[0].status == "shipped"
        assert features[0].priority == "P1"

    def test_scaffolding_feature(self, tmp_path):
        content = (
            "## P2 — Hardening\n\n"
            "| Feature | Status | Notes |\n"
            "|---|---|---|\n"
            "| Blockchain | Scaffolding | Code exists but untested |\n"
        )
        compiler = self._make_compiler(tmp_path, content)
        features = compiler._classify_features([], {})
        assert len(features) == 1
        assert features[0].status == "scaffolding"
        assert features[0].priority == "P2"

    def test_gap_feature(self, tmp_path):
        content = (
            "## P0 — Blockers\n\n"
            "| Feature | Status | Notes |\n"
            "|---|---|---|\n"
            "| Pen test | Not started | Vendor needed |\n"
        )
        compiler = self._make_compiler(tmp_path, content)
        features = compiler._classify_features([], {})
        assert len(features) == 1
        assert features[0].status == "gap"
        assert features[0].priority == "P0"

    def test_issue_evidence_extracted(self, tmp_path):
        content = (
            "## P1 — GTM\n\n"
            "| Feature | Status | Notes |\n"
            "|---|---|---|\n"
            "| Widget | Working | Tracked in [#817](url) |\n"
        )
        compiler = self._make_compiler(tmp_path, content)
        features = compiler._classify_features([], {})
        assert len(features) == 1
        assert "issue:#817" in features[0].evidence

    def test_no_gap_file(self, tmp_path):
        compiler = self._make_compiler(tmp_path, "")
        features = compiler._classify_features([], {})
        assert features == []


# ---------------------------------------------------------------------------
# Delta computation
# ---------------------------------------------------------------------------


class TestComputeDelta:
    def test_health_improvement(self):
        prev = _make_assessment(assessment_id="ca-prev", timestamp=1000.0, health_score=0.7)
        curr = _make_assessment(assessment_id="ca-curr", timestamp=2000.0, health_score=0.85)
        delta = compute_delta(curr, prev)
        assert delta.previous_id == "ca-prev"
        assert delta.current_id == "ca-curr"
        assert delta.time_elapsed_seconds == pytest.approx(1000.0)
        assert delta.health_score_change == pytest.approx(0.15)

    def test_new_features(self):
        prev = _make_assessment(
            assessment_id="ca-prev",
            features=[FeatureEntry(name="A", status="shipped")],
        )
        curr = _make_assessment(
            assessment_id="ca-curr",
            features=[
                FeatureEntry(name="A", status="shipped"),
                FeatureEntry(name="B", status="scaffolding"),
            ],
        )
        delta = compute_delta(curr, prev)
        assert delta.new_features == ["B"]
        assert delta.resolved_features == []

    def test_status_changes(self):
        prev = _make_assessment(
            assessment_id="ca-prev",
            features=[FeatureEntry(name="Widget", status="scaffolding")],
        )
        curr = _make_assessment(
            assessment_id="ca-curr",
            features=[FeatureEntry(name="Widget", status="shipped")],
        )
        delta = compute_delta(curr, prev)
        assert len(delta.status_changes) == 1
        assert delta.status_changes[0]["name"] == "Widget"
        assert delta.status_changes[0]["old_status"] == "scaffolding"
        assert delta.status_changes[0]["new_status"] == "shipped"

    def test_findings_diff(self):
        prev = _make_assessment(
            assessment_id="ca-prev",
            recurring=[{"description": "issue1"}, {"description": "issue2"}],
        )
        curr = _make_assessment(
            assessment_id="ca-curr",
            recurring=[{"description": "issue1"}],
        )
        delta = compute_delta(curr, prev)
        assert delta.resolved_findings == 1
        assert delta.new_findings == 0


# ---------------------------------------------------------------------------
# SQLite persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_save_and_load(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        assessment = _make_assessment(
            features=[FeatureEntry(name="X", status="shipped", priority="P1")],
        )
        aid = save_assessment(assessment, db_path=db_path)
        assert aid == "ca-test123"

        loaded = load_assessment("ca-test123", db_path=db_path)
        assert loaded is not None
        assert loaded.assessment_id == assessment.assessment_id
        assert loaded.health_report == assessment.health_report
        assert len(loaded.feature_inventory) == 1
        assert loaded.feature_inventory[0].name == "X"

    def test_load_latest(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        old = _make_assessment(assessment_id="ca-old", timestamp=100.0)
        new = _make_assessment(assessment_id="ca-new", timestamp=200.0)
        save_assessment(old, db_path=db_path)
        save_assessment(new, db_path=db_path)

        latest = load_latest_assessment(db_path=db_path)
        assert latest is not None
        assert latest.assessment_id == "ca-new"

    def test_load_nonexistent(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        loaded = load_assessment("ca-nonexistent", db_path=db_path)
        assert loaded is None

    def test_load_latest_empty(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        latest = load_latest_assessment(db_path=db_path)
        assert latest is None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCLI:
    def test_json_output(self, capsys, tmp_path):
        """Test cmd_assess with --format json produces valid JSON."""
        from argparse import Namespace

        from aragora.cli.commands.assess import cmd_assess

        mock_assessment = _make_assessment()

        with (
            patch(
                "aragora.nomic.canonical_assessment.CanonicalAssessmentCompiler.compile",
                new_callable=AsyncMock,
                return_value=mock_assessment,
            ),
            patch.dict(os.environ, {"ARAGORA_DATA_DIR": str(tmp_path)}),
        ):
            args = Namespace(format="json", save=False, diff=False)
            cmd_assess(args)

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["assessment_id"] == "ca-test123"
        assert data["health_report"]["health_score"] == 0.85

    def test_text_output(self, capsys, tmp_path):
        """Test cmd_assess with --format text prints summary."""
        from argparse import Namespace

        from aragora.cli.commands.assess import cmd_assess

        mock_assessment = _make_assessment(
            features=[FeatureEntry(name="Widget", status="shipped")],
        )

        with (
            patch(
                "aragora.nomic.canonical_assessment.CanonicalAssessmentCompiler.compile",
                new_callable=AsyncMock,
                return_value=mock_assessment,
            ),
            patch.dict(os.environ, {"ARAGORA_DATA_DIR": str(tmp_path)}),
        ):
            args = Namespace(format="text", save=False, diff=False)
            cmd_assess(args)

        captured = capsys.readouterr()
        assert "ca-test123" in captured.out
        assert "Health Score" in captured.out
        assert "shipped" in captured.out

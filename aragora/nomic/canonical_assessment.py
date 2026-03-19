"""Canonical Repo Assessment Compiler — single-artifact codebase assessment.

Aggregates signals from AutonomousAssessmentEngine, StrategicScanner,
StrategicMemoryStore, and FEATURE_GAP_LIST.md into one
CanonicalRepoAssessment artifact with delta analysis, SQLite persistence,
and pipeline bridge.

No LLM calls — pure signal aggregation.

Usage:
    compiler = CanonicalAssessmentCompiler()
    assessment = await compiler.compile()
    print(f"Health: {assessment.health_report['health_score']:.2f}")
    print(f"Features: {len(assessment.feature_inventory)}")
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class FeatureEntry:
    """A single feature from the gap list with evidence cross-references."""

    name: str
    status: str  # "shipped" | "scaffolding" | "stale" | "gap"
    evidence: list[str] = field(default_factory=list)  # ["file:path", "test:path", ...]
    priority: str = "P3"  # "P0"-"P5"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "evidence": self.evidence,
            "priority": self.priority,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeatureEntry:
        return cls(
            name=data["name"],
            status=data["status"],
            evidence=data.get("evidence", []),
            priority=data.get("priority", "P3"),
            notes=data.get("notes", ""),
        )


@dataclass
class AssessmentDelta:
    """Diff between two consecutive canonical assessments."""

    previous_id: str
    current_id: str
    time_elapsed_seconds: float
    health_score_change: float
    new_features: list[str] = field(default_factory=list)
    resolved_features: list[str] = field(default_factory=list)
    status_changes: list[dict[str, str]] = field(default_factory=list)
    new_findings: int = 0
    resolved_findings: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "previous_id": self.previous_id,
            "current_id": self.current_id,
            "time_elapsed_seconds": self.time_elapsed_seconds,
            "health_score_change": self.health_score_change,
            "new_features": self.new_features,
            "resolved_features": self.resolved_features,
            "status_changes": self.status_changes,
            "new_findings": self.new_findings,
            "resolved_findings": self.resolved_findings,
        }


@dataclass
class CanonicalRepoAssessment:
    """Complete canonical repository assessment artifact."""

    assessment_id: str
    timestamp: float
    health_report: dict[str, Any] = field(default_factory=dict)
    scanner_metrics: dict[str, Any] = field(default_factory=dict)
    feature_inventory: list[FeatureEntry] = field(default_factory=list)
    improvement_candidates: list[dict[str, Any]] = field(default_factory=list)
    recurring_findings: list[dict[str, Any]] = field(default_factory=list)
    audit_results: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "timestamp": self.timestamp,
            "health_report": self.health_report,
            "scanner_metrics": self.scanner_metrics,
            "feature_inventory": [f.to_dict() for f in self.feature_inventory],
            "improvement_candidates": self.improvement_candidates,
            "recurring_findings": self.recurring_findings,
            "audit_results": self.audit_results,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CanonicalRepoAssessment:
        return cls(
            assessment_id=data["assessment_id"],
            timestamp=data["timestamp"],
            health_report=data.get("health_report", {}),
            scanner_metrics=data.get("scanner_metrics", {}),
            feature_inventory=[
                FeatureEntry.from_dict(f) for f in data.get("feature_inventory", [])
            ],
            improvement_candidates=data.get("improvement_candidates", []),
            recurring_findings=data.get("recurring_findings", []),
            audit_results=data.get("audit_results", {}),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Compiler
# ---------------------------------------------------------------------------


class CanonicalAssessmentCompiler:
    """Compile all signal sources into one CanonicalRepoAssessment.

    Signal sources (all lazy-imported, all fail gracefully):
    1. AutonomousAssessmentEngine.assess() -> health_report
    2. StrategicScanner.scan() -> scanner_metrics
    3. StrategicMemoryStore.get_recurring_findings() -> recurring
    4. _collect_audit_signals() -> audit_results
    5. _classify_features() -> feature_inventory
    6. _collect_git_metadata() -> metadata
    """

    def __init__(self, repo_path: Path | None = None) -> None:
        self._repo_path = repo_path or Path.cwd()

    async def compile(self) -> CanonicalRepoAssessment:
        """Run all signal sources, compile into one assessment."""
        assessment_id = f"ca-{uuid.uuid4().hex[:12]}"
        ts = time.time()

        # 1. Health report from AutonomousAssessmentEngine
        health_report, improvement_candidates = self._collect_health_report()

        # 2. Scanner metrics from StrategicScanner
        scanner_metrics, scanner_findings = self._collect_scanner_metrics()

        # 3. Recurring findings from StrategicMemoryStore
        recurring_findings = self._collect_recurring_findings()

        # 4. Lightweight audit signals
        audit_results = self._collect_audit_signals()

        # 5. Feature inventory from FEATURE_GAP_LIST.md cross-referenced
        feature_inventory = self._classify_features(scanner_findings, health_report)

        # 6. Git metadata
        metadata = self._collect_git_metadata()

        return CanonicalRepoAssessment(
            assessment_id=assessment_id,
            timestamp=ts,
            health_report=health_report,
            scanner_metrics=scanner_metrics,
            feature_inventory=feature_inventory,
            improvement_candidates=improvement_candidates,
            recurring_findings=recurring_findings,
            audit_results=audit_results,
            metadata=metadata,
        )

    # --- Signal collectors ---

    def _collect_health_report(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Collect health report from AutonomousAssessmentEngine."""
        try:
            import asyncio

            from aragora.nomic.assessment_engine import AutonomousAssessmentEngine

            engine = AutonomousAssessmentEngine()
            # Use asyncio to run the async assess() method
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # We're inside an event loop already — create a task
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    report = loop.run_in_executor(pool, lambda: asyncio.run(engine.assess()))
                    # Can't await here synchronously; fall back to empty
                    report_dict = {}
                    candidates = []
                    logger.debug("Nested event loop detected, skipping health report")
                    return report_dict, candidates
            else:
                report = asyncio.run(engine.assess())

            report_dict = report.to_dict()
            candidates = [c.to_dict() for c in report.improvement_candidates]
            return report_dict, candidates
        except ImportError:
            logger.debug("AutonomousAssessmentEngine not available")
            return {}, []
        except (RuntimeError, ValueError, OSError) as e:
            logger.debug("Health report collection failed: %s", e)
            return {}, []

    def _collect_scanner_metrics(self) -> tuple[dict[str, Any], list[Any]]:
        """Collect scanner metrics from StrategicScanner."""
        try:
            from aragora.nomic.strategic_scanner import StrategicScanner

            scanner = StrategicScanner(repo_path=self._repo_path)
            assessment = scanner.scan()
            return assessment.metrics, assessment.findings
        except ImportError:
            logger.debug("StrategicScanner not available")
            return {}, []
        except (RuntimeError, ValueError, OSError) as e:
            logger.debug("Scanner metrics collection failed: %s", e)
            return {}, []

    def _collect_recurring_findings(self) -> list[dict[str, Any]]:
        """Collect recurring findings from StrategicMemoryStore."""
        try:
            from aragora.nomic.strategic_memory import StrategicMemoryStore

            store = StrategicMemoryStore()
            findings = store.get_recurring_findings(min_occurrences=2)
            return [
                {
                    "category": f.category,
                    "severity": f.severity,
                    "file_path": f.file_path,
                    "description": f.description,
                }
                for f in findings
            ]
        except ImportError:
            logger.debug("StrategicMemoryStore not available")
            return []
        except (RuntimeError, ValueError, OSError, sqlite3.Error) as e:
            logger.debug("Recurring findings collection failed: %s", e)
            return []

    def _collect_audit_signals(self) -> dict[str, Any]:
        """Lightweight inline audit checks (no subprocess).

        Checks for common code quality signals by scanning key paths.
        """
        results: dict[str, Any] = {
            "bare_except_count": 0,
            "todo_count": 0,
            "fixme_count": 0,
            "missing_init_files": [],
        }

        src_root = self._repo_path / "aragora"
        if not src_root.exists():
            return results

        todo_pattern = re.compile(r"#\s*(TODO|FIXME)\b", re.IGNORECASE)

        try:
            for py_file in src_root.rglob("*.py"):
                if py_file.name.startswith("__"):
                    continue
                try:
                    content = py_file.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue

                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("except:") or stripped == "except:":
                        results["bare_except_count"] += 1
                    m = todo_pattern.search(stripped)
                    if m:
                        tag = m.group(1).upper()
                        if tag == "TODO":
                            results["todo_count"] += 1
                        elif tag == "FIXME":
                            results["fixme_count"] += 1

            # Check for missing __init__.py
            for subdir in src_root.iterdir():
                if subdir.is_dir() and not subdir.name.startswith("."):
                    init_path = subdir / "__init__.py"
                    if not init_path.exists():
                        rel = str(subdir.relative_to(self._repo_path))
                        results["missing_init_files"].append(rel)
        except OSError as e:
            logger.debug("Audit signal collection failed: %s", e)

        return results

    def _classify_features(
        self,
        scanner_findings: list[Any],
        health_report: dict[str, Any],
    ) -> list[FeatureEntry]:
        """Parse FEATURE_GAP_LIST.md, cross-ref with scanner findings."""
        raw_features = self._parse_feature_gap_list()
        if not raw_features:
            return []

        # Build a set of file paths from scanner findings for cross-referencing
        finding_paths: set[str] = set()
        for f in scanner_findings:
            path = getattr(f, "file_path", None) if not isinstance(f, dict) else f.get("file_path")
            if path:
                finding_paths.add(path)

        entries: list[FeatureEntry] = []
        for raw in raw_features:
            name = raw.get("name", "")
            status_text = raw.get("status", "").lower()
            priority = raw.get("priority", "P3")
            notes = raw.get("notes", "")

            # Classify status based on status text
            status = self._classify_status(status_text, name, finding_paths)

            evidence: list[str] = []
            if raw.get("issue"):
                evidence.append(f"issue:{raw['issue']}")

            entries.append(
                FeatureEntry(
                    name=name,
                    status=status,
                    evidence=evidence,
                    priority=priority,
                    notes=notes,
                )
            )

        return entries

    @staticmethod
    def _classify_status(status_text: str, name: str, finding_paths: set[str]) -> str:
        """Determine feature status from gap list text and scanner evidence."""
        completed_indicators = [
            "complete",
            "shipped",
            "validated",
            "live",
            "verified",
            "closed",
            "deployed",
            "working",
        ]
        scaffolding_indicators = [
            "scaffolding",
            "partial",
            "contracts written",
            "design only",
            "code exists",
        ]
        not_started_indicators = ["not started"]

        for indicator in completed_indicators:
            if indicator in status_text:
                return "shipped"

        for indicator in scaffolding_indicators:
            if indicator in status_text:
                return "scaffolding"

        for indicator in not_started_indicators:
            if indicator in status_text:
                return "gap"

        # Default: if status text is non-empty, treat as scaffolding
        if status_text:
            return "scaffolding"
        return "gap"

    def _parse_feature_gap_list(self) -> list[dict[str, Any]]:
        """Regex-based markdown table parser for FEATURE_GAP_LIST.md."""
        gap_file = self._repo_path / "docs" / "FEATURE_GAP_LIST.md"
        if not gap_file.exists():
            logger.debug("FEATURE_GAP_LIST.md not found at %s", gap_file)
            return []

        try:
            content = gap_file.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.debug("Failed to read FEATURE_GAP_LIST.md: %s", e)
            return []

        features: list[dict[str, Any]] = []
        current_priority = "P3"

        # Match priority headers like "## P0 — GA Blockers"
        priority_pattern = re.compile(r"^##\s+(P\d)\b", re.MULTILINE)
        # Match table rows: | Feature | Status | Notes |
        row_pattern = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|$")
        # Extract issue references like [#123](...)
        issue_pattern = re.compile(r"\[#(\d+)\]")

        for line in content.splitlines():
            # Check for priority header
            pm = priority_pattern.match(line)
            if pm:
                current_priority = pm.group(1)
                continue

            # Skip header/separator rows
            if line.strip().startswith("|--") or line.strip().startswith("| Feature"):
                continue

            # Check for completed section
            if "## Completed" in line or "## Scaffolding" in line:
                # Scaffolding section uses same priority, completed uses "shipped"
                if "Completed" in line:
                    current_priority = "shipped"
                continue

            rm = row_pattern.match(line.strip())
            if not rm:
                continue

            name = rm.group(1).strip()
            status = rm.group(2).strip()
            notes = rm.group(3).strip()

            # Skip header rows that leaked through
            if name.lower() in ("feature", "------", "---"):
                continue

            # Extract issue number if present
            issue_match = issue_pattern.search(notes) or issue_pattern.search(status)
            issue = f"#{issue_match.group(1)}" if issue_match else ""

            features.append(
                {
                    "name": name,
                    "status": status,
                    "priority": current_priority,
                    "notes": notes,
                    "issue": issue,
                }
            )

        return features

    def _collect_git_metadata(self) -> dict[str, Any]:
        """Collect git rev-parse HEAD, branch, dirty status via subprocess."""
        metadata: dict[str, Any] = {
            "repo_path": str(self._repo_path),
        }

        try:
            # HEAD commit
            proc = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(self._repo_path),
                timeout=10,
            )
            if proc.returncode == 0:
                metadata["commit_sha"] = proc.stdout.strip()

            # Current branch
            proc = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(self._repo_path),
                timeout=10,
            )
            if proc.returncode == 0:
                metadata["branch"] = proc.stdout.strip()

            # Dirty status
            proc = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=str(self._repo_path),
                timeout=10,
            )
            if proc.returncode == 0:
                metadata["dirty"] = bool(proc.stdout.strip())
            else:
                metadata["dirty"] = None

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug("Git metadata collection failed: %s", e)
            metadata["git_error"] = str(type(e).__name__)

        return metadata


# ---------------------------------------------------------------------------
# Delta
# ---------------------------------------------------------------------------


def compute_delta(
    current: CanonicalRepoAssessment,
    previous: CanonicalRepoAssessment,
) -> AssessmentDelta:
    """Pure data comparison between two assessments."""
    # Health score change
    cur_health = current.health_report.get("health_score", 0.0)
    prev_health = previous.health_report.get("health_score", 0.0)

    # Feature diff
    cur_names = {f.name for f in current.feature_inventory}
    prev_names = {f.name for f in previous.feature_inventory}
    new_features = sorted(cur_names - prev_names)
    resolved_features = sorted(prev_names - cur_names)

    # Status changes for features present in both
    prev_status_map = {f.name: f.status for f in previous.feature_inventory}
    status_changes: list[dict[str, str]] = []
    for feat in current.feature_inventory:
        old_status = prev_status_map.get(feat.name)
        if old_status and old_status != feat.status:
            status_changes.append(
                {
                    "name": feat.name,
                    "old_status": old_status,
                    "new_status": feat.status,
                }
            )

    # Findings diff
    cur_findings = len(current.recurring_findings)
    prev_findings = len(previous.recurring_findings)

    return AssessmentDelta(
        previous_id=previous.assessment_id,
        current_id=current.assessment_id,
        time_elapsed_seconds=current.timestamp - previous.timestamp,
        health_score_change=cur_health - prev_health,
        new_features=new_features,
        resolved_features=resolved_features,
        status_changes=status_changes,
        new_findings=max(0, cur_findings - prev_findings),
        resolved_findings=max(0, prev_findings - cur_findings),
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

_DEFAULT_DB_DIR = os.environ.get("ARAGORA_DATA_DIR", str(Path.home() / ".aragora"))
_DEFAULT_DB_PATH = os.path.join(_DEFAULT_DB_DIR, "canonical_assessments.db")


def _get_db_path() -> str:
    """Resolve the canonical assessments database path."""
    try:
        from aragora.config import resolve_db_path

        return resolve_db_path("canonical_assessments.db")
    except ImportError:
        return _DEFAULT_DB_PATH


def _ensure_table(conn: sqlite3.Connection) -> None:
    """Create the canonical_assessments table if it does not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS canonical_assessments (
            assessment_id TEXT PRIMARY KEY,
            timestamp REAL NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_canonical_timestamp
        ON canonical_assessments(timestamp DESC)
    """)
    conn.commit()


def _connect(db_path: str) -> sqlite3.Connection:
    """Create a new connection with WAL mode."""
    parent = Path(db_path).parent
    parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    _ensure_table(conn)
    return conn


def save_assessment(
    assessment: CanonicalRepoAssessment,
    db_path: str | None = None,
) -> str:
    """Persist a canonical assessment to SQLite.

    Args:
        assessment: The assessment to persist.
        db_path: Optional custom DB path.

    Returns:
        The assessment ID.
    """
    path = db_path or _get_db_path()
    conn = _connect(path)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO canonical_assessments
                (assessment_id, timestamp, data_json)
            VALUES (?, ?, ?)
            """,
            (
                assessment.assessment_id,
                assessment.timestamp,
                json.dumps(assessment.to_dict()),
            ),
        )
        conn.commit()
        logger.debug("Canonical assessment saved: %s", assessment.assessment_id)
        return assessment.assessment_id
    finally:
        conn.close()


def load_latest_assessment(
    db_path: str | None = None,
) -> CanonicalRepoAssessment | None:
    """Load the most recent canonical assessment from SQLite."""
    path = db_path or _get_db_path()
    conn = _connect(path)
    try:
        row = conn.execute(
            """
            SELECT data_json
            FROM canonical_assessments
            ORDER BY timestamp DESC
            LIMIT 1
            """,
        ).fetchone()
        if row is None:
            return None
        return CanonicalRepoAssessment.from_dict(json.loads(row["data_json"]))
    finally:
        conn.close()


def load_assessment(
    assessment_id: str,
    db_path: str | None = None,
) -> CanonicalRepoAssessment | None:
    """Load a specific canonical assessment by ID."""
    path = db_path or _get_db_path()
    conn = _connect(path)
    try:
        row = conn.execute(
            """
            SELECT data_json
            FROM canonical_assessments
            WHERE assessment_id = ?
            """,
            (assessment_id,),
        ).fetchone()
        if row is None:
            return None
        return CanonicalRepoAssessment.from_dict(json.loads(row["data_json"]))
    finally:
        conn.close()


__all__ = [
    "AssessmentDelta",
    "CanonicalAssessmentCompiler",
    "CanonicalRepoAssessment",
    "FeatureEntry",
    "compute_delta",
    "load_assessment",
    "load_latest_assessment",
    "save_assessment",
]

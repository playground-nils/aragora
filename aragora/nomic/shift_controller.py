"""Bounded shift controller for long-running autonomous improvement.

Manages timing, budget, mandatory refresh intervals, and checkpoint
persistence for autonomous improvement "shifts".  Does NOT orchestrate
execution — the caller (CLI or pipeline) drives the loop by calling
``run_cycle()`` and checking ``check_should_stop()``.

Usage:
    from aragora.nomic.shift_controller import ShiftController, ShiftConfig

    ctrl = ShiftController(ShiftConfig(max_duration_hours=4.0))
    state = await ctrl.start_shift(assessment_id="abc-123")
    while True:
        should_stop, reason = ctrl.check_should_stop()
        if should_stop:
            if reason.startswith("RefreshDue"):
                await ctrl.pause_for_refresh()
                # ... compile fresh assessment ...
                await ctrl.resume_after_refresh(new_assessment_id="def-456")
                continue
            ctrl.complete_shift(reason)
            break
        result = await ctrl.run_cycle("improve test coverage")
"""

from __future__ import annotations

import logging
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class ShiftConfig:
    """Configuration for a bounded autonomous shift."""

    max_duration_hours: float = 8.0
    refresh_interval_minutes: float = 120.0  # Pause for refresh every 2h
    budget_limit_usd: float = 10.0
    max_cycles: int = 50
    require_fresh_assessment: bool = True  # Must have assessment before starting
    require_receipts: bool = False  # Require receipt_id when recording a cycle
    enforce_clean_repo: bool = False  # Stop if repo cleanliness cannot be proven
    enforce_worktree_collision_check: bool = False  # Stop on duplicate worktree refs
    repo_path: str | None = None  # Repo to validate for hygiene checks
    checkpoint_dir: str = ".aragora_shifts"


# ---------------------------------------------------------------------------
# Persistent state
# ---------------------------------------------------------------------------


@dataclass
class ShiftState:
    """Persistent state for an active shift."""

    shift_id: str
    started_at: float
    config: dict[str, Any]  # Serialized ShiftConfig
    status: str = "running"  # running | paused_for_refresh | completed | failed | stopped
    current_cycle: int = 0
    elapsed_seconds: float = 0.0
    budget_spent_usd: float = 0.0
    refresh_count: int = 0
    last_refresh_at: float = 0.0
    last_checkpoint_at: float = 0.0
    assessment_id: str | None = None  # Links to CanonicalRepoAssessment
    current_objective: str = ""
    last_receipt_id: str | None = None
    objectives_completed: list[str] = field(default_factory=list)
    objectives_failed: list[str] = field(default_factory=list)
    blocked_reasons: list[str] = field(default_factory=list)
    next_refresh_actions: list[str] = field(default_factory=list)
    stop_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "shift_id": self.shift_id,
            "started_at": self.started_at,
            "config": self.config,
            "status": self.status,
            "current_cycle": self.current_cycle,
            "elapsed_seconds": self.elapsed_seconds,
            "budget_spent_usd": self.budget_spent_usd,
            "refresh_count": self.refresh_count,
            "last_refresh_at": self.last_refresh_at,
            "last_checkpoint_at": self.last_checkpoint_at,
            "assessment_id": self.assessment_id,
            "current_objective": self.current_objective,
            "last_receipt_id": self.last_receipt_id,
            "objectives_completed": list(self.objectives_completed),
            "objectives_failed": list(self.objectives_failed),
            "blocked_reasons": list(self.blocked_reasons),
            "next_refresh_actions": list(self.next_refresh_actions),
            "stop_reason": self.stop_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShiftState:
        """Deserialize from a dictionary."""
        return cls(
            shift_id=data["shift_id"],
            started_at=data["started_at"],
            config=data.get("config", {}),
            status=data.get("status", "running"),
            current_cycle=data.get("current_cycle", 0),
            elapsed_seconds=data.get("elapsed_seconds", 0.0),
            budget_spent_usd=data.get("budget_spent_usd", 0.0),
            refresh_count=data.get("refresh_count", 0),
            last_refresh_at=data.get("last_refresh_at", 0.0),
            last_checkpoint_at=data.get("last_checkpoint_at", 0.0),
            assessment_id=data.get("assessment_id"),
            current_objective=data.get("current_objective", ""),
            last_receipt_id=data.get("last_receipt_id"),
            objectives_completed=data.get("objectives_completed", []),
            objectives_failed=data.get("objectives_failed", []),
            blocked_reasons=data.get("blocked_reasons", []),
            next_refresh_actions=data.get("next_refresh_actions", []),
            stop_reason=data.get("stop_reason", ""),
        )


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------


class ShiftController:
    """Manages bounded autonomous improvement shifts with mandatory refresh.

    The controller tracks timing, budget, cycle count, and refresh intervals.
    It does NOT orchestrate execution — the caller is responsible for driving
    the improvement loop and calling ``run_cycle()`` with objectives.
    """

    def __init__(self, config: ShiftConfig | None = None) -> None:
        self._config = config or ShiftConfig()
        self._state: ShiftState | None = None
        self._checkpoint_dir = Path(self._config.checkpoint_dir)

    @property
    def state(self) -> ShiftState | None:
        """Current shift state (None if no shift is active)."""
        return self._state

    @property
    def config(self) -> ShiftConfig:
        """Current shift configuration."""
        return self._config

    # ------------------------------------------------------------------
    # Shift lifecycle
    # ------------------------------------------------------------------

    async def start_shift(self, assessment_id: str | None = None) -> ShiftState:
        """Start a new bounded shift.

        If ``require_fresh_assessment`` is True, *assessment_id* must be
        provided.  Otherwise the shift starts without one.

        Args:
            assessment_id: Links this shift to a CanonicalRepoAssessment.

        Returns:
            The newly created ShiftState.

        Raises:
            ValueError: If an assessment is required but not provided, or
                if a shift is already active.
        """
        if self._state is not None and self._state.status == "running":
            raise ValueError(
                f"Shift {self._state.shift_id} is already running; "
                "complete or stop it before starting a new one"
            )

        if self._config.require_fresh_assessment and not assessment_id:
            raise ValueError(
                "A fresh assessment_id is required before starting a shift "
                "(set require_fresh_assessment=False to skip)"
            )

        now = time.time()
        config_dict = {
            "max_duration_hours": self._config.max_duration_hours,
            "refresh_interval_minutes": self._config.refresh_interval_minutes,
            "budget_limit_usd": self._config.budget_limit_usd,
            "max_cycles": self._config.max_cycles,
            "require_fresh_assessment": self._config.require_fresh_assessment,
            "require_receipts": self._config.require_receipts,
            "enforce_clean_repo": self._config.enforce_clean_repo,
            "enforce_worktree_collision_check": self._config.enforce_worktree_collision_check,
            "repo_path": self._config.repo_path,
            "checkpoint_dir": self._config.checkpoint_dir,
        }

        self._state = ShiftState(
            shift_id=uuid.uuid4().hex[:12],
            started_at=now,
            config=config_dict,
            status="running",
            last_refresh_at=now,
            assessment_id=assessment_id,
        )

        self._save_checkpoint()
        logger.info(
            "shift_started shift_id=%s assessment=%s",
            self._state.shift_id,
            assessment_id,
        )
        return self._state

    async def run_cycle(
        self,
        objective: str,
        *,
        cost_usd: float = 0.0,
        receipt_id: str | None = None,
        quality_gate_passed: bool = True,
        ownership_clear: bool = True,
    ) -> dict[str, Any]:
        """Run one improvement cycle within the shift.

        Checks all stop conditions before execution.  The controller does
        NOT execute the objective itself — it records the cycle and returns
        a result dict that the caller uses to drive the next step.

        Args:
            objective: Description of the improvement objective.
            cost_usd: Optional cost accrued by the cycle.
            receipt_id: Optional receipt/provenance id for the cycle.
            quality_gate_passed: Whether execution cleared quality gates.
            ownership_clear: Whether ownership/scope was unambiguous.

        Returns:
            Dict with ``completed``, ``cycle``, ``stop_reason`` keys.

        Raises:
            RuntimeError: If no shift is active or shift is not running.
        """
        if self._state is None:
            raise RuntimeError("No active shift; call start_shift() first")
        if self._state.status != "running":
            raise RuntimeError(f"Shift is not running (status={self._state.status})")

        # Pre-flight stop check
        should_stop, reason = self.check_should_stop()
        if should_stop:
            return {"completed": False, "cycle": self._state.current_cycle, "stop_reason": reason}

        self._state.current_objective = objective
        self._state.stop_reason = ""
        self._state.blocked_reasons = []
        self._state.next_refresh_actions = []

        if not ownership_clear:
            return self._block_cycle(
                objective,
                "OwnershipAmbiguous: objective lacks clear ownership or scope evidence",
            )

        if self._config.require_receipts and not receipt_id:
            return self._block_cycle(
                objective,
                "MissingReceipt: cycle result did not include a receipt_id",
            )

        if not quality_gate_passed:
            return self._block_cycle(
                objective,
                "QualityGateFailed: cycle did not clear quality gates",
            )

        # Record the cycle
        self._state.current_cycle += 1
        self._state.elapsed_seconds = time.time() - self._state.started_at
        self._state.budget_spent_usd += max(0.0, float(cost_usd))
        self._state.last_receipt_id = receipt_id
        self._state.objectives_completed.append(objective)

        # Save checkpoint
        self._save_checkpoint()

        # Post-flight stop check
        should_stop, reason = self.check_should_stop()
        return {
            "completed": True,
            "cycle": self._state.current_cycle,
            "stop_reason": reason if should_stop else None,
        }

    def check_should_stop(self) -> tuple[bool, str]:
        """Check all stop conditions.

        Returns:
            Tuple of ``(should_stop, reason)``.  When ``should_stop`` is
            False, ``reason`` is the empty string.
        """
        if self._state is None:
            return True, "NoActiveShift"

        if self._state.status not in ("running",):
            return True, f"ShiftNotRunning: status={self._state.status}"

        if self._config.enforce_clean_repo and self._is_repo_dirty():
            return True, "DirtyWorktree: repository has uncommitted changes"

        if self._config.enforce_worktree_collision_check and self._has_colliding_worktrees():
            return True, "CollidingWorktrees: duplicate worktree paths or branches detected"

        # Time limit
        elapsed_hours = (time.time() - self._state.started_at) / 3600.0
        if elapsed_hours >= self._config.max_duration_hours:
            return (
                True,
                f"TimeLimit: {elapsed_hours:.2f}h >= max {self._config.max_duration_hours:.2f}h",
            )

        # Budget limit
        if self._state.budget_spent_usd >= self._config.budget_limit_usd:
            return (
                True,
                f"BudgetExhausted: ${self._state.budget_spent_usd:.4f} >= "
                f"limit ${self._config.budget_limit_usd:.4f}",
            )

        # Cycle limit
        if self._state.current_cycle >= self._config.max_cycles:
            return True, f"CycleLimit: {self._state.current_cycle} >= max {self._config.max_cycles}"

        # Refresh due (soft stop — caller decides whether to pause)
        if self.check_refresh_due():
            elapsed_since = time.time() - (self._state.last_refresh_at or self._state.started_at)
            return (
                True,
                f"RefreshDue: {elapsed_since / 60:.0f}m since last refresh "
                f"(interval={self._config.refresh_interval_minutes:.0f}m)",
            )

        return False, ""

    def check_refresh_due(self) -> bool:
        """Check if it's time for a mandatory refresh pause."""
        if self._state is None:
            return False
        reference = self._state.last_refresh_at or self._state.started_at
        elapsed_since_refresh = time.time() - reference
        return elapsed_since_refresh >= self._config.refresh_interval_minutes * 60

    # ------------------------------------------------------------------
    # Pause / resume
    # ------------------------------------------------------------------

    async def pause_for_refresh(self, reason: str | None = None) -> ShiftState:
        """Pause the shift for mandatory assessment refresh.

        Saves a checkpoint and sets the status to ``paused_for_refresh``.

        Returns:
            The updated ShiftState.

        Raises:
            RuntimeError: If no shift is active.
        """
        if self._state is None:
            raise RuntimeError("No active shift to pause")

        pause_reason = reason or self._state.stop_reason or "RefreshDue"
        self._state.status = "paused_for_refresh"
        self._state.stop_reason = pause_reason
        self._state.blocked_reasons = [pause_reason]
        self._state.next_refresh_actions = self._recommended_refresh_actions(pause_reason)
        self._state.elapsed_seconds = time.time() - self._state.started_at
        self._save_checkpoint()
        logger.info(
            "shift_paused_for_refresh shift_id=%s cycle=%d",
            self._state.shift_id,
            self._state.current_cycle,
        )
        return self._state

    async def resume_after_refresh(self, new_assessment_id: str) -> ShiftState:
        """Resume shift after a fresh assessment.

        Args:
            new_assessment_id: The ID of the freshly compiled assessment.

        Returns:
            The updated ShiftState.

        Raises:
            RuntimeError: If no shift is active or shift is not paused.
            ValueError: If *new_assessment_id* is empty.
        """
        if self._state is None:
            raise RuntimeError("No active shift to resume")
        if self._state.status != "paused_for_refresh":
            raise RuntimeError(f"Shift is not paused for refresh (status={self._state.status})")
        if not new_assessment_id:
            raise ValueError("A fresh assessment_id is required to resume")
        if self._config.require_fresh_assessment and new_assessment_id == self._state.assessment_id:
            raise ValueError("A fresh assessment_id must differ from the previous assessment")

        self._state.status = "running"
        self._state.assessment_id = new_assessment_id
        self._state.refresh_count += 1
        self._state.last_refresh_at = time.time()
        self._state.stop_reason = ""
        self._state.blocked_reasons = []
        self._state.next_refresh_actions = []
        self._state.current_objective = ""
        self._save_checkpoint()
        logger.info(
            "shift_resumed shift_id=%s assessment=%s refresh_count=%d",
            self._state.shift_id,
            new_assessment_id,
            self._state.refresh_count,
        )
        return self._state

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    def complete_shift(self, reason: str = "completed") -> ShiftState:
        """Mark shift as completed with reason.

        Args:
            reason: Why the shift ended (e.g. "completed", "TimeLimit", ...).

        Returns:
            The final ShiftState.

        Raises:
            RuntimeError: If no shift is active.
        """
        if self._state is None:
            raise RuntimeError("No active shift to complete")

        self._state.status = "completed"
        self._state.stop_reason = reason
        self._state.blocked_reasons = [reason] if reason and reason != "completed" else []
        self._state.next_refresh_actions = (
            self._recommended_refresh_actions(reason) if self._state.blocked_reasons else []
        )
        self._state.elapsed_seconds = time.time() - self._state.started_at
        self._save_checkpoint()
        logger.info(
            "shift_completed shift_id=%s reason=%s cycles=%d",
            self._state.shift_id,
            reason,
            self._state.current_cycle,
        )
        return self._state

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def get_progress_summary(self) -> dict[str, Any]:
        """Current shift progress for operator/integrator view.

        Returns:
            Dict with elapsed, budget, cycle, and remaining-time info.
        """
        if self._state is None:
            return {"active": False}

        now = time.time()
        elapsed_hours = (now - self._state.started_at) / 3600.0
        remaining_hours = max(0.0, self._config.max_duration_hours - elapsed_hours)

        reference = self._state.last_refresh_at or self._state.started_at
        next_refresh_minutes = max(
            0.0,
            self._config.refresh_interval_minutes - (now - reference) / 60.0,
        )

        return {
            "active": True,
            "shift_id": self._state.shift_id,
            "status": self._state.status,
            "assessment_id": self._state.assessment_id,
            "elapsed_hours": round(elapsed_hours, 2),
            "remaining_hours": round(remaining_hours, 2),
            "budget_spent_usd": round(self._state.budget_spent_usd, 4),
            "budget_remaining_usd": round(
                self._config.budget_limit_usd - self._state.budget_spent_usd, 4
            ),
            "cycles_completed": self._state.current_cycle,
            "max_cycles": self._config.max_cycles,
            "objectives_completed": len(self._state.objectives_completed),
            "objectives_failed": len(self._state.objectives_failed),
            "refresh_count": self._state.refresh_count,
            "minutes_until_next_refresh": round(next_refresh_minutes, 1),
            "current_objective": self._state.current_objective,
            "last_receipt_id": self._state.last_receipt_id,
            "stop_reason": self._state.stop_reason,
            "blocked_reasons": list(self._state.blocked_reasons),
            "next_refresh_actions": list(self._state.next_refresh_actions),
        }

    # ------------------------------------------------------------------
    # Checkpoint persistence
    # ------------------------------------------------------------------

    def _save_checkpoint(self) -> None:
        """Save current state via CheckpointManager."""
        if self._state is None:
            return

        try:
            from aragora.nomic.checkpoints import CheckpointManager

            mgr = CheckpointManager(
                checkpoint_dir=str(self._checkpoint_dir),
                auto_cleanup=True,
                max_checkpoints=20,
            )
            mgr.save(
                data={"shift_state": self._state.to_dict()},
                cycle_id=self._state.shift_id,
                state_name=self._state.status,
            )
            self._state.last_checkpoint_at = time.time()
        except (OSError, ImportError, ValueError) as exc:
            logger.warning("shift_checkpoint_save_failed: %s", exc)

    def _block_cycle(self, objective: str, reason: str) -> dict[str, Any]:
        """Record a truthful blocked cycle without pretending execution succeeded."""
        if self._state is None:
            raise RuntimeError("No active shift; cannot block cycle")
        self._state.stop_reason = reason
        self._state.blocked_reasons = [reason]
        self._state.next_refresh_actions = self._recommended_refresh_actions(reason)
        self._state.objectives_failed.append(objective)
        self._state.elapsed_seconds = time.time() - self._state.started_at
        self._save_checkpoint()
        return {
            "completed": False,
            "cycle": self._state.current_cycle,
            "stop_reason": reason,
        }

    def _recommended_refresh_actions(self, reason: str) -> list[str]:
        """Suggest next refresh steps after a blocked or paused shift."""
        actions = [
            "Run `aragora assess --save --diff` before resuming the shift.",
            "Review the accepted backlog slice and current stop reason before continuing.",
        ]
        if reason.startswith("DirtyWorktree"):
            actions.insert(0, "Reconcile or clean the dirty worktree before resuming.")
        elif reason.startswith("CollidingWorktrees"):
            actions.insert(0, "Reconcile duplicate/colliding worktrees before resuming.")
        elif reason.startswith("MissingReceipt"):
            actions.insert(0, "Ensure cycle execution returns a receipt_id before resuming.")
        elif reason.startswith("QualityGateFailed"):
            actions.insert(0, "Inspect and resolve the failing quality gates before resuming.")
        elif reason.startswith("OwnershipAmbiguous"):
            actions.insert(0, "Tighten file ownership or scope evidence for the next cycle.")
        return actions

    def _repo_path(self) -> Path:
        return Path(self._config.repo_path or Path.cwd()).resolve()

    def _is_repo_dirty(self) -> bool:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self._repo_path(),
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if proc.returncode != 0:
            logger.debug("shift_repo_cleanliness_check_failed returncode=%s", proc.returncode)
            return True
        return bool(proc.stdout.strip())

    def _has_colliding_worktrees(self) -> bool:
        proc = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self._repo_path(),
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if proc.returncode != 0:
            logger.debug("shift_worktree_collision_check_failed returncode=%s", proc.returncode)
            return True

        paths: set[str] = set()
        branches: set[str] = set()
        current_path: str | None = None

        for line in proc.stdout.splitlines():
            if line.startswith("worktree "):
                current_path = line.split(" ", 1)[1].strip()
                if current_path in paths:
                    return True
                paths.add(current_path)
            elif line.startswith("branch "):
                branch = line.split(" ", 1)[1].strip()
                if current_path and branch in branches:
                    return True
                if branch:
                    branches.add(branch)
        return False

    @classmethod
    def resume_from_checkpoint(
        cls, checkpoint_dir: str = ".aragora_shifts"
    ) -> ShiftController | None:
        """Resume a paused shift from the latest checkpoint.

        Args:
            checkpoint_dir: Directory containing shift checkpoints.

        Returns:
            A ShiftController with restored state, or None if no
            resumable checkpoint exists.
        """
        try:
            from aragora.nomic.checkpoints import CheckpointManager

            mgr = CheckpointManager(checkpoint_dir=checkpoint_dir, auto_cleanup=False)
            data = mgr.load_latest()
        except (ImportError, OSError, ValueError) as exc:
            logger.warning("shift_checkpoint_load_failed: %s", exc)
            return None

        if data is None:
            return None

        shift_data = data.get("shift_state")
        if shift_data is None:
            return None

        state = ShiftState.from_dict(shift_data)

        # Rebuild config from persisted state
        cfg_data = state.config
        config = ShiftConfig(
            max_duration_hours=cfg_data.get("max_duration_hours", 8.0),
            refresh_interval_minutes=cfg_data.get("refresh_interval_minutes", 120.0),
            budget_limit_usd=cfg_data.get("budget_limit_usd", 10.0),
            max_cycles=cfg_data.get("max_cycles", 50),
            require_fresh_assessment=cfg_data.get("require_fresh_assessment", True),
            require_receipts=cfg_data.get("require_receipts", False),
            enforce_clean_repo=cfg_data.get("enforce_clean_repo", False),
            enforce_worktree_collision_check=cfg_data.get(
                "enforce_worktree_collision_check", False
            ),
            repo_path=cfg_data.get("repo_path"),
            checkpoint_dir=checkpoint_dir,
        )

        controller = cls(config=config)
        controller._state = state
        logger.info(
            "shift_resumed_from_checkpoint shift_id=%s status=%s cycle=%d",
            state.shift_id,
            state.status,
            state.current_cycle,
        )
        return controller

    @classmethod
    def load_shift_history(cls, checkpoint_dir: str = ".aragora_shifts") -> list[dict[str, Any]]:
        """List all historical shifts with summary.

        Args:
            checkpoint_dir: Directory containing shift checkpoints.

        Returns:
            List of shift summary dicts, most recent first.
        """
        try:
            from aragora.nomic.checkpoints import CheckpointManager

            mgr = CheckpointManager(checkpoint_dir=checkpoint_dir, auto_cleanup=False)
            entries = mgr.list_all()
        except (ImportError, OSError, ValueError) as exc:
            logger.warning("shift_history_load_failed: %s", exc)
            return []

        summaries: list[dict[str, Any]] = []
        for entry in entries:
            path = entry.get("path")
            if not path:
                continue
            try:
                from aragora.nomic.checkpoints import load_checkpoint

                data = load_checkpoint(path)
                if data and "shift_state" in data:
                    ss = data["shift_state"]
                    summaries.append(
                        {
                            "shift_id": ss.get("shift_id"),
                            "status": ss.get("status"),
                            "cycles": ss.get("current_cycle", 0),
                            "elapsed_seconds": ss.get("elapsed_seconds", 0.0),
                            "budget_spent_usd": ss.get("budget_spent_usd", 0.0),
                            "stop_reason": ss.get("stop_reason", ""),
                            "checkpoint_path": path,
                        }
                    )
            except (OSError, KeyError, ValueError) as exc:
                logger.debug("shift_history_entry_skip: %s", exc)

        return summaries


__all__ = [
    "ShiftConfig",
    "ShiftController",
    "ShiftState",
]

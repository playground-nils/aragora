# Execution Safety Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce an `ExecutionMode` enum (AUTONOMOUS/INTERACTIVE) that flows through the entire stack, wire backbone to remaining gaps, narrow Docker capabilities, redact token logging, and split monolith files.

**Architecture:** A single enum determines whether execution paths auto-approve (boss loop) or gate on approval (API handlers). Backbone wiring is async and non-blocking in AUTONOMOUS mode, fail-closed in INTERACTIVE. Monolith splits are pure refactors with backwards-compatible re-exports.

**Tech Stack:** Python 3.11, dataclasses, pytest, TypeScript (frontend token fix)

**Spec:** `docs/superpowers/specs/2026-04-01-execution-safety-modes-design.md`

---

## File Structure

| File | Responsibility | Task |
|------|---------------|------|
| `aragora/pipeline/execution_mode.py` | ExecutionMode enum + helpers | 1 |
| `aragora/harnesses/claude_code.py` | Conditional `--yes` based on mode | 2 |
| `aragora/swarm/worker_launcher.py` | Thread execution_mode through LaunchConfig | 3 |
| `aragora/swarm/commander.py` | Pass execution_mode to LaunchConfig | 3 |
| `aragora/swarm/boss_loop.py` | Backbone wiring + execution_mode default | 4 |
| `aragora/debate/post_debate_coordinator.py` | Backbone wiring for plan creation | 5 |
| `aragora/computer_use/sandbox.py` | Narrow Docker capabilities | 6 |
| `aragora/live/src/app/(app)/auth/callback/page.tsx` | Redact token logging | 7 |
| `aragora/swarm/boss_feed.py` | Extracted from boss_loop.py | 8 |
| `aragora/swarm/boss_freshness.py` | Extracted from boss_loop.py | 8 |
| `aragora/swarm/boss_dispatch.py` | Extracted from boss_loop.py | 8 |
| `aragora/swarm/worker_process.py` | Extracted from worker_launcher.py | 9 |
| `aragora/debate/post_debate_config.py` | Extracted from post_debate_coordinator.py | 10 |

---

### Task 1: Create ExecutionMode Enum

**Files:**
- Create: `aragora/pipeline/execution_mode.py`
- Test: `tests/pipeline/test_execution_mode.py`

- [ ] **Step 1: Write the test**

```python
"""Tests for ExecutionMode enum."""
from aragora.pipeline.execution_mode import ExecutionMode

def test_autonomous_is_default_for_boss_contexts():
    assert ExecutionMode.AUTONOMOUS == "autonomous"

def test_interactive_is_default_for_api_contexts():
    assert ExecutionMode.INTERACTIVE == "interactive"

def test_enum_is_str_subclass():
    # Allows direct string comparison in configs
    assert isinstance(ExecutionMode.AUTONOMOUS, str)
    assert ExecutionMode.AUTONOMOUS == "autonomous"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_execution_mode.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

```python
"""Execution mode for the Aragora pipeline.

AUTONOMOUS: Pre-approved by config. Used by boss loop, swarm, nomic loop.
INTERACTIVE: Per-action approval required. Used by API handlers, attended CLI.
"""
from __future__ import annotations
from enum import Enum

class ExecutionMode(str, Enum):
    AUTONOMOUS = "autonomous"
    INTERACTIVE = "interactive"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_execution_mode.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add aragora/pipeline/execution_mode.py tests/pipeline/test_execution_mode.py
git commit -m "feat(pipeline): add ExecutionMode enum"
```

---

### Task 2: Wire ExecutionMode into Claude Code Harness

**Files:**
- Modify: `aragora/harnesses/claude_code.py:46-69` (ClaudeCodeConfig) and `:528-533` (execute_implementation)
- Test: `tests/harnesses/test_claude_code.py` (find existing or create)

- [ ] **Step 1: Write failing tests**

```python
from aragora.harnesses.claude_code import ClaudeCodeConfig, ClaudeCodeHarness
from aragora.pipeline.execution_mode import ExecutionMode

def test_autonomous_mode_adds_yes_flag():
    """Mock subprocess to capture the command built by the harness."""
    config = ClaudeCodeConfig(execution_mode=ExecutionMode.AUTONOMOUS)
    harness = ClaudeCodeHarness(config=config)
    # Patch subprocess to capture the command args
    captured_cmds = []
    async def mock_subprocess(*args, **kwargs):
        captured_cmds.append(list(args))
        proc = MagicMock()
        proc.communicate = AsyncMock(return_value=(b"done", b""))
        proc.returncode = 0
        return proc
    with patch("asyncio.create_subprocess_exec", side_effect=mock_subprocess):
        asyncio.run(harness.execute_implementation("test", Path("/tmp/repo")))
    assert any("--yes" in cmd for cmd in captured_cmds)

def test_interactive_mode_omits_yes_flag():
    config = ClaudeCodeConfig(execution_mode=ExecutionMode.INTERACTIVE)
    harness = ClaudeCodeHarness(config=config)
    captured_cmds = []
    async def mock_subprocess(*args, **kwargs):
        captured_cmds.append(list(args))
        proc = MagicMock()
        proc.communicate = AsyncMock(return_value=(b"done", b""))
        proc.returncode = 0
        return proc
    with patch("asyncio.create_subprocess_exec", side_effect=mock_subprocess):
        asyncio.run(harness.execute_implementation("test", Path("/tmp/repo")))
    assert not any("--yes" in cmd for cmd in captured_cmds)

def test_default_mode_is_autonomous():
    config = ClaudeCodeConfig()
    assert config.execution_mode == ExecutionMode.AUTONOMOUS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/harnesses/test_claude_code.py -v -k "execution_mode or yes_flag"`
Expected: FAIL — `execution_mode` not a field

- [ ] **Step 3: Add execution_mode to ClaudeCodeConfig**

In `aragora/harnesses/claude_code.py`, add to `ClaudeCodeConfig` (after line 65):

```python
    # Execution safety mode
    execution_mode: ExecutionMode = ExecutionMode.AUTONOMOUS
```

Add import at top:
```python
from aragora.pipeline.execution_mode import ExecutionMode
```

- [ ] **Step 4: Make `--yes` conditional**

Replace line 532:
```python
            "--yes",  # Auto-approve file edits
```
With:
```python
        ]
        if self.config.execution_mode == ExecutionMode.AUTONOMOUS:
            cmd.append("--yes")  # Auto-approve file edits in autonomous mode
```

Note: The `]` closes the existing cmd list. `--yes` is appended conditionally after.

- [ ] **Step 5: Run tests and verify they pass**

Run: `pytest tests/harnesses/test_claude_code.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add aragora/harnesses/claude_code.py tests/harnesses/test_claude_code.py
git commit -m "feat(harness): make --yes conditional on ExecutionMode"
```

---

### Task 3: Thread ExecutionMode Through LaunchConfig and Commander

**Files:**
- Modify: `aragora/swarm/worker_launcher.py:153-171` (LaunchConfig)
- Modify: `aragora/swarm/commander.py:245-281` (run_supervised_from_spec)
- Modify: `aragora/swarm/boss_loop.py:1088-1103` (dispatch_bounded_spec signature)
- Test: `tests/swarm/test_worker_launcher.py`

- [ ] **Step 1: Write failing test**

```python
from aragora.pipeline.execution_mode import ExecutionMode

def test_launch_config_defaults_autonomous():
    config = LaunchConfig()
    assert config.execution_mode == ExecutionMode.AUTONOMOUS

def test_interactive_mode_blocks_dangerous_permissions():
    config = LaunchConfig(
        execution_mode=ExecutionMode.INTERACTIVE,
        allow_claude_dangerously_skip_permissions=True,
    )
    launcher = WorkerLauncher(config)
    cmd = launcher._build_agent_command("claude", "test")
    assert "--dangerously-skip-permissions" not in cmd

def test_interactive_mode_blocks_full_auto():
    config = LaunchConfig(
        execution_mode=ExecutionMode.INTERACTIVE,
        allow_codex_full_auto=True,
    )
    launcher = WorkerLauncher(config)
    cmd = launcher._build_agent_command("codex", "test")
    assert "--full-auto" not in cmd
```

- [ ] **Step 2: Add execution_mode to LaunchConfig**

In `worker_launcher.py`, add after line 171:
```python
    execution_mode: ExecutionMode = ExecutionMode.AUTONOMOUS
```

Add import at top:
```python
from aragora.pipeline.execution_mode import ExecutionMode
```

- [ ] **Step 3: Gate dangerous flags on execution_mode**

In `_build_agent_command`, for the claude branch (line 600-601):
```python
        if (self.config.allow_claude_dangerously_skip_permissions
                and self.config.execution_mode == ExecutionMode.AUTONOMOUS):
            cmd.append("--dangerously-skip-permissions")
```

For the codex branch (line 615-616):
```python
        if (self.config.allow_codex_full_auto
                and self.config.execution_mode == ExecutionMode.AUTONOMOUS):
            cmd.append("--full-auto")
```

Same for the unknown-agent fallback branch.

- [ ] **Step 4: Thread through commander.py**

Add `execution_mode` parameter to `run_supervised_from_spec()` (after line 246):
```python
    execution_mode: ExecutionMode = ExecutionMode.AUTONOMOUS,
```

Pass to `LaunchConfig(...)`:
```python
    execution_mode=execution_mode,
```

- [ ] **Step 5: Thread through dispatch_bounded_spec**

Add `execution_mode` parameter to `dispatch_bounded_spec()` in boss_loop.py (after line 1102):
```python
    execution_mode: ExecutionMode = ExecutionMode.AUTONOMOUS,
```

Pass to `commander.run_supervised_from_spec(...)`:
```python
    execution_mode=execution_mode,
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/swarm/test_worker_launcher.py -v --timeout=30`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add aragora/swarm/worker_launcher.py aragora/swarm/commander.py aragora/swarm/boss_loop.py tests/swarm/test_worker_launcher.py
git commit -m "feat(swarm): thread ExecutionMode through LaunchConfig and commander"
```

---

### Task 4: Boss Loop Backbone Wiring

**Files:**
- Modify: `aragora/swarm/boss_loop.py` (around line 2870, the dispatch_bounded_spec call site)
- Test: `tests/swarm/test_boss_loop.py` (add backbone wiring test)

- [ ] **Step 1: Write failing test**

```python
def test_boss_loop_creates_backbone_ledger_entry(monkeypatch):
    """Boss loop dispatch should create a backbone run entry."""
    created_runs = []

    class MockRuntime:
        def create_run(self, ledger):
            created_runs.append(ledger)
        def update_run(self, run_id, **kwargs):
            pass
        def append_stage_event(self, run_id, stage, **kwargs):
            pass

    monkeypatch.setattr(
        "aragora.swarm.boss_loop.BackboneRuntime",
        lambda *a, **kw: MockRuntime(),
        raising=False,
    )
    # ... dispatch setup and assertion that created_runs is non-empty
```

- [ ] **Step 2: Add backbone wiring to _dispatch_issue**

In `boss_loop.py`, around line 2869 (before `dispatch_bounded_spec`), add:

```python
        backbone_run_id = None
        runtime = None
        try:
            from aragora.pipeline.backbone_runtime import BackboneRuntime
            from aragora.pipeline.backbone_contracts import RunLedger
            runtime = BackboneRuntime()
            ledger = RunLedger(
                run_id=f"boss-{self.run_id}-issue{issue.number}",
                entrypoint="boss_loop",
                status="dispatching",
                metadata={"issue_number": issue.number, "issue_title": issue.title},
            )
            runtime.create_run(ledger)
            backbone_run_id = ledger.run_id
        except Exception:
            pass  # Never block autonomous dispatch
```

After the `dispatch_bounded_spec` call:

```python
        if backbone_run_id and runtime is not None:
            try:
                runtime.update_run(
                    backbone_run_id,
                    status="completed" if result.get("status") == "completed" else "failed",
                    execution_id=result.get("run_id"),
                    receipt_id=result.get("receipt_id"),
                )
            except Exception:
                pass
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/swarm/test_boss_loop.py -v --timeout=30 -x`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add aragora/swarm/boss_loop.py tests/swarm/test_boss_loop.py
git commit -m "feat(swarm): wire boss loop dispatch to backbone ledger"
```

---

### Task 5: PostDebateCoordinator Backbone Wiring

**Files:**
- Modify: `aragora/debate/post_debate_coordinator.py` (in `run()` method)
- Test: `tests/debate/test_post_debate_coordinator.py`

- [ ] **Step 1: Write failing test**

```python
def test_post_debate_wires_backbone_when_run_id_present():
    """Coordinator should append stage event when backbone_run_id in metadata."""
    events = []

    class MockRuntime:
        def append_stage_event(self, run_id, stage, **kwargs):
            events.append({"run_id": run_id, "stage": stage, **kwargs})
        def update_run(self, run_id, **kwargs):
            pass

    # ... setup coordinator with mock debate_result containing backbone_run_id
    # ... assert events contains plan_created stage event
```

- [ ] **Step 2: Add backbone wiring**

In `post_debate_coordinator.py`, after plan creation (around line 250), add:

```python
        backbone_run_id = (
            getattr(debate_result, "metadata", {}) or {}
        ).get("backbone_run_id")
        if backbone_run_id and result.plan:
            try:
                from aragora.pipeline.backbone_runtime import BackboneRuntime
                runtime = BackboneRuntime()
                runtime.append_stage_event(
                    backbone_run_id, "plan",
                    status="created",
                    artifact_ref=str(result.plan.get("id", "")),
                )
                runtime.update_run(backbone_run_id, plan_id=str(result.plan.get("id", "")))
            except Exception:
                logger.debug("Backbone wiring skipped for post-debate plan")
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/debate/test_post_debate_coordinator.py -v --timeout=30 -x`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add aragora/debate/post_debate_coordinator.py tests/debate/test_post_debate_coordinator.py
git commit -m "feat(debate): wire post-debate coordinator to backbone ledger"
```

---

### Task 6: Narrow Docker SYS_ADMIN

**Files:**
- Modify: `aragora/computer_use/sandbox.py:177-180`
- Test: `tests/computer_use/test_sandbox.py`

- [ ] **Step 1: Write failing test**

```python
def test_sandbox_does_not_use_sys_admin_by_default():
    """Docker sandbox should not grant SYS_ADMIN unless explicitly configured."""
    config = SandboxConfig()
    # Build the docker command
    provider = DockerSandboxProvider(config)
    cmd = provider._build_docker_command(instance)
    assert "SYS_ADMIN" not in cmd

def test_sandbox_uses_narrower_capabilities():
    config = SandboxConfig()
    provider = DockerSandboxProvider(config)
    cmd = provider._build_docker_command(instance)
    cmd_str = " ".join(cmd)
    assert "DAC_OVERRIDE" in cmd_str
    assert "SYS_PTRACE" in cmd_str
```

- [ ] **Step 2: Replace SYS_ADMIN**

In `sandbox.py`, replace lines 179-180:
```python
                "--cap-add",
                "SYS_ADMIN",
```
With:
```python
                "--cap-add",
                "DAC_OVERRIDE",
                "--cap-add",
                "SYS_PTRACE",
```

- [ ] **Step 3: Add config fallback**

Add to `SandboxConfig`:
```python
    sandbox_use_sys_admin: bool = False  # Only enable if Playwright fails with narrower caps
```

In the docker command building, if `config.sandbox_use_sys_admin`:
```python
            if config.sandbox_use_sys_admin:
                cmd.extend(["--cap-add", "SYS_ADMIN"])
            else:
                cmd.extend(["--cap-add", "DAC_OVERRIDE", "--cap-add", "SYS_PTRACE"])
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/computer_use/test_sandbox.py -v --timeout=30`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add aragora/computer_use/sandbox.py tests/computer_use/test_sandbox.py
git commit -m "fix(security): narrow Docker sandbox from SYS_ADMIN to DAC_OVERRIDE+SYS_PTRACE"
```

---

### Task 7: Redact Token Logging

**Files:**
- Modify: `aragora/live/src/app/(app)/auth/callback/page.tsx:65,70,92`

- [ ] **Step 1: Fix line 65**

Replace:
```typescript
logger.debug('[OAuth Callback] Hash fragment:', tokenString ? `${tokenString.substring(0, 50)}...` : '(empty)');
```
With:
```typescript
logger.debug('[OAuth Callback] Hash fragment present:', !!tokenString);
```

- [ ] **Step 2: Fix line 70**

Replace:
```typescript
logger.debug('[OAuth Callback] Query params fallback:', tokenString ? `${tokenString.substring(0, 50)}...` : '(empty)');
```
With:
```typescript
logger.debug('[OAuth Callback] Query params fallback present:', !!tokenString);
```

- [ ] **Step 3: Fix line 92**

Replace:
```typescript
logger.debug('[OAuth Callback] Calling setTokens with access_token:', accessToken.substring(0, 20) + '...');
```
With:
```typescript
logger.debug('[OAuth Callback] Processing OAuth token pair');
```

- [ ] **Step 4: Commit**

```bash
git add aragora/live/src/app/\(app\)/auth/callback/page.tsx
git commit -m "fix(security): redact token content from OAuth callback logs"
```

---

### Task 8: Split boss_loop.py

**Files:**
- Create: `aragora/swarm/boss_feed.py`
- Create: `aragora/swarm/boss_freshness.py`
- Create: `aragora/swarm/boss_dispatch.py`
- Modify: `aragora/swarm/boss_loop.py` (move code out, add re-exports)
- Test: existing `tests/swarm/test_boss_loop.py` must still pass

- [ ] **Step 1: Extract boss_feed.py**

Move from `boss_loop.py`:
- `GitHubIssue` dataclass
- `GitHubIssueFeed` class
- `sanitize_issue_body_for_dispatch()`
- `_compose_issue_dispatch_goal()`
- `_normalize_dispatch_text()`
- `_normalize_validation_line()`
- `_match_issue_section_prefix()`
- Value ranking helpers

Add re-exports in `boss_loop.py`:
```python
from aragora.swarm.boss_feed import (
    GitHubIssue, GitHubIssueFeed,
    sanitize_issue_body_for_dispatch,
)
```

- [ ] **Step 2: Extract boss_freshness.py**

Move from `boss_loop.py`:
- `RunnerFreshnessResult` dataclass
- `check_runner_freshness()` function
- Runner probe helpers

Add re-exports in `boss_loop.py`.

- [ ] **Step 3: Extract boss_dispatch.py**

Move from `boss_loop.py`:
- `dispatch_bounded_spec()` function
- `run_pre_dispatch_validation_commands()`
- Related helpers

Add re-exports in `boss_loop.py`.

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/swarm/ -v --timeout=60`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add aragora/swarm/boss_feed.py aragora/swarm/boss_freshness.py aragora/swarm/boss_dispatch.py aragora/swarm/boss_loop.py
git commit -m "refactor(swarm): extract boss_feed, boss_freshness, boss_dispatch from boss_loop.py"
```

---

### Task 9: Split worker_launcher.py

**Files:**
- Create: `aragora/swarm/worker_process.py`
- Modify: `aragora/swarm/worker_launcher.py` (move code out, add re-exports)
- Test: existing tests must still pass

- [ ] **Step 1: Extract worker_process.py**

Move from `worker_launcher.py`:
- `WorkerProcess` dataclass
- `LaunchConfig` dataclass
- `SESSION_ARTIFACTS` frozenset
- `_SALVAGEABLE_EXIT_CODES` frozenset
- `DEFAULT_VERIFICATION_TIMEOUT_SECONDS` constant

Add re-exports in `worker_launcher.py`:
```python
from aragora.swarm.worker_process import (
    WorkerProcess, LaunchConfig,
    SESSION_ARTIFACTS, DEFAULT_VERIFICATION_TIMEOUT_SECONDS,
)
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/swarm/test_worker_launcher.py -v --timeout=30`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add aragora/swarm/worker_process.py aragora/swarm/worker_launcher.py
git commit -m "refactor(swarm): extract WorkerProcess and LaunchConfig to worker_process.py"
```

---

### Task 10: Split post_debate_coordinator.py

**Files:**
- Create: `aragora/debate/post_debate_config.py`
- Modify: `aragora/debate/post_debate_coordinator.py` (move code out, add re-exports)
- Test: existing tests must still pass

- [ ] **Step 1: Extract post_debate_config.py**

Move from `post_debate_coordinator.py`:
- `PostDebateConfig` dataclass
- `PostDebateResult` dataclass

Add re-exports in `post_debate_coordinator.py`:
```python
from aragora.debate.post_debate_config import PostDebateConfig, PostDebateResult
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/debate/test_post_debate_coordinator.py -v --timeout=30`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add aragora/debate/post_debate_config.py aragora/debate/post_debate_coordinator.py
git commit -m "refactor(debate): extract PostDebateConfig to separate module"
```

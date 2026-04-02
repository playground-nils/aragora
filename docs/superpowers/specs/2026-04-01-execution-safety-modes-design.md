# Execution Safety Modes Design

**Goal:** Make the codebase as sound as possible while preserving autonomous founder/boss loop operation. Resolve the tension between safety gates and autonomous execution by introducing a single `ExecutionMode` enum that flows through the entire stack.

**Context:** Factory's architecture review rated the repo "unsound" due to 4 cruxes. All 4 are now fixed. The remaining gaps are: (1) Claude Code harness `--yes` bypass, (2) Docker SYS_ADMIN capability, (3) PostDebateCoordinator not wired to backbone, (4) boss loop not wired to backbone, (5) monolith files, (6) token prefix logging.

---

## 1. ExecutionMode Enum

### New file: `aragora/pipeline/execution_mode.py`

```python
from enum import Enum

class ExecutionMode(str, Enum):
    AUTONOMOUS = "autonomous"
    INTERACTIVE = "interactive"
```

**Rules:**
- `AUTONOMOUS` — pre-approved by config. Safety comes from scope limits, merge gates, and the fact that a human explicitly launched the loop. Used by: boss loop, swarm, nomic loop, self-improve scripts.
- `INTERACTIVE` — per-action approval required. Safety comes from capability gates and the backbone ledger. Used by: server API handlers, CLI when a user is present.

**Defaults:**
- `BossLoopConfig.execution_mode` → `AUTONOMOUS`
- `SwarmCommanderConfig.execution_mode` → inherits from caller
- `LaunchConfig.execution_mode` → inherits from commander
- Server API handlers → `INTERACTIVE`
- CLI commands → `INTERACTIVE` (override with `--autonomous` flag)

---

## 2. Claude Code Harness: Conditional `--yes`

### File: `aragora/harnesses/claude_code.py`

**Current problem:** Line 532 unconditionally adds `--yes` (auto-approve file edits).

**Fix:** Add `execution_mode` to the harness config. Only add `--yes` when `AUTONOMOUS`.

```python
# In ClaudeCodeConfig (or equivalent config dataclass):
execution_mode: ExecutionMode = ExecutionMode.AUTONOMOUS

# In execute_implementation():
if self.config.execution_mode == ExecutionMode.AUTONOMOUS:
    cmd.append("--yes")
```

**No capability gate needed in AUTONOMOUS mode** — the caller already authorized the run by launching the boss loop with explicit config.

**In INTERACTIVE mode:** Omit `--yes`. Claude Code will prompt for approval on each file edit, which is correct for human-attended sessions.

---

## 3. LaunchConfig: Wire ExecutionMode

### File: `aragora/swarm/worker_launcher.py`

Add `execution_mode` to `LaunchConfig`:

```python
@dataclass(slots=True)
class LaunchConfig:
    # ... existing fields ...
    execution_mode: ExecutionMode = ExecutionMode.AUTONOMOUS
```

In `_build_agent_command()` for the claude branch, propagate to the harness:
- When building the Claude command, if `execution_mode == INTERACTIVE`, do NOT add `--dangerously-skip-permissions` even if `allow_claude_dangerously_skip_permissions` is True.
- The `allow_*` flags are the "can this run at all" gate. `execution_mode` is the "how much autonomy does it get" gate.

### File: `aragora/swarm/commander.py`

Pass `execution_mode` through `run_supervised_from_spec()` to `LaunchConfig`.

### File: `aragora/swarm/boss_loop.py`

`BossLoopConfig` gets `execution_mode: ExecutionMode = ExecutionMode.AUTONOMOUS`. Passed to `dispatch_bounded_spec()` and down through the commander.

---

## 4. Docker SYS_ADMIN Narrowing

### File: `aragora/computer_use/sandbox.py`

**Current problem:** Line 180 grants `SYS_ADMIN` to Docker containers used for browser automation.

**Fix:** Replace with narrower capabilities:

```python
# Before:
"--cap-drop", "ALL",
"--cap-add", "SYS_ADMIN",

# After:
"--cap-drop", "ALL",
"--cap-add", "DAC_OVERRIDE",   # File permission bypass (Playwright needs this)
"--cap-add", "SYS_PTRACE",     # Process inspection (Chrome DevTools protocol)
```

**Validation:** Run Playwright tests in the container after the change. If mount syscalls fail, add `--cap-add SYS_ADMIN` back behind a `sandbox_privileged: bool = False` config flag.

---

## 5. PostDebateCoordinator Backbone Wiring

### File: `aragora/debate/post_debate_coordinator.py`

**Current problem:** Creates plans and triggers execution with no RunLedger entry.

**Fix:** Add optional backbone wiring that is:
- **Non-blocking** in AUTONOMOUS mode (try/except, log warning on failure)
- **Required** in INTERACTIVE mode (fail-closed if ledger unavailable)

**Insertion point:** In `run()` method, after plan creation:

```python
def run(self, debate_id, debate_result, ...) -> PostDebateResult:
    # ... existing plan creation ...

    # Wire to backbone (if available)
    backbone_run_id = (debate_result.metadata or {}).get("backbone_run_id")
    if backbone_run_id:
        try:
            from aragora.pipeline.backbone_runtime import BackboneRuntime
            runtime = BackboneRuntime()
            runtime.append_stage_event(backbone_run_id, "plan", status="created",
                                       artifact_ref=result.plan.get("id", ""))
        except Exception:
            if self.config.execution_mode == ExecutionMode.INTERACTIVE:
                raise
            logger.debug("Backbone wiring skipped in autonomous mode")

    # ... rest of coordinator ...
```

**Scope:** Only wire the plan-creation and execution-completion stages. Don't wire every internal step (notification, gauntlet, settlement) — those are implementation details, not backbone contract events.

---

## 6. Boss Loop Backbone Wiring

### File: `aragora/swarm/boss_loop.py`

**Current problem:** No RunLedger entries for dispatched work.

**Fix:** Create a lightweight ledger entry per dispatch in `_dispatch_issue()`, around the `dispatch_bounded_spec()` call:

```python
# Before dispatch:
backbone_run_id = None
runtime = None  # Declared at outer scope so post-dispatch block can reference it
try:
    from aragora.pipeline.backbone_runtime import BackboneRuntime
    from aragora.pipeline.backbone_contracts import RunLedger
    runtime = BackboneRuntime()
    ledger = RunLedger(
        run_id=f"boss-{self.run_id}-iter{iteration}-{issue.number}",
        entrypoint="boss_loop",
        status="dispatching",
        metadata={"issue_number": issue.number, "issue_title": issue.title},
    )
    runtime.create_run(ledger)
    backbone_run_id = ledger.run_id
except Exception:
    pass  # Never block autonomous dispatch

# dispatch_bounded_spec(spec, ...) — existing call

# After dispatch:
if backbone_run_id:
    try:
        runtime.update_run(backbone_run_id,
            status="completed" if result.get("status") == "completed" else "failed",
            execution_id=result.get("run_id"),
            receipt_id=result.get("receipt_id"),
        )
    except Exception:
        pass
```

**Key constraint:** All backbone calls are wrapped in try/except. The boss loop NEVER blocks on backbone failures.

---

## 7. Token Logging Redaction

### File: `aragora/live/src/app/(app)/auth/callback/page.tsx`

**Current problem:** Line 65 logs first 50 chars of hash fragment. Line 92 logs first 20 chars of access token.

**Fix:**

```typescript
// Line 65: Replace
logger.debug('[OAuth Callback] Hash fragment:', tokenString ? `${tokenString.substring(0, 50)}...` : '(empty)');
// With:
logger.debug('[OAuth Callback] Hash fragment present:', !!tokenString);

// Line 70: Also fix the query-params fallback branch (same leak):
logger.debug('[OAuth Callback] Query params fragment:', tokenString ? `${tokenString.substring(0, 50)}...` : '(empty)');
// With:
logger.debug('[OAuth Callback] Query params fragment present:', !!tokenString);

// Line 92: Replace
logger.debug('[OAuth Callback] Calling setTokens with access_token:', accessToken.substring(0, 20) + '...');
// With:
logger.debug('[OAuth Callback] Processing OAuth token pair');
```

---

## 8. Monolith File Splits

### 8a. `boss_loop.py` (3104 lines) → 3 extracted files

| New File | What Moves | Approx Lines |
|---|---|---|
| `aragora/swarm/boss_feed.py` | `GitHubIssue`, `GitHubIssueFeed`, value ranking, issue sanitization | ~400 |
| `aragora/swarm/boss_freshness.py` | `check_runner_freshness()`, `RunnerFreshnessResult`, probe helpers | ~300 |
| `aragora/swarm/boss_dispatch.py` | `dispatch_bounded_spec()`, pre-dispatch validation, test discovery | ~400 |

`boss_loop.py` keeps: `BossLoop`, `BossLoopConfig`, `BossLoopResult`, `BossIterationStatus`, main loop logic (~2000 lines). Re-exports extracted symbols for backwards compatibility.

### 8b. `worker_launcher.py` (2154 lines) → 2 extracted files

| New File | What Moves | Approx Lines |
|---|---|---|
| `aragora/swarm/worker_process.py` | `WorkerProcess`, `LaunchConfig` dataclasses, session artifacts | ~150 |
| `aragora/swarm/worker_verification.py` | Verification execution, test running, result collection | ~400 |

`worker_launcher.py` keeps: `WorkerLauncher` class with launch/wait/command-building (~1600 lines).

### 8c. `post_debate_coordinator.py` (2020 lines) → config extraction

| New File | What Moves | Approx Lines |
|---|---|---|
| `aragora/debate/post_debate_config.py` | `PostDebateConfig`, `PostDebateResult` dataclasses | ~150 |

`post_debate_coordinator.py` keeps: coordinator class and all step methods (~1870 lines). Further step extraction is optional and lower priority.

---

## Behavioral Matrix

| Behavior | AUTONOMOUS | INTERACTIVE |
|---|---|---|
| Claude Code `--yes` | Added | Omitted |
| `--dangerously-skip-permissions` | Controlled by `allow_*` flag | Blocked regardless of flag |
| Codex `--full-auto` | Controlled by `allow_*` flag | Blocked regardless of flag |
| Backbone ledger | Async, non-blocking, silent on failure | Required, fail-closed |
| Taint gate | Log warning, proceed | Block execution |
| Merge gate | Always enforced | Always enforced |
| Scope enforcement | Always enforced | Always enforced |
| Receipt generation | Always generated | Always generated |

---

## What Does NOT Change

- Existing `allow_claude_dangerously_skip_permissions` / `allow_codex_full_auto` flags stay
- `ExecutionMode` sits above them as the intent layer, not a replacement
- AUTONOMOUS mode still requires explicit opt-in via config
- Merge gate and scope enforcement are always on regardless of mode
- Receipt generation is always on regardless of mode

---

## Success Criteria

After implementation:
1. Boss loop works identically to today with `execution_mode=AUTONOMOUS`
2. Server API handlers reject dangerous execution unless explicitly approved
3. Every boss loop dispatch creates a backbone ledger entry (async, non-blocking)
4. PostDebateCoordinator wires plan creation to backbone (when backbone_run_id present)
5. Docker containers use narrower capabilities
6. No token content appears in any log output
7. Monolith files are split with backwards-compatible re-exports
8. All existing tests pass

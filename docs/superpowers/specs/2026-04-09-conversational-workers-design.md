# Conversational Workers: Upgrading Swarm Workers from Single-Shot to Multi-Turn

## Problem

Swarm workers currently run `claude -p <prompt>` — one prompt in, one response out, exit. This is fundamentally insufficient for most coding tasks:

- **No exploration**: Worker can't read files, understand context, then decide what to do
- **No iteration**: If the first attempt has a bug, there's no second chance within the session
- **No diagnosis**: Worker can't run tests, see failures, and fix them
- **Massive prompt overhead**: Everything (task, context, constraints, discipline rules) must be crammed into one prompt, consuming tokens on instructions instead of work

Evidence: 3 root issues generated 20+ auto-decomposed children across 60+ failed single-shot attempts. A conversational session fixed all 3 in 5 minutes.

## Vision

A set of vague high-level goals and ideas can be autonomously implemented over long periods by an orchestrated swarm of agents using fixed-cost plans, where the human does not need to intervene — including all evolution/roadmap goals in the Aragora codebase.

## Current Architecture (What Exists)

```
Boss Loop → selects issue → builds prompt → launches worker
  Worker: claude -p "<giant prompt>"  ← ONE SHOT
    → success: commit + receipt
    → failure: repair (another one-shot) × 3
    → exhausted: auto-decompose → smaller issues → retry
```

**What works well and should NOT change:**
- Boss loop issue selection and prioritization
- Worktree isolation per worker
- Receipt/lease tracking
- Merge arbiter + draft promotion pipeline
- Initiative mode for roadmap work
- Session coordination (directives, claims, findings)

**What must change:** The worker primitive — from single-shot to conversational.

## Proposed Architecture

```
Boss Loop → selects issue → builds task file → launches worker session
  Worker Session: claude --task <file> --max-turns 20 --auto-commit
    Turn 1: Read target files + callers + test patterns
    Turn 2: Understand the task in context
    Turn 3: Write the code change
    Turn 4: Run tests
    Turn 5: Fix any failures
    Turn 6: Commit with descriptive message
    → success: commit + receipt
    → failure after max turns: salvage partial work + diagnostic report
```

## Design

### 1. Task File Format

Replace the giant prompt string with a structured YAML task file written to the worktree:

```yaml
# .swarm_task.yaml
task_id: "issue-4105"
title: "Add context to bare raise in visualization exporter"
goal: "Replace bare raise with RuntimeError including install instructions"

# Pre-loaded context (supervisor reads these before dispatch)
context_files:
  - path: "aragora/visualization/exporter.py"
    focus_lines: [165, 175]
    reason: "The bare raise is on line 171"
  - path: "aragora/visualization/exporter.py"
    focus_lines: [259, 277]
    reason: "_get_cache_backend catches ImportError — must also catch RuntimeError after change"

# What callers/consumers look like (auto-discovered by supervisor)
related_code:
  - pattern: "_get_cache_backend"
    found_in: ["aragora/visualization/exporter.py:290", "aragora/visualization/exporter.py:295"]
  - pattern: "RedisCacheBackend"
    found_in: ["aragora/visualization/exporter.py:268"]

# Test patterns from the same directory
test_examples:
  - path: "tests/visualization/test_exporter.py"
    relevant_tests: ["test_redis_import_error_logs_install_instructions_and_falls_back"]

file_scope:
  - "aragora/visualization/exporter.py"
  - "tests/visualization/test_exporter.py"

validation:
  - "python3 -m pytest tests/visualization/test_exporter.py -q"

acceptance:
  - "Bare raise replaced with RuntimeError including pip install instructions"
  - "All existing tests pass"

budget:
  max_turns: 20
  max_time_minutes: 10
```

### 2. Supervisor Context Enrichment

Before dispatching a worker, the supervisor builds the task file by:

1. **Reading the target files** and extracting the relevant lines
2. **Finding callers** via `grep -rn` for functions/classes that will be affected
3. **Finding test patterns** in the corresponding test directory
4. **Including recent git history** for the target files (what changed recently, by whom)

This is the key difference: instead of telling the worker "go figure it out," we hand them the relevant code on a platter.

```python
# In worker_launcher.py, before dispatch:
def _enrich_task_context(work_order: dict, worktree_path: str) -> dict:
    """Read target files and related code to build rich task context."""
    file_scope = work_order.get("file_scope", [])
    context_files = []
    related_code = []

    for file_path in file_scope:
        full_path = Path(worktree_path) / file_path
        if full_path.exists():
            content = full_path.read_text()
            context_files.append({
                "path": file_path,
                "content": content[:5000],  # First 5k chars
                "line_count": len(content.splitlines()),
            })

            # Find functions/classes defined in this file
            for match in re.finditer(r'(?:def|class)\s+(\w+)', content):
                name = match.group(1)
                # Find callers in the codebase
                result = subprocess.run(
                    ["grep", "-rn", name, "aragora/", "--include=*.py", "-l"],
                    capture_output=True, text=True, cwd=worktree_path, timeout=10,
                )
                if result.stdout.strip():
                    related_code.append({
                        "symbol": name,
                        "found_in": result.stdout.strip().splitlines()[:5],
                    })

    work_order["context_files"] = context_files
    work_order["related_code"] = related_code
    return work_order
```

### 3. Worker Session Mode

Replace `claude -p` with interactive mode using `--resume` for crash recovery:

```python
def _build_command(self, agent, prompt, *, worktree_path="", **kwargs):
    if agent == "claude":
        # Write task file to worktree
        task_path = Path(worktree_path) / ".swarm_task.yaml"
        task_path.write_text(yaml.dump(task_data))

        # Use interactive mode with CLAUDE.md task injection
        cmd = [self.config.claude_path]

        # Instead of -p (one-shot), use the task as initial prompt
        # but allow the session to continue for multiple turns
        cmd.extend(["--max-turns", str(task_data.get("budget", {}).get("max_turns", 20))])
        cmd.append("--dangerously-skip-permissions")
        cmd.extend(["-p", prompt])  # Still use -p but with --max-turns

        # Key: --max-turns allows multiple tool calls within a single -p invocation
        # Claude Code's -p mode already supports multi-turn tool use
        # The difference is the prompt quality, not the invocation mode

        return cmd
```

**Important realization:** `claude -p` already supports multi-turn tool use within a single invocation. The model can read files, write code, run tests, and fix failures — all within one `-p` call. The problem isn't the invocation mode, it's:

1. The prompt doesn't tell the worker to explore first
2. No codebase context is pre-loaded
3. The prompt demands "NEVER spend more than 2 minutes reading/exploring" — actively preventing exploration
4. The `--max-turns` default may be too low

### 4. Revised Worker Prompt Strategy

The current prompt says "NEVER spend more than 2 minutes reading/exploring before writing code." This is exactly wrong. Replace with:

```python
WORKER_PROMPT_TEMPLATE = """
# Task: {title}

## Context (pre-loaded by supervisor)

{context_files_formatted}

## Related Code

{related_code_formatted}

## What To Do

{description}

## How To Work

1. READ the context files above carefully. Understand what you're changing and what depends on it.
2. If anything is unclear, use Read/Grep to check the actual code.
3. Write your change.
4. Run the validation commands.
5. If tests fail, read the error, fix it, run again.
6. When tests pass, commit with `git add <files> && git commit -m "fix: ..."`.

## Validation

{validation_commands}

## Constraints

- Only modify files in: {file_scope}
- Commit before exiting — uncommitted work is lost.
- If you're stuck after 3 attempts to fix test failures, commit what you have with an honest message describing what's broken.
"""
```

### 5. Failure Diagnosis Instead of Auto-Decomposition

When a worker fails, instead of blindly decomposing the issue:

```python
async def _handle_worker_failure(self, work_order, worker_result):
    """Diagnose failure and decide: retry with better context, or escalate."""
    stdout = worker_result.get("stdout", "")

    # Classify failure
    if "Permission denied" in stdout or "authentication_error" in stdout:
        return FailureAction.RETRY_WITH_FIX, "auth_failure"

    if "No such file" in stdout or "not found" in stdout:
        # Worker couldn't find the target file — fix the file scope
        actual_files = self._find_actual_files(work_order)
        work_order["file_scope"] = actual_files
        return FailureAction.RETRY_WITH_CONTEXT, "fixed_file_scope"

    if "FAILED" in stdout and "test" in stdout.lower():
        # Tests failed — include the failure output as context for retry
        work_order["prior_attempt"] = {
            "what_was_tried": self._extract_code_changes(stdout),
            "test_failures": self._extract_test_failures(stdout),
        }
        return FailureAction.RETRY_WITH_CONTEXT, "test_failure_context"

    if "assert" in stdout.lower() or "error" in stdout.lower():
        # Generic code error — enrich context and retry once
        return FailureAction.RETRY_WITH_CONTEXT, "enriched_context"

    # Truly stuck — escalate with diagnosis
    return FailureAction.ESCALATE, self._build_diagnosis_report(stdout)
```

### 6. Cost Control

Each worker session has a fixed budget:

```yaml
budget:
  max_turns: 20        # Max tool-use turns within the session
  max_time_minutes: 10  # Wall clock limit
  max_tokens: 50000     # Total input+output token limit
  max_retries: 2        # Max retries with enriched context (not decomposition)
```

Estimated cost per worker session:
- Current (single-shot): ~$0.02-0.05 per attempt, but 3-60 wasted attempts = $0.60-3.00 per issue
- Conversational (20 turns): ~$0.10-0.20 per session, but 1-2 sessions per issue = $0.10-0.40 per issue

**Conversational workers are cheaper** because they succeed more often.

## Implementation Plan

### Phase 1: Context Enrichment (highest impact, lowest risk)

**Keep `claude -p` invocation unchanged.** Just improve what's in the prompt.

Files:
- Modify: `aragora/swarm/worker_launcher.py` — add `_enrich_task_context()`
- Modify: `aragora/swarm/worker_launcher.py` — rewrite `_build_prompt()` to use enriched context

Changes:
1. Before dispatch, read target files and include their content in the prompt
2. Find callers/consumers and include them
3. Find test patterns and include them
4. Remove "NEVER spend more than 2 minutes reading/exploring" — replace with "READ the context above carefully"

**Why this first:** It's the highest ROI change. The invocation mode stays the same, but the prompt goes from "figure it out" to "here's everything you need."

### Phase 2: Failure Diagnosis

Replace auto-decomposition with diagnosis and retry-with-context.

Files:
- Modify: `aragora/swarm/boss_loop.py` — replace decomposition cascade with `_handle_worker_failure()`
- Create: `aragora/swarm/failure_diagnostics.py` — failure classification and context enrichment

Changes:
1. On first failure: read worker stdout, classify the failure, enrich context, retry
2. On second failure: retry with even more context (include the first failure's stdout as "what was tried")
3. On third failure: escalate with a diagnosis report, not a decomposed issue tree

**Why this second:** Prevents the 20+ issue decomposition cascades that waste API calls.

### Phase 3: Worker Session Budget

Add explicit budget controls and `--max-turns` to worker invocations.

Files:
- Modify: `aragora/swarm/worker_launcher.py` — add `--max-turns` to claude command
- Modify: `aragora/swarm/worker_process.py` — add wall-clock timeout enforcement

Changes:
1. Pass `--max-turns 20` to claude (allows multi-turn tool use within single -p)
2. Add per-worker token tracking
3. Add wall-clock timeout (10 min default)

### Phase 4: Task File Format

Formalize the task specification as a YAML file written to the worktree.

Files:
- Create: `aragora/swarm/task_spec.py` — TaskSpec dataclass + builder
- Modify: `aragora/swarm/worker_launcher.py` — write task file, reference it in prompt

Changes:
1. Define TaskSpec schema
2. Build TaskSpec from work order + enriched context
3. Write to `.swarm_task.yaml` in worktree
4. Include in CLAUDE.md or prompt

### Phase 5: Long-Running Goal Execution

Connect the improved workers to initiative mode for roadmap/evolution goals.

Files:
- Modify: `aragora/swarm/initiative_loop.py` — use enriched workers for initiative slices
- Modify: `aragora/swarm/initiative_planner.py` — generate TaskSpecs per slice

Changes:
1. Initiative planner generates TaskSpecs with full context for each slice
2. Initiative executor dispatches workers with enriched context
3. Failure diagnosis feeds back into the initiative's slice dependencies
4. Milestone checkpoints use the worker's diagnostic reports

## Success Criteria

- Workers complete 80%+ of boss-ready issues on first attempt (currently <30%)
- No auto-decomposition cascades (replaced by diagnosis + retry)
- Initiative pilot completes 4+ slices without human intervention
- Cost per resolved issue decreases from ~$1-3 to ~$0.10-0.40
- Evolution/roadmap goals can be expressed as initiatives and make progress overnight

## Out of Scope

- Changing the boss loop issue selection algorithm
- Redesigning the merge arbiter
- Multi-worker collaboration on a single task
- Real-time human-in-the-loop during worker execution

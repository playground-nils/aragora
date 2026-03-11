# Campaign Pipeline Validated — First Successful End-to-End Execution

**Date:** March 10, 2026
**Manifest:** dogfood-6 (prebuilt, 2 projects)
**Outcome:** `campaign_complete`
**Budget spent:** $3.00 / $5.00

## Results

| Project | Status | Outcome | Review | Branch |
|---------|--------|---------|--------|--------|
| proj-001 | completed | deliverable_created | passed | `codex/swarm-a83ea62b-subtask_` |
| proj-002 | completed | deliverable_created | passed | `codex/swarm-a56eac88-subtask_` |

## What was validated

1. **Worker dispatch (Codex)** — produced correct documentation content
2. **Auto-commit** — porcelain path fix (PR #919) enables correct staging
3. **File-scope enforcement** — passes legitimately
4. **Heterogeneous review** — Claude reviewing Codex's work, passes with findings
5. **Sequential dependency chain** — proj-002 waited for proj-001 completion
6. **Campaign completion** — `campaign_complete` stop reason, budget coherent
7. **Receipt emission** — authoritative receipts emitted at terminal transitions

## Deliverables produced

- **proj-001:** `docs/guides/SWARM_DOGFOOD_OPERATOR.md` — 10-line campaign vs
  single-run section (campaign distinction, YAML manifest, dependency ordering)
- **proj-002:** `docs/reference/CLI_REFERENCE.md` — 9-line stop-reason table
  (all 5 stop reasons with descriptions)

## Fixes required to reach this point

| PR | Fix | Impact |
|----|-----|--------|
| #916 | Worker no-deliverable hardening | Auto-push, prompt push instruction, WorkerOutcome enum |
| #917 | Disable nested worktree for campaign workers | Eliminated session script wrapper SIGPIPE vector |
| #918 | Bypass pre-commit hooks + timeout fix | `--no-verify` in auto-commit, `config.timeout_seconds` |
| #919 | Porcelain path truncation fix | Leading-space status lines no longer truncated |

## Additional fixes from this session (not yet merged)

- **B-0 untracked file detection**: `git diff HEAD` misses NEW files. Fix:
  always fall back to `git status --porcelain` for all clean-exit workers,
  not just SIGPIPE exits.
- **Receipt emission**: `_emit_receipt()` on `CampaignExecutor` writes
  authoritative YAML receipts at terminal transitions (completed, failed,
  blocked, skipped). 34 tests.

## Commands used

```bash
# Campaign execution (from dogfood-6 worktree)
python -m aragora.cli.main swarm campaign run --manifest .aragora/campaign_manifest.yaml --json

# Proof task (from this worktree — failed on retry exhaustion, B-0 fix not applied in time)
python -m aragora.cli.main swarm campaign run --manifest docs/plans/phase0a_proof_manifest.yaml
```

## Baseline rollout shape

The validated campaign path is:
1. Prebuilt YAML manifest with `max_parallel_ready_projects: 1`
2. Worker model: `codex`, Review model: `claude`
3. `use_managed_session_script: false` (direct subprocess, no shell wrapper)
4. Sequential dependency gating via `dependencies` list
5. Heterogeneous cross-model review
6. Budget and time limit enforcement
7. Authoritative receipt emission at terminal transitions

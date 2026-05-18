# Worktree Value Inventory Status

Last updated: 2026-05-18T05:10:14Z

This repo-tracked status surface captures the most recent run of `scripts/codex_worktree_value_inventory.py` against the canonical and legacy Aragora worktree roots, classifying each checkout as preserve / harvest_candidate / cleanup_candidate.

## Summary

- Source inventory: `/private/tmp/v9_inv.json`
- Base ref: `origin/main`
- Roots: `/Users/armand/Development/aragora/.worktrees/codex-auto`
- Total candidates: `56`
- Active sessions: `12`
- Registered worktrees: `41`
- Candidates with open PR: `0`
- Dirty checkouts: `2`

## Classifications

- `active_or_dirty`: 14
- `no_git_cache_residue`: 3
- `patch_equivalent_or_merged`: 4
- `receipt_protected`: 1
- `unique_unharvested`: 34

## Decisions

- `cleanup_candidate`: 7
- `harvest_candidate`: 34
- `preserve`: 15

## Harvest Candidates

| Path | Branch | Classification | Ahead | Behind | Dirty | Active |
| --- | --- | --- | --- | --- | --- | --- |
| `ragora/.worktrees/codex-auto/claude-20260517-055957-e394d5d3` | `droid/phase2-worktree-value-inventory-20260516v2` | `unique_unharvested` | 1 | 27 | no | no |
| `ragora/.worktrees/codex-auto/claude-20260517-060809-e5b4ee1c` | `droid/phase3-list-active-agent-sessions-20260516` | `unique_unharvested` | 2 | 27 | no | no |
| `ragora/.worktrees/codex-auto/claude-20260517-062140-26e58382` | `droid/phase4-publication-freshness-probe-20260516` | `unique_unharvested` | 2 | 17 | no | no |
| `ragora/.worktrees/codex-auto/claude-20260517-144653-9da7e596` | `droid/phase3-lane-registry-integration-20260517` | `unique_unharvested` | 4 | 17 | no | no |
| `ragora/.worktrees/codex-auto/claude-20260517-145705-fb0a272d` | `droid/phase4-freshness-launchagent-20260517` | `unique_unharvested` | 4 | 25 | no | no |
| `ragora/.worktrees/codex-auto/claude-20260517-165018-00bb191c` | `worktree-packets-keyboard-throughput-20260517` | `unique_unharvested` | 3 | 22 | no | no |
| `ragora/.worktrees/codex-auto/claude-20260518-041625-69149fbf` | `claude/P24-canonical-test-definitions-count-drift-20260518-041606` | `unique_unharvested` | 1 | 3 | no | no |
| `ragora/.worktrees/codex-auto/claude-20260518-043718-a1054f6f` | `claude/P28-A-identify-lane-owner-20260518-043722` | `unique_unharvested` | 1 | 3 | no | no |
| `aragora/.worktrees/codex-auto/codex-20260516-184833-3348d471` | `codex/review-pr-advisory-hardening` | `unique_unharvested` | 1 | 41 | no | no |
| `aragora/.worktrees/codex-auto/codex-20260517-185017-9874a26b` | `codex/codex-20260517-185017-9874a26b` | `unique_unharvested` | 3 | 12 | no | no |
| `aragora/.worktrees/codex-auto/droid-20260517-204819-018cc17d` | `droid/P02-freshness-probe-rerun-20260517-204809` | `unique_unharvested` | 2 | 11 | no | no |
| `aragora/.worktrees/codex-auto/droid-20260518-002344-c62e03f6` | `droid/P16-stage2-auto-merge-bucket-a-20260518-002325` | `unique_unharvested` | 10 | 3 | no | no |
| `aragora/.worktrees/codex-auto/droid-20260518-015653-1486bdb7` | `droid/P17-stage3-triage-bucket-c-batcher-20260518-015641` | `unique_unharvested` | 1 | 4 | no | no |
| `aragora/.worktrees/codex-auto/droid-20260518-041442-0e8aade8` | `droid/P20-model-pins-frontier-aligned-20260518-041438` | `unique_unharvested` | 1 | 3 | no | no |
| `ees/codex-auto/harvest-github-cli-health-unused-sys-20260516` | `codex/harvest-github-cli-health-unused-sys-20260516` | `unique_unharvested` | 1 | 41 | no | no |
| `agora/.worktrees/codex-auto/harvest-metrics-refresh-20260516` | `codex/harvest-metrics-refresh-20260516` | `unique_unharvested` | 1 | 35 | no | no |
| `ees/codex-auto/harvest-preflight-rescue-guard-tests-20260516` | `codex/harvest-preflight-rescue-guard-tests-20260516` | `unique_unharvested` | 2 | 41 | no | no |
| `lopment/aragora/.worktrees/codex-auto/swarm-3844d54a-micro-1` | `codex/swarm-3844d54a-micro-1` | `unique_unharvested` | 1 | 41 | no | no |
| `lopment/aragora/.worktrees/codex-auto/swarm-3844d54a-micro-2` | `codex/swarm-3844d54a-micro-2` | `unique_unharvested` | 1 | 41 | no | no |
| `lopment/aragora/.worktrees/codex-auto/swarm-3844d54a-micro-3` | `codex/swarm-3844d54a-micro-3` | `unique_unharvested` | 2 | 41 | no | no |
| `lopment/aragora/.worktrees/codex-auto/swarm-3844d54a-micro-4` | `codex/swarm-3844d54a-micro-4` | `unique_unharvested` | 3 | 41 | no | no |
| `lopment/aragora/.worktrees/codex-auto/swarm-5a555597-micro-1` | `codex/swarm-5a555597-micro-1` | `unique_unharvested` | 1 | 44 | no | no |
| `lopment/aragora/.worktrees/codex-auto/swarm-5a555597-micro-2` | `codex/swarm-5a555597-micro-2` | `unique_unharvested` | 1 | 44 | no | no |
| `lopment/aragora/.worktrees/codex-auto/swarm-5a555597-micro-4` | `codex/swarm-5a555597-micro-4` | `unique_unharvested` | 2 | 43 | no | no |
| `lopment/aragora/.worktrees/codex-auto/swarm-5a555597-micro-5` | `codex/swarm-5a555597-micro-5` | `unique_unharvested` | 3 | 43 | no | no |

*Truncated: 9 additional rows omitted.*

## Cleanup Candidates

| Path | Branch | Classification | Ahead | Behind | Dirty | Active |
| --- | --- | --- | --- | --- | --- | --- |
| `ragora/.worktrees/codex-auto/claude-20260501-195315-89c3c0ad` | `-` | `no_git_cache_residue` | - | - | no | no |
| `ragora/.worktrees/codex-auto/claude-20260517-143423-4810eda2` | `droid/phase1-b0-refresh-20260517` | `patch_equivalent_or_merged` | 1 | 27 | no | no |
| `ragora/.worktrees/codex-auto/claude-20260517-144003-b211740c` | `droid/phase2-auth-failure-fixture-20260517` | `patch_equivalent_or_merged` | 1 | 26 | no | no |
| `ragora/.worktrees/codex-auto/claude-20260517-171434-066430b1` | `worktree-operator-decisions-ingestion-20260517` | `patch_equivalent_or_merged` | 8 | 17 | no | no |
| `ragora/.worktrees/codex-auto/claude-20260517-174858-47953d00` | `worktree-operator-delegation-policy-20260517` | `patch_equivalent_or_merged` | 2 | 16 | no | no |
| `aragora/.worktrees/codex-auto/codex-20260422-194119-a5c0dd59` | `-` | `no_git_cache_residue` | - | - | no | no |
| `ent/aragora/.worktrees/codex-auto/rbac-health-fix-20260413-1` | `-` | `no_git_cache_residue` | - | - | no | no |

## Preserved (active or dirty)

| Path | Branch | Classification | Ahead | Behind | Dirty | Active |
| --- | --- | --- | --- | --- | --- | --- |
| `ragora/.worktrees/codex-auto/claude-20260430-041011-3b22a0f5` | `-` | `active_or_dirty` | - | - | no | yes |
| `ragora/.worktrees/codex-auto/claude-20260430-042801-d58ae59e` | `-` | `active_or_dirty` | - | - | no | yes |
| `ragora/.worktrees/codex-auto/claude-20260430-044410-204ba6b3` | `-` | `active_or_dirty` | - | - | no | yes |
| `ragora/.worktrees/codex-auto/claude-20260430-125421-513d6f8d` | `-` | `active_or_dirty` | - | - | no | yes |
| `ragora/.worktrees/codex-auto/claude-20260430-132040-05232470` | `-` | `active_or_dirty` | - | - | no | yes |
| `ragora/.worktrees/codex-auto/claude-20260430-132610-4446bddf` | `-` | `active_or_dirty` | - | - | no | yes |
| `ragora/.worktrees/codex-auto/claude-20260501-174558-6eed6d67` | `-` | `active_or_dirty` | - | - | no | yes |
| `ragora/.worktrees/codex-auto/claude-20260501-230411-bc06dedc` | `-` | `active_or_dirty` | - | - | no | yes |
| `ragora/.worktrees/codex-auto/claude-20260503-144747-b1c1b5ad` | `-` | `active_or_dirty` | - | - | no | yes |
| `ragora/.worktrees/codex-auto/claude-20260503-150130-e21247fc` | `-` | `active_or_dirty` | - | - | no | yes |
| `ragora/.worktrees/codex-auto/claude-20260507-171638-9eaae229` | `-` | `active_or_dirty` | - | - | no | yes |
| `ragora/.worktrees/codex-auto/claude-20260517-180111-e41d43ca` | `worktree-triage-classifier-20260517` | `active_or_dirty` | 4 | 16 | yes | no |
| `aragora/.worktrees/codex-auto/codex-20260515-152237-14d11f01` | `-` | `active_or_dirty` | - | - | no | yes |
| `aragora/.worktrees/codex-auto/droid-20260517-231527-ce5c3b15` | `droid/P13a-canonical-km-adapter-count-drift-20260517-231510` | `active_or_dirty` | 2 | 7 | yes | no |
| `lopment/aragora/.worktrees/codex-auto/swarm-5a555597-micro-3` | `codex/swarm-5a555597-micro-3` | `receipt_protected` | 1 | 43 | no | no |

## Provenance

- Generator: `scripts/codex_worktree_value_inventory.py` (see PR #7250 for canonical+legacy smart roots; PR #7253/#7254 for managed-session lookup and foreign-worktree preservation).
- Publisher: `scripts/publish_worktree_value_inventory.py` (this file). Read-only; never deletes worktrees or branches.

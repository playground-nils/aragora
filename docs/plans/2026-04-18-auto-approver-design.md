# Auto-approver for safe automation PRs

**Date:** 2026-04-18
**Owner:** automation platform
**Status:** dry-run (phase 1)
**Related PR:** `feature/github-app-auto-approver`

## Problem

Every PR in `synaptent/aragora` requires a review approval before auto-merge
fires. All automations (Codex autopilots, droid missions, Claude Code) author
PRs under `an0mium` and therefore cannot self-approve. The human founder has
been using `gh pr merge --admin` to bypass the review gate, which works but
skips the safety net. Without an automated approver, the merge-arbiter drains
zero PRs autonomously — review is the load-bearing bottleneck.

## Solution

A new cron-style script `scripts/auto_approve_safe_prs.py` uses the
`aragora-automation` GitHub App (App ID `3328101`, installation
`122689816`) to submit `APPROVE` reviews on PRs that satisfy **every** gate in
a conservative allowlist. The App has `pull_requests: write` granted
(verified at mission start via `GET /app/installations/:id`).

### Approval criteria (ALL must pass)

| # | Gate | Rationale |
|---|------|-----------|
| 1 | PR is `OPEN` and `MERGEABLE` (not conflicting, not blocked) | Don't approve PRs with conflicts or failing required checks. |
| 2 | PR is not a draft | Drafts opt out of auto-merge. |
| 3 | Author in allowlist (`an0mium`, `factory-droid[bot]`, `codex-bot`, ...) | Scope to automation accounts only. |
| 4 | PR carries at least one opt-in label (`autonomous`, `codex-automation`, `droid-generated`, `auto-approve`) | Explicit consent per-PR. |
| 5 | ALL CI checks have `conclusion: SUCCESS` | No pending, failed, cancelled runs. |
| 6 | No protected paths touched | CLAUDE.md, `aragora/__init__.py`, `.env*`, `.github/workflows/*`, `scripts/baselines/*`, `*private-key*`, `*secrets*`, `scripts/nomic_loop.py`. |
| 7 | Diff under LOC threshold (default **5000** additions+deletions) | Large refactors need human review. |
| 8 | Not already approved for same head SHA by the App (idempotent) | Don't spam. Re-approves when head SHA changes. |

### Self-approval protection

Gate 0 (checked before all others): if the PR author is
`aragora-automation[bot]`, we refuse — prevents any future scenario where the
App opens its own PRs and approves them.

## Safety layer

| Feature | Mechanism | Operator action |
|---------|-----------|-----------------|
| Dry-run | Default. Requires `~/.aragora/auto_approver.live` to submit reviews. | `scripts/auto_approver_activate.sh on` to go live. |
| Kill switch | `~/.aragora/auto_approver.disabled` (exit 0 without action). | `touch ~/.aragora/auto_approver.disabled` to pause. |
| Rate limit | Max 10 approvals/hour via `~/.aragora/auto_approver_rate.json`. | `--rate-limit-per-hour N` to tune. |
| Audit log | `~/.aragora/auto_approver_audit.jsonl`, one JSON line per decision. | `tail -f` to watch in real time. |
| Idempotency | Lists prior reviews; skips when App approved current head SHA. | Re-approves automatically when head SHA changes. |
| Allowlists | Authors, labels, and protected paths all opt-in. | `--allowed-author`, `--optin-label` to override. |

## Deployment

`launchd` agent at `scripts/launchd/com.aragora.auto-approver.plist`, scheduled every 5
minutes. Logs consolidated at `~/.aragora/auto-approver-launchd.log`.

```bash
cp scripts/launchd/com.aragora.auto-approver.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.aragora.auto-approver.plist
```

On first load it runs in DRY-RUN mode. Decisions are logged but no reviews are
submitted. Operator verifies the `auto_approver_audit.jsonl` stream for 2+
hours and at least one full cycle of open PRs before flipping to live:

```bash
scripts/auto_approver_activate.sh on      # create ~/.aragora/auto_approver.live
scripts/auto_approver_activate.sh status  # confirm
```

## Rollback / emergency

If the approver approves something bad:

1. **Immediate pause:** `touch ~/.aragora/auto_approver.disabled`. The next
   invocation (within 5 min) exits without action.
2. **Dismiss the review:** `gh pr review <number> -R synaptent/aragora --request-changes`
   (or via the UI).
3. **Revert merged change:** `gh pr revert <number>` if the merge already fired.
4. **Audit:** `grep '"number": <number>' ~/.aragora/auto_approver_audit.jsonl` shows the
   exact gate-pass reasoning plus the head SHA at approval time.
5. **Tighten gates:** shrink the label allowlist, lower `--max-diff-loc`, or
   add the offending path to `PROTECTED_PATH_PATTERNS`.

## Expected velocity impact

Pre-approver: zero auto-approvals. Every merge blocks on human review.

Post-approver (dry-run): zero behavior change, full audit trail of
*would-have-approved* PRs. Operator uses this window to calibrate gates.

Post-approver (live): automation-labeled PRs with all-green CI and no protected
paths auto-approve within ~5 min. Combined with the existing merge-arbiter,
this removes the single biggest human gate on the autonomous pipeline while
keeping allowlist-scoped risk and the kill switch as an immediate off-switch.

## Known follow-ups

- Shrink dry-run window after first verification cycle.
- Consider expanding `DEFAULT_OPTIN_LABELS` once first wave proves stable.
- Consider a SLO alert if `approvals_in_window` regularly exceeds 70% of quota.
- Consider cross-linking to `scripts/merge_codex_automation_prs.py` so the same
  safety signals feed both the approver and the merge-arbiter.

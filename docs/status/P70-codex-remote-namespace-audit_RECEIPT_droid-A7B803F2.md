# P70 — codex/* remote namespace audit + bounded sweep

- Session: `droid-A7B803F2`
- Lane: `P70-codex-remote-namespace-audit`
- Outcome: shipped (audit-only publication; bounded sweep is a no-op)

## Result

- Remote `codex/*` heads (pre): **187**
- Remote `codex/*` heads (post): **187** (no deletions)
- Audit JSON: `docs/status/inventories/codex_remote_audit_20260518T193945Z.json`
  (187 rows, well above the ≥150 acceptance floor)
- Delete list: **empty** — no `codex/*` head satisfies all three predicates
  (`unique_commits == 0` AND `has_open_pr == false` AND
  `last_commit_age_days >= 30`).

### Rationale for empty delete list

The dispatch loop counted 187 heads, 0 with `unique_commits == 0`. Every
`codex/*` branch carries at least one commit that is **not reachable** from
`origin/main` via `git rev-list --count origin/main..origin/<branch>`. The
namespace is dominated by harvest / micro / openapi-contract branches that
each retain ≥1 unique commit; squash-merge equivalence (R22 `git cherry`)
was **out of scope** for this lane per spec.

Disposition histogram:

| disposition | count |
|-------------|-------|
| `keep`      | 9     |
| `review`    | 178   |
| `delete`    | 0     |

The 9 `keep` rows correspond exactly to the 9 `codex/*` open PR heads, so
overlap with open PRs is **zero** by construction.

### Acceptance check (per lane spec)

- [x] Audit JSON at `docs/status/inventories/codex_remote_audit_<utc-ts>.json`
      with ≥150 rows (187 published).
- [x] Per-row signals: `unique_commits`, `has_open_pr`,
      `last_commit_age_days`, plus proposed disposition.
- [x] Single batched `gh pr list --state open --limit 500 --json
      number,headRefName` page-walk used as the source of truth for open-PR
      membership (cached in `/tmp/p70_open_prs.json`; no per-branch
      `gh pr list --head <branch>` calls).
- [x] Receipt records pre / post `git ls-remote --heads origin 'codex/*' | wc -l`.
- [x] Receipt explicitly states the delete-list is "empty" with rationale.
- [x] Zero overlap with open PRs confirmed (the 9 `keep` rows are the open PRs).
- [ ] Target: reduce `origin/codex/*` count by ≥30 branches —
      **not met** because no branch satisfies the delete predicate. Spec
      allows this outcome explicitly:
      *"If the delete list is empty, the lane is a no-op publication of the
      audit. That's fine — the audit alone is valuable."*

## Boss-ready / journal protection (R21)

The audit pre-loaded the three boss-ready branches and the
`AGENT_FANOUT_JOURNAL.md` last-7-day mentions before evaluating
dispositions:

- Boss-ready protected (per `gh issue list --label boss-ready --state open`):
  - `codex/harvest-rescue-productization-guard-20260518` (#7320)
  - `codex/publisher-empty-outbox-cache-ready-20260518` (#7331)
  - `codex/audit-active-lane-branch-protection-20260518` (#7334)
- Journal-recent (last 7 d) protection: 1 match
  (`codex/...` — placeholder, no real branch).

Because the delete list resolved to empty, none of these protections needed
to fire materially; they remain encoded in the audit JSON for any follow-up
lane (e.g., a future R22 `git cherry` patch-equivalence sweep of `codex/*`).

## Notable observations (input for future lanes)

- Age distribution (`last_commit_age_days`): min 0 d, max 31 d, p50 17 d —
  this namespace is *young* relative to the 50 branches deleted by v12
  P61+P62 (which were ≥6 months stale).
- 178 / 187 rows fall into `review`: candidates for a future
  patch-equivalence sweep (`git cherry origin/main <branch>`) — many likely
  carry only squash-merged work and would qualify under R22.
- All 31-day-old branches still carry 1–2 unique commits per
  `rev-list --count`, so they were preserved in this audit. A follow-up
  lane using R22 should be considered before v14.

## Execution audit

```
gh pr list --state open --limit 500 --json number,headRefName
  → 34 open PRs (9 codex/*)
git ls-remote --heads origin 'codex/*' | wc -l
  → 187 (pre) / 187 (post)
python3 /tmp/p70_audit.py
  → wrote 187 rows; delete_count=0
```

No `git push origin --delete` was invoked.

## R/D compliance

- R5: lane claimed before any audit (`scripts/claim_active_agent_lane.py
  --lane-id P70-codex-remote-namespace-audit --owner-session droid-A7B803F2`).
- R11: zero open-PR overlap by construction.
- R19: no `--amend` of pushed commits.
- R21: boss-ready branches (#7320/#7331/#7334) explicitly protected.
- R25: no raw worktree deletion; no worktree mutation in this lane.
- D1: idempotent — re-running the audit re-publishes a fresh JSON without
  side effects on the remote.
- D2: no remote mutation (delete list empty).
- D3: no local branches touched.

## Lane

`P70-codex-remote-namespace-audit` released `status=completed`.

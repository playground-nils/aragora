# Six-Week Founder Operating Plan

Last updated: 2026-03-25
Window: March 25, 2026 to May 5, 2026
Owner: Founder

## Purpose

Use the next six weeks to answer one practical question: does Aragora have a
repeatable founder-led wedge that is painful enough to keep using and credible
enough to sell?

This is an operating plan, not a feature wishlist.

If a task does not improve one of these three things, it is out of scope for
this window:

1. daily inbox trust-wedge use
2. repeatable live demo readiness
3. first design-partner pull

## Starting Point On March 25, 2026

- The live founder loop is proven repeatable: 5/5 runs, 35-62s, all acceptance
  items pass.
- Receipts persist to the receipt store and are visible via API, dashboard, and
  share-link surfaces.
- `aragora spec` runs end-to-end in about 23 seconds.
- The inbox trust wedge CLI is dogfood-ready, but not yet proven in daily live
  use.
- The commercial blocker is not missing quarter-scale infrastructure. It is the
  absence of daily-use proof and repeatable partner-facing evidence.

## Hard Decisions

- One daily-use wedge: the Gmail inbox trust wedge.
- One external proof path: the quickstart receipt demo plus inbox proof.
- One commercial goal: start one weekly design-partner pilot that reaches a
  first receipt.
- No second product track unless it directly unblocks those outcomes.

## Outcomes Required By Tuesday, May 5, 2026

| Outcome | Concrete result | Evidence |
|---|---|---|
| Daily-use wedge proof | Founder runs the inbox wedge on 10 business days, processes at least 50 real emails, keeps `100%` receipt-before-action, keeps reply/send/forward at `0`, keeps average cost at or below `$0.20`, keeps average latency at or below `30s`, keeps override rate at or below `30%`, and achieves at least `90%` important-email recall on the first labeled slice. | Receipt logs, cost/latency log, labeled evaluation slice, override counts |
| Repeatable demo pack | One 7-minute live demo script is frozen, one seeded demo setup exists, setup can be completed from a clean checklist in under 10 minutes, three clean rehearsals are completed, and one short receipt-backed case study is drafted from founder dogfood. | Demo script, runbook, rehearsal notes, case study draft |
| First partner pull | 15 named target accounts are shortlisted, 5 discovery calls are completed, 3 live demos are run on real artifacts, 2 prospects score at least `65` on the PMF scorecard, and 1 design partner starts a weekly pilot that reaches a first receipt. | Target list, call notes, PMF scorecards, pilot receipt |

## Weekly Sequence

### Week 1: March 25-31, 2026

Goal: make the founder inbox loop measurable.

Tasks:
- complete Gmail auth, signing, and receipt verification setup
- verify there is no demo fallback in the live inbox path
- create the first labeled evaluation slice of 25 messages
- run 5 manual-review founder sessions with auto-approve off
- fix only receipt, cost, latency, or obvious classification blockers

Exit criteria:
- first 15-25 emails are processed with persisted receipts
- a metrics log exists for cost, latency, overrides, and important-email misses

### Week 2: April 1-7, 2026

Goal: make the inbox loop safe enough to repeat.

Tasks:
- run 5 more founder sessions and reach 50 processed emails cumulative
- reduce prompt/model complexity until the operating thresholds are within reach
- keep allowed actions narrow: `ARCHIVE`, `STAR`, `LABEL`, `IGNORE`
- if hard gates hold, enable auto-approve only for `ARCHIVE` and `IGNORE`

Exit criteria:
- `100%` receipt-before-action still holds
- no silent fallback exists in the wedge path
- a written decision exists on whether auto-approve stays on, stays off, or is
  limited to specific actions

### Week 3: April 8-14, 2026

Goal: freeze the story that will be shown externally.

Tasks:
- produce the 7-minute demo script
- prepare the seeded demo inbox or artifact set
- draft one short case study from founder dogfood evidence
- complete 3 clean rehearsals with no local debugging during the demo

Exit criteria:
- the demo runs from a checklist in under 10 minutes of setup
- the case study has one clear before/after claim supported by receipts

### Week 4: April 15-21, 2026

Goal: qualify prospects against the actual wedge, not the full vision deck.

Tasks:
- narrow to 15 named accounts across two best-fit segments
- run 2-3 discovery calls
- map each prospect to one bounded workflow only
- continue 3 founder inbox sessions so daily-use proof stays live

Exit criteria:
- the top 5 prospects are ranked by fit
- PMF scorecards are opened for the best prospects

### Week 5: April 22-28, 2026

Goal: run live demos on real artifacts.

Tasks:
- complete 3 live demos
- score every prospect immediately after the session
- fix only blockers that prevented the demo or prevented a first receipt
- stop pitching any surface that was not shown live

Exit criteria:
- at least 2 prospects score `>=65`
- the top objections are written down as either product blockers or ICP
  mismatches

### Week 6: April 29-May 5, 2026

Goal: start one pilot and decide what to cut.

Tasks:
- get 1 partner to first receipt on a weekly workflow
- review metrics across inbox proof, demo readiness, and partner pull
- write the next six-week plan from measured evidence
- explicitly kill or defer anything that did not help the wedge

Exit criteria:
- 1 weekly pilot is active, or the exact blocker is documented truthfully
- there is a scale, iterate, or narrow decision for each proof surface

## Founder Weekly Cadence

- Monday: review the previous week's metrics and choose one product blocker plus
  one commercial objective for the week.
- Tuesday and Wednesday: dogfood the inbox wedge and land only blocking fixes.
- Thursday: run discovery calls or live demos.
- Friday: update PMF scorecards, case-study notes, and the next bounded issue
  tranche.

Time budget:
- 2 days per week on dogfood plus blocker removal
- 2 days per week on calls, demos, and follow-up
- 1 day per week on evidence packaging and next-step planning

## Scoreboard

Track these every Friday:

| Metric | Target by May 5, 2026 |
|---|---|
| Founder inbox sessions completed | 10 business days |
| Real emails processed | `>=50` |
| Executed actions with persisted receipts | `100%` |
| Reply/send/forward actions | `0` |
| Average cost per email | `<= $0.20` |
| Average latency per email | `<= 30s` |
| Override rate | `<= 30%` |
| Important-email recall on labeled slice | `>= 90%` |
| Clean demo rehearsals | `>=3` |
| Completed discovery calls | `>=5` |
| Completed live demos | `>=3` |
| Prospects scored `>=65` | `>=2` |
| Weekly pilots with first receipt | `>=1` |

## Explicit Non-Goals Through May 5, 2026

- no broad connector expansion beyond Gmail
- no reply, forward, or send autonomy
- no pentest or SOC 2 kickoff
- no marketplace, on-chain identity, or horizontal-scale work
- no new workbench/canvas program unless it directly improves the demo or pilot
- no generic "43 agents / 45 adapters" positioning as the sales story

## Kill And Pause Rules

- If any inbox action executes without a previously persisted valid receipt,
  stop the rollout immediately.
- If a critical email is missed in live use or on the labeled slice, keep the
  wedge in human-review mode until recall recovers.
- If override rate remains above `30%` after Week 2, disable auto-approve and
  treat the wedge as not yet safe for routine use.
- If the demo still needs code surgery or local debugging after April 14, 2026,
  postpone external outreach until the demo path is stable.
- If no prospect scores at least `65` by May 5, 2026, narrow the ICP or wedge
  before spending time on enterprise assurance or broader platform work.

## What Counts As Success

Success at the end of this window is not "more shipped features." Success is:

- the founder would miss the inbox wedge if it disappeared
- at least one external prospect has seen a real receipt on a real workflow
- the next plan is derived from repeatability and partner pull, not optimism

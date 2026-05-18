# Agent Fan-out Journal

Append-only ledger of autonomous agent sessions running the v2 (and later) idempotent fan-out prompt. One row per session, written by the session itself at Phase 4 receipt time. Read this file first when starting a new fan-out session to avoid duplicating recently completed work.

Columns: `timestamp_utc | session_id | agent_family | phase_id | pr_number | outcome`

`outcome` ∈ {`shipped`, `finish-existing`, `deferred`, `no-work`, `conflict`}

---

2026-05-17T16:56:00Z | droid-DC5A5821 | droid | P03-lane-registry-claim-helper-rebase | 7267 | finish-existing

2026-05-17T17:23:00Z | droid-A5312D6A | droid | P05-publication-freshness-probe-rebase | 7261 | finish-existing
2026-05-17T17:23:00Z | droid-A5312D6A | prompt-bug: v3 heredoc shim '/tmp/fanout_claim.py <<PYEOF ... PYEOF' still hangs in test shell; v4 must ship shim as tracked scripts/ file (see P12 deferral)
2026-05-17T20:53:00Z | droid-6916BE6B | droid | P02-freshness-probe-rerun | 7287 | shipped
2026-05-17T20:53:00Z | droid-6916BE6B | prompt-bug: v4 lists scripts/triage_open_prs.py as required observer but doesn't say what to do when it isn't yet on main (it's still in PR #7285); fell back to manual bucket classification against OPERATOR_DELEGATION_POLICY.md
2026-05-17T23:25:00Z | droid-826081D8 | droid | P13a-canonical-km-adapter-count-drift | 7289 | shipped
2026-05-17T23:25:00Z | droid-826081D8 | prompt-bug: v5 lists scripts/detect_active_lane_collisions.py as a required observer; that script does not exist on main — collision detection landed in scripts/agent_bridge.py health (#7288). v6 should reference agent_bridge.py health instead.
2026-05-18T02:21:00Z | droid-F46C5B20 | droid | P17-stage3-triage-bucket-c-batcher | 7294 | shipped
2026-05-18T02:21:00Z | droid-F46C5B20 | note: v7 prompt was the cleanest iteration yet — no required-observer drift, no hung-shim issues, no missing-flag issues. Two minor v8 polish items: (a) canonicalize the y-advance label name (rollout doc says "label + ready + comment" but doesn't pin a name; v7 P17 shipped without the label step to avoid creating a phantom label), and (b) decide whether to keep YAML-as-JSON-superset response files or add an opt-in PyYAML loader.
2026-05-18T04:33:00Z | droid-F473CDBF | droid | P20-model-pins-frontier-aligned | 7306 | shipped
2026-05-18T04:33:00Z | droid-F473CDBF | note: v8 prompt was clean to execute (no hard prompt-bugs). Two minor accuracy notes for v9: (a) v8 ack list said model_pins.frontier_aligned was no longer failing; it WAS still failing — P20 closed it. (b) v8 P23 (km_adapters drift) was already fixed by #7289 P13a; canonical-metrics receipt shows it passes. v9 should refresh both facts from the live canonical-metrics receipt at prompt-publication time, and clarify P19's "owner detection" since `gh pr view --json author` returns the operator's GitHub login (an0mium) for any PR opened via `gh` on the operator's machine — lane ownership lives in the **branch name prefix**, not the author field.

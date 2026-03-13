# Campaign Receipt Enforcement

This note documents how `CampaignExecutor` in `aragora/swarm/campaign.py`
enforces receipt persistence as part of project finalization.

## Terminal Triggers

The executor emits a receipt only when a project reaches a terminal status:

- `completed`
- `failed`
- `blocked`
- `skipped`

Non-terminal states such as `pending`, `ready`, `active`, and
`needs_revision` do not emit receipts.

## Enforced Code Paths

Three code paths call `_emit_receipt()` when a project becomes terminal:

1. `_apply_dispatch_result()` after dispatch classification drives a project to
   `completed`, `failed`, or `blocked`.
2. `_apply_review_result()` when review leaves the project in a terminal state,
   which in practice is `completed` or `blocked`.
3. `_ready_projects()` when retry exhaustion converts a project to `skipped`.

These paths make receipt creation part of the transition itself rather than a
best-effort follow-up step.

## Storage Path Pattern

Authoritative receipts are written atomically to:

```text
docs/receipts/<campaign_id>/<project_id>.yaml
```

Example:

```text
docs/receipts/phase0a-bootstrap-governance/phase0a-001.yaml
```

`_emit_receipt()` creates the campaign directory, writes
`<project_id>.yaml.tmp`, and replaces it with the final YAML path.

## Authoritative Receipts vs Audit Notes

An authoritative receipt is emitted by the campaign executor at terminal
transition time. That file is the execution record used by the exit gate.

An audit note is a backfilled receipt-shaped file written later by an operator
after manual rescue. Audit notes document what happened, but they are not
authoritative because the executor did not emit them at the terminal
transition.

## Failure Behavior

Receipt persistence is fail-closed. If `_emit_receipt()` cannot serialize the
payload, create the directory, write the temp file, or replace the final path,
it logs `receipt_emit_failed` and raises:

```text
RuntimeError: Failed to emit receipt for <project_id>: <error>
```

A terminal project without this file is therefore not treated as cleanly
finalized.

## Schema Reference

The machine-readable receipt fields are defined in
`docs/plans/2026-03-10-bootstrap-plan.md` under "Machine-Readable Receipt
Format". This page covers enforcement and storage semantics only.

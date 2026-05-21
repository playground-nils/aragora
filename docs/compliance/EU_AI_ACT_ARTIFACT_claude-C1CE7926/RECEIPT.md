# EU AI Act Compliance Artifact — claude-C1CE7926

**Generated:** 2026-05-21T03:17:13Z
**Session:** claude-C1CE7926 (Phase 8 of substrate-soak)
**Bundle ID:** EUAIA-2b3f5776
**Integrity Hash:** `da6a4432747189bd4ad48f0ec13cb9740e20b0d4ff2a8862a6e542808739335d`

## Generation command

```bash
aragora compliance eu-ai-act generate \
  --output . \
  --provider-name "Synaptent / Aragora" \
  --provider-contact "armand@synaptent.com" \
  --system-name "Aragora Decision Integrity Platform" \
  --system-version "2.9.0" \
  --format all
```

Synthetic-demo input was used (no `receipt_file` argument). To regenerate against a live decision receipt, pass the receipt JSON path as the positional argument.

## Outcome

| Field | Value |
|-------|-------|
| Risk Level (bundle context) | HIGH |
| Annex III Category | Cat. 4 (Employment and worker management) |
| Conformity | **CONFORMANT** |
| Deadline | August 2, 2026 |

### Article compliance

| Article | Description | Status |
|---------|-------------|--------|
| Article 9 | Identify and analyze known and reasonably foreseeable risks | PASS |
| Article 12 | Automatic logging of events with traceability | PASS |
| Article 13 | Identify participating agents, their arguments | PASS |
| Article 14 | Enable human oversight, including ability to override | PASS |
| Article 15 | Appropriate levels of accuracy and robustness | PASS |

## Bundle contents

| File | Bytes |
|------|-------|
| `compliance_bundle.json` | 23320 |
| `conformity_report.json` | 3767 |
| `conformity_report.md` | 2001 |
| `article_9_risk_management.json` | 2607 |
| `article_12_record_keeping.json` | 3461 |
| `article_13_transparency.json` | 2284 |
| `article_14_human_oversight.json` | 2573 |
| `article_15_accuracy_robustness.json` | 1014 |
| `status.txt` (`aragora compliance status` snapshot) | 1353 |
| `audit.txt` (`aragora compliance audit conformity_report.json` snapshot) | 1750 |
| `generate.log` | 1485 |

## Substrate-freeze rationale

This artifact is the external-proof deliverable for the 2026-05-20 substrate-soak run (per [`feedback_substrate_freeze_external_proof.md`](file:///Users/armand/.claude/projects/-Users-armand-Development-aragora/memory/feedback_substrate_freeze_external_proof.md)). No new tooling, no new orchestration verbs — the artifact is produced by existing CLI commands shipped on main (`aragora compliance eu-ai-act generate`, polished for GTM in PR #725 / Mar 6, 2026).

Per memory baseline: 85/100 compliance score; this snapshot demonstrates the artifact pipeline produces a CONFORMANT bundle end-to-end with integrity hashing in place ahead of the August 2, 2026 deadline.

## Notes

- The `aragora compliance audit` re-derivation used `conformity_report.json` as input and produced a MINIMAL-risk classification — this is expected: the audit command re-classifies based on the receipt body, and the demo-data receipt body doesn't carry the Annex III HIGH-risk fingerprint that the bundle generator inferred via `--system-name`. This is documented behavior, not a defect. For production use, the input receipt should carry explicit risk-classification metadata.
- The `.nomic/` subdirectory is empty (auto-created by some downstream tool).
- All artifact JSON is deterministic given the same inputs (the SHA-256 hash will only change if input semantics change).

# Inbox Triage: Instrumentation, Feedback Loop, and Content Digest Plan

> **Status:** Design doc (Mar 30, 2026)
> **Corrective note:** This doc acknowledges that most of the feedback/review substrate already exists in Aragora. The work is NOT "invent RLHF" — it is "make existing labeling UX fast and wire it into an active-learning loop."

---

## What Already Exists (Don't Reinvent)

| Capability | Location | Status |
|-----------|----------|--------|
| Approve/reject/edit/skip review | `cli_review.py:131` | Production |
| Service-level review/edit | `trust_wedge.py:1190` | Production |
| HTTP receipt CRUD endpoints | `trust_wedge_handler.py:21` | Production |
| Per-decision audit trail | `trust_wedge.py:527` (decision_json) | Production |
| Synthesized rationale per email | `triage_runner.py:600` | Production |
| Dissent summary capture | `triage_runner.py:309-330` | Production |
| Diagnostics per-run + per-decision | `triage_diagnostics.py:196-406` | Production |
| Web rule builder UI | `live/components/inbox/TriageRulesPanel.tsx` | Production |
| Email body access (2000 char) | `triage_runner.py:435` | Production |
| Confidence, latency, tier, escalation | `decision_json` fields | Production |
| Email priority analysis (3-tier) | `analysis/email_priority.py` (871 lines) | Built, not wired |
| Document summarization engine | `analysis/nl_query.py` (859 lines) | Built, not wired |
| Insight extraction | `insights/extractor.py` (535 lines) | Built, not wired |
| Report generator | `reports/generator.py` | Built, not wired |

---

## What's Actually Missing (The Real Gaps)

### Gap 1: Receipt Review Queue with Smart Prioritization

**Problem:** All receipts are treated equally. The founder has to manually spot-check. There's no prioritized queue that surfaces the decisions most worth reviewing.

**What to build:** A review queue that sorts by:
1. Low confidence (< 0.7)
2. Escalated tier (not fast)
3. Blocked by policy
4. Edited by human (learn from corrections)
5. Repeated sender (first email from this sender — might be miscategorized)
6. High-stakes keywords (payment, contract, deadline, urgent)

**Implementation:** This is a SQL query + CLI command. The data already exists in `decision_json`.

```sql
SELECT receipt_id, action,
       json_extract(decision_json, '$.confidence') as conf,
       json_extract(decision_json, '$.execution_tier') as tier,
       json_extract(decision_json, '$.blocked_by_policy') as blocked,
       review_choice
FROM inbox_trust_receipts
WHERE state IN ('created', 'executed')
ORDER BY
  CASE WHEN json_extract(decision_json, '$.blocked_by_policy') = 1 THEN 0
       WHEN json_extract(decision_json, '$.execution_tier') = 'escalated' THEN 1
       WHEN json_extract(decision_json, '$.confidence') < 0.7 THEN 2
       WHEN review_choice IS NOT NULL AND review_choice != 'auto_approve' THEN 3
       ELSE 4 END,
  json_extract(decision_json, '$.confidence') ASC
LIMIT 20;
```

**CLI:** `aragora triage review-queue [--limit 10]` — shows prioritized list, enters interactive review loop.

### Gap 2: Fast Labeling UX (RLHF-style feedback)

**Problem:** The review flow exists (`cli_review.py`) but requires looking at each email. The founder needs a way to spend ~2 minutes labeling 20 decisions as good/bad.

**What to build:** A fast-label command that shows one-line summaries and accepts single-key responses:

```
[1/20] archive 95%  newsletter@example.com "Spring Sale 50% Off"
       Rationale: Promotional email, no action needed
       [g]ood / [b]ad / [s]kip > g

[2/20] ignore  0%   bank@chase.com "Transaction Declined"
       Rationale: Financial notification, blocked by policy
       [g]ood / [b]ad / [s]kip > g

[3/20] archive 95%  colleague@work.com "RE: Project Update"
       Rationale: Newsletter-style update, low engagement
       [g]ood / [b]ad / [s]kip > b  ← WRONG! This is from a colleague
```

**Implementation:**
- New CLI: `aragora triage label [--limit 20] [--queue prioritized|recent|random]`
- Store labels in new column `feedback` on `inbox_trust_receipts` (or new table `inbox_trust_feedback`)
- Track: receipt_id, label (good/bad/skip), timestamp, corrections (what action *should* have been)

**Existing substrate:** `cli_review.py` already has the interactive loop with approve/reject/edit. This is a thin wrapper that:
1. Queries the review queue
2. Shows a compact one-liner per decision
3. Accepts g/b/s keystrokes
4. Writes feedback to DB

### Gap 3: Cross-Email Daily Digest

**Problem:** Per-email reasoning summaries exist, but there's no daily rollup that clusters archived messages into a compact summary.

**Competitor benchmark:** SaneBox's SaneDigest shows sender + subject of SaneLater items. Superhuman's Auto Summarize shows one-line per thread. alfred_ provides a "Daily Brief" with key emails. Shortwave extracts key points + decisions + action items per thread.

**What to build:** A daily digest command that:
1. Queries all receipts from the last 24h (or since last digest)
2. Groups by action (archived, blocked, executed)
3. For archived: clusters by topic/sender-domain, shows count + sample subjects
4. For blocked: shows each one with rationale (these need human review)
5. Optionally: uses DocumentQueryEngine to produce a 3-paragraph summary of "what you missed"

**Implementation:**
- `aragora triage digest [--since 24h] [--summarize]`
- Without `--summarize`: Pure SQL grouping, no LLM call, instant
- With `--summarize`: Feeds archived email subjects+snippets into `analysis/nl_query.py:summarize_documents()` for a cross-email synthesis

**Example output:**
```
Daily Triage Digest (Mar 30, 2026)
═══════════════════════════════════
Processed: 40 emails
Archived:  37 (93%)  |  Blocked: 3 (7%)

Archived by category:
  Newsletters (18): Finance (5), Health (4), Tech (3), Marketing (6)
  Promotions (12): Sales/discounts from 8 vendors
  Social (4): LinkedIn, Twitter notifications
  Duplicate (3): Same email sent twice

Blocked (review needed):
  1. "Transaction Declined" — bank@chase.com — financial notification
  2. "Reminder: Complete survey" — hr@company.com — action item
  3. "Middle East Update" — news@source.com — geopolitical content

Cross-email summary (AI-generated):
  Today's archived mail was mostly promotional (Spring sales from 8 vendors)
  and newsletters (pharma/biotech news, fintech updates, AI developments).
  No personal emails were archived. The 3 blocked items all require your
  attention: a bank alert, an HR survey deadline, and a news briefing you
  may want to read.
```

### Gap 4: Skeptical Batch Review by Claude

**Problem:** The founder asked "how can you review each email that was processed and skeptically review whether the processing was good or not."

**What to build:** A command that exports the last N decisions with full context, then feeds them to Claude for adversarial review.

**Implementation:**
- `aragora triage audit [--batch 20] [--since 24h]`
- Exports: subject, sender, snippet, action taken, confidence, rationale, dissent
- Prompts Claude: "Review these triage decisions. Flag any that look wrong: important emails archived, junk kept, or low confidence decisions that should have been escalated."
- Outputs: list of flagged decisions with reasons

**This is meta-triage** — using debate to audit the triage. The infrastructure (debate engine, receipt system) already exists.

### Gap 5: Active Learning Loop (Feeding Labels Back)

**Problem:** Labels collected in Gap 2 need to influence future triage decisions.

**What to build:** A feedback → routing pipeline:
1. Collect labels (good/bad per decision)
2. Identify patterns in "bad" labels:
   - Sender domains that get misclassified
   - Subject keyword patterns that predict errors
   - Confidence calibration: are 95% decisions really 95% accurate?
3. Feed patterns into `auto_approval.py` policy:
   - Add sender domains to watch list
   - Adjust confidence threshold based on calibration
   - Add keyword patterns to escalation triggers
4. Feed into Knowledge Mound for cross-session learning

**Implementation (phased):**
- **Phase 1:** `aragora triage calibrate` — reads all feedback labels, computes accuracy by confidence bucket, recommends threshold adjustments
- **Phase 2:** Auto-update `auto_approval.py` policy from calibration data
- **Phase 3:** KM integration — persist sender reputation, topic preferences as knowledge entries

---

## Competitive Feature Gap Analysis

Based on research of 15 AI inbox products (full details in `COMPETITIVE_INBOX_TRIAGE_LANDSCAPE.md`):

### Baseline Features (must match to be competitive)

| Feature | Best Example | Aragora Status | Gap |
|---------|-------------|----------------|-----|
| Auto-categorize (Act/FYI/Noise) | Fyxer, Superhuman | Partial (archive/ignore only) | Add STAR=important tier |
| Thread summarization | Shortwave (key points + action items) | Not wired (engine exists) | Wire `nl_query.py` |
| Sender importance weighting | SaneBox (98.5% from metadata only) | Not implemented | Use feedback labels |
| Explicit feedback (drag to correct) | SaneBox folder-drag | Partial (CLI review exists) | Add fast-label UX |
| Daily digest | SaneBox SaneDigest, alfred_ Daily Brief | Not implemented | Build `triage digest` |
| Follow-up detection | SaneBox SaneNoReplies | Not implemented | Future |
| Unsubscribe/block sender | SaneBox SaneBlackHole, Clean Email | Not implemented | Future |

### Aragora Differentiators (no competitor has these)

| Feature | Why It's Unique |
|---------|----------------|
| Multi-agent debate on ambiguous emails | No tool asks "what if this is actually important?" |
| Cryptographic decision receipts | No tool produces audit trails for triage actions |
| Cross-email pattern synthesis | No tool identifies themes across emails |
| Evidence-backed prioritization | No tool says "this references a contract deadline in 3 days" |
| Knowledge Mound integration | No tool uses organizational knowledge to inform triage |
| Human-in-the-loop for high-stakes | Most tools auto-sort silently; Aragora blocks + explains |

### Key Insight from Research

> Less than 1% of email interactions generate explicit feedback (Google Research).
> SaneBox's 98.5% accuracy comes from **implicit behavioral signals** (opens, replies, archive timing), not explicit labeling.

**Implication for Aragora:** The fast-label UX (Gap 2) is valuable for bootstrapping, but long-term learning should also track implicit signals: did the founder un-archive something? Did they reply to a "blocked" email? Did they search for an archived email?

---

## Implementation Priority

| Priority | Gap | Effort | Value |
|----------|-----|--------|-------|
| P0 | Receipt review queue | 2h | Enables quality assessment |
| P0 | Fast-label UX | 3h | Enables RLHF loop |
| P1 | Daily digest (SQL-only) | 2h | Replaces manual inbox scanning |
| P1 | Skeptical batch review | 3h | Automated quality audit |
| P2 | Daily digest (AI summary) | 4h | Cross-email synthesis |
| P2 | Calibration command | 3h | Closes the active-learning loop |
| P3 | Implicit signal tracking | 8h | Gmail API watch for un-archive/reply |
| P3 | Auto-categorize into 3+ tiers | 4h | Feature parity |

**Total P0+P1:** ~10 hours of implementation using existing substrate.

---

## Web Interface Consideration

The founder asked about a web interface. Current state:
- `trust_wedge_handler.py` already serves receipt CRUD via REST API
- `TriageRulesPanel.tsx` exists for rule building
- `CommandCenter.tsx` exists for email prioritization

**Minimal web path:** Add a `/triage/review` page to `aragora/live/` that:
1. Fetches prioritized review queue from `GET /api/v1/inbox/wedge/receipts?state=created&sort=confidence`
2. Shows cards with subject, sender, action, confidence, rationale
3. Each card has Good/Bad/Skip buttons
4. Posts feedback to `POST /api/v1/inbox/wedge/receipts/{id}/feedback`

This is ~4-6h of React work using existing components and API endpoints.

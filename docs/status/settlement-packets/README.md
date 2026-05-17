# Settlement packets — operator UI

This directory holds **operator settlement packets** — read-only synthesis
documents that batch every open-PR settlement decision into one sign-off.
Each packet is paired with a SHA-256-bound JSON receipt at
`docs/receipts/<receipt-name>.json`.

## What's here

- `<date>-open-queue-settlement.md` — the human-readable packet (Markdown)
- `operator-ui.html` — a local web UI for batch sign-off on a packet
- `README.md` — this file

## Using `operator-ui.html`

The UI is a **single self-contained HTML file** that reads a settlement
receipt JSON, renders each PR as a card with a decision picker, and
downloads a SHA-256-bound JSON record of your decisions.

### Quickstart

From the repo root:

```bash
# 1. Serve docs/ via Python's stdlib HTTP server (no install needed):
python3 -m http.server 8765 --directory docs

# 2. Open the UI in a browser:
open http://127.0.0.1:8765/status/settlement-packets/operator-ui.html
#   (or paste the URL into your browser)

# 3. In the UI, either:
#    - Click "Choose File" and pick docs/receipts/open-queue-settlement-<ts>.json
#    - OR paste the relative path:
#         ../receipts/open-queue-settlement-20260517T142811Z.json
#      and click "Fetch"
```

The page is **fully local**:

- No network calls outside `127.0.0.1`
- No AI provider keys consumed
- No PR mutation (download-only; you commit/comment yourself)
- SHA-256 verification of the loaded receipt against its canonical payload
- Output is a JSON blob in your browser's Downloads folder

### Decision options per PR

Each PR card offers five radio options:

| Option | Meaning |
|---|---|
| `APPROVE this tier` | Accept the packet's tier classification and approve at that tier |
| `APPROVE downgraded` | Approve, but at a lower tier than the packet assigned (record reasoning in the comment box) |
| `REQUEST changes` | Mark needs-work; record the change request in the comment box |
| `REJECT` | Close the PR; record reasoning in the comment box |
| `HOLD (operator-only)` | Hold off pending operator-only action; do not advance in this batch |

### What the downloaded JSON looks like

```json
{
  "schema_version": "aragora-operator-decision-receipt/1.0",
  "generated_at_utc": "2026-05-17T...",
  "operator": "armand@synaptent.com",
  "source_receipt": {
    "path": "../receipts/open-queue-settlement-20260517T142811Z.json",
    "sha256": "b93358c76358bab8b1a41a2843bc4c7ee36446ce433ebab8ab301d0c359cf9a2",
    "generated_at_utc": "2026-05-17T14:28:11..."
  },
  "decisions": [
    {"number": 7215, "head_sha": "0d148f...", "tier_observed": "2",
     "decision": "approve_tier", "comment": ""},
    ...
  ],
  "decisions_made": 15,
  "decisions_pending": 0,
  "sha256": "<canonical hash of the decisions payload above>"
}
```

### How to record decisions in the PR

You have two options after downloading the decision receipt:

1. **Commit it under `docs/receipts/`** with a `git add`/`git commit` and
   reference it from your PR review or comment.
2. **Paste it as a PR comment** on the source settlement-packet PR
   (the UI's "Copy decisions to clipboard" button copies a
   fenced JSON block ready to paste).

### Security / discipline

- **Zero network calls beyond `127.0.0.1`.** The UI uses `fetch()` only
  against same-origin paths.
- **No JS dependencies.** Single HTML file, vanilla JS, no npm, no
  CDN.
- **No PR mutation from JS.** All `gh` / `git` actions are operator-only.
- **No AI provider keys touched.** No model calls.
- **SHA-256 binding verified in the browser.** When you load a receipt,
  the UI re-computes its canonical-payload hash via `crypto.subtle.digest`
  and compares to the receipt's `sha256` field (✅ match or ❌ mismatch
  shown in the header).

### Troubleshooting

| Symptom | Likely cause |
|---|---|
| "Failed to fetch receipt at …" | The relative path you typed isn't reachable from where the page lives. Try the file-picker instead. |
| "Receipt JSON is missing pinned_state[]" | The file you loaded isn't an open-queue-settlement receipt. The UI expects `pinned_state[]` as the per-PR array. |
| SHA-256 shows ❌ MISMATCH | The JSON file was edited after generation; canonical-payload hash no longer matches the receipt's `sha256` field. Regenerate via the source script, or treat this as a tampered file. |
| Browser refuses to open from `file://` | Use the `python3 -m http.server` approach instead. Some browsers (and `crypto.subtle.digest`) require an origin context. |

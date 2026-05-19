#!/usr/bin/env bash
# Unified agent-wake dispatcher (Phase 2 of agent-dispatch reach plan, R02).
#
# Reads the lane's `contact_method` (added to LaneRecord by R01 / PR #7336)
# and dispatches a prompt to that lane's owner via the right backend:
#   tmux:NAME       -> scripts/tmux_send_prompt.sh
#   mailbox-only    -> scripts/send_operator_steering.py
#   osascript:*     -> not yet implemented (R03+); falls back to --fallback
#   factory-api:*   -> not yet implemented (R04 opt-in); falls back to --fallback
#
# Every dispatch writes a JSON delivery receipt to
#   .aragora/dispatch-receipts/<utc>-<lane>-<sha8>.json
# capturing the chosen backend, message SHA-256, and outcome.
#
# Usage:
#   ./scripts/wake_agent.sh --lane LANE_ID \
#       [--prompt TEXT | --prompt-file PATH] \
#       [--priority {low,normal,high,blocking}] \
#       [--dry-run | --apply] \
#       [--fallback {mailbox-only,fail}] \
#       [--json]
#
# Flags:
#   --lane <id>           Required. Lane id whose owner should be woken.
#   --prompt <text>       Inline prompt text.
#   --prompt-file <path>  Path to a prompt file (read as-is, UTF-8).
#   --priority <level>    Mailbox priority hint (default: normal).
#   --dry-run             (Default.) Resolve lane, pick backend, write
#                         receipt with `dispatch_attempted=false`, but do
#                         NOT actually send. Idempotent and safe.
#   --apply               Opt-in mutate — actually dispatch.
#   --fallback <mode>     What to do if contact_method is missing / unknown:
#                           mailbox-only (default) — fall back to mailbox.
#                           fail — exit non-zero without dispatching.
#   --json                Print the dispatch receipt to stdout.
#
# Exit codes:
#   0   success (dispatched or dry-run resolved)
#   1   usage error
#   2   lane not found
#   3   missing contact_method AND --fallback fail
#   4   dispatch backend invocation failed
#
# Dependencies (all already shipped):
#   - scripts/identify_lane_owner.py  (PR #7308, on main)
#   - scripts/tmux_send_prompt.sh
#   - scripts/send_operator_steering.py (PR #7310)
#
# Depends on R01 (PR #7336) for the `contact_method` field on LaneRecord
# rows, but degrades gracefully when contact_method is absent (treats as
# mailbox-only fallback).

set -euo pipefail

LANE_ID=""
PROMPT_TEXT=""
PROMPT_FILE=""
PRIORITY="normal"
MODE="dry-run"     # default fail-closed
FALLBACK="mailbox-only"
JSON_OUTPUT=0

usage() {
    cat <<'EOF'
wake_agent.sh — unified dispatch CLI (reach plan Phase 2 / R02)

Required:
  --lane <id>           Lane id to wake.

One of:
  --prompt <text>       Inline prompt.
  --prompt-file <path>  Read prompt from file.

Optional:
  --priority {low,normal,high,blocking}  (default: normal)
  --dry-run            (default) Resolve + write receipt, do not send.
  --apply              Opt-in: actually dispatch.
  --fallback {mailbox-only,fail}         (default: mailbox-only)
  --json               Emit JSON receipt to stdout.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --lane)         LANE_ID="$2"; shift 2 ;;
        --prompt)       PROMPT_TEXT="$2"; shift 2 ;;
        --prompt-file)  PROMPT_FILE="$2"; shift 2 ;;
        --priority)     PRIORITY="$2"; shift 2 ;;
        --dry-run)      MODE="dry-run"; shift ;;
        --apply)        MODE="apply"; shift ;;
        --fallback)     FALLBACK="$2"; shift 2 ;;
        --json)         JSON_OUTPUT=1; shift ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Unknown flag: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [[ -z "$LANE_ID" ]]; then
    echo "error: --lane is required" >&2
    exit 1
fi
if [[ -z "$PROMPT_TEXT" && -z "$PROMPT_FILE" ]]; then
    echo "error: one of --prompt or --prompt-file is required" >&2
    exit 1
fi
if [[ -n "$PROMPT_TEXT" && -n "$PROMPT_FILE" ]]; then
    echo "error: --prompt and --prompt-file are mutually exclusive" >&2
    exit 1
fi
case "$PRIORITY" in
    low|normal|high|blocking) ;;
    *) echo "error: --priority must be one of low|normal|high|blocking" >&2; exit 1 ;;
esac
case "$FALLBACK" in
    mailbox-only|fail) ;;
    *) echo "error: --fallback must be one of mailbox-only|fail" >&2; exit 1 ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$REPO_ROOT/scripts"
RECEIPT_DIR="$REPO_ROOT/.aragora/dispatch-receipts"
mkdir -p "$RECEIPT_DIR"

# Resolve prompt content + SHA-256 for receipt binding.
if [[ -n "$PROMPT_FILE" ]]; then
    if [[ ! -r "$PROMPT_FILE" ]]; then
        echo "error: prompt file not readable: $PROMPT_FILE" >&2
        exit 1
    fi
    PROMPT_CONTENT="$(cat "$PROMPT_FILE")"
else
    PROMPT_CONTENT="$PROMPT_TEXT"
fi
PROMPT_SHA="$(printf '%s' "$PROMPT_CONTENT" | shasum -a 256 | awk '{print $1}')"

# Look up lane owner + contact_method via the canonical Phase A reader.
# Falls back to direct registry parse if identify_lane_owner.py is absent
# (e.g., legacy worktree predating PR #7308).
LANE_JSON=""
if [[ -x "$SCRIPTS_DIR/identify_lane_owner.py" || -r "$SCRIPTS_DIR/identify_lane_owner.py" ]]; then
    LANE_JSON="$(python3 "$SCRIPTS_DIR/identify_lane_owner.py" --lane-id "$LANE_ID" --json 2>/dev/null || true)"
fi
if [[ -z "$LANE_JSON" || "$LANE_JSON" == "null" ]]; then
    # Fallback: read the raw registry.
    LANE_JSON="$(python3 -c "
import json, sys
from pathlib import Path
for p in (Path('$REPO_ROOT/.aragora/agent-bridge/lanes.json'),
          Path.home()/'.aragora'/'agent-bridge'/'lanes.json'):
    if p.exists():
        for row in json.loads(p.read_text() or '[]'):
            if row.get('lane_id') == '$LANE_ID':
                print(json.dumps(row))
                sys.exit(0)
" 2>/dev/null || true)"
fi
if [[ -z "$LANE_JSON" ]]; then
    echo "error: lane not found: $LANE_ID" >&2
    exit 2
fi

OWNER="$(printf '%s' "$LANE_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('owner_session','') or '')")"
CONTACT_METHOD="$(printf '%s' "$LANE_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('contact_method','') or '')")"

CHOSEN_BACKEND=""
BACKEND_TARGET=""
if [[ -z "$CONTACT_METHOD" ]]; then
    if [[ "$FALLBACK" == "fail" ]]; then
        echo "error: lane $LANE_ID has no contact_method and --fallback fail" >&2
        exit 3
    fi
    CHOSEN_BACKEND="mailbox-only"
    BACKEND_TARGET="$OWNER"
elif [[ "$CONTACT_METHOD" == "mailbox-only"* ]]; then
    CHOSEN_BACKEND="mailbox-only"
    BACKEND_TARGET="$OWNER"
elif [[ "$CONTACT_METHOD" == tmux:* ]]; then
    CHOSEN_BACKEND="tmux"
    BACKEND_TARGET="${CONTACT_METHOD#tmux:}"
else
    # Unknown / not-yet-implemented backend (osascript:* / factory-api:*).
    if [[ "$FALLBACK" == "fail" ]]; then
        echo "error: contact_method $CONTACT_METHOD not implemented and --fallback fail" >&2
        exit 3
    fi
    CHOSEN_BACKEND="mailbox-only"
    BACKEND_TARGET="$OWNER"
fi

UTC_TS="$(date -u +%Y%m%dT%H%M%SZ)"
SHA_SHORT="${PROMPT_SHA:0:8}"
RECEIPT_PATH="$RECEIPT_DIR/${UTC_TS}-${LANE_ID}-${SHA_SHORT}.json"
DISPATCH_OUTCOME="dry-run-only"
DISPATCH_ERROR=""

if [[ "$MODE" == "apply" ]]; then
    case "$CHOSEN_BACKEND" in
        tmux)
            # Build a tmp prompt file for the tmux script (handles multi-line correctly).
            TMP_FILE="$(mktemp -t wake_agent_tmux.XXXXXX)"
            printf '%s' "$PROMPT_CONTENT" > "$TMP_FILE"
            if bash "$SCRIPTS_DIR/tmux_send_prompt.sh" \
                    --name "$BACKEND_TARGET" \
                    --prompt-file "$TMP_FILE" \
                    --source "wake_agent.sh:$LANE_ID" >/dev/null 2>&1; then
                DISPATCH_OUTCOME="dispatched"
            else
                DISPATCH_OUTCOME="failed"
                DISPATCH_ERROR="tmux_send_prompt.sh exited non-zero"
            fi
            rm -f "$TMP_FILE"
            ;;
        mailbox-only)
            if python3 "$SCRIPTS_DIR/send_operator_steering.py" \
                    --to "$BACKEND_TARGET" \
                    --body "$PROMPT_CONTENT" \
                    --priority "$PRIORITY" \
                    --lane-id "$LANE_ID" >/dev/null 2>&1; then
                DISPATCH_OUTCOME="dispatched"
            else
                DISPATCH_OUTCOME="failed"
                DISPATCH_ERROR="send_operator_steering.py exited non-zero"
            fi
            ;;
    esac
fi

# Always write the receipt (idempotent, includes dry-run resolutions).
python3 - "$RECEIPT_PATH" "$LANE_ID" "$OWNER" "$CONTACT_METHOD" "$CHOSEN_BACKEND" \
        "$BACKEND_TARGET" "$MODE" "$DISPATCH_OUTCOME" "$DISPATCH_ERROR" \
        "$PROMPT_SHA" "$PRIORITY" "$FALLBACK" <<'PYEOF'
import json
import sys
from datetime import UTC, datetime

(_, path, lane_id, owner, contact_method, chosen_backend, backend_target,
 mode, outcome, err, prompt_sha, priority, fallback) = sys.argv
receipt = {
    "schema_version": "aragora-wake-agent-receipt/1.0",
    "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "lane_id": lane_id,
    "owner_session": owner,
    "contact_method": contact_method or None,
    "chosen_backend": chosen_backend,
    "backend_target": backend_target,
    "fallback_policy": fallback,
    "mode": mode,
    "dispatch_attempted": mode == "apply",
    "dispatch_outcome": outcome,
    "dispatch_error": err or None,
    "priority": priority,
    "prompt_sha256": prompt_sha,
}
with open(path, "w", encoding="utf-8") as fh:
    json.dump(receipt, fh, indent=2, sort_keys=True)
PYEOF

if [[ "$JSON_OUTPUT" -eq 1 ]]; then
    cat "$RECEIPT_PATH"
else
    echo "wake_agent: lane=$LANE_ID owner=$OWNER backend=$CHOSEN_BACKEND mode=$MODE outcome=$DISPATCH_OUTCOME receipt=$RECEIPT_PATH"
fi

if [[ "$DISPATCH_OUTCOME" == "failed" ]]; then
    exit 4
fi
exit 0

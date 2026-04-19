#!/usr/bin/env bash
# Toggle the auto-approver between dry-run and live mode.
#
# Usage:
#   scripts/auto_approver_activate.sh on    # enable live approvals
#   scripts/auto_approver_activate.sh off   # return to dry-run mode
#   scripts/auto_approver_activate.sh status
#
# The auto-approver script refuses to submit reviews unless
# ~/.aragora/auto_approver.live exists, so this toggle is the operator's
# explicit opt-in into production mode.

set -euo pipefail

STATE_DIR="${HOME}/.aragora"
LIVE_FLAG="${STATE_DIR}/auto_approver.live"
DISABLED_FLAG="${STATE_DIR}/auto_approver.disabled"

mkdir -p "${STATE_DIR}"

case "${1:-status}" in
  on|enable|live)
    touch "${LIVE_FLAG}"
    if [[ -e "${DISABLED_FLAG}" ]]; then
      echo "WARNING: kill switch ${DISABLED_FLAG} is still present; remove it to unblock approvals." >&2
    fi
    echo "auto-approver: LIVE (flag: ${LIVE_FLAG})"
    ;;
  off|disable|dryrun|dry-run)
    rm -f "${LIVE_FLAG}"
    echo "auto-approver: DRY-RUN (flag removed: ${LIVE_FLAG})"
    ;;
  kill|pause)
    touch "${DISABLED_FLAG}"
    echo "auto-approver: KILL SWITCH engaged (${DISABLED_FLAG})."
    echo "Remove the file to resume: rm ${DISABLED_FLAG}"
    ;;
  resume|unkill)
    rm -f "${DISABLED_FLAG}"
    echo "auto-approver: KILL SWITCH cleared. Mode is $( [[ -e "${LIVE_FLAG}" ]] && echo LIVE || echo DRY-RUN )."
    ;;
  status|*)
    mode="DRY-RUN"
    if [[ -e "${LIVE_FLAG}" ]]; then mode="LIVE"; fi
    kill_state="no"
    if [[ -e "${DISABLED_FLAG}" ]]; then kill_state="YES (paused)"; fi
    echo "auto-approver: mode=${mode} kill_switch=${kill_state}"
    echo "  live flag:     ${LIVE_FLAG}"
    echo "  disable flag:  ${DISABLED_FLAG}"
    ;;
esac

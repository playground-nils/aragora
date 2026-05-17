#!/usr/bin/env bash
# Install the publication-freshness probe LaunchAgent from the template.
#
# Reads `scripts/launch_agents/com.aragora.publication-freshness-probe.plist`,
# substitutes the absolute paths, writes the rendered plist to
# `~/Library/LaunchAgents/com.aragora.publication-freshness-probe.plist`,
# then `launchctl unload`s any previous instance and `launchctl load`s the
# new one.
#
# Strictly opt-in: this script is not invoked by any automation in the
# repository. Running it is the only way the LaunchAgent gets installed
# on a workstation.
#
# Usage:
#   bash scripts/install_publication_freshness_probe_launchd.sh
#
# Options:
#   --interval-seconds <n>   StartInterval seconds (default: 14400 = 4 hours)
#   --python <path>          Python interpreter (default: <repo>/.venv/bin/python3
#                             if present, else /usr/bin/env python3)
#   --uninstall              Remove the LaunchAgent and exit.
#   --dry-run                Render the plist to stdout without installing.
#   --help                   Print usage.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.aragora.publication-freshness-probe"
TEMPLATE="${REPO_ROOT}/scripts/launch_agents/${LABEL}.plist"
RENDERED="${HOME}/Library/LaunchAgents/${LABEL}.plist"
INTERVAL_SECONDS=14400
DEFAULT_VENV_PYTHON="${REPO_ROOT}/.venv/bin/python3"
ACTION="install"
DRY_RUN=false

PYTHON=""

usage() {
    cat <<'EOF'
Usage: bash scripts/install_publication_freshness_probe_launchd.sh [options]

Options:
  --interval-seconds <n>   StartInterval seconds (default: 14400 = 4 hours)
  --python <path>          Python interpreter override.
  --uninstall              Remove the LaunchAgent and exit.
  --dry-run                Render the plist to stdout without installing.
  --help                   Print usage.

What it does (install mode):
  - Reads scripts/launch_agents/com.aragora.publication-freshness-probe.plist
  - Substitutes __ARAGORA_REPO_ROOT__ and __ARAGORA_PYTHON__
  - Writes ~/Library/LaunchAgents/com.aragora.publication-freshness-probe.plist
  - launchctl unload (best-effort) any previous instance
  - launchctl load the new instance

What it does (--uninstall):
  - launchctl unload + rm of the rendered plist (best-effort).
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --interval-seconds)
            INTERVAL_SECONDS="${2:-14400}"
            shift 2
            ;;
        --python)
            PYTHON="${2:-}"
            shift 2
            ;;
        --uninstall)
            ACTION="uninstall"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ "$ACTION" == "uninstall" ]]; then
    if [[ -f "$RENDERED" ]]; then
        launchctl unload "$RENDERED" >/dev/null 2>&1 || true
        rm -f "$RENDERED"
        echo "Removed: $RENDERED"
    else
        echo "Nothing to uninstall at: $RENDERED"
    fi
    exit 0
fi

if [[ ! -f "$TEMPLATE" ]]; then
    echo "error: template not found at $TEMPLATE" >&2
    exit 1
fi

if ! [[ "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]]; then
    echo "error: --interval-seconds must be numeric" >&2
    exit 2
fi

if [[ -z "$PYTHON" ]]; then
    if [[ -x "$DEFAULT_VENV_PYTHON" ]]; then
        PYTHON="$DEFAULT_VENV_PYTHON"
    else
        PYTHON="$(/usr/bin/env which python3 || true)"
    fi
fi
if [[ -z "$PYTHON" || ! -x "$PYTHON" ]]; then
    echo "error: could not resolve a Python interpreter; pass --python <path>" >&2
    exit 1
fi

rendered_body="$(
    sed \
        -e "s|__ARAGORA_REPO_ROOT__|${REPO_ROOT}|g" \
        -e "s|__ARAGORA_PYTHON__|${PYTHON}|g" \
        -e "s|<integer>14400</integer>|<integer>${INTERVAL_SECONDS}</integer>|" \
        "$TEMPLATE"
)"

if [[ "$DRY_RUN" == true ]]; then
    printf '%s\n' "$rendered_body"
    exit 0
fi

mkdir -p "$(dirname "$RENDERED")"
printf '%s\n' "$rendered_body" >"$RENDERED"
launchctl unload "$RENDERED" >/dev/null 2>&1 || true
launchctl load "$RENDERED"

echo "Installed LaunchAgent: ${LABEL}"
echo "Rendered plist: ${RENDERED}"
echo "StartInterval: ${INTERVAL_SECONDS}s"
echo "Python: ${PYTHON}"
echo "Probe command:"
echo "  cd \"${REPO_ROOT}\" && \"${PYTHON}\" scripts/publish_publication_freshness_probe.py --render-markdown"

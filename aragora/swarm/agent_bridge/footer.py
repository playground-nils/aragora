from __future__ import annotations

import json
from typing import Any

from aragora.swarm.agent_bridge.types import BridgeFooter

FOOTER_PREFIX = "AGENT_BRIDGE_FOOTER:"
FOOTER_TEMPLATE = {
    "summary": "One-sentence outcome summary",
    "next_actor": "actor-name-or-null",
    "needs_human": False,
    "done": False,
    "artifacts": [],
    "tests_run": [],
}


def footer_instructions() -> str:
    return (
        "End your response with exactly one final line using this prefix and JSON shape:\n"
        f"{FOOTER_PREFIX} " + json.dumps(FOOTER_TEMPLATE, separators=(", ", ": ")) + "\n"
        "The footer must be the last non-empty line."
    )


def extract_footer(text: str) -> tuple[BridgeFooter | None, str]:
    footer_payload: dict[str, Any] | None = None
    footer_index = -1
    lines = text.splitlines()
    for index in range(len(lines) - 1, -1, -1):
        line = lines[index].strip()
        if not line:
            continue
        if line.startswith(FOOTER_PREFIX):
            footer_index = index
            raw_json = line.removeprefix(FOOTER_PREFIX).strip()
            try:
                parsed = json.loads(raw_json)
            except json.JSONDecodeError:
                return None, text
            if not isinstance(parsed, dict):
                return None, text
            footer_payload = parsed
            break
        # The footer must be the last non-empty line.
        return None, text

    if footer_payload is None or footer_index < 0:
        return None, text

    try:
        footer = BridgeFooter.from_dict(footer_payload)
    except (TypeError, ValueError):
        return None, text
    if not footer.summary:
        return None, text
    body = "\n".join(lines[:footer_index]).rstrip()
    return footer, body


def build_footer_repair_prompt(previous_response: str) -> str:
    excerpt = previous_response.strip()
    if len(excerpt) > 1200:
        excerpt = excerpt[:1197].rstrip() + "..."
    return (
        "Your previous response was missing the required agent bridge footer or the footer was malformed.\n"
        "Do not repeat the full response. Return exactly one line containing only a corrected footer.\n"
        f"Prefix it with {FOOTER_PREFIX} and include valid JSON with keys "
        "summary, next_actor, needs_human, done, artifacts, tests_run.\n\n"
        "Previous response excerpt:\n"
        f"{excerpt}"
    )

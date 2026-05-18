"""Public-repo visibility guard for synthetic prediction markets (AGT-04 SD-7).

Limits market creation to publicly observable GitHub repositories so resolution
events are derived from unambiguous public state rather than private API calls
that may be unavailable, rate-limited differently, or misleading.

Feature flag: ``ARAGORA_MARKET_REPO_GUARD_ENABLED`` (env var, default OFF).
When the flag is off the guard is a transparent pass-through — all existing
markets and tests are unaffected.

Allowlist: ``ARAGORA_MARKET_REPO_ALLOWLIST`` — comma-separated ``owner/repo``
entries.  The special token ``*`` allows any syntactically valid ``owner/repo``
without explicit listing (trust-public-repos mode, useful for test environments
and future network-backed visibility probing).

Fail-closed rule: when the flag is ON and ``ARAGORA_MARKET_REPO_ALLOWLIST`` is
empty or unset, the guard **denies all repos**.  Operators must explicitly list
repos or set ``ARAGORA_MARKET_REPO_ALLOWLIST=*``.

Does NOT call the GitHub API.  Network-backed public-visibility probing (e.g.
checking ``repo.visibility`` via the REST API) is a follow-on slice that can be
wired in by subclassing :class:`RepoVisibilityGuard` and overriding
:meth:`is_allowed`.

Advances: issue #6065 (AGT-04), sub-deliverable 7 — publicly observable repos.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

_FLAG = "ARAGORA_MARKET_REPO_GUARD_ENABLED"
_ALLOWLIST_VAR = "ARAGORA_MARKET_REPO_ALLOWLIST"
_WILDCARD = "*"

# Accepts GitHub-style owner/repo with alphanumerics, dots, dashes, underscores.
_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")


class RepoVisibilityError(ValueError):
    """Raised when a market targets a repo not in the visibility allowlist."""


def _guard_enabled() -> bool:
    return os.environ.get(_FLAG, "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_allowlist(raw: str) -> frozenset[str]:
    """Parse a comma-separated allowlist string into a normalised frozenset.

    The wildcard token ``*`` is kept as-is; all other tokens are lowercased
    and stripped so comparisons are case-insensitive.
    """
    parts: set[str] = set()
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if token == _WILDCARD:
            parts.add(_WILDCARD)
        else:
            parts.add(token.lower())
    return frozenset(parts)


@dataclass
class RepoVisibilityGuard:
    """Flag-gated allowlist guard for synthetic-market target repos.

    Prefer :meth:`from_env` for production use.  Direct construction is
    available so unit tests can build instances without touching the
    process environment.

    Attributes:
        enabled: When ``False`` the guard is a transparent pass-through;
            :meth:`is_allowed` always returns ``True``.
        allowlist: Normalised ``owner/repo`` entries, or ``{"*"}`` for
            wildcard mode.  Empty when ``enabled`` is ``False``.
    """

    enabled: bool = False
    allowlist: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_env(cls) -> "RepoVisibilityGuard":
        """Build a guard from the current process environment."""
        if not _guard_enabled():
            return cls(enabled=False, allowlist=frozenset())
        raw = os.environ.get(_ALLOWLIST_VAR, "").strip()
        return cls(enabled=True, allowlist=_parse_allowlist(raw))

    def is_allowed(self, repo: str) -> bool:
        """Return ``True`` if *repo* is permitted as a market target.

        Always returns ``True`` when the guard is disabled.

        In wildcard mode (``allowlist == {"*"}``), any syntactically valid
        ``owner/repo`` string is accepted; malformed strings are rejected so
        they fail cleanly before reaching the GitHub resolver.
        """
        if not self.enabled:
            return True
        if _WILDCARD in self.allowlist:
            return bool(_REPO_RE.match(repo.strip()))
        return repo.strip().lower() in self.allowlist

    def require_allowed(self, repo: str) -> None:
        """Raise :exc:`RepoVisibilityError` if *repo* is not permitted.

        No-op when the guard is disabled.
        """
        if self.is_allowed(repo):
            return
        if not self.allowlist:
            raise RepoVisibilityError(
                f"Repo {repo!r} is not allowed: guard is enabled but "
                f"{_ALLOWLIST_VAR} is empty (fail-closed). "
                f"Set {_ALLOWLIST_VAR}=owner/repo or {_ALLOWLIST_VAR}=* "
                "to permit repos."
            )
        raise RepoVisibilityError(
            f"Repo {repo!r} is not in the market visibility allowlist. "
            f"Add it to {_ALLOWLIST_VAR} or set {_ALLOWLIST_VAR}=* "
            "to allow any syntactically valid repo."
        )


__all__ = [
    "RepoVisibilityError",
    "RepoVisibilityGuard",
]

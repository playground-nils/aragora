"""Centralized registry of documented receipt enforcement exemptions.

Provides a singleton ``ExemptionRegistry`` that tracks which
(domain, action_type) pairs are exempt from receipt enforcement and why.

Built-in exemptions cover read-only operations, health checks, and
metrics collection.  Additional exemptions can be registered at runtime
or at import time by calling ``ExemptionRegistry.get_instance().register(…)``.
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RegisteredExemption:
    """A single documented exemption from receipt enforcement."""

    domain: str  # "*" matches any domain
    action_pattern: str  # fnmatch-style pattern (e.g. "read_*")
    reason: str
    approved_by: str
    category: str  # "read_only", "metadata_only", "health_check", "system_internal"


class ExemptionRegistry:
    """Singleton registry for documented receipt enforcement exemptions."""

    _instance: ExemptionRegistry | None = None

    def __init__(self) -> None:
        self._exemptions: list[RegisteredExemption] = []
        self._register_builtins()

    # ------------------------------------------------------------------
    # Built-in exemptions
    # ------------------------------------------------------------------

    def _register_builtins(self) -> None:
        """Register exemptions for operations that legitimately don't need receipts."""
        builtins = [
            ("*", "read_*", "Read-only operations", "system", "read_only"),
            ("*", "list_*", "List operations", "system", "read_only"),
            ("*", "get_*", "Get operations", "system", "read_only"),
            ("*", "health_check", "Health check endpoints", "system", "health_check"),
            ("*", "metrics", "Metrics collection", "system", "system_internal"),
        ]
        for domain, pattern, reason, approved_by, category in builtins:
            self.register(domain, pattern, reason, approved_by, category)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(
        self,
        domain: str,
        action_pattern: str,
        reason: str,
        approved_by: str,
        category: str,
    ) -> RegisteredExemption:
        """Register a new exemption and return it."""
        exemption = RegisteredExemption(
            domain=domain,
            action_pattern=action_pattern,
            reason=reason,
            approved_by=approved_by,
            category=category,
        )
        self._exemptions.append(exemption)
        return exemption

    def is_exempt(
        self,
        domain: str,
        action_type: str,
    ) -> RegisteredExemption | None:
        """Return the first matching exemption, or ``None`` if the action is not exempt."""
        for exemption in self._exemptions:
            if exemption.domain != "*" and exemption.domain != domain:
                continue
            if fnmatch.fnmatch(action_type, exemption.action_pattern):
                return exemption
        return None

    @property
    def exemptions(self) -> list[RegisteredExemption]:
        """Return a copy of all registered exemptions."""
        return list(self._exemptions)

    # ------------------------------------------------------------------
    # Singleton accessor
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> ExemptionRegistry:
        """Return the singleton instance, creating it if needed."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None


__all__ = [
    "ExemptionRegistry",
    "RegisteredExemption",
]

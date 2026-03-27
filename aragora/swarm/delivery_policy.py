"""Execution-policy helpers for roadmap handoffs and queue creation."""

from __future__ import annotations

from typing import Any


_SENSITIVE_SCOPE_MARKERS: dict[str, tuple[str, ...]] = {
    "auth_rbac": (
        "/auth/",
        "auth/",
        "/rbac/",
        "rbac/",
        "oauth",
        "oidc",
        "saml",
        "mfa",
        "permission",
    ),
    "billing_payments": (
        "/billing/",
        "billing/",
        "/payments/",
        "payments/",
        "stripe",
        "invoice",
        "receipt",
    ),
    "secrets_credentials": (
        "secret",
        "credential",
        ".env",
        "token_store",
        "api_key",
        "private_key",
    ),
    "deployment_infra": (
        ".github/",
        "docker",
        "k8s",
        "kubernetes",
        "terraform",
        "deploy",
        "render.yaml",
        "netlify",
        "vercel",
        "cloudflare",
        "infra/",
        "infrastructure/",
    ),
    "security_enforcement": (
        "/security/",
        "security/",
        "crypto",
        "csrf",
        "xss",
        "vuln",
        "scanner",
    ),
    "destructive_migrations": (
        "/migrations/",
        "migrations/",
        "alembic",
        "schema/",
        "drop_",
        "truncate",
    ),
}

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def sensitive_scope_categories(file_scope: list[str] | None) -> list[str]:
    """Return matched sensitive-scope categories for the provided paths."""
    categories: list[str] = []
    for raw_path in file_scope or []:
        path = str(raw_path or "").strip().lower()
        if not path:
            continue
        for category, markers in _SENSITIVE_SCOPE_MARKERS.items():
            if any(marker in path for marker in markers):
                categories.append(category)
    return list(dict.fromkeys(categories))


def apply_delivery_policy(
    *,
    file_scope: list[str] | None,
    requested_risk: str,
    requested_merge_class: str,
    requested_autonomy_mode: str,
) -> dict[str, Any]:
    """Downgrade autonomy and merge behavior for sensitive scope."""
    requested_risk_normalized = _normalize_risk(requested_risk)
    requested_merge_normalized = _normalize_merge_class(requested_merge_class)
    requested_autonomy_normalized = _normalize_autonomy_mode(requested_autonomy_mode)

    categories = sensitive_scope_categories(file_scope)
    effective_risk = requested_risk_normalized
    effective_merge_class = requested_merge_normalized
    effective_autonomy_mode = requested_autonomy_normalized
    reasons: list[str] = []

    if categories:
        effective_risk = _max_risk(requested_risk_normalized, "high")
        effective_merge_class = "manual"
        effective_autonomy_mode = "checkpoint"
        reasons.extend(f"sensitive_scope:{category}" for category in categories)

    return {
        "requested_risk": requested_risk_normalized,
        "requested_merge_class": requested_merge_normalized,
        "requested_autonomy_mode": requested_autonomy_normalized,
        "effective_risk": effective_risk,
        "effective_merge_class": effective_merge_class,
        "effective_autonomy_mode": effective_autonomy_mode,
        "sensitive_scope_categories": categories,
        "downgraded": (
            effective_risk != requested_risk_normalized
            or effective_merge_class != requested_merge_normalized
            or effective_autonomy_mode != requested_autonomy_normalized
        ),
        "policy_reasons": reasons,
    }


def _normalize_risk(value: str | None) -> str:
    text = str(value or "").strip().lower()
    return text if text in _RISK_ORDER else "medium"


def _normalize_merge_class(value: str | None) -> str:
    text = str(value or "").strip().lower()
    return text if text in {"manual", "low_risk"} else "manual"


def _normalize_autonomy_mode(value: str | None) -> str:
    text = str(value or "").strip().lower()
    return (
        text if text in {"full-auto", "checkpoint", "adaptive", "fire_and_forget"} else "checkpoint"
    )


def _max_risk(left: str, right: str) -> str:
    if _RISK_ORDER.get(left, 1) >= _RISK_ORDER.get(right, 1):
        return left
    return right

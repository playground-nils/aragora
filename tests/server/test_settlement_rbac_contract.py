from __future__ import annotations

import json
from types import SimpleNamespace

from aragora.rbac.defaults.helpers import get_role_permissions
from aragora.rbac.middleware import RBACMiddleware
from aragora.rbac.models import AuthorizationContext
from aragora.server.handlers.settlements import SettlementHandler


def test_settlement_permissions_are_granted_to_expected_roles() -> None:
    member_permissions = get_role_permissions("member")
    admin_permissions = get_role_permissions("admin")
    owner_permissions = get_role_permissions("owner")

    assert "settlements.read" in member_permissions
    assert "settlements.write" not in member_permissions
    assert "settlements.read" in admin_permissions
    assert "settlements.write" in admin_permissions
    assert "settlements.read" in owner_permissions
    assert "settlements.write" in owner_permissions


def test_rbac_middleware_knows_settlement_routes() -> None:
    middleware = RBACMiddleware()

    assert middleware.get_required_permission("/api/v1/settlements", "GET") == "settlements.read"
    assert (
        middleware.get_required_permission("/api/v1/settlements/history", "GET")
        == "settlements.read"
    )
    assert (
        middleware.get_required_permission("/api/v1/settlements/agent/codex/accuracy", "GET")
        == "settlements.read"
    )
    assert (
        middleware.get_required_permission("/api/v1/settlements/settle-123/settle", "POST")
        == "settlements.write"
    )
    assert (
        middleware.get_required_permission("/api/v1/settlements/batch", "POST")
        == "settlements.write"
    )

    member_ctx = AuthorizationContext(
        user_id="member-1", permissions=get_role_permissions("member")
    )
    admin_ctx = AuthorizationContext(user_id="admin-1", permissions=get_role_permissions("admin"))

    allowed, _, permission = middleware.check_request("/api/v1/settlements", "GET", member_ctx)
    assert allowed is True
    assert permission == "settlements.read"

    allowed, _, permission = middleware.check_request(
        "/api/v1/settlements/settle-123/settle", "POST", admin_ctx
    )
    assert allowed is True
    assert permission == "settlements.write"

    allowed, reason, permission = middleware.check_request(
        "/api/v1/settlements/settle-123/settle", "POST", member_ctx
    )
    assert allowed is False
    assert permission == "settlements.write"
    assert "not granted" in reason


def test_settlement_post_handler_requires_write_permission(monkeypatch) -> None:
    settlement_handler = SettlementHandler(ctx={})
    member_ctx = SimpleNamespace(
        is_authenticated=True,
        user_id="member-1",
        role="member",
        error_reason=None,
    )
    http_handler = SimpleNamespace(headers={})

    monkeypatch.setattr(
        "aragora.billing.jwt_auth.extract_user_from_request",
        lambda handler, user_store=None: member_ctx,
    )

    result = settlement_handler.handle_post(
        "/api/v1/settlements/settle-123/settle", {}, http_handler
    )

    assert result is not None
    assert result.status_code == 403
    assert json.loads(result.body)["error"] == "Permission denied"

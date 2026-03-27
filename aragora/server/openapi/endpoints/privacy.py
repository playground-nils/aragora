"""Privacy endpoint definitions."""

from aragora.server.openapi.helpers import STANDARD_ERRORS, _ok_response

_privacy_preferences_schema = {
    "type": "object",
    "properties": {
        "do_not_sell": {"type": "boolean"},
        "marketing_opt_out": {"type": "boolean"},
        "analytics_opt_out": {"type": "boolean"},
        "third_party_sharing": {"type": "boolean"},
    },
}

_privacy_preferences_response = {
    "type": "object",
    "properties": {
        "preferences": _privacy_preferences_schema,
    },
}

_data_inventory_schema = {
    "type": "object",
    "properties": {
        "categories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "examples": {"type": "array", "items": {"type": "string"}},
                    "purpose": {"type": "string"},
                    "retention": {"type": "string"},
                },
            },
        },
        "third_party_sharing": {"type": "object"},
        "data_sold": {"type": "boolean"},
        "opt_out_available": {"type": "boolean"},
    },
}

_data_export_schema = {
    "type": "object",
    "properties": {
        "profile": {"type": "object"},
        "api_key": {"type": "object"},
        "organization": {"type": "object"},
        "oauth_providers": {"type": "array", "items": {"type": "object"}},
        "preferences": {"type": "object"},
        "audit_log": {"type": "array", "items": {"type": "object"}},
        "usage_summary": {"type": "object"},
        "consent_records": {"type": "object"},
        "_export_metadata": {
            "type": "object",
            "properties": {
                "exported_at": {"type": "string", "format": "date-time"},
                "format": {"type": "string"},
                "data_controller": {"type": "string"},
                "contact": {"type": "string", "format": "email"},
                "legal_basis": {"type": "string"},
            },
        },
    },
}

_delete_account_request_schema = {
    "type": "object",
    "required": ["password", "confirm"],
    "properties": {
        "password": {"type": "string"},
        "confirm": {"type": "boolean"},
        "reason": {"type": "string"},
    },
}

_delete_account_response_schema = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "deletion_id": {"type": "string"},
        "data_deleted": {"type": "array", "items": {"type": "string"}},
        "retention_note": {"type": "string"},
    },
}


PRIVACY_ENDPOINTS = {
    "/api/v1/privacy/export": {
        "get": {
            "tags": ["Privacy"],
            "summary": "Export user data",
            "operationId": "exportPrivacyData",
            "description": "Export the authenticated user's data in GDPR/CCPA-compliant format.",
            "security": [{"bearerAuth": []}],
            "parameters": [
                {
                    "name": "format",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string", "enum": ["json", "csv"], "default": "json"},
                    "description": "Export format.",
                }
            ],
            "responses": {
                "200": _ok_response("User data export", _data_export_schema),
                "401": STANDARD_ERRORS["401"],
            },
        }
    },
    "/api/v1/privacy/data-inventory": {
        "get": {
            "tags": ["Privacy"],
            "summary": "Get data inventory",
            "operationId": "getPrivacyDataInventory",
            "description": "Return the categories of personal data collected for the authenticated user.",
            "security": [{"bearerAuth": []}],
            "responses": {
                "200": _ok_response("Privacy data inventory", _data_inventory_schema),
                "401": STANDARD_ERRORS["401"],
            },
        }
    },
    "/api/v1/privacy/account": {
        "delete": {
            "tags": ["Privacy"],
            "summary": "Delete account",
            "operationId": "deletePrivacyAccount",
            "description": "Delete the authenticated user's account and associated personal data.",
            "security": [{"bearerAuth": []}],
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": _delete_account_request_schema}},
            },
            "responses": {
                "200": _ok_response("Account deletion scheduled", _delete_account_response_schema),
                "400": STANDARD_ERRORS["400"],
                "401": STANDARD_ERRORS["401"],
                "403": STANDARD_ERRORS["403"],
            },
        }
    },
    "/api/v1/privacy/preferences": {
        "get": {
            "tags": ["Privacy"],
            "summary": "Get privacy preferences",
            "operationId": "getPrivacyPreferences",
            "description": "Return the authenticated user's current privacy preferences.",
            "security": [{"bearerAuth": []}],
            "responses": {
                "200": _ok_response("Privacy preferences", _privacy_preferences_response),
                "401": STANDARD_ERRORS["401"],
            },
        },
        "post": {
            "tags": ["Privacy"],
            "summary": "Update privacy preferences",
            "operationId": "updatePrivacyPreferences",
            "description": "Update the authenticated user's privacy preferences.",
            "security": [{"bearerAuth": []}],
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": _privacy_preferences_schema}},
            },
            "responses": {
                "200": _ok_response("Privacy preferences updated", _privacy_preferences_response),
                "400": STANDARD_ERRORS["400"],
                "401": STANDARD_ERRORS["401"],
            },
        },
    },
}

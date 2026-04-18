"""
Settlements Namespace API

Provides methods for managing debate claim settlements.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..client import AragoraAsyncClient, AragoraClient


class SettlementsAPI:
    """Synchronous Settlements API."""

    def __init__(self, client: AragoraClient):
        self._client = client

    def list_pending(self, **params: Any) -> dict[str, Any]:
        """List pending settlements."""
        return self._client.request("GET", "/api/v1/settlements", params=params or None)

    def get_history(self, **params: Any) -> dict[str, Any]:
        """Get settlement history."""
        return self._client.request("GET", "/api/v1/settlements/history", params=params or None)

    def get_summary(self) -> dict[str, Any]:
        """Get settlement summary statistics."""
        return self._client.request("GET", "/api/v1/settlements/summary")

    def get(self, settlement_id: str) -> dict[str, Any]:
        """Get a settlement by ID."""
        return self._client.request("GET", f"/api/v1/settlements/{settlement_id}")

    def get_agent_accuracy(self, agent: str) -> dict[str, Any]:
        """Get accuracy statistics for an agent."""
        return self._client.request("GET", f"/api/v1/settlements/agent/{agent}/accuracy")

    def settle(self, settlement_id: str, **kwargs: Any) -> dict[str, Any]:
        """Submit a settlement outcome."""
        return self._client.request(
            "POST",
            f"/api/v1/settlements/{settlement_id}/settle",
            json=kwargs,
        )

    def settle_batch(self, **kwargs: Any) -> dict[str, Any]:
        """Settle multiple claims in one request."""
        return self._client.request("POST", "/api/v1/settlements/batch", json=kwargs)


class AsyncSettlementsAPI:
    """Asynchronous Settlements API."""

    def __init__(self, client: AragoraAsyncClient):
        self._client = client

    async def list_pending(self, **params: Any) -> dict[str, Any]:
        """List pending settlements."""
        return await self._client.request("GET", "/api/v1/settlements", params=params or None)

    async def get_history(self, **params: Any) -> dict[str, Any]:
        """Get settlement history."""
        return await self._client.request(
            "GET", "/api/v1/settlements/history", params=params or None
        )

    async def get_summary(self) -> dict[str, Any]:
        """Get settlement summary statistics."""
        return await self._client.request("GET", "/api/v1/settlements/summary")

    async def get(self, settlement_id: str) -> dict[str, Any]:
        """Get a settlement by ID."""
        return await self._client.request("GET", f"/api/v1/settlements/{settlement_id}")

    async def get_agent_accuracy(self, agent: str) -> dict[str, Any]:
        """Get accuracy statistics for an agent."""
        return await self._client.request("GET", f"/api/v1/settlements/agent/{agent}/accuracy")

    async def settle(self, settlement_id: str, **kwargs: Any) -> dict[str, Any]:
        """Submit a settlement outcome."""
        return await self._client.request(
            "POST",
            f"/api/v1/settlements/{settlement_id}/settle",
            json=kwargs,
        )

    async def settle_batch(self, **kwargs: Any) -> dict[str, Any]:
        """Settle multiple claims in one request."""
        return await self._client.request("POST", "/api/v1/settlements/batch", json=kwargs)

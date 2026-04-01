"""Tests for BlockchainIdentityBridge JSON file persistence.

Verifies that blockchain identity links are persisted to a JSON file
and can be restored when the bridge is re-created.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aragora.control_plane.blockchain_identity import (
    AgentBlockchainLink,
    BlockchainIdentityBridge,
)


class TestBlockchainIdentityPersistence:
    """Tests for JSON file-based persistence of blockchain identity links."""

    @pytest.fixture
    def mock_provider(self):
        """Create mock Web3Provider."""
        provider = MagicMock()
        config = MagicMock()
        config.chain_id = 1
        provider.get_config.return_value = config
        return provider

    @pytest.fixture
    def persistence_path(self, tmp_path: Path) -> Path:
        return tmp_path / "blockchain_links.json"

    def test_persistence_path_creates_file_on_save(self, mock_provider, persistence_path):
        """Saving state creates the JSON file."""
        bridge = BlockchainIdentityBridge(
            provider=mock_provider,
            persistence_path=persistence_path,
        )
        # Manually add a link
        link = AgentBlockchainLink(
            aragora_agent_id="agent-1",
            chain_id=1,
            token_id=42,
            owner_address="0xabc",
            verified=True,
            linked_at="2026-01-01T00:00:00",
        )
        bridge._links["agent-1"] = link
        bridge._token_to_agent[(1, 42)] = "agent-1"
        bridge._save_state()

        assert persistence_path.exists()
        data = json.loads(persistence_path.read_text())
        assert len(data["links"]) == 1
        assert data["links"][0]["aragora_agent_id"] == "agent-1"

    def test_load_state_restores_links(self, mock_provider, persistence_path):
        """Loading state restores links from JSON file."""
        # Write state manually
        state = {
            "links": [
                {
                    "aragora_agent_id": "agent-1",
                    "chain_id": 1,
                    "token_id": 42,
                    "owner_address": "0xabc",
                    "verified": True,
                    "linked_at": "2026-01-01T00:00:00",
                    "metadata": {"role": "reviewer"},
                }
            ]
        }
        persistence_path.write_text(json.dumps(state))

        bridge = BlockchainIdentityBridge(
            provider=mock_provider,
            persistence_path=persistence_path,
        )

        assert "agent-1" in bridge._links
        link = bridge._links["agent-1"]
        assert link.chain_id == 1
        assert link.token_id == 42
        assert link.owner_address == "0xabc"
        assert link.verified is True
        assert link.metadata == {"role": "reviewer"}

        # Token-to-agent index should be rebuilt
        assert bridge._token_to_agent[(1, 42)] == "agent-1"

    @pytest.mark.asyncio
    async def test_link_agent_persists(self, mock_provider, persistence_path):
        """link_agent should persist state after linking."""
        bridge = BlockchainIdentityBridge(
            provider=mock_provider,
            persistence_path=persistence_path,
        )

        mock_identity = MagicMock()
        mock_identity.owner = "0xdef"

        with patch.object(bridge, "_get_identity_contract") as mock_contract:
            mock_contract.return_value.get_agent.return_value = mock_identity
            await bridge.link_agent("agent-2", token_id=99)

        assert persistence_path.exists()
        data = json.loads(persistence_path.read_text())
        assert len(data["links"]) == 1
        assert data["links"][0]["aragora_agent_id"] == "agent-2"
        assert data["links"][0]["token_id"] == 99

    @pytest.mark.asyncio
    async def test_unlink_agent_persists(self, mock_provider, persistence_path):
        """unlink_agent should persist state after unlinking."""
        bridge = BlockchainIdentityBridge(
            provider=mock_provider,
            persistence_path=persistence_path,
        )

        # Pre-populate
        link = AgentBlockchainLink(
            aragora_agent_id="agent-3",
            chain_id=1,
            token_id=55,
            owner_address="0x123",
            verified=True,
        )
        bridge._links["agent-3"] = link
        bridge._token_to_agent[(1, 55)] = "agent-3"
        bridge._save_state()

        result = await bridge.unlink_agent("agent-3")
        assert result is True

        data = json.loads(persistence_path.read_text())
        assert len(data["links"]) == 0

    def test_no_persistence_path_means_no_file(self, mock_provider):
        """When no persistence_path is given, no file operations occur."""
        bridge = BlockchainIdentityBridge(provider=mock_provider)
        # Should not raise
        bridge._save_state()
        bridge._load_state()

    def test_corrupted_file_handled_gracefully(self, mock_provider, persistence_path):
        """Corrupted JSON file should not crash, just log warning."""
        persistence_path.write_text("not valid json {{{")

        # Should not raise
        bridge = BlockchainIdentityBridge(
            provider=mock_provider,
            persistence_path=persistence_path,
        )
        assert len(bridge._links) == 0

    def test_missing_file_handled_gracefully(self, mock_provider, tmp_path):
        """Missing file should not crash, just start with empty state."""
        missing_path = tmp_path / "does_not_exist.json"
        bridge = BlockchainIdentityBridge(
            provider=mock_provider,
            persistence_path=missing_path,
        )
        assert len(bridge._links) == 0

    def test_roundtrip_multiple_links(self, mock_provider, persistence_path):
        """Multiple links survive a save/load roundtrip."""
        bridge1 = BlockchainIdentityBridge(
            provider=mock_provider,
            persistence_path=persistence_path,
        )

        for i in range(5):
            link = AgentBlockchainLink(
                aragora_agent_id=f"agent-{i}",
                chain_id=1,
                token_id=100 + i,
                owner_address=f"0x{i:040x}",
                verified=True,
            )
            bridge1._links[f"agent-{i}"] = link
            bridge1._token_to_agent[(1, 100 + i)] = f"agent-{i}"

        bridge1._save_state()

        # Create fresh bridge from the same file
        bridge2 = BlockchainIdentityBridge(
            provider=mock_provider,
            persistence_path=persistence_path,
        )

        assert len(bridge2._links) == 5
        assert len(bridge2._token_to_agent) == 5
        for i in range(5):
            assert f"agent-{i}" in bridge2._links
            assert bridge2._token_to_agent[(1, 100 + i)] == f"agent-{i}"

    @pytest.mark.asyncio
    async def test_verify_link_persists(self, mock_provider, persistence_path):
        """verify_link should persist updated state."""
        bridge = BlockchainIdentityBridge(
            provider=mock_provider,
            persistence_path=persistence_path,
        )

        link = AgentBlockchainLink(
            aragora_agent_id="agent-v",
            chain_id=1,
            token_id=77,
            owner_address="0xold",
            verified=False,
        )
        bridge._links["agent-v"] = link
        bridge._token_to_agent[(1, 77)] = "agent-v"

        mock_identity = MagicMock()
        mock_identity.owner = "0xnew"

        with patch.object(bridge, "_get_identity_contract") as mock_contract:
            mock_contract.return_value.get_agent.return_value = mock_identity
            result = await bridge.verify_link("agent-v")

        assert result is True
        data = json.loads(persistence_path.read_text())
        assert data["links"][0]["owner_address"] == "0xnew"
        assert data["links"][0]["verified"] is True

"""Tests for aragora tasks CLI command."""

from __future__ import annotations

import argparse
import json
from unittest.mock import MagicMock, patch

import pytest

from aragora.cli.commands.tasks import add_tasks_parser, cmd_tasks


@pytest.fixture
def parser():
    """Build a parser with the tasks subcommand registered."""
    root = argparse.ArgumentParser()
    sub = root.add_subparsers(dest="command")
    add_tasks_parser(sub)
    return root


class TestParserRegistration:
    def test_tasks_parser_registered(self, parser):
        args = parser.parse_args(["tasks", "list"])
        assert args.tasks_command == "list"

    def test_tasks_stats_subcommand(self, parser):
        args = parser.parse_args(["tasks", "stats"])
        assert args.tasks_command == "stats"

    def test_tasks_show_with_id(self, parser):
        args = parser.parse_args(["tasks", "show", "w-123"])
        assert args.tasks_command == "show"
        assert args.task_id == "w-123"

    def test_tasks_claim_with_ttl(self, parser):
        args = parser.parse_args(["tasks", "claim", "w-1", "--ttl", "4"])
        assert args.tasks_command == "claim"
        assert args.task_id == "w-1"
        assert args.ttl == 4.0

    def test_tasks_leases_json(self, parser):
        args = parser.parse_args(["tasks", "leases", "--format", "json"])
        assert args.tasks_command == "leases"
        assert args.output_format == "json"


class TestListCommand:
    def test_list_json_output(self, capsys, parser):
        mock_item = MagicMock()
        mock_item.to_dict.return_value = {
            "id": "w-1",
            "status": "pending",
            "computed_priority": 10,
            "title": "Fix bug",
        }
        mock_queue = MagicMock()
        mock_queue.list_items.return_value = [mock_item]
        args = parser.parse_args(["tasks", "list", "--format", "json"])
        with patch(
            "aragora.nomic.global_work_queue.GlobalWorkQueue",
            return_value=mock_queue,
        ):
            args.func(args)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert len(parsed) == 1
        assert parsed[0]["id"] == "w-1"

    def test_list_table_output(self, capsys, parser):
        mock_item = MagicMock()
        mock_item.to_dict.return_value = {
            "id": "w-1",
            "status": "pending",
            "computed_priority": 10,
            "title": "Fix bug",
        }
        mock_queue = MagicMock()
        mock_queue.list_items.return_value = [mock_item]
        args = parser.parse_args(["tasks", "list"])
        with patch(
            "aragora.nomic.global_work_queue.GlobalWorkQueue",
            return_value=mock_queue,
        ):
            args.func(args)
        captured = capsys.readouterr()
        assert "w-1" in captured.out
        assert "pending" in captured.out


class TestStatsCommand:
    def test_stats_output(self, capsys, parser):
        mock_queue = MagicMock()
        mock_queue.get_statistics.return_value = {
            "total_items": 10,
            "pending_items": 5,
        }
        args = parser.parse_args(["tasks", "stats"])
        with patch(
            "aragora.nomic.global_work_queue.GlobalWorkQueue",
            return_value=mock_queue,
        ):
            args.func(args)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["total_items"] == 10


class TestLeasesCommand:
    def test_leases_empty(self, capsys, parser):
        mock_store = MagicMock()
        mock_store.list_active_leases.return_value = []
        args = parser.parse_args(["tasks", "leases"])
        with patch(
            "aragora.nomic.dev_coordination.DevCoordinationStore",
            return_value=mock_store,
        ):
            args.func(args)
        captured = capsys.readouterr()
        assert "Lease ID" in captured.out

    def test_leases_json(self, capsys, parser):
        mock_lease = MagicMock()
        mock_lease.lease_id = "l-1"
        mock_lease.task_id = "t-1"
        mock_lease.owner_agent = "claude"
        mock_lease.expires_at = "2026-03-18T20:00:00+00:00"
        mock_store = MagicMock()
        mock_store.list_active_leases.return_value = [mock_lease]
        args = parser.parse_args(["tasks", "leases", "--format", "json"])
        with patch(
            "aragora.nomic.dev_coordination.DevCoordinationStore",
            return_value=mock_store,
        ):
            args.func(args)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert len(parsed) == 1
        assert parsed[0]["lease_id"] == "l-1"


class TestSalvageCommand:
    def test_salvage_empty(self, capsys, parser):
        mock_store = MagicMock()
        mock_store.list_salvage_candidates.return_value = []
        args = parser.parse_args(["tasks", "salvage"])
        with patch(
            "aragora.nomic.dev_coordination.DevCoordinationStore",
            return_value=mock_store,
        ):
            args.func(args)
        captured = capsys.readouterr()
        assert "Candidate ID" in captured.out


class TestNoSubcommand:
    def test_no_subcommand_exits(self, parser):
        args = parser.parse_args(["tasks"])
        with pytest.raises(SystemExit):
            args.func(args)

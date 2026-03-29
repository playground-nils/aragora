"""Regression coverage for protocol package import boundaries."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path


def test_debate_import_survives_missing_httpx() -> None:
    """Importing debate modules should not require the optional A2A httpx client."""
    project_root = Path(__file__).resolve().parents[2]
    script = textwrap.dedent(
        """
        import importlib.abc
        import importlib
        import sys

        class BlockHTTPX(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "httpx" or fullname.startswith("httpx."):
                    raise ImportError("httpx unavailable")
                return None

        sys.meta_path.insert(0, BlockHTTPX())

        module = importlib.import_module("aragora.debate.orchestrator_init")
        assert module.run_init_subsystems is not None
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout

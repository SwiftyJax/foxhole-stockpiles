"""Tests for the ``python -m foxhole_stockpiles`` entry point.

Ensures the package ``__main__`` module is wired to the Typer CLI and that the
``fs`` command can be invoked via module syntax. The ``fs_tools`` command entry
points are covered by ``fs_tools/tests/commands/test_main_modules.py``.
"""

import subprocess
import sys

from foxhole_stockpiles import __main__ as package_main


class TestPackageMainModule:
    """Test suite for the package-level ``__main__`` entry point."""

    def test_main_module_help(self) -> None:
        """``python -m foxhole_stockpiles --help`` lists the CLI commands."""
        result = subprocess.run(
            [sys.executable, "-m", "foxhole_stockpiles", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "Foxhole Stockpiles" in result.stdout
        assert "scan" in result.stdout

    def test_main_module_version(self) -> None:
        """``python -m foxhole_stockpiles --version`` prints the version."""
        result = subprocess.run(
            [sys.executable, "-m", "foxhole_stockpiles", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "Foxhole Stockpiles v" in result.stdout

    def test_main_callable_exported(self) -> None:
        """The package ``__main__`` module exposes a callable ``main``."""
        assert callable(package_main.main)

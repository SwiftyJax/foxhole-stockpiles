"""Tests for the ``fs`` command __main__.py entry points.

This module tests that the main ``foxhole_stockpiles`` command modules can be
invoked via ``python -m`` syntax, ensuring the ``__main__.py`` files are properly
configured and importable. The ``fs_tools`` command entry points are covered by
``fs_tools/tests/commands/test_main_modules.py``.
"""

import subprocess
import sys
from pathlib import Path

import pytest


class TestMainModules:
    """Test suite for command module entry points."""

    def test_fs_main_module(self) -> None:
        """Test that foxhole_stockpiles.commands.fs can be run as module."""
        result = subprocess.run(
            [sys.executable, "-m", "foxhole_stockpiles.commands.fs", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "Foxhole Stockpiles" in result.stdout or "usage" in result.stdout.lower()

    def test_api_server_main_module(self) -> None:
        """Test that foxhole_stockpiles.commands.api_server can be run as module."""
        result = subprocess.run(
            [sys.executable, "-m", "foxhole_stockpiles.commands.api_server", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "API Server" in result.stdout or "usage" in result.stdout.lower()

    def test_stockpile_scanner_main_module(self) -> None:
        """Test that foxhole_stockpiles.commands.stockpile_scanner can be run as module."""
        result = subprocess.run(
            [sys.executable, "-m", "foxhole_stockpiles.commands.stockpile_scanner", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "Scanner" in result.stdout

    def test_update_config_main_module(self) -> None:
        """Test that foxhole_stockpiles.commands.update_config can be run as module."""
        result = subprocess.run(
            [sys.executable, "-m", "foxhole_stockpiles.commands.update_config", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "update" in result.stdout.lower()


class TestMainModuleImports:
    """Test suite for __main__.py module imports."""

    def test_fs_main_import(self) -> None:
        """Test importing fs __main__ module."""
        from foxhole_stockpiles.commands.fs import __main__ as fs_main

        assert hasattr(fs_main, "main")

    def test_api_server_main_import(self) -> None:
        """Test importing api_server __main__ module."""
        from foxhole_stockpiles.commands.api_server import __main__ as api_server_main

        assert hasattr(api_server_main, "main")

    def test_stockpile_scanner_main_import(self) -> None:
        """Test importing stockpile_scanner __main__ module."""
        from foxhole_stockpiles.commands.stockpile_scanner import (
            __main__ as stockpile_scanner_main,
        )

        assert hasattr(stockpile_scanner_main, "main")

    def test_update_config_main_import(self) -> None:
        """Test importing update_config __main__ module."""
        from foxhole_stockpiles.commands.update_config import __main__ as update_config_main

        assert hasattr(update_config_main, "main")


class TestMainModuleFiles:
    """Test that all __main__.py files exist and are valid Python."""

    MAIN_MODULE_PATHS = [
        "foxhole_stockpiles/commands/fs/__main__.py",
        "foxhole_stockpiles/commands/api_server/__main__.py",
        "foxhole_stockpiles/commands/stockpile_scanner/__main__.py",
        "foxhole_stockpiles/commands/update_config/__main__.py",
    ]

    @pytest.mark.parametrize("module_path", MAIN_MODULE_PATHS)
    def test_main_file_exists(self, module_path: str) -> None:
        """Test that __main__.py file exists.

        Args:
            module_path (str): Path to the __main__.py file.
        """
        # Get project root (assumes test is in tests/commands/)
        project_root = Path(__file__).parent.parent.parent
        main_file = project_root / module_path

        assert main_file.exists(), f"__main__.py not found at {main_file}"
        assert main_file.is_file(), f"__main__.py at {main_file} is not a file"

    @pytest.mark.parametrize("module_path", MAIN_MODULE_PATHS)
    def test_main_file_contains_required_code(self, module_path: str) -> None:
        """Test that __main__.py contains required structure.

        Args:
            module_path (str): Path to the __main__.py file.
        """
        project_root = Path(__file__).parent.parent.parent
        main_file = project_root / module_path

        content = main_file.read_text()

        # Should have if __name__ == "__main__": guard
        assert '__name__ == "__main__"' in content or "__name__ == '__main__'" in content
        # Should import or reference main function
        assert "main" in content.lower()

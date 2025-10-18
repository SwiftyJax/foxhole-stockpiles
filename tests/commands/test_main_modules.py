"""Tests for all command __main__.py entry points.

This module tests that all command modules can be invoked via python -m syntax,
ensuring the __main__.py files are properly configured and importable.
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

    def test_database_builder_main_module(self) -> None:
        """Test that foxhole_stockpiles.commands.database_builder can be run as module."""
        result = subprocess.run(
            [sys.executable, "-m", "foxhole_stockpiles.commands.database_builder", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "Database" in result.stdout

    def test_generate_templates_main_module(self) -> None:
        """Test that foxhole_stockpiles.commands.generate_templates can be run as module."""
        result = subprocess.run(
            [sys.executable, "-m", "foxhole_stockpiles.commands.generate_templates", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "template" in result.stdout.lower()

    def test_uasset_extractor_main_module(self) -> None:
        """Test that foxhole_stockpiles.commands.uasset_extractor can be run as module."""
        result = subprocess.run(
            [sys.executable, "-m", "foxhole_stockpiles.commands.uasset_extractor", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "extract" in result.stdout.lower()

    def test_candidate_inspector_main_module(self) -> None:
        """Test that foxhole_stockpiles.commands.candidate_inspector can be run as module."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "foxhole_stockpiles.commands.candidate_inspector",
                "--help",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "inspect" in result.stdout.lower()

    def test_add_icon_main_module(self) -> None:
        """Test that foxhole_stockpiles.commands.add_icon can be run as module."""
        result = subprocess.run(
            [sys.executable, "-m", "foxhole_stockpiles.commands.add_icon", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "icon" in result.stdout.lower()


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

    def test_database_builder_main_import(self) -> None:
        """Test importing database_builder __main__ module."""
        from foxhole_stockpiles.commands.database_builder import (
            __main__ as database_builder_main,
        )

        assert hasattr(database_builder_main, "main")

    def test_generate_templates_main_import(self) -> None:
        """Test importing generate_templates __main__ module."""
        from foxhole_stockpiles.commands.generate_templates import (
            __main__ as generate_templates_main,
        )

        assert hasattr(generate_templates_main, "main")

    def test_uasset_extractor_main_import(self) -> None:
        """Test importing uasset_extractor __main__ module."""
        from foxhole_stockpiles.commands.uasset_extractor import (
            __main__ as uasset_extractor_main,
        )

        assert hasattr(uasset_extractor_main, "main")

    def test_candidate_inspector_main_import(self) -> None:
        """Test importing candidate_inspector __main__ module."""
        from foxhole_stockpiles.commands.candidate_inspector import (
            __main__ as candidate_inspector_main,
        )

        assert hasattr(candidate_inspector_main, "main")

    def test_add_icon_main_import(self) -> None:
        """Test importing add_icon __main__ module."""
        from foxhole_stockpiles.commands.add_icon import __main__ as add_icon_main

        assert hasattr(add_icon_main, "main")


class TestMainModuleFiles:
    """Test that all __main__.py files exist and are valid Python."""

    @pytest.mark.parametrize(
        "module_path",
        [
            "foxhole_stockpiles/commands/fs/__main__.py",
            "foxhole_stockpiles/commands/api_server/__main__.py",
            "foxhole_stockpiles/commands/stockpile_scanner/__main__.py",
            "foxhole_stockpiles/commands/database_builder/__main__.py",
            "foxhole_stockpiles/commands/generate_templates/__main__.py",
            "foxhole_stockpiles/commands/uasset_extractor/__main__.py",
            "foxhole_stockpiles/commands/candidate_inspector/__main__.py",
            "foxhole_stockpiles/commands/add_icon/__main__.py",
        ],
    )
    def test_main_file_exists(self, module_path: str) -> None:
        """Test that __main__.py file exists.

        Args:
            module_path: Path to the __main__.py file
        """
        # Get project root (assumes test is in tests/commands/)
        project_root = Path(__file__).parent.parent.parent
        main_file = project_root / module_path

        assert main_file.exists(), f"__main__.py not found at {main_file}"
        assert main_file.is_file(), f"__main__.py at {main_file} is not a file"

    @pytest.mark.parametrize(
        "module_path",
        [
            "foxhole_stockpiles/commands/fs/__main__.py",
            "foxhole_stockpiles/commands/api_server/__main__.py",
            "foxhole_stockpiles/commands/stockpile_scanner/__main__.py",
            "foxhole_stockpiles/commands/database_builder/__main__.py",
            "foxhole_stockpiles/commands/generate_templates/__main__.py",
            "foxhole_stockpiles/commands/uasset_extractor/__main__.py",
            "foxhole_stockpiles/commands/candidate_inspector/__main__.py",
            "foxhole_stockpiles/commands/add_icon/__main__.py",
        ],
    )
    def test_main_file_contains_required_code(self, module_path: str) -> None:
        """Test that __main__.py contains required structure.

        Args:
            module_path: Path to the __main__.py file
        """
        project_root = Path(__file__).parent.parent.parent
        main_file = project_root / module_path

        content = main_file.read_text()

        # Should have if __name__ == "__main__": guard
        assert '__name__ == "__main__"' in content or "__name__ == '__main__'" in content
        # Should import or reference main function
        assert "main" in content.lower()

"""Tests for the root Typer application (``foxhole_stockpiles.cli.app``).

Covers help output, alias registration, the ``--version`` flag, and the
no-subcommand GUI launch behaviour.
"""

from unittest.mock import patch

from typer.testing import CliRunner

from foxhole_stockpiles import __version__
from foxhole_stockpiles.cli.app import app

runner = CliRunner()


class TestRootHelp:
    """Test suite for the root ``fs`` help output."""

    def test_help_lists_canonical_commands(self) -> None:
        """Help text lists the canonical subcommands."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        for command in ("scan", "sav", "serve", "gui"):
            assert command in result.output

    def test_help_hides_aliases(self) -> None:
        """Hidden alias commands do not appear in the help listing."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        for alias in ("scanner", "process-sav"):
            assert alias not in result.output


class TestVersion:
    """Test suite for the ``--version`` flag."""

    def test_version_flag(self) -> None:
        """``--version`` prints the version and exits cleanly."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert f"Foxhole Stockpiles v{__version__}" in result.output


class TestNoSubcommand:
    """Test suite for invoking ``fs`` with no subcommand."""

    def test_no_args_launches_gui(self) -> None:
        """Running with no subcommand launches the GUI."""
        with patch("foxhole_stockpiles.cli.commands.gui.launch_gui") as mock_launch:
            result = runner.invoke(app, [])

            assert result.exit_code == 0
            mock_launch.assert_called_once()


class TestAliases:
    """Test suite for command alias resolution."""

    def test_scanner_alias_resolves_to_scan(self) -> None:
        """The ``scanner`` alias exposes the same options as ``scan``."""
        result = runner.invoke(app, ["scanner", "--help"])

        assert result.exit_code == 0
        assert "--image" in result.output

    def test_server_alias_resolves_to_serve(self) -> None:
        """The ``server`` alias exposes the same options as ``serve``."""
        result = runner.invoke(app, ["server", "--help"])

        assert result.exit_code == 0
        assert "--host" in result.output


class TestMainEntryPoint:
    """Test suite for the ``main`` entry point."""

    def test_main_calls_freeze_support(self) -> None:
        """``main`` invokes ``multiprocessing.freeze_support`` before the app."""
        import multiprocessing
        import sys

        # The ``cli`` package re-exports ``app``, which shadows the submodule on
        # attribute access; fetch the real module object from ``sys.modules``.
        app_module = sys.modules["foxhole_stockpiles.cli.app"]

        with (
            patch.object(multiprocessing, "freeze_support") as mock_freeze,
            patch.object(app_module, "app") as mock_app,
        ):
            app_module.main()

            mock_freeze.assert_called_once()
            mock_app.assert_called_once()

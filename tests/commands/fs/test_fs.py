"""Tests for commands.fs.fs module.

This module contains comprehensive tests for the unified CLI dispatcher,
including command resolution, alias handling, and command execution.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from foxhole_stockpiles.commands.fs.fs import CLIDispatcher, main


class TestCLIDispatcherInitialization:
    """Test suite for CLIDispatcher initialization.

    This class contains tests for CLIDispatcher instance creation
    and available commands discovery.
    """

    async def test_initialization(self) -> None:
        """Test CLIDispatcher initialization."""
        dispatcher = CLIDispatcher()

        assert dispatcher._commands is not None
        assert len(dispatcher._commands) > 0

    async def test_available_commands(self) -> None:
        """Test that all expected commands are available."""
        dispatcher = CLIDispatcher()
        commands = dispatcher.list_commands()

        # Verify core commands exist
        assert "scanner" in commands
        assert "database-builder" in commands
        assert "generate-templates" in commands
        assert "extract-assets" in commands
        assert "inspect" in commands


class TestCLIDispatcherAliases:
    """Test suite for CLIDispatcher alias resolution.

    This class contains tests for command alias resolution and
    canonical name lookup.
    """

    async def test_resolve_command_direct_match(self) -> None:
        """Test resolving command with direct name match."""
        dispatcher = CLIDispatcher()

        result = dispatcher.resolve_command_alias("scanner")

        assert result == "scanner"

    async def test_resolve_command_alias(self) -> None:
        """Test resolving command with alias."""
        dispatcher = CLIDispatcher()

        result = dispatcher.resolve_command_alias("scan")

        assert result == "scanner"

    async def test_resolve_command_not_found(self) -> None:
        """Test resolving non-existent command."""
        dispatcher = CLIDispatcher()

        result = dispatcher.resolve_command_alias("nonexistent")

        assert result is None

    async def test_get_command_info_by_name(self) -> None:
        """Test getting command info by canonical name."""
        dispatcher = CLIDispatcher()

        cmd_info = dispatcher.get_command_info("scanner")

        assert cmd_info is not None
        assert cmd_info.module == "foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner"

    async def test_get_command_info_by_alias(self) -> None:
        """Test getting command info by alias."""
        dispatcher = CLIDispatcher()

        cmd_info = dispatcher.get_command_info("scan")

        assert cmd_info is not None
        assert cmd_info.module == "foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner"

    async def test_get_command_info_not_found(self) -> None:
        """Test getting command info for non-existent command."""
        dispatcher = CLIDispatcher()

        cmd_info = dispatcher.get_command_info("nonexistent")

        assert cmd_info is None


class TestCLIDispatcherHelp:
    """Test suite for CLIDispatcher help generation.

    This class contains tests for help text generation.
    """

    async def test_get_help(self) -> None:
        """Test generating help text."""
        dispatcher = CLIDispatcher()

        help_text = dispatcher.get_help()

        assert "Foxhole Stockpiles" in help_text
        assert "scanner" in help_text
        assert "database-builder" in help_text
        assert "Usage:" in help_text

    async def test_get_help_includes_aliases(self) -> None:
        """Test that help text includes command aliases."""
        dispatcher = CLIDispatcher()

        help_text = dispatcher.get_help()

        assert "Aliases:" in help_text


class TestCLIDispatcherExecution:
    """Test suite for CLIDispatcher command execution.

    This class contains tests for command execution and module importing.
    """

    def test_execute_command_success(self) -> None:
        """Test successful command execution."""
        with (
            patch("foxhole_stockpiles.commands.fs.fs.asyncio.run") as mock_asyncio_run,
            patch("foxhole_stockpiles.commands.fs.fs.importlib.import_module") as mock_import,
        ):
            # Mock the module and main function
            mock_module = MagicMock()

            async def mock_main() -> None:
                return None

            mock_module.main = mock_main
            mock_import.return_value = mock_module
            mock_asyncio_run.return_value = None

            dispatcher = CLIDispatcher()
            dispatcher.execute_command("scanner")

            # Verify asyncio.run was called with the main function
            assert mock_asyncio_run.called

    def test_execute_command_not_found(self) -> None:
        """Test executing non-existent command."""
        dispatcher = CLIDispatcher()

        with pytest.raises(SystemExit) as exc_info:
            dispatcher.execute_command("nonexistent")

        # Should have exited with code 1
        assert exc_info.value.code == 1

    @patch("foxhole_stockpiles.commands.fs.fs.importlib.import_module")
    def test_execute_command_import_error(self, mock_import: Mock) -> None:
        """Test command execution when import fails.

        Args:
            mock_import (Mock): Mocked importlib.import_module function.
        """
        dispatcher = CLIDispatcher()

        mock_import.side_effect = ImportError("Module not found")

        with pytest.raises(SystemExit) as exc_info:
            dispatcher.execute_command("scanner")

        # Should have exited with code 1
        assert exc_info.value.code == 1


class TestMainFunction:
    """Test suite for the main CLI entry point.

    This class contains tests for the main function including
    argument parsing and help display.
    """

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "--help"])
    @patch("builtins.print")
    def test_main_with_help_flag(self, mock_print: Mock) -> None:
        """Test main function with --help flag.

        Args:
            mock_print (Mock): Mocked print function.
        """
        main()

        # Should print help text
        assert mock_print.called
        call_args = mock_print.call_args[0][0]
        assert "Foxhole Stockpiles" in call_args

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs"])
    @patch("builtins.print")
    def test_main_with_no_args(self, mock_print: Mock) -> None:
        """Test main function with no arguments.

        Args:
            mock_print (Mock): Mocked print function.
        """
        main()

        # Should print help text
        assert mock_print.called
        call_args = mock_print.call_args[0][0]
        assert "Foxhole Stockpiles" in call_args

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "--version"])
    @patch("builtins.print")
    def test_main_with_version_flag(self, mock_print: Mock) -> None:
        """Test main function with --version flag.

        Args:
            mock_print (Mock): Mocked print function.
        """
        main()

        # Should print version
        assert mock_print.called
        call_args = mock_print.call_args[0][0]
        assert "Foxhole Stockpiles" in call_args

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "scanner", "--help"])
    @patch("foxhole_stockpiles.commands.fs.fs.CLIDispatcher.execute_command")
    def test_main_with_subcommand(self, mock_execute: Mock) -> None:
        """Test main function with subcommand.

        Args:
            mock_execute (Mock): Mocked execute_command method.
        """
        mock_execute.return_value = None

        main()

        # Should execute the subcommand
        mock_execute.assert_called_once_with("scanner")

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "scan", "--help"])
    @patch("foxhole_stockpiles.commands.fs.fs.CLIDispatcher.execute_command")
    def test_main_with_alias(self, mock_execute: Mock) -> None:
        """Test main function with command alias.

        Args:
            mock_execute (Mock): Mocked execute_command method.
        """
        mock_execute.return_value = None

        main()

        # Should execute the command using alias
        mock_execute.assert_called_once_with("scan")

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "scanner"])
    @patch("foxhole_stockpiles.commands.fs.fs.sys.exit")
    @patch("foxhole_stockpiles.commands.fs.fs.CLIDispatcher.execute_command")
    def test_main_handles_system_exit(self, mock_execute: Mock, mock_exit: Mock) -> None:
        """Test main function handles SystemExit from subcommand.

        Args:
            mock_execute (Mock): Mocked execute_command method.
            mock_exit (Mock): Mocked sys.exit function.
        """
        mock_execute.side_effect = SystemExit(1)

        main()

        # Should exit with the same code
        mock_exit.assert_called_once_with(1)

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "scanner"])
    @patch("foxhole_stockpiles.commands.fs.fs.CLIDispatcher.execute_command")
    @patch("builtins.print")
    def test_main_with_json_result(self, mock_print: Mock, mock_execute: Mock) -> None:
        """Test main function with JSON result from command.

        Args:
            mock_print (Mock): Mocked print function.
            mock_execute (Mock): Mocked execute_command method.
        """
        mock_execute.return_value = {"result": "success"}

        main()

        # Should print JSON output
        assert mock_print.called
        # Check that JSON was printed
        printed_text = str(mock_print.call_args[0][0])
        assert "result" in printed_text or "success" in printed_text

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "scanner"])
    @patch("foxhole_stockpiles.commands.fs.fs.sys.exit")
    @patch("foxhole_stockpiles.commands.fs.fs.CLIDispatcher.execute_command")
    def test_main_handles_exception(self, mock_execute: Mock, mock_exit: Mock) -> None:
        """Test main function handles exceptions from subcommand.

        Args:
            mock_execute (Mock): Mocked execute_command method.
            mock_exit (Mock): Mocked sys.exit function.
        """
        mock_execute.side_effect = RuntimeError("Test error")

        main()

        # Should exit with code 1
        mock_exit.assert_called_once_with(1)

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "scanner"])
    @patch("foxhole_stockpiles.commands.fs.fs.sys.exit")
    @patch("foxhole_stockpiles.commands.fs.fs.CLIDispatcher.execute_command")
    def test_main_handles_keyboard_interrupt(self, mock_execute: Mock, mock_exit: Mock) -> None:
        """Test main function handles KeyboardInterrupt.

        Args:
            mock_execute (Mock): Mocked execute_command method.
            mock_exit (Mock): Mocked sys.exit function.
        """
        mock_execute.side_effect = KeyboardInterrupt()

        main()

        # Should exit with code 130
        mock_exit.assert_called_once_with(130)

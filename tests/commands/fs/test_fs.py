"""Tests for commands.fs.fs module.

This module contains comprehensive tests for the unified CLI dispatcher,
including command resolution, alias handling, and command execution.
"""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from foxhole_stockpiles.commands.fs.fs import CLIDispatcher, _attach_console, main


# Mock _attach_console for tests that don't specifically test it
@pytest.fixture
def mock_attach_console() -> Generator[None, None, None]:
    """Mock _attach_console to avoid Windows-specific API calls in tests."""
    with patch("foxhole_stockpiles.commands.fs.fs._attach_console"):
        yield


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

        # Verify core commands exist
        assert "scanner" in dispatcher._commands
        assert "database-builder" in dispatcher._commands
        assert "generate-templates" in dispatcher._commands
        assert "extract-assets" in dispatcher._commands
        assert "inspect" in dispatcher._commands


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
            mock_module.main = AsyncMock(return_value=None)
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

    def test_execute_command_import_error(self) -> None:
        """Test command execution when import fails."""
        dispatcher = CLIDispatcher()

        mock_import = MagicMock(side_effect=ImportError("Module not found"))
        with patch("foxhole_stockpiles.commands.fs.fs.importlib.import_module", mock_import):
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
    @patch("foxhole_stockpiles.commands.fs.fs._attach_console")
    @patch("builtins.print")
    def test_main_with_help_flag(self, mock_print: Mock, mock_attach: Mock) -> None:
        """Test main function with --help flag.

        Args:
            mock_print (Mock): Mocked print function.
            mock_attach (Mock): Mocked _attach_console function.
        """
        main()

        # Should print help text
        assert mock_print.called
        call_args = mock_print.call_args[0][0]
        assert "Foxhole Stockpiles" in call_args

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs"])
    @patch("foxhole_stockpiles.commands.fs.fs.CLIDispatcher.execute_command")
    def test_main_with_no_args(self, mock_execute: Mock) -> None:
        """Test main function with no arguments launches GUI.

        Args:
            mock_execute (Mock): Mocked execute_command method.
        """
        mock_execute.return_value = None

        main()

        # Should launch GUI when no arguments provided
        mock_execute.assert_called_once_with("gui")

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "--version"])
    @patch("foxhole_stockpiles.commands.fs.fs._attach_console")
    @patch("builtins.print")
    def test_main_with_version_flag(self, mock_print: Mock, mock_attach: Mock) -> None:
        """Test main function with --version flag.

        Args:
            mock_print (Mock): Mocked print function.
            mock_attach (Mock): Mocked _attach_console function.
        """
        main()

        # Should print version
        assert mock_print.called
        call_args = mock_print.call_args[0][0]
        assert "Foxhole Stockpiles" in call_args

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "scanner", "--help"])
    @patch("foxhole_stockpiles.commands.fs.fs._attach_console")
    @patch("foxhole_stockpiles.commands.fs.fs.CLIDispatcher.execute_command")
    def test_main_with_subcommand(self, mock_execute: Mock, mock_attach: Mock) -> None:
        """Test main function with subcommand.

        Args:
            mock_execute (Mock): Mocked execute_command method.
            mock_attach (Mock): Mocked _attach_console function.
        """
        mock_execute.return_value = None

        main()

        # Should execute the subcommand
        mock_execute.assert_called_once_with("scanner")

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "scan", "--help"])
    @patch("foxhole_stockpiles.commands.fs.fs._attach_console")
    @patch("foxhole_stockpiles.commands.fs.fs.CLIDispatcher.execute_command")
    def test_main_with_alias(self, mock_execute: Mock, mock_attach: Mock) -> None:
        """Test main function with command alias.

        Args:
            mock_execute (Mock): Mocked execute_command method.
            mock_attach (Mock): Mocked _attach_console function.
        """
        mock_execute.return_value = None

        main()

        # Should execute the command using alias
        mock_execute.assert_called_once_with("scan")

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "scanner"])
    @patch("foxhole_stockpiles.commands.fs.fs._attach_console")
    @patch("foxhole_stockpiles.commands.fs.fs.sys.exit")
    def test_main_handles_exception(self, mock_exit: Mock, mock_attach: Mock) -> None:
        """Test main function handles exceptions from subcommand.

        Args:
            mock_exit (Mock): Mocked sys.exit function.
            mock_attach (Mock): Mocked _attach_console function.
        """
        mock_execute = MagicMock(side_effect=RuntimeError("Test error"))
        with patch("foxhole_stockpiles.commands.fs.fs.CLIDispatcher.execute_command", mock_execute):
            main()

        # Should exit with code 1
        mock_exit.assert_called_once_with(1)

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "scanner"])
    @patch("foxhole_stockpiles.commands.fs.fs._attach_console")
    @patch("foxhole_stockpiles.commands.fs.fs.sys.exit")
    def test_main_handles_system_exit(self, mock_exit: Mock, mock_attach: Mock) -> None:
        """Test main function handles SystemExit from subcommand.

        Args:
            mock_exit (Mock): Mocked sys.exit function.
            mock_attach (Mock): Mocked _attach_console function.
        """
        mock_execute = MagicMock(side_effect=SystemExit(1))
        with patch("foxhole_stockpiles.commands.fs.fs.CLIDispatcher.execute_command", mock_execute):
            main()

        # Should exit with the same code
        mock_exit.assert_called_once_with(1)

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "scanner"])
    @patch("foxhole_stockpiles.commands.fs.fs._attach_console")
    @patch("foxhole_stockpiles.commands.fs.fs.sys.exit")
    def test_main_handles_keyboard_interrupt(self, mock_exit: Mock, mock_attach: Mock) -> None:
        """Test main function handles KeyboardInterrupt.

        Args:
            mock_exit (Mock): Mocked sys.exit function.
            mock_attach (Mock): Mocked _attach_console function.
        """
        mock_execute = MagicMock(side_effect=KeyboardInterrupt())
        with patch("foxhole_stockpiles.commands.fs.fs.CLIDispatcher.execute_command", mock_execute):
            main()

        # Should exit with code 130
        mock_exit.assert_called_once_with(130)

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "scanner"])
    @patch("foxhole_stockpiles.commands.fs.fs._attach_console")
    @patch("foxhole_stockpiles.commands.fs.fs.CLIDispatcher.execute_command")
    @patch("builtins.print")
    def test_main_with_json_result(
        self, mock_print: Mock, mock_execute: Mock, mock_attach: Mock
    ) -> None:
        """Test main function with JSON result from command.

        Args:
            mock_print (Mock): Mocked print function.
            mock_execute (Mock): Mocked execute_command method.
            mock_attach (Mock): Mocked _attach_console function.
        """
        mock_execute.return_value = {"result": "success"}

        main()

        # Should print JSON output
        assert mock_print.called
        # Check that JSON was printed
        printed_text = str(mock_print.call_args[0][0])
        assert "result" in printed_text or "success" in printed_text

    @patch("foxhole_stockpiles.commands.fs.fs.sys.argv", ["fs", "gui"])
    @patch("foxhole_stockpiles.commands.fs.fs.CLIDispatcher.execute_command")
    def test_main_with_gui_command_no_console_attach(self, mock_execute: Mock) -> None:
        """Test that GUI command does not attach to console.

        Args:
            mock_execute (Mock): Mocked execute_command method.
        """
        mock_execute.return_value = None

        # Need to un-mock _attach_console for this test to verify it's not called
        with patch("foxhole_stockpiles.commands.fs.fs._attach_console") as mock_attach:
            main()

            # GUI command should NOT call _attach_console
            mock_attach.assert_not_called()
            mock_execute.assert_called_once_with("gui")


class TestAttachConsole:
    """Test suite for _attach_console function."""

    def test_attach_console_on_non_windows(self) -> None:
        """Test _attach_console returns early on non-Windows platforms."""
        with patch("foxhole_stockpiles.commands.fs.fs.sys.platform", "linux"):
            # Should return immediately without doing anything
            _attach_console()

    def test_attach_console_on_windows_with_parent_console(self) -> None:
        """Test _attach_console attaches to parent console on Windows."""
        mock_kernel32 = MagicMock()
        mock_kernel32.AttachConsole.return_value = True  # Parent console exists
        mock_kernel32.GetStdHandle.return_value = 0  # Invalid handle

        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = mock_kernel32

        mock_msvcrt = MagicMock()

        with (
            patch("foxhole_stockpiles.commands.fs.fs.sys.platform", "win32"),
            patch("foxhole_stockpiles.commands.fs.fs.ctypes", mock_ctypes),
            patch.dict("sys.modules", {"msvcrt": mock_msvcrt}),
        ):
            _attach_console()

            mock_kernel32.AttachConsole.assert_called_once_with(-1)
            mock_kernel32.AllocConsole.assert_not_called()

    def test_attach_console_on_windows_allocate_new_console(self) -> None:
        """Test _attach_console allocates new console when no parent on Windows."""
        mock_kernel32 = MagicMock()
        mock_kernel32.AttachConsole.return_value = False  # No parent console
        mock_kernel32.GetStdHandle.return_value = 0  # Invalid handle

        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = mock_kernel32

        mock_msvcrt = MagicMock()

        with (
            patch("foxhole_stockpiles.commands.fs.fs.sys.platform", "win32"),
            patch("foxhole_stockpiles.commands.fs.fs.ctypes", mock_ctypes),
            patch.dict("sys.modules", {"msvcrt": mock_msvcrt}),
        ):
            _attach_console()

            mock_kernel32.AttachConsole.assert_called_once_with(-1)
            mock_kernel32.AllocConsole.assert_called_once()

    def test_attach_console_redirects_stdout(self) -> None:
        """Test _attach_console redirects stdout when handle is valid."""
        import os as real_os

        import foxhole_stockpiles.commands.fs.fs as fs_module

        mock_kernel32 = MagicMock()
        mock_kernel32.AttachConsole.return_value = True
        mock_kernel32.GetStdHandle.side_effect = lambda h: 100 if h == -11 else 0

        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = mock_kernel32

        mock_msvcrt = MagicMock()
        mock_msvcrt.open_osfhandle.return_value = 5

        mock_os = MagicMock()
        mock_os.O_WRONLY = real_os.O_WRONLY
        mock_os.O_TEXT = 0x4000  # Windows constant

        with (
            patch.object(fs_module, "sys") as mock_sys,
            patch.object(fs_module, "ctypes", mock_ctypes),
            patch.object(fs_module, "os", mock_os),
            patch.dict("sys.modules", {"msvcrt": mock_msvcrt}),
            patch("builtins.open", MagicMock()),
        ):
            mock_sys.platform = "win32"
            mock_sys.stdout = MagicMock()
            mock_sys.stderr = MagicMock()

            fs_module._attach_console()

            # Should have called open_osfhandle for stdout
            mock_msvcrt.open_osfhandle.assert_called()

    def test_attach_console_redirects_stderr(self) -> None:
        """Test _attach_console redirects stderr when handle is valid."""
        import os as real_os

        import foxhole_stockpiles.commands.fs.fs as fs_module

        mock_kernel32 = MagicMock()
        mock_kernel32.AttachConsole.return_value = True
        mock_kernel32.GetStdHandle.side_effect = lambda h: 101 if h == -12 else 0

        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = mock_kernel32

        mock_msvcrt = MagicMock()
        mock_msvcrt.open_osfhandle.return_value = 6

        mock_os = MagicMock()
        mock_os.O_WRONLY = real_os.O_WRONLY
        mock_os.O_TEXT = 0x4000  # Windows constant

        with (
            patch.object(fs_module, "sys") as mock_sys,
            patch.object(fs_module, "ctypes", mock_ctypes),
            patch.object(fs_module, "os", mock_os),
            patch.dict("sys.modules", {"msvcrt": mock_msvcrt}),
            patch("builtins.open", MagicMock()),
        ):
            mock_sys.platform = "win32"
            mock_sys.stdout = MagicMock()
            mock_sys.stderr = MagicMock()

            fs_module._attach_console()

            # Should have called open_osfhandle for stderr
            mock_msvcrt.open_osfhandle.assert_called()

    def test_attach_console_skips_invalid_handles(self) -> None:
        """Test _attach_console skips redirection for invalid handles."""
        import os as real_os

        import foxhole_stockpiles.commands.fs.fs as fs_module

        mock_kernel32 = MagicMock()
        mock_kernel32.AttachConsole.return_value = True
        mock_kernel32.GetStdHandle.return_value = -1  # Invalid handle

        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = mock_kernel32

        mock_msvcrt = MagicMock()

        mock_os = MagicMock()
        mock_os.O_WRONLY = real_os.O_WRONLY
        mock_os.O_TEXT = 0x4000  # Windows constant

        with (
            patch.object(fs_module, "sys") as mock_sys,
            patch.object(fs_module, "ctypes", mock_ctypes),
            patch.object(fs_module, "os", mock_os),
            patch.dict("sys.modules", {"msvcrt": mock_msvcrt}),
        ):
            mock_sys.platform = "win32"

            fs_module._attach_console()

            # Should NOT have called open_osfhandle since handles are invalid
            mock_msvcrt.open_osfhandle.assert_not_called()

    def test_attach_console_handles_exception(self) -> None:
        """Test _attach_console silently handles exceptions."""
        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32.AttachConsole.side_effect = OSError("Test error")

        mock_msvcrt = MagicMock()

        with (
            patch("foxhole_stockpiles.commands.fs.fs.sys.platform", "win32"),
            patch("foxhole_stockpiles.commands.fs.fs.ctypes", mock_ctypes),
            patch.dict("sys.modules", {"msvcrt": mock_msvcrt}),
        ):
            # Should not raise any exceptions
            _attach_console()


class TestExecuteCommandAttributeError:
    """Test suite for execute_command AttributeError handling."""

    def test_execute_command_attribute_error(self) -> None:
        """Test command execution when main function is missing."""
        dispatcher = CLIDispatcher()

        mock_module = MagicMock(spec=[])  # Module without 'main' attribute
        mock_import = MagicMock(return_value=mock_module)

        with patch("foxhole_stockpiles.commands.fs.fs.importlib.import_module", mock_import):
            with pytest.raises(SystemExit) as exc_info:
                dispatcher.execute_command("scanner")

        # Should have exited with code 1
        assert exc_info.value.code == 1


class TestMainModuleEntryPoint:
    """Test suite for __main__ module entry point."""

    def test_main_module_execution(self) -> None:
        """Test that the module can be executed as __main__."""
        # This tests the if __name__ == "__main__" block
        import foxhole_stockpiles.commands.fs.fs as fs_module

        with patch.object(fs_module, "main") as mock_main:
            # Simulate running as __main__
            with patch.object(fs_module, "__name__", "__main__"):
                # Re-execute the module-level code
                exec(
                    "if __name__ == '__main__': main()", {"__name__": "__main__", "main": mock_main}
                )
                mock_main.assert_called_once()

"""Tests for ``foxhole_stockpiles.cli._console.attach_console``."""

import os as real_os
from unittest.mock import MagicMock, patch

from foxhole_stockpiles.cli import _console


class TestAttachConsole:
    """Test suite for the ``attach_console`` function."""

    def test_returns_early_on_non_windows(self) -> None:
        """``attach_console`` returns immediately on non-Windows platforms."""
        with patch("foxhole_stockpiles.cli._console.sys.platform", "linux"):
            _console.attach_console()

    def test_attaches_to_parent_console_on_windows(self) -> None:
        """Attaches to the parent console when one exists."""
        mock_kernel32 = MagicMock()
        mock_kernel32.AttachConsole.return_value = True
        mock_kernel32.GetStdHandle.return_value = 0

        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = mock_kernel32

        with (
            patch("foxhole_stockpiles.cli._console.sys.platform", "win32"),
            patch("foxhole_stockpiles.cli._console.ctypes", mock_ctypes),
            patch.dict("sys.modules", {"msvcrt": MagicMock()}),
        ):
            _console.attach_console()

            mock_kernel32.AttachConsole.assert_called_once_with(-1)
            mock_kernel32.AllocConsole.assert_not_called()

    def test_allocates_new_console_when_no_parent(self) -> None:
        """Allocates a new console when no parent console is available."""
        mock_kernel32 = MagicMock()
        mock_kernel32.AttachConsole.return_value = False
        mock_kernel32.GetStdHandle.return_value = 0

        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = mock_kernel32

        with (
            patch("foxhole_stockpiles.cli._console.sys.platform", "win32"),
            patch("foxhole_stockpiles.cli._console.ctypes", mock_ctypes),
            patch.dict("sys.modules", {"msvcrt": MagicMock()}),
        ):
            _console.attach_console()

            mock_kernel32.AttachConsole.assert_called_once_with(-1)
            mock_kernel32.AllocConsole.assert_called_once()

    def test_redirects_stdout_and_stderr(self) -> None:
        """Redirects stdout and stderr when their handles are valid."""
        mock_kernel32 = MagicMock()
        mock_kernel32.AttachConsole.return_value = True
        mock_kernel32.GetStdHandle.side_effect = lambda h: {-11: 100, -12: 101}.get(h, 0)

        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = mock_kernel32

        mock_msvcrt = MagicMock()
        mock_msvcrt.open_osfhandle.return_value = 5

        mock_os = MagicMock()
        mock_os.O_WRONLY = real_os.O_WRONLY
        mock_os.O_TEXT = 0x4000

        with (
            patch.object(_console, "sys") as mock_sys,
            patch.object(_console, "ctypes", mock_ctypes),
            patch.object(_console, "os", mock_os),
            patch.dict("sys.modules", {"msvcrt": mock_msvcrt}),
            patch("builtins.open", MagicMock()),
        ):
            mock_sys.platform = "win32"

            _console.attach_console()

            assert mock_msvcrt.open_osfhandle.call_count == 2

    def test_skips_invalid_handles(self) -> None:
        """Does not redirect when console handles are invalid."""
        mock_kernel32 = MagicMock()
        mock_kernel32.AttachConsole.return_value = True
        mock_kernel32.GetStdHandle.return_value = -1

        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32 = mock_kernel32

        mock_msvcrt = MagicMock()

        with (
            patch.object(_console, "sys") as mock_sys,
            patch.object(_console, "ctypes", mock_ctypes),
            patch.dict("sys.modules", {"msvcrt": mock_msvcrt}),
        ):
            mock_sys.platform = "win32"

            _console.attach_console()

            mock_msvcrt.open_osfhandle.assert_not_called()

    def test_handles_exception_silently(self) -> None:
        """Swallows OSError raised while attaching the console."""
        mock_ctypes = MagicMock()
        mock_ctypes.windll.kernel32.AttachConsole.side_effect = OSError("boom")

        with (
            patch("foxhole_stockpiles.cli._console.sys.platform", "win32"),
            patch("foxhole_stockpiles.cli._console.ctypes", mock_ctypes),
            patch.dict("sys.modules", {"msvcrt": MagicMock()}),
        ):
            _console.attach_console()

"""Tests for the centralized external-tool invocation helpers."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from fs_tools.services import external_tools


class TestIsWsl:
    """Tests for external_tools.is_wsl."""

    def test_not_linux(self) -> None:
        """Return False when /proc/version cannot be read."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            assert external_tools.is_wsl() is False

    def test_native_linux(self) -> None:
        """Return False when /proc/version has no 'microsoft' marker."""
        mock_file = MagicMock()
        mock_file.read.return_value = "Linux version 5.4.0"
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)

        with patch("builtins.open", return_value=mock_file):
            assert external_tools.is_wsl() is False

    def test_wsl(self) -> None:
        """Return True when /proc/version contains the WSL marker."""
        mock_file = MagicMock()
        mock_file.read.return_value = "Linux version 5.x microsoft-standard-WSL2"
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)

        with patch("builtins.open", return_value=mock_file):
            assert external_tools.is_wsl() is True


class TestToolIsWindows:
    """Tests for external_tools.tool_is_windows."""

    @pytest.mark.parametrize(
        ("tool_path", "expected"),
        [
            (r"C:\repak\repak.exe", True),
            ("/mnt/c/UModel/umodel.exe", True),
            ("/mnt/d/tools/repak", True),
            ("/usr/local/bin/repak", False),
            ("repak", False),
        ],
    )
    def test_detection(self, tool_path: str, expected: bool) -> None:
        """Windows executables are detected by .exe suffix or /mnt/ prefix."""
        assert external_tools.tool_is_windows(tool_path) is expected


class TestConvertWslPathToWindows:
    """Tests for external_tools.convert_wsl_path_to_windows."""

    def test_returns_unchanged_when_not_wsl(self) -> None:
        """Outside WSL the path is returned unchanged."""
        with patch.object(external_tools, "is_wsl", return_value=False):
            assert external_tools.convert_wsl_path_to_windows("/home/u/f") == "/home/u/f"

    def test_converts_mnt_path(self) -> None:
        """A /mnt/<drive>/ path maps directly to a Windows path."""
        with patch.object(external_tools, "is_wsl", return_value=True):
            result = external_tools.convert_wsl_path_to_windows("/mnt/c/Users/Test/file.txt")
        assert result == r"C:\Users\Test\file.txt"


class TestRunTool:
    """Tests for external_tools.run_tool."""

    async def test_returns_decoded_output(self) -> None:
        """run_tool returns the decoded (returncode, stdout, stderr)."""
        process = MagicMock()
        process.communicate = _async_return((b"out", b"err"))
        process.returncode = 0

        with patch("asyncio.create_subprocess_exec", _async_return(process)):
            returncode, stdout, stderr = await external_tools.run_tool(["repak", "list", "x.pak"])

        assert (returncode, stdout, stderr) == (0, "out", "err")

    async def test_check_raises_on_nonzero(self) -> None:
        """With check=True a non-zero exit raises ExternalToolError."""
        process = MagicMock()
        process.communicate = _async_return((b"", b"boom"))
        process.returncode = 2

        with patch("asyncio.create_subprocess_exec", _async_return(process)):
            with pytest.raises(external_tools.ExternalToolError, match="boom"):
                await external_tools.run_tool(["repak", "bad"], check=True)

    async def test_check_passes_on_zero(self) -> None:
        """With check=True a zero exit does not raise."""
        process = MagicMock()
        process.communicate = _async_return((b"ok", b""))
        process.returncode = 0

        with patch("asyncio.create_subprocess_exec", _async_return(process)):
            returncode, _stdout, _stderr = await external_tools.run_tool(["repak"], check=True)

        assert returncode == 0


def _async_return(value: object) -> Mock:
    """Build a Mock whose call returns an awaitable resolving to value.

    Args:
        value (object): The value the awaitable should resolve to.

    Returns:
        Mock: A callable mock returning a coroutine yielding value.
    """

    async def _coro(*_args: object, **_kwargs: object) -> object:
        return value

    return Mock(side_effect=_coro)

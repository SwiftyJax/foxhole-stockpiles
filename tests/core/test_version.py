"""Tests for version utilities."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from foxhole_stockpiles import __version__
from foxhole_stockpiles.core.version import (
    _read_git_info_from_file,
    get_git_info,
    get_version_info,
)


class TestReadGitInfoFromFile:
    """Test _read_git_info_from_file function."""

    def test_read_valid_git_info_file(self, tmp_path: Path) -> None:
        """Test reading a valid .git_info file."""
        # Create a valid .git_info file
        git_info_file = tmp_path / ".git_info"
        git_info_file.write_text(
            "GIT_COMMIT_HASH=abc123def456\n"
            "GIT_COMMIT_SHORT_HASH=abc123d\n"
            "GIT_COMMIT_DATE=2025-12-24\n"
            "GIT_DIRTY=clean\n"
        )

        # Patch the file path to use our temp file
        with patch("foxhole_stockpiles.core.version.Path") as mock_path:
            mock_path.return_value.parent.parent.parent = tmp_path
            result = _read_git_info_from_file()

        assert result is not None
        assert result["hash"] == "abc123def456"
        assert result["short_hash"] == "abc123d"
        assert result["date"] == "2025-12-24"
        assert result["dirty"] == "clean"

    def test_read_git_info_file_not_exists(self, tmp_path: Path) -> None:
        """Test when .git_info file doesn't exist."""
        with patch("foxhole_stockpiles.core.version.Path") as mock_path:
            mock_path.return_value.parent.parent.parent = tmp_path
            result = _read_git_info_from_file()

        assert result is None

    def test_read_git_info_file_incomplete(self, tmp_path: Path) -> None:
        """Test reading .git_info file with missing fields."""
        git_info_file = tmp_path / ".git_info"
        # Missing GIT_DIRTY field
        git_info_file.write_text(
            "GIT_COMMIT_HASH=abc123def456\n"
            "GIT_COMMIT_SHORT_HASH=abc123d\n"
            "GIT_COMMIT_DATE=2025-12-24\n"
        )

        with patch("foxhole_stockpiles.core.version.Path") as mock_path:
            mock_path.return_value.parent.parent.parent = tmp_path
            result = _read_git_info_from_file()

        assert result is None

    def test_read_git_info_file_invalid_format(self, tmp_path: Path) -> None:
        """Test reading .git_info file with invalid format."""
        git_info_file = tmp_path / ".git_info"
        git_info_file.write_text("invalid content without equals signs\n")

        with patch("foxhole_stockpiles.core.version.Path") as mock_path:
            mock_path.return_value.parent.parent.parent = tmp_path
            result = _read_git_info_from_file()

        assert result is None

    def test_read_git_info_file_permission_error(self, tmp_path: Path) -> None:
        """Test handling of permission errors."""
        # Create a file but make open raise an error
        git_info_file = tmp_path / ".git_info"
        git_info_file.write_text("dummy")

        with patch("foxhole_stockpiles.core.version.Path") as mock_path:
            mock_path.return_value.parent.parent.parent = tmp_path
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                result = _read_git_info_from_file()

        assert result is None


class TestGetGitInfo:
    """Test get_git_info function."""

    def test_get_git_info_from_file(self, tmp_path: Path) -> None:
        """Test getting git info from .git_info file (Docker scenario)."""
        git_info_file = tmp_path / ".git_info"
        git_info_file.write_text(
            "GIT_COMMIT_HASH=dockerhash123\n"
            "GIT_COMMIT_SHORT_HASH=docker1\n"
            "GIT_COMMIT_DATE=2025-12-24\n"
            "GIT_DIRTY=clean\n"
        )

        with patch("foxhole_stockpiles.core.version.Path") as mock_path:
            mock_path.return_value.parent.parent.parent = tmp_path
            result = get_git_info()

        assert result["hash"] == "dockerhash123"
        assert result["short_hash"] == "docker1"
        assert result["date"] == "2025-12-24"
        assert result["dirty"] == "clean"

    def test_get_git_info_from_git_commands(self, tmp_path: Path) -> None:
        """Test getting git info from git commands (development scenario)."""
        # Mock git directory exists
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Mock subprocess calls
        mock_subprocess = MagicMock()
        mock_subprocess.stdout = "commithash123\n"

        with patch("foxhole_stockpiles.core.version.Path") as mock_path:
            mock_path.return_value.parent.parent.parent = tmp_path
            with patch("subprocess.run") as mock_run:
                # Setup different return values for different git commands
                mock_run.side_effect = [
                    MagicMock(stdout="fullhash123456789"),  # git rev-parse HEAD
                    MagicMock(stdout="fullhas"),  # git rev-parse --short=7 HEAD
                    MagicMock(stdout="2025-12-24"),  # git log -1 --format=%cd
                    MagicMock(stdout=""),  # git status --porcelain (clean)
                ]
                result = get_git_info()

        assert result["hash"] == "fullhash123456789"
        assert result["short_hash"] == "fullhas"
        assert result["date"] == "2025-12-24"
        assert result["dirty"] == "clean"

    def test_get_git_info_dirty_working_directory(self, tmp_path: Path) -> None:
        """Test detecting dirty working directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch("foxhole_stockpiles.core.version.Path") as mock_path:
            mock_path.return_value.parent.parent.parent = tmp_path
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = [
                    MagicMock(stdout="hash123"),
                    MagicMock(stdout="hash123"),
                    MagicMock(stdout="2025-12-24"),
                    MagicMock(stdout="M file.py\n"),  # Modified file
                ]
                result = get_git_info()

        assert result["dirty"] == "dirty"

    def test_get_git_info_no_git_directory(self, tmp_path: Path) -> None:
        """Test when .git directory doesn't exist."""
        with patch("foxhole_stockpiles.core.version.Path") as mock_path:
            mock_path.return_value.parent.parent.parent = tmp_path
            result = get_git_info()

        assert result["hash"] == "unknown"
        assert result["short_hash"] == "unknown"
        assert result["date"] == "unknown"
        assert result["dirty"] == "unknown"

    def test_get_git_info_git_command_fails(self, tmp_path: Path) -> None:
        """Test handling of git command failures."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch("foxhole_stockpiles.core.version.Path") as mock_path:
            mock_path.return_value.parent.parent.parent = tmp_path
            with patch(
                "subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "git"),
            ):
                result = get_git_info()

        assert result["hash"] == "unknown"
        assert result["short_hash"] == "unknown"
        assert result["date"] == "unknown"
        assert result["dirty"] == "unknown"

    def test_get_git_info_git_timeout(self, tmp_path: Path) -> None:
        """Test handling of git command timeout."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch("foxhole_stockpiles.core.version.Path") as mock_path:
            mock_path.return_value.parent.parent.parent = tmp_path
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 2)):
                result = get_git_info()

        assert result["hash"] == "unknown"
        assert result["short_hash"] == "unknown"

    def test_get_git_info_file_not_found(self, tmp_path: Path) -> None:
        """Test handling when git executable is not found."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch("foxhole_stockpiles.core.version.Path") as mock_path:
            mock_path.return_value.parent.parent.parent = tmp_path
            with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
                result = get_git_info()

        assert result["hash"] == "unknown"


class TestGetVersionInfo:
    """Test get_version_info function."""

    def test_get_version_info_with_git_clean(self) -> None:
        """Test version info with clean git info (no dirty flag shown)."""
        with patch(
            "foxhole_stockpiles.core.version.get_git_info",
            return_value={
                "hash": "abc123def456",
                "short_hash": "abc123d",
                "date": "2025-12-24",
                "dirty": "clean",
            },
        ):
            result = get_version_info()

        # Clean builds don't show the "clean" flag, only dirty builds show "dirty"
        assert result == f"{__version__} (git: abc123d, 2025-12-24)"

    def test_get_version_info_with_git_dirty(self) -> None:
        """Test version info with dirty git info."""
        with patch(
            "foxhole_stockpiles.core.version.get_git_info",
            return_value={
                "hash": "abc123def456",
                "short_hash": "abc123d",
                "date": "2025-12-24",
                "dirty": "dirty",
            },
        ):
            result = get_version_info()

        assert result == f"{__version__} (git: abc123d, 2025-12-24, dirty)"

    def test_get_version_info_without_git(self) -> None:
        """Test version info when git is not available."""
        with patch(
            "foxhole_stockpiles.core.version.get_git_info",
            return_value={
                "hash": "unknown",
                "short_hash": "unknown",
                "date": "unknown",
                "dirty": "unknown",
            },
        ):
            result = get_version_info()

        assert result == __version__

    def test_get_version_info_uses_current_version(self) -> None:
        """Test that version info uses the current package version."""
        with patch(
            "foxhole_stockpiles.core.version.get_git_info",
            return_value={
                "hash": "unknown",
                "short_hash": "unknown",
                "date": "unknown",
                "dirty": "unknown",
            },
        ):
            result = get_version_info()

        # Should return just the version from __init__.py
        assert result == __version__
        assert "git:" not in result

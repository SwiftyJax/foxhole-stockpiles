"""Tests for update-config command module.

This module contains comprehensive tests for the update-config command,
including successful updates, error handling, and various edge cases.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from foxhole_stockpiles.commands.update_config.update_config import main


class TestUpdateConfigCommand:
    """Test cases for update-config command."""

    @pytest.mark.asyncio
    async def test_update_v1_to_v2_success(self, tmp_path: Path, capsys: Any) -> None:
        """Test successful update from v1 to v2.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            capsys: Pytest fixture to capture stdout/stderr.
        """
        # Create v1 config file
        config_path = tmp_path / "config.json"
        v1_config = {
            "output_format": {
                "output_format": "json",
                "output_destination": "webhook",
                "file_path": "/tmp/output.json",
                "webhook_url": "https://example.com/webhook",
                "webhook_auth_type": "bearer",
                "webhook_token": "secret123",
            }
        }
        config_path.write_text(json.dumps(v1_config, indent=2))

        # Run update command
        with patch("sys.argv", ["update-config", "--config", str(config_path)]):
            await main()

        # Verify backup was created
        backup_path = Path(str(config_path) + ".backup")
        assert backup_path.exists()

        # Verify config was updated
        updated_config = json.loads(config_path.read_text())
        assert updated_config["config_version"] == 2
        assert "output" in updated_config
        assert updated_config["output"]["destination"] == "webhook"
        assert updated_config["output"]["webhook"]["url"] == "https://example.com/webhook"
        assert updated_config["output"]["webhook"]["auth_type"] == "bearer"
        assert updated_config["output"]["webhook"]["token"] == "secret123"

        # Verify output messages
        captured = capsys.readouterr()
        assert "Update complete" in captured.out
        assert "Config version: 2" in captured.out

    @pytest.mark.asyncio
    async def test_already_at_latest_version(self, tmp_path: Path, capsys: Any) -> None:
        """Test when config is already at latest version.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            capsys: Pytest fixture to capture stdout/stderr.
        """
        # Create v2 config file
        config_path = tmp_path / "config.json"
        v2_config = {
            "config_version": 2,
            "output": {
                "format": "json",
                "destination": "return",
                "file": {"path": "output.json"},
                "webhook": {"url": None},
            },
        }
        config_path.write_text(json.dumps(v2_config, indent=2))

        # Run update command
        with patch("sys.argv", ["update-config", "--config", str(config_path)]):
            await main()

        # Verify no backup was created
        backup_path = Path(str(config_path) + ".backup")
        assert not backup_path.exists()

        # Verify config unchanged
        unchanged_config = json.loads(config_path.read_text())
        assert unchanged_config == v2_config

        # Verify output message
        captured = capsys.readouterr()
        assert "already at the latest version" in captured.out
        assert "No update needed" in captured.out

    @pytest.mark.asyncio
    async def test_config_file_not_found(self, tmp_path: Path, capsys: Any) -> None:
        """Test when config file doesn't exist.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            capsys: Pytest fixture to capture stdout/stderr.
        """
        # Point to non-existent file
        config_path = tmp_path / "nonexistent.json"

        # Run update command
        with patch("sys.argv", ["update-config", "--config", str(config_path)]):
            await main()

        # Verify output message
        captured = capsys.readouterr()
        assert "No config file found" in captured.out
        assert "Nothing to update" in captured.out

    @pytest.mark.asyncio
    async def test_invalid_json(self, tmp_path: Path, capsys: Any) -> None:
        """Test when config file contains invalid JSON.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            capsys: Pytest fixture to capture stdout/stderr.
        """
        # Create file with invalid JSON
        config_path = tmp_path / "config.json"
        config_path.write_text("{ invalid json }")

        # Run update command
        with patch("sys.argv", ["update-config", "--config", str(config_path)]):
            await main()

        # Verify output message
        captured = capsys.readouterr()
        assert "not valid JSON" in captured.out

    @pytest.mark.asyncio
    async def test_unknown_version_higher_than_latest(self, tmp_path: Path, capsys: Any) -> None:
        """Test when config version is higher than latest known version.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            capsys: Pytest fixture to capture stdout/stderr.
        """
        # Create config with future version
        config_path = tmp_path / "config.json"
        future_config = {"config_version": 999}
        config_path.write_text(json.dumps(future_config, indent=2))

        # Run update command
        with patch("sys.argv", ["update-config", "--config", str(config_path)]):
            await main()

        # Verify no backup was created
        backup_path = Path(str(config_path) + ".backup")
        assert not backup_path.exists()

        # Verify output message
        captured = capsys.readouterr()
        assert "newer than expected" in captured.out
        assert "newer version of the software" in captured.out

    @pytest.mark.asyncio
    async def test_dry_run_mode(self, tmp_path: Path, capsys: Any) -> None:
        """Test dry-run mode doesn't modify files.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            capsys: Pytest fixture to capture stdout/stderr.
        """
        # Create v1 config file
        config_path = tmp_path / "config.json"
        v1_config = {
            "output_format": {
                "output_format": "json",
                "output_destination": "return",
            }
        }
        original_content = json.dumps(v1_config, indent=2)
        config_path.write_text(original_content)

        # Run update command with --dry-run
        with patch("sys.argv", ["update-config", "--config", str(config_path), "--dry-run"]):
            await main()

        # Verify no backup was created
        backup_path = Path(str(config_path) + ".backup")
        assert not backup_path.exists()

        # Verify config unchanged
        assert config_path.read_text() == original_content

        # Verify output shows preview
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out
        assert "Preview of updated config" in captured.out
        assert "config_version" in captured.out
        assert "To apply update, run without --dry-run" in captured.out

    @pytest.mark.asyncio
    async def test_custom_backup_path(self, tmp_path: Path) -> None:
        """Test using custom backup path.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        # Create v1 config file
        config_path = tmp_path / "config.json"
        v1_config = {"output_format": {"output_format": "json"}}
        config_path.write_text(json.dumps(v1_config, indent=2))

        # Custom backup path
        custom_backup = tmp_path / "my_backup.json"

        # Run update command with custom backup path
        with patch(
            "sys.argv",
            ["update-config", "--config", str(config_path), "--backup-path", str(custom_backup)],
        ):
            await main()

        # Verify custom backup was created
        assert custom_backup.exists()

        # Verify default backup was NOT created
        default_backup = Path(str(config_path) + ".backup")
        assert not default_backup.exists()

    @pytest.mark.asyncio
    async def test_error_creating_backup(self, tmp_path: Path, capsys: Any) -> None:
        """Test error handling when backup creation fails.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            capsys: Pytest fixture to capture stdout/stderr.
        """
        # Create v1 config file
        config_path = tmp_path / "config.json"
        v1_config = {"output_format": {"output_format": "json"}}
        config_path.write_text(json.dumps(v1_config, indent=2))

        # Mock shutil.copy2 to raise an exception
        with patch("shutil.copy2", side_effect=PermissionError("Permission denied")):
            with patch("sys.argv", ["update-config", "--config", str(config_path)]):
                await main()

        # Verify error message
        captured = capsys.readouterr()
        assert "Error creating backup" in captured.out
        assert "Permission denied" in captured.out

        # Verify original config unchanged
        original_config = json.loads(config_path.read_text())
        assert original_config == v1_config

    @pytest.mark.asyncio
    async def test_error_writing_updated_config(self, tmp_path: Path, capsys: Any) -> None:
        """Test error handling when writing updated config fails.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            capsys: Pytest fixture to capture stdout/stderr.
        """
        # Create v1 config file
        config_path = tmp_path / "config.json"
        v1_config = {"output_format": {"output_format": "json"}}
        config_path.write_text(json.dumps(v1_config, indent=2))

        # Mock Path.open to raise exception on write
        original_open = Path.open

        def mock_open(self: Any, *args: Any, **kwargs: Any) -> Any:
            if "w" in args or kwargs.get("mode") == "w":
                raise PermissionError("Cannot write")
            return original_open(self, *args, **kwargs)

        with patch.object(Path, "open", mock_open):
            with patch("sys.argv", ["update-config", "--config", str(config_path)]):
                await main()

        # Verify error message
        captured = capsys.readouterr()
        assert "Error writing updated config" in captured.out
        assert "Cannot write" in captured.out
        assert "original config is safe" in captured.out

        # Verify backup was still created
        backup_path = Path(str(config_path) + ".backup")
        assert backup_path.exists()

    @pytest.mark.asyncio
    async def test_generic_exception_during_migration(self, tmp_path: Path, capsys: Any) -> None:
        """Test error handling for generic exceptions during migration.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            capsys: Pytest fixture to capture stdout/stderr.
        """
        # Create v1 config file
        config_path = tmp_path / "config.json"
        v1_config = {"output_format": {"output_format": "json"}}
        config_path.write_text(json.dumps(v1_config, indent=2))

        # Mock AppSettings.migrate_config to raise exception
        with patch(
            "foxhole_stockpiles.commands.update_config.update_config.AppSettings.migrate_config",
            side_effect=ValueError("Migration failed"),
        ):
            with patch("sys.argv", ["update-config", "--config", str(config_path)]):
                await main()

        # Verify error message
        captured = capsys.readouterr()
        assert "Error during migration" in captured.out
        assert "Migration failed" in captured.out

        # Verify no backup was created (error before backup)
        backup_path = Path(str(config_path) + ".backup")
        assert not backup_path.exists()

    @pytest.mark.asyncio
    async def test_error_reading_config_file(self, tmp_path: Path, capsys: Any) -> None:
        """Test error handling when reading config file fails.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            capsys: Pytest fixture to capture stdout/stderr.
        """
        # Create config file
        config_path = tmp_path / "config.json"
        config_path.write_text("{}")

        # Mock Path.open to raise exception on read
        with patch.object(Path, "open", side_effect=PermissionError("Cannot read")):
            with patch("sys.argv", ["update-config", "--config", str(config_path)]):
                await main()

        # Verify error message
        captured = capsys.readouterr()
        assert "Error reading config file" in captured.out
        assert "Cannot read" in captured.out

    @pytest.mark.asyncio
    async def test_default_config_path(self, tmp_path: Path, capsys: Any, monkeypatch: Any) -> None:
        """Test that default config path is ~/.fs_config.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            capsys: Pytest fixture to capture stdout/stderr.
            monkeypatch: Pytest fixture to mock Path.home().
        """
        # Mock home directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create v2 config at default location
        config_path = tmp_path / ".fs_config"
        v2_config = {"config_version": 2}
        config_path.write_text(json.dumps(v2_config, indent=2))

        # Run update command without --config argument
        with patch("sys.argv", ["update-config"]):
            await main()

        # Verify it used the default path
        captured = capsys.readouterr()
        assert "already at the latest version" in captured.out


class TestUpdateConfigEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_migration_returns_non_dict(self, tmp_path: Path, capsys: Any) -> None:
        """Test when migration returns non-dictionary value.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
            capsys: Pytest fixture to capture stdout/stderr.
        """
        # Create v1 config file
        config_path = tmp_path / "config.json"
        v1_config = {"output_format": {"output_format": "json"}}
        config_path.write_text(json.dumps(v1_config, indent=2))

        # Mock migrate_config to return non-dict
        with patch(
            "foxhole_stockpiles.commands.update_config.update_config.AppSettings.migrate_config",
            return_value="not a dict",
        ):
            with patch("sys.argv", ["update-config", "--config", str(config_path)]):
                await main()

        # Verify error message
        captured = capsys.readouterr()
        assert "Error during migration" in captured.out
        assert "did not return a dictionary" in captured.out

    @pytest.mark.asyncio
    async def test_v1_config_with_minimal_fields(self, tmp_path: Path) -> None:
        """Test updating v1 config with only minimal fields.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        # Create minimal v1 config
        config_path = tmp_path / "config.json"
        v1_config: dict[str, Any] = {"output_format": {}}  # Empty output_format
        config_path.write_text(json.dumps(v1_config, indent=2))

        # Run update command
        with patch("sys.argv", ["update-config", "--config", str(config_path)]):
            await main()

        # Verify config was updated
        updated_config = json.loads(config_path.read_text())
        assert updated_config["config_version"] == 2
        assert "output" in updated_config

    @pytest.mark.asyncio
    async def test_preserves_other_config_fields(self, tmp_path: Path) -> None:
        """Test that update preserves other config fields.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        # Create v1 config with extra fields
        config_path = tmp_path / "config.json"
        v1_config = {
            "output_format": {"output_format": "json"},
            "logging": {"log_level": "DEBUG"},
            "ocr": {"height": 1080},
        }
        config_path.write_text(json.dumps(v1_config, indent=2))

        # Run update command
        with patch("sys.argv", ["update-config", "--config", str(config_path)]):
            await main()

        # Verify other fields preserved
        updated_config = json.loads(config_path.read_text())
        assert updated_config["logging"]["log_level"] == "DEBUG"
        assert updated_config["ocr"]["height"] == 1080

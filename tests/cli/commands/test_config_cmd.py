"""Tests for the ``fs update-config`` command.

Covers ``foxhole_stockpiles.cli.commands.config_cmd`` migration behaviour,
dry-run mode, custom backup paths, and error handling.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from typer.testing import CliRunner

from foxhole_stockpiles.cli.commands import config_cmd

runner = CliRunner()


class TestUpdateConfigCommand:
    """Test suite for the ``update-config`` command via CliRunner."""

    def test_update_v1_to_latest(self, tmp_path: Path) -> None:
        """A v1 config is migrated to the latest version with a backup.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
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

        result = runner.invoke(config_cmd.app, ["--config", str(config_path)])

        assert result.exit_code == 0
        backup_path = Path(str(config_path) + ".backup")
        assert backup_path.exists()

        updated = json.loads(config_path.read_text())
        assert updated["config_version"] == 5
        assert "handlers" in updated["output"]
        assert "Update complete" in result.output

    def test_already_latest_version(self, tmp_path: Path) -> None:
        """A config already at the latest version is left unchanged.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        config_path = tmp_path / "config.json"
        v5_config = {
            "config_version": 5,
            "output": {
                "handlers": [
                    {
                        "name": "API Response",
                        "format": {"type": "json"},
                        "handler": {"type": "return"},
                    }
                ]
            },
        }
        config_path.write_text(json.dumps(v5_config, indent=2))

        result = runner.invoke(config_cmd.app, ["--config", str(config_path)])

        assert result.exit_code == 0
        assert not Path(str(config_path) + ".backup").exists()
        assert json.loads(config_path.read_text()) == v5_config
        assert "already at the latest version" in result.output

    def test_config_file_not_found(self, tmp_path: Path) -> None:
        """A missing config file reports nothing to update.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        result = runner.invoke(config_cmd.app, ["--config", str(tmp_path / "nonexistent.json")])

        assert result.exit_code == 0
        assert "No config file found" in result.output

    def test_invalid_json(self, tmp_path: Path) -> None:
        """An invalid JSON config reports a parse error.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        config_path = tmp_path / "config.json"
        config_path.write_text("{ invalid json }")

        result = runner.invoke(config_cmd.app, ["--config", str(config_path)])

        assert result.exit_code == 0
        assert "not valid JSON" in result.output

    def test_version_higher_than_latest(self, tmp_path: Path) -> None:
        """A future config version is reported as newer than expected.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"config_version": 999}, indent=2))

        result = runner.invoke(config_cmd.app, ["--config", str(config_path)])

        assert result.exit_code == 0
        assert "newer than expected" in result.output
        assert not Path(str(config_path) + ".backup").exists()

    def test_dry_run_does_not_modify(self, tmp_path: Path) -> None:
        """Dry-run mode previews the migration without writing files.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        config_path = tmp_path / "config.json"
        v1_config = {"output_format": {"output_format": "json", "output_destination": "return"}}
        original = json.dumps(v1_config, indent=2)
        config_path.write_text(original)

        result = runner.invoke(config_cmd.app, ["--config", str(config_path), "--dry-run"])

        assert result.exit_code == 0
        assert not Path(str(config_path) + ".backup").exists()
        assert config_path.read_text() == original
        assert "DRY RUN" in result.output

    def test_custom_backup_path(self, tmp_path: Path) -> None:
        """A custom backup path is honoured.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"output_format": {"output_format": "json"}}, indent=2))
        custom_backup = tmp_path / "my_backup.json"

        result = runner.invoke(
            config_cmd.app,
            ["--config", str(config_path), "--backup-path", str(custom_backup)],
        )

        assert result.exit_code == 0
        assert custom_backup.exists()
        assert not Path(str(config_path) + ".backup").exists()

    def test_migration_failure(self, tmp_path: Path) -> None:
        """A migration failure is reported and no backup is created.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"output_format": {"output_format": "json"}}, indent=2))

        with patch(
            "foxhole_stockpiles.cli.commands.config_cmd.AppSettings.migrate_config",
            side_effect=ValueError("Migration failed"),
        ):
            result = runner.invoke(config_cmd.app, ["--config", str(config_path)])

        assert result.exit_code == 0
        assert "Error during migration" in result.output
        assert not Path(str(config_path) + ".backup").exists()

    def test_migration_returns_non_dict(self, tmp_path: Path) -> None:
        """A non-dict migration result is reported as an error.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"output_format": {"output_format": "json"}}, indent=2))

        with patch(
            "foxhole_stockpiles.cli.commands.config_cmd.AppSettings.migrate_config",
            return_value="not a dict",
        ):
            result = runner.invoke(config_cmd.app, ["--config", str(config_path)])

        assert result.exit_code == 0
        assert "did not return a dictionary" in result.output

    def test_backup_failure(self, tmp_path: Path) -> None:
        """A backup creation failure is reported.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        config_path = tmp_path / "config.json"
        v1_config: dict[str, Any] = {"output_format": {"output_format": "json"}}
        config_path.write_text(json.dumps(v1_config, indent=2))

        with patch(
            "foxhole_stockpiles.cli.commands.config_cmd.shutil.copy2",
            side_effect=PermissionError("Permission denied"),
        ):
            result = runner.invoke(config_cmd.app, ["--config", str(config_path)])

        assert result.exit_code == 0
        assert "Error creating backup" in result.output
        assert json.loads(config_path.read_text()) == v1_config

    def test_preserves_other_fields(self, tmp_path: Path) -> None:
        """Migration preserves unrelated config fields.

        Args:
            tmp_path (Path): Temporary directory from pytest fixture.
        """
        config_path = tmp_path / "config.json"
        v1_config = {
            "output_format": {"output_format": "json"},
            "logging": {"log_level": "DEBUG"},
            "ocr": {"height": 1080},
        }
        config_path.write_text(json.dumps(v1_config, indent=2))

        result = runner.invoke(config_cmd.app, ["--config", str(config_path)])

        assert result.exit_code == 0
        updated = json.loads(config_path.read_text())
        assert updated["logging"]["log_level"] == "DEBUG"
        assert updated["ocr"]["height"] == 1080

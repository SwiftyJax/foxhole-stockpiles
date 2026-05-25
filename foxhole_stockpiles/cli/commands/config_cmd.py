"""``fs update-config`` — migrate ``.fs_config`` to the latest format version.

This command:
1. Reads the existing config file directly (without env var merging).
2. Backs up the old config to ``.fs_config.backup``.
3. Applies all necessary migrations to bring it to the latest version.
4. Writes the updated config back.

Only the config FILE is updated; environment variable overrides continue to work.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import typer

from foxhole_stockpiles.core.settings import AppSettings

# Current latest config version.
LATEST_CONFIG_VERSION = 5

app = typer.Typer(help="Update .fs_config to the latest format version.")


@app.callback(invoke_without_command=True)
def update_config(
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Path to config file (default: ~/.fs_config).",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview update without making changes."),
    backup_path: Path | None = typer.Option(
        None, "--backup-path", help="Custom backup path (default: <config>.backup)."
    ),
) -> None:
    """Update ``.fs_config`` to the latest format version.

    Args:
        config (Path | None): Path to the config file to migrate. Defaults to
            ``~/.fs_config`` when not provided.
        dry_run (bool): If True, print the migrated config without writing it.
        backup_path (Path | None): Where to back up the old config. Defaults to
            ``<config>.backup``.
    """
    config = config if config is not None else Path.home() / ".fs_config"
    resolved_backup = backup_path or Path(str(config) + ".backup")

    # Check if config exists.
    if not config.exists():
        typer.echo(f"❌ No config file found at {config}")
        typer.echo("Nothing to update.")
        return

    # Read config file directly (not through Pydantic settings).
    typer.echo(f"Loading config from {config}...")
    try:
        with config.open("r") as f:
            config_data: dict[str, Any] = json.load(f)
    except json.JSONDecodeError as e:
        typer.echo(f"❌ Error: Config file is not valid JSON: {e}")
        return
    except Exception as e:  # noqa: BLE001 - report any read failure to the user
        typer.echo(f"❌ Error reading config file: {e}")
        return

    # Check current version.
    current_version = config_data.get("config_version", 1)

    if current_version == LATEST_CONFIG_VERSION:
        typer.echo(f"✅ Config is already at the latest version ({LATEST_CONFIG_VERSION}).")
        typer.echo("No update needed.")
        return

    if current_version > LATEST_CONFIG_VERSION:
        typer.echo(f"⚠️  Warning: Config version {current_version} is newer than expected.")
        typer.echo(f"This tool supports up to version {LATEST_CONFIG_VERSION}.")
        typer.echo("Your config may be from a newer version of the software.")
        return

    typer.echo(f"Current config version: {current_version}")
    typer.echo(f"Latest config version: {LATEST_CONFIG_VERSION}")
    typer.echo("Updating config...")

    # Apply migrations through the AppSettings model validator (v1→v2, v2→v3, ...).
    try:
        updated_data = AppSettings.migrate_config(config_data.copy())  # type: ignore[operator]

        if not isinstance(updated_data, dict):
            raise ValueError("Migration did not return a dictionary")

        updated_data["config_version"] = LATEST_CONFIG_VERSION
    except Exception as e:  # noqa: BLE001 - report any migration failure to the user
        typer.echo(f"❌ Error during migration: {e}")
        return

    # Show preview in dry-run mode.
    if dry_run:
        typer.echo("\n📋 DRY RUN - Preview of updated config:")
        typer.echo("=" * 60)
        typer.echo(json.dumps(updated_data, indent=2))
        typer.echo("=" * 60)
        typer.echo("\n✅ Dry run complete. To apply update, run without --dry-run")
        return

    # Create backup of old config.
    typer.echo(f"Creating backup at {resolved_backup}...")
    try:
        shutil.copy2(config, resolved_backup)
    except Exception as e:  # noqa: BLE001 - report any backup failure to the user
        typer.echo(f"❌ Error creating backup: {e}")
        return

    # Write updated config to file.
    typer.echo(f"Writing updated config to {config}...")
    try:
        with config.open("w") as f:
            json.dump(updated_data, f, indent=2)
    except Exception as e:  # noqa: BLE001 - report any write failure to the user
        typer.echo(f"❌ Error writing updated config: {e}")
        typer.echo(f"Your original config is safe at {resolved_backup}")
        return

    typer.echo("\n✅ Update complete!")
    typer.echo(f"   - Old config backed up to: {resolved_backup}")
    typer.echo(f"   - Updated config written to: {config}")
    typer.echo(f"   - Config version: {updated_data['config_version']}")
    typer.echo("\n📝 Note: Environment variables will continue to override file settings.")

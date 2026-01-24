#!/usr/bin/env python3
"""CLI command to update .fs_config to the latest format version.

This command:
1. Reads your existing config file directly (without env var merging)
2. Backs up your old config to .fs_config.backup
3. Applies all necessary migrations to bring it to the latest version
4. Writes the updated config back to .fs_config

IMPORTANT: This only updates the config FILE. It does not include
environment variable values, preserving proper separation of concerns.
"""

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from foxhole_stockpiles.core.settings import AppSettings

# Current latest config version
LATEST_CONFIG_VERSION = 5


async def main() -> None:
    """Main entry point for the update-config command."""
    parser = argparse.ArgumentParser(
        description="Update .fs_config to the latest format version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fs update-config              # Update ~/.fs_config to latest version
  fs update-config --dry-run    # Preview changes without applying them
  fs update-config --config /path/to/config.json  # Update a specific config file

Note: This only updates the config file itself. Environment variable
overrides will continue to work as expected.
        """,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path.home() / ".fs_config",
        help="Path to config file (default: ~/.fs_config)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview update without making changes",
    )
    parser.add_argument(
        "--backup-path",
        type=Path,
        help="Custom backup path (default: <config>.backup)",
    )

    args = parser.parse_args()

    config_path: Path = args.config
    backup_path: Path = args.backup_path or Path(str(config_path) + ".backup")

    # Check if config exists
    if not config_path.exists():
        print(f"❌ No config file found at {config_path}")
        print("Nothing to update.")
        return

    # Read config file directly (not through Pydantic settings)
    print(f"Loading config from {config_path}...")
    try:
        with config_path.open("r") as f:
            config_data: dict[str, Any] = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Config file is not valid JSON: {e}")
        return
    except Exception as e:
        print(f"❌ Error reading config file: {e}")
        return

    # Check current version
    current_version = config_data.get("config_version", 1)

    if current_version == LATEST_CONFIG_VERSION:
        print(f"✅ Config is already at the latest version ({LATEST_CONFIG_VERSION}).")
        print("No update needed.")
        return

    if current_version > LATEST_CONFIG_VERSION:
        print(f"⚠️  Warning: Config version {current_version} is newer than expected.")
        print(f"This tool supports up to version {LATEST_CONFIG_VERSION}.")
        print("Your config may be from a newer version of the software.")
        return

    print(f"Current config version: {current_version}")
    print(f"Latest config version: {LATEST_CONFIG_VERSION}")
    print("Updating config...")

    # Apply migrations through AppSettings model validator
    # This will apply all necessary migrations (v1→v2, v2→v3, etc.)
    try:
        # The migrate_config validator will automatically apply all necessary migrations
        # Note: migrate_config is a @model_validator decorated classmethod
        updated_data = AppSettings.migrate_config(config_data.copy())  # type: ignore[operator]

        # Ensure version is set to latest
        if not isinstance(updated_data, dict):
            raise ValueError("Migration did not return a dictionary")

        updated_data["config_version"] = LATEST_CONFIG_VERSION
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return

    # Show preview in dry-run mode
    if args.dry_run:
        print("\n📋 DRY RUN - Preview of updated config:")
        print("=" * 60)
        print(json.dumps(updated_data, indent=2))
        print("=" * 60)
        print("\n✅ Dry run complete. To apply update, run without --dry-run")
        return

    # Create backup of old config
    print(f"Creating backup at {backup_path}...")
    try:
        shutil.copy2(config_path, backup_path)
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        return

    # Write updated config to file
    print(f"Writing updated config to {config_path}...")
    try:
        with config_path.open("w") as f:
            json.dump(updated_data, f, indent=2)
    except Exception as e:
        print(f"❌ Error writing updated config: {e}")
        print(f"Your original config is safe at {backup_path}")
        return

    print("\n✅ Update complete!")
    print(f"   - Old config backed up to: {backup_path}")
    print(f"   - Updated config written to: {config_path}")
    print(f"   - Config version: {updated_data['config_version']}")
    print("\n📝 Note: Environment variables will continue to override file settings.")

"""CLI command to process Foxhole save files."""

import argparse
import os
import sys
from copy import copy
from pathlib import Path

from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.core.settings import AppSettings, get_settings
from foxhole_stockpiles.core.settings.sections.output import (
    FileHandlerSettings,
    JsonFormatSettings,
    OutputHandlerConfig,
    OutputSettings,
)
from foxhole_stockpiles.services.output_coordinator import OutputCoordinator
from foxhole_stockpiles.services.savefile_converter import SaveFileConverter
from foxhole_stockpiles.services.savefile_processor import SaveFileProcessor


def _get_default_savefile_path() -> Path | None:
    """Get the default Foxhole save file path based on OS.

    Returns:
        Path | None: Default save file path or None if not determinable.
    """
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            return Path(local_appdata) / "Foxhole" / "Saved" / "SaveGames"
    elif sys.platform == "linux":
        # WSL path
        # Try common WSL mount points
        wsl_users = Path("/mnt/c/Users")
        if wsl_users.exists():
            try:
                for user_dir in wsl_users.iterdir():
                    try:
                        wsl_path = (
                            user_dir / "AppData" / "Local" / "Foxhole" / "Saved" / "SaveGames"
                        )
                        if wsl_path.exists():
                            return wsl_path
                    except PermissionError:
                        continue
            except PermissionError:
                pass

        # Native Linux (Proton/Wine)
        home = Path.home()
        proton_path = (
            home
            / ".steam"
            / "steam"
            / "steamapps"
            / "compatdata"
            / "505460"
            / "pfx"
            / "drive_c"
            / "users"
            / "steamuser"
            / "AppData"
            / "Local"
            / "Foxhole"
            / "Saved"
            / "SaveGames"
        )
        if proton_path.exists():
            return proton_path
    return None


def _find_mapdata_file(save_dir: Path) -> Path | None:
    """Find the MapData.sav file in the save directory.

    Args:
        save_dir (Path): Save games directory.

    Returns:
        Path | None: Path to MapData.sav or None if not found.
    """
    for f in save_dir.glob("*_MapData.sav"):
        return f
    return None


async def main() -> None:
    """Main function to handle command line arguments and execute monitoring."""
    parser = argparse.ArgumentParser(
        description="Process Foxhole save files and extract stockpile data"
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Path to the MapData.sav file (auto-detected if not specified)",
    )
    parser.add_argument(
        "--save-dir",
        type=Path,
        help="Path to Foxhole SaveGames directory",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process file once and exit (no monitoring)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Polling interval in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (overrides config handlers, supports {timestamp} placeholder)",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Determine the save file path
    save_file: Path | None = None

    if args.file:
        save_file = args.file
    elif args.save_dir:
        save_file = _find_mapdata_file(args.save_dir)
        if save_file is None:
            print(f"Error: No MapData.sav file found in {args.save_dir}", file=sys.stderr)
            sys.exit(1)
    else:
        # Try to auto-detect
        default_dir = _get_default_savefile_path()
        if default_dir and default_dir.exists():
            save_file = _find_mapdata_file(default_dir)

    if save_file is None:
        print(
            "Error: Could not find save file. Use --file or --save-dir to specify.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not save_file.exists():
        print(f"Error: File not found: {save_file}", file=sys.stderr)
        sys.exit(1)

    # Setup logging and settings
    if args.config:
        original_json_file = AppSettings.model_config.get("env_file")
        AppSettings.model_config["env_file"] = args.config
        settings = AppSettings()
        AppSettings.model_config["env_file"] = original_json_file
    else:
        settings = copy(get_settings())

    logging_settings = settings.logging
    if args.verbose:
        logging_settings.log_level = "DEBUG"
    setup_logging(logging_settings)

    # Initialize converter
    try:
        converter = SaveFileConverter()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup output: --output flag overrides config handlers
    if args.output:
        # Create ad-hoc FileHandler with specified path
        output_settings = OutputSettings(
            handlers=[
                OutputHandlerConfig(
                    name="CLI Output",
                    format=JsonFormatSettings(),
                    handler=FileHandlerSettings(path=str(args.output)),
                )
            ]
        )
    else:
        # Use handlers from config
        output_settings = settings.output

    output_coordinator = OutputCoordinator(output_settings)

    # Create and run processor
    processor = SaveFileProcessor(
        file_path=save_file,
        converter=converter,
        output_coordinator=output_coordinator,
        poll_interval=args.poll_interval,
    )

    if args.once:
        await processor.run_once()
        return

    try:
        await processor.run()
    except KeyboardInterrupt:
        print("\nStopping processor...")
        processor.stop()

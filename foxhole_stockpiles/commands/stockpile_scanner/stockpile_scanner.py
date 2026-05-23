"""Foxhole Stockpile Detection Script."""

import argparse
import asyncio
import sys
from copy import copy
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.core.settings import AppSettings, get_settings
from foxhole_stockpiles.core.settings.sections.output import (
    ConsoleHandlerSettings,
    FileHandlerSettings,
    JsonFormatSettings,
    OutputHandlerConfig,
    OutputSettings,
    ReturnHandlerSettings,
)
from foxhole_stockpiles.core.settings.sections.scanner import ScannerSettings
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.output_destination import OutputDestination
from foxhole_stockpiles.enums.output_format import OutputFormat
from foxhole_stockpiles.enums.supported_language import SupportedLanguage
from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.services.output_coordinator import OutputCoordinator
from fs_ocr._impl.coordinator import OCRCoordinator


def _create_handler_config_for_destination(
    destination: OutputDestination, output_file: Path | None = None
) -> OutputHandlerConfig:
    """Create a handler config for a specific output destination.

    Args:
        destination: The output destination type
        output_file: Optional file path for file destination

    Returns:
        OutputHandlerConfig: Handler configuration for the destination
    """
    destination_names = {
        OutputDestination.RETURN: "CLI Return",
        OutputDestination.FILE: "CLI File Output",
        OutputDestination.CONSOLE: "CLI Console",
    }

    if destination == OutputDestination.FILE:
        return OutputHandlerConfig(
            name=destination_names.get(destination, "CLI Output"),
            format=JsonFormatSettings(),
            handler=FileHandlerSettings(path=str(output_file) if output_file else "output.json"),
        )
    elif destination == OutputDestination.CONSOLE:
        return OutputHandlerConfig(
            name=destination_names.get(destination, "CLI Output"),
            format=JsonFormatSettings(),
            handler=ConsoleHandlerSettings(),
        )
    else:  # RETURN is default
        return OutputHandlerConfig(
            name=destination_names.get(destination, "CLI Output"),
            format=JsonFormatSettings(),
            handler=ReturnHandlerSettings(),
        )


def get_app_settings(config_file: str | None = None) -> AppSettings:
    """Get application settings, optionally from a specified config file.

    Args:
        config_file (str | None): Path to the configuration file. If None, use default
            configuration.

    Returns:
        AppSettings: Application settings
    """
    if config_file is None:
        return get_settings()

    original_json_file = AppSettings.model_config.get("env_file")
    AppSettings.model_config["env_file"] = config_file
    settings = AppSettings()
    AppSettings.model_config["env_file"] = original_json_file

    return settings


async def main() -> dict[str, Any] | None:
    """Main function to handle command line arguments and execute detection.

    Returns:
        dict[str, Any] | None: Detected stockpile data or None depending on the output format.
    """
    parser = argparse.ArgumentParser(
        description="Detect quantity boxes and title regions in Foxhole game screenshot"
    )
    parser.add_argument("--image", help="Path to the input image file")
    parser.add_argument("--database", type=Path, help="Path to the template database file")
    parser.add_argument(
        "--early_exit",
        type=float,
        help="Early exit threshold for icon matching.",
    )
    parser.add_argument(
        "--faction",
        type=str,
        help=ItemFaction.get_cli_help_text(),
    )
    parser.add_argument(
        "--language",
        type=str,
        choices=[lang.value for lang in SupportedLanguage],
        help="Language for text detection. If not specified, uses all supported languages.",
    )
    parser.add_argument(
        "--debug_image", action="store_true", help="Save debug image with detected regions"
    )
    parser.add_argument("--log-file", type=Path, help="Path to log file (default: console only)")
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging (debug level)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all output except errors and warnings. "
        "Only errors will be printed to console.",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        choices=[fmt.value for fmt in OutputFormat],
        help="Data serialization format (default: json)",
    )
    parser.add_argument(
        "--output-destination",
        type=str,
        choices=[dest.value for dest in OutputDestination],
        default=None,
        help="Output destination (default: return)",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="File path when using file destination (supports {timestamp} placeholder)",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--token", type=str, help="Override the webhook token from the configuration file"
    )

    args = parser.parse_args()

    # Setup logging and load settings first
    settings = copy(get_app_settings(args.config))

    # Use database from args or fall back to config
    database_path = args.database if args.database is not None else settings.scanner.database_path
    if database_path is None:
        parser.error("Database path must be provided via --database or in config file")

    # Validate database file exists
    if not database_path.exists():
        print(f"Error: Database file not found: {database_path}", file=sys.stderr)
        sys.exit(1)
    if not database_path.is_file():
        print(f"Error: Database path is not a file: {database_path}", file=sys.stderr)
        sys.exit(1)

    # Load and preprocess the image
    _image = await asyncio.to_thread(cv2.imread, args.image, cv2.IMREAD_COLOR)
    if _image is None:
        print(f"Error: Could not load image from '{args.image}'")
        sys.exit(1)

    # Image is already in BGR format (OpenCV default), which is what OCRCoordinator expects
    image = np.asarray(_image, dtype=np.uint8)

    # Determine output settings
    if args.output_destination:
        # Create a single-handler config for the specified destination
        output_destination = OutputDestination(args.output_destination)
        handler_config = _create_handler_config_for_destination(
            output_destination, args.output_file
        )
        output_settings = OutputSettings(handlers=[handler_config])
    elif args.output_file:
        # If output_file is specified without destination, default to file destination
        handler_config = _create_handler_config_for_destination(
            OutputDestination.FILE, args.output_file
        )
        output_settings = OutputSettings(handlers=[handler_config])
    else:
        # Use configured handlers from settings
        output_settings = settings.output

    logging_settings = settings.logging
    # Setup logging
    if args.quiet:
        logging_settings.log_level = "WARNING"
    elif args.verbose:
        logging_settings.log_level = "DEBUG"

    logging_settings.log_file = args.log_file
    setup_logging(logging_settings)

    # Validate inputs
    if not Path(args.image).exists():
        print(f"Error: File '{args.image}' does not exist")
        sys.exit(1)

    # Parse faction filter
    faction_filter = ItemFaction.from_string(args.faction)

    # Parse language filter (wrap single language in list for API)
    language_filter: list[SupportedLanguage] | None = (
        [SupportedLanguage(args.language)] if args.language else None
    )

    try:
        scanner_settings: ScannerSettings = settings.scanner
        scanner_settings.database_path = database_path
        scanner_settings.debug_mode = args.debug_image
        if args.early_exit:
            scanner_settings.early_exit_threshold = args.early_exit

        coordinator = OCRCoordinator(scanner_settings)
        stockpile: Stockpile = await coordinator.analyze_stockpile(
            image, languages=language_filter, faction=faction_filter
        )
        output_coordinator = OutputCoordinator(output_settings=output_settings)

        # Prepare kwargs for output coordinator
        output_kwargs: dict[str, Any] = {}
        if args.token:
            output_kwargs["token"] = args.token

        return await output_coordinator.handle_output(stockpiles=[stockpile], **output_kwargs)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

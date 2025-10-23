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
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.output_format import OutputFormat
from foxhole_stockpiles.enums.supported_language import SupportedLanguage
from foxhole_stockpiles.handlers.output_handler import OutputHandler
from foxhole_stockpiles.models.ocr_coordinator_config import OCRCoordinatorConfig
from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.services.ocr_coordinator import OCRCoordinator


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
    parser.add_argument(
        "--database", type=Path, required=True, help="Path to the template database file"
    )
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
        "--mod",
        type=str,
        help="Mod filter. If not specified, all mods will be included.",
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
        help="Output format for the results (default: console)",
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

    # Load and preprocess the image
    _image = await asyncio.to_thread(cv2.imread, args.image, cv2.IMREAD_COLOR)
    if _image is None:
        print(f"Error: Could not load image from '{args.image}'")
        sys.exit(1)

    # Image is already in BGR format (OpenCV default), which is what OCRCoordinator expects
    image = np.asarray(_image, dtype=np.uint8)

    # Setup logging
    settings = copy(get_app_settings(args.config))
    output_format = (
        OutputFormat(args.output_format)
        if args.output_format
        else settings.output_format.output_format
    )

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

    # Parse mod filter
    mod_filter = args.mod.strip() if args.mod else None

    # Parse language filter
    language_filter = SupportedLanguage(args.language) if args.language else None

    try:
        scanner_settings: OCRCoordinatorConfig = settings.scanner
        scanner_settings.database_path = args.database
        scanner_settings.faction_filter = faction_filter
        scanner_settings.mod_name = mod_filter
        scanner_settings.language = language_filter
        scanner_settings.debug_mode = args.debug_image
        if args.early_exit:
            scanner_settings.early_exit_threshold = args.early_exit

        coordinator = OCRCoordinator(scanner_settings)
        stockpile: Stockpile = await coordinator.analyze_stockpile(image)
        output_handler = OutputHandler(settings=settings)
        return await output_handler.handle_output(
            stockpile=stockpile, output_format=output_format, token=args.token
        )

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

    return None


if __name__ == "__main__":
    stockpile = asyncio.run(main())
    print(stockpile)
    sys.exit(0)

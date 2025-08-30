"""Foxhole Stockpile Detection Script."""

import argparse
import datetime
import logging
import sys
from copy import copy
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from foxhole_stockpiles.connectors.webhook import WebhookConnector
from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.core.settings import AppSettings, get_settings
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.output_format import OutputFormat
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


def main() -> dict[str, Any] | None:
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
        "--confidence",
        type=float,
        default=0.85,
        help="Minimum confidence threshold for icon matching (default: 0.85).",
    )
    parser.add_argument(
        "--early_exit",
        type=float,
        default=0.95,
        help="Early exit threshold for icon matching (default: 0.95).",
    )
    parser.add_argument(
        "--faction",
        type=str,
        help=ItemFaction.get_cli_help_text(),
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
        default=OutputFormat.CONSOLE.value,
        help="Output format for the results (default: console)",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
    )

    args = parser.parse_args()

    # Load and preprocess the image
    _image = cv2.imread(args.image, cv2.IMREAD_COLOR)
    if _image is None:
        print(f"Error: Could not load image from '{args.image}'")
        sys.exit(1)

    # Convert BGR to RGB for processing
    image = np.asarray(cv2.cvtColor(_image, cv2.COLOR_BGR2RGB), dtype=np.uint8)

    output_format = OutputFormat(args.output_format)

    # Setup logging
    settings = copy(get_app_settings(args.config))
    logging_settings = settings.logging
    # Setup logging
    if args.quiet:
        logging_settings.log_level = "WARNING"
    elif args.verbose:
        logging_settings.log_level = "DEBUG"

    logging_settings.log_file = args.log_file
    setup_logging(logging_settings)

    # Validate inputs
    if args.confidence < 0.0 or args.confidence > 1.0:
        parser.error("Confidence threshold must be between 0.0 and 1.0")

    if not Path(args.image).exists():
        print(f"Error: File '{args.image}' does not exist")
        sys.exit(1)

    # Parse faction filter
    faction_filter = None
    if args.faction:
        faction_filter = ItemFaction.from_string(args.faction)

    try:
        scanner_settings: OCRCoordinatorConfig = settings.scanner
        scanner_settings.database_path = args.database
        scanner_settings.confidence_threshold = args.confidence
        scanner_settings.faction_filter = faction_filter
        scanner_settings.debug_mode = args.debug_image
        scanner_settings.early_exit_threshold = args.early_exit

        coordinator = OCRCoordinator(scanner_settings)
        stockpile: Stockpile = coordinator.analyze_stockpile(image)

        match output_format:
            case OutputFormat.CONSOLE:
                logger = logging.getLogger(__name__)
                logger.info("Name: %s", stockpile.name)
                logger.info("Type: %s", stockpile.type.value)
                logger.info("Hex: %s", stockpile.hex_name)
                logger.info("Shard: %s", stockpile.shard)
                logger.info("Ingame timestamp: %s", stockpile.ingame_timestamp)
                logger.info("Items:")
                for item in stockpile.items:
                    code = item.code
                    if item.crated:
                        code += "_crated"
                    logger.info(
                        "* code: %-35s quantity: %-3d, confidence: %.3f",
                        code,
                        item.quantity,
                        item.confidence or 0.0,
                    )
            case OutputFormat.JSON:
                return stockpile.model_dump(mode="json")
            case OutputFormat.FILE:
                file = settings.output_format.file_path
                if not file:
                    file = "output.json"

                if "{timestamp}" in file:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    file = file.replace("{timestamp}", timestamp)
                output_path = Path(file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with output_path.open("w", encoding="utf-8") as f:
                    f.write(stockpile.model_dump_json())
            case OutputFormat.WEBHOOK:
                if not settings.output_format.webhook_url:
                    raise ValueError("Webhook URL is not set in the configuration")

                webhook_connector = WebhookConnector(settings.output_format)
                if not webhook_connector:
                    raise ValueError("Failed to initialize Webhook connector")

                payload = stockpile.model_dump(mode="json")
                response = webhook_connector.send_stockpile(payload)
                logger = logging.getLogger(__name__)
                logger.info("Webhook response: %s", response)

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
    stockpile = main()
    print(stockpile)
    sys.exit(0)

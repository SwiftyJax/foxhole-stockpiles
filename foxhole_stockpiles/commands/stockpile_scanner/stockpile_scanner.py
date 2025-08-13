"""Foxhole Stockpile Detection Script."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.models.ocr_coordinator_config import OCRCoordinatorConfig
from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.services.ocr_coordinator import OCRCoordinator


def main() -> dict[str, Any]:
    """Main function to handle command line arguments and execute detection.

    Returns:
        dict: Output of the scanned stockpile.
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
        default=0.8,
        help="Minimum confidence threshold for icon matching (default: 0.8). "
        "Only used with --icon parameter.",
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
    args = parser.parse_args()

    # Setup logging
    if args.quiet:
        log_level = logging.WARNING
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    setup_logging(log_level=log_level, log_file=str(args.log_file) if args.log_file else "")

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
        # Create configuration and coordinator
        config = OCRCoordinatorConfig(
            database_path=args.database,
            confidence_threshold=args.confidence,
            faction_filter=faction_filter,
            debug_mode=args.debug_image,
        )

        coordinator = OCRCoordinator(config)

        # Analyze the stockpile
        stockpile: Stockpile = coordinator.analyze_stockpile(args.image)
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
            logger.info("* code: %-35s quantity: %d", code, item.quantity)

        return stockpile.model_dump(mode="json")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    stockpile = main()
    print(stockpile)
    sys.exit(0)

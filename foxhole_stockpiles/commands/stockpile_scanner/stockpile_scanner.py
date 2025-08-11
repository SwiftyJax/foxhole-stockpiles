"""Foxhole Stockpile Detection Script."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.core.utils import most_frequent
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.stockpile_image_regions import StockpileImageRegions
from foxhole_stockpiles.services.stockpile_detector import StockpileDetector
from foxhole_stockpiles.services.template_manager import TemplateManager


def main() -> None:
    """Main function to handle command line arguments and execute detection."""
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
    logger = logging.getLogger(__name__)

    # Parse faction filter
    faction_filter = None
    if args.faction:
        faction_filter = ItemFaction.from_string(args.faction)
        logger.info("Using faction filter: %s", faction_filter.value)

    # Validate confidence parameter
    if args.confidence < 0.0 or args.confidence > 1.0:
        parser.error("Confidence threshold must be between 0.0 and 1.0")

    # Check if input file exists
    if not Path(args.image).exists():
        print(f"Error: File '{args.image}' does not exist")
        sys.exit(1)

    try:
        # Create detector and process image
        detector = StockpileDetector(args.image)
    except FileNotFoundError as e:
        logger.exception("Error: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        sys.exit(1)

    detector.analize()
    if args.debug_image:
        detector.draw_and_save_results()

    # Display results
    ("\nDetection Summary:")
    logger.info("- Resolution scale factor: %.3f", detector.scale_factor)
    logger.info("- Detected %d quantity boxes", len(detector.quantities))
    logger.info("- Detected %d icon groups", len(detector.groups))

    stockpile_images: StockpileImageRegions = detector.get_stockpile_images()

    # Initialize template manager
    manager = TemplateManager(database_path=args.database)

    try:
        target_resolution = SupportedResolution(str(stockpile_images.vertical_resolution))
    except ValueError:
        valid_resolutions = [r.value for r in SupportedResolution]
        parser.error(
            f"Invalid resolution '{stockpile_images.vertical_resolution}'. "
            f"Valid resolutions are: {', '.join(valid_resolutions)}"
        )
    manager.set_active_resolution(int(target_resolution.value))
    database = manager.load_database(resolution=target_resolution)

    logger.info(
        "Loaded database for resolution %s with %d templates",
        target_resolution.value,
        len(database.templates),
    )

    scanned_stockpile: dict[str, Any] = {
        "items": [],
        "quantities": [],
        "type": "",
        "name": "",
        "hex_name": "",
        "shard": "",
        "timestamp": "",
    }
    mod: str | None = None
    for group_index, (group_amount, group_start_index) in enumerate(stockpile_images.groups):
        logger.debug(
            "Processing group %d with %d icons starting at index %d",
            group_index,
            group_amount,
            group_start_index,
        )

        category: ItemCategory | None = None
        crated: bool | None = None
        detected: dict[str, list[Any]] = {"category": [], "crated": [], "mod": []}
        for icon_index in range(group_start_index, group_start_index + group_amount):
            category = ItemCategory.Invalid
            image = stockpile_images.icons[icon_index]
            if image is None:
                logger.warning("Icon image at index %d is None, skipping", icon_index)
                continue

            logger.debug("Processing icon at index %d", icon_index)

            try:
                match_result = manager.match_icon(
                    icon_image=image,
                    confidence_threshold=args.confidence,
                    faction=faction_filter,
                    category=category,
                    crated=crated,
                    mod=mod,
                )

                icon_match = match_result.icon
                if not icon_match:
                    logger.warning(
                        "Group %d: No match found for icon at index %d with confidence %.2f",
                        group_index,
                        icon_index,
                        args.confidence,
                    )
                    continue

                # Add the item to the scanned stockpile
                scanned_stockpile["items"].append(icon_match.code)

                # Update the detected properties once we have enough data,
                expected_length = 2 if group_index == 0 else 5
                if len(detected["category"]) >= expected_length:
                    category = most_frequent(detected["category"])
                    crated = most_frequent(detected["crated"])
                    if mod is None:
                        mod = most_frequent(detected["mod"])
                else:
                    detected["category"].append(icon_match.category.value)
                    detected["crated"].append(icon_match.crated)
                    detected["mod"].append(icon_match.mod)

                logger.info(
                    "Group %d: Icon at index %d matched with template '%s%s' (confidence: %.2f)",
                    group_index,
                    icon_index,
                    icon_match.code,
                    " (crated)" if icon_match.crated else "",
                    match_result.confidence,
                )

            except Exception as e:
                logger.error("Error during candidate filtering/icon matching: %s", e)
                if args.verbose:
                    logger.exception("Full error details:")


if __name__ == "__main__":
    sys.argv = [
        "stockpile_scanner.py",
        "--database",
        "database/db.pkl",
        "--image",
        "/mnt/c/Users/Xurxogr/Downloads/02-33-06-Seaport-VELI-PTD-C-1920x1080-5KkRRsD35C.png",
        "--debug_image",
    ]
    main()

"""Test candidates command for debugging template matching."""

import argparse
import logging
from pathlib import Path
from typing import Any

import cv2
import numpy

from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.services.template_manager import TemplateManager


def print_message(message: str, quiet: bool = False) -> None:
    """Print a message to the console if not in quiet mode."""
    if not quiet:
        print(message)


def main() -> dict[str, Any] | None:
    """Main entry point for test candidates command.

    Always uses TemplateManager.match_icon() to get candidates and optionally
    perform icon matching. Returns structured results with candidate indices
    and optional icon match details.

    Returns:
        dict[str, Any] | None: Results or None
    """
    parser = argparse.ArgumentParser(
        description="Test template candidates matching and icon recognition for debugging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Test all candidates for specific resolution\n"
            "  python -m foxhole_stockpiles.commands.database_builder.test_candidates \\\n"
            "    --database db.pkl --resolution 1080\n"
            "\n"
            "  # Test candidates for specific item\n"
            "  python -m foxhole_stockpiles.commands.database_builder.test_candidates \\\n"
            "    --database db.pkl --filter Rifle --resolution 1080\n"
            "\n"
            "  # Test candidates with faction, crated, and resolution filters\n"
            "  python -m foxhole_stockpiles.commands.database_builder.test_candidates \\\n"
            "    --database db.pkl --faction c --crated true --resolution 1080 --print\n"
            "\n"
            "  # Test icon matching against filtered candidates\n"
            "  python -m foxhole_stockpiles.commands.database_builder.test_candidates \\\n"
            "    --database db.pkl --resolution 1080 --icon icon.png --faction c\n"
        ),
    )

    parser.add_argument(
        "--database", type=Path, required=True, help="Path to the template database file"
    )
    parser.add_argument(
        "--code", type=str, help="Item code to search for (partial match supported)"
    )
    parser.add_argument(
        "--faction",
        type=str,
        help=ItemFaction.get_cli_help_text(),
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=[category.value for category in ItemCategory],
        help="Category filter. Valid categories: "
        + ", ".join([f"'{c.value}'" for c in ItemCategory])
        + ". "
        "If not specified, all categories will be included.",
    )
    parser.add_argument(
        "--crated",
        type=str,
        choices=["true", "false"],
        help="Crated filter: 'true' for crated items only, 'false' for normal items only. "
        "If not specified, both crated and normal items will be included.",
    )
    parser.add_argument(
        "--mod", type=str, help="Mod filter. If not specified, all mods will be included. "
    )
    parser.add_argument(
        "--resolution",
        type=str,
        required=True,
        help="Resolution filter (e.g., '1080', '2160'). Required parameter.",
    )
    parser.add_argument(
        "--icon",
        type=Path,
        help="Path to icon image file to match against filtered candidates. "
        "When specified, performs template matching in addition to candidate listing.",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.8,
        help="Minimum confidence threshold for icon matching (default: 0.8). "
        "Only used with --icon parameter.",
    )
    parser.add_argument(
        "--phash-threshold",
        type=int,
        default=12,
        help="Maximum Hamming distance for pHash filtering (default: 12). "
        "Lower values are more strict. Only used with --icon.",
    )
    parser.add_argument(
        "--max-ncc-candidates",
        type=int,
        default=10,
        help="Maximum candidates for NCC optimization (default: 10). "
        "Only used with --icon and optimization enabled.",
    )
    parser.add_argument("--log-file", type=Path, help="Path to log file (default: console only)")
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging (debug level)"
    )
    parser.add_argument(
        "--print",
        action="store_true",
        default=False,
        help="Print full list of matching candidates. If not specified, only shows count.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress all output except errors and warnings. "
        "Only errors will be printed to console.",
    )

    args = parser.parse_args()

    # Validate confidence parameter
    if args.confidence < 0.0 or args.confidence > 1.0:
        parser.error("Confidence threshold must be between 0.0 and 1.0")

    # Setup logging
    if args.quiet:
        log_level = logging.WARNING
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    setup_logging(log_level=log_level, log_file=str(args.log_file) if args.log_file else "")

    logger = logging.getLogger(__name__)

    # Initialize template manager
    manager = TemplateManager(database_path=args.database)

    # Parse resolution (required)
    try:
        target_resolution = SupportedResolution(args.resolution)
    except ValueError:
        valid_resolutions = [r.value for r in SupportedResolution]
        parser.error(
            f"Invalid resolution '{args.resolution}'. "
            f"Valid resolutions are: {', '.join(valid_resolutions)}"
        )

    try:
        # Load the database for the target resolution
        database = manager.load_database(resolution=target_resolution)
        logger.debug(
            "Loaded database for resolution %s with %d templates",
            target_resolution.value,
            len(database.templates),
        )
    except FileNotFoundError:
        logger.error("Database file not found: %s", args.database)
        exit(1)

    # Set active resolution for template manager
    manager.set_active_resolution(int(target_resolution.value))

    # Apply item code filter if specified
    code_filter = None
    if args.code:
        logger.info("Applying item code filter: '%s'", args.code)
        code_filter = args.code.strip()

    # Parse category filter
    category_filter = None
    if args.category:
        category_filter = ItemCategory(args.category)
        logger.info("Using category filter: %s", category_filter.value)

    # Parse mod filter
    mod_filter = None
    if args.mod:
        mod_filter = args.mod.strip()
        logger.info("Using mod filter: %s", mod_filter)

    # Parse faction filter
    faction_filter = None
    if args.faction:
        faction_filter = ItemFaction.from_string(args.faction)
        logger.info("Using faction filter: %s", faction_filter.value)

    # Parse crated filter
    crated_filter = None
    if args.crated:
        crated_filter = args.crated.lower() == "true"
        logger.info("Using crated filter: %s", crated_filter)

    # Load and validate icon image if provided
    icon_image = None
    if args.icon:
        try:
            if not args.icon.exists():
                logger.error("Icon file not found: %s", args.icon)
                exit(1)

            # Load image in BGR format (OpenCV default)
            _icon_image = cv2.imread(str(args.icon), cv2.IMREAD_COLOR)
            if _icon_image is None:
                logger.error("Failed to load icon image: %s", args.icon)
                exit(1)

            logger.debug("Loaded icon image: %s (shape: %s)", args.icon, _icon_image.shape)
            icon_image = _icon_image.astype(numpy.uint8)

        except Exception as e:
            logger.error("Error loading icon image: %s", e)
            if args.verbose:
                logger.exception("Full error details:")
            exit(1)

    # Always use match_icon to get candidates and optional icon matching
    try:
        match_result = manager.match_icon(
            icon_image=icon_image,
            faction=faction_filter,
            mod=mod_filter,
            category=category_filter,
            crated=crated_filter,
            code=code_filter,
            confidence_threshold=args.confidence,
            phash_threshold=args.phash_threshold,
            max_ncc_candidates=args.max_ncc_candidates,
        )

        candidate_indices = match_result.candidates
        icon_match = match_result.icon
    except Exception as e:
        logger.error("Error during candidate filtering/icon matching: %s", e)
        if args.verbose:
            logger.exception("Full error details:")
        exit(1)

    # Display results
    if not candidate_indices:
        logger.info("No candidates found matching the specified criteria.")
        return None

    # Display icon matching results if icon was provided
    if args.icon:
        if icon_match:
            crated_str = " (crated)" if icon_match.crated else ""
            logger.info(
                (
                    f"Match found: {icon_match.code}{crated_str}"
                    f" Faction: {icon_match.faction.value}"
                    f" Category: {icon_match.category.value}"
                    f" Mod: {icon_match.mod}"
                    f" Confidence: {match_result.confidence:.4f}"
                    f" Threshold: {args.confidence}"
                    f" Resolution: {icon_match.resolution.value}px"
                ),
            )
        else:
            logger.info(
                (
                    f"No match found above confidence threshold {args.confidence}"
                    f" Searched {len(candidate_indices)} candidates"
                ),
            )
    else:
        logger.info(f"Total: {len(candidate_indices)} candidates")

    # Show regular candidate listing results when no icon provided
    if args.print and candidate_indices:
        logger.info(
            "%-25s | %-10s | %-12s | %-15s | Resolution", "Code", "Faction", "Category", "Mod"
        )
        for idx in candidate_indices:
            template = database.templates[idx]
            crated_str = " (crated)" if template.crated else ""
            logger.info(
                "%-25s | %-10s | %-12s | %-15s | %spx%s",
                template.code,
                template.faction.value,
                template.category.value,
                template.mod,
                template.resolution.value,
                crated_str,
            )
    else:
        logger.info("Found %d candidates", len(candidate_indices))

    # Show statistics breakdown (only for candidate listing, not icon matching)
    if candidate_indices and not args.icon:
        logger.info("Statistics breakdown:")

        # Count by faction, mod, and category
        faction_counts: dict[str, int] = {}
        mod_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}
        crated_counts = {"normal": 0, "crated": 0}

        for idx in candidate_indices:
            template = database.templates[idx]

            # Count factions
            faction_counts[template.faction.value] = (
                faction_counts.get(template.faction.value, 0) + 1
            )

            # Count mods
            mod_counts[template.mod] = mod_counts.get(template.mod, 0) + 1

            # Count categories
            category_counts[template.category.value] = (
                category_counts.get(template.category.value, 0) + 1
            )

            # Count crated vs normal
            if template.crated:
                crated_counts["crated"] += 1
            else:
                crated_counts["normal"] += 1

        logger.info(
            (
                f"Factions: {dict(sorted(faction_counts.items()))}"
                f"Mods: {dict(sorted(mod_counts.items()))}"
                f"Categories: {dict(sorted(category_counts.items()))}"
                f"Types: {crated_counts}"
            ),
        )

    if icon_match is None:
        return None

    data = icon_match.model_dump(mode="json", exclude={"image"})
    data["confidence"] = match_result.confidence
    return data


if __name__ == "__main__":
    result = main()
    import json
    import sys

    print(json.dumps(result) if result is not None else "")
    sys.exit(0)

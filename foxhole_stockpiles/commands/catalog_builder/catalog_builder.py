"""Catalog builder command for Foxhole stockpile items.

This module builds catalog files from PAK files by:
1. Extracting needed directories from PAK using repak
2. Converting .uasset files to .json using UAssetGUI
3. Building the catalog using CatalogAssembler
"""

import argparse
import asyncio
import json
import logging
import sys
from copy import copy
from pathlib import Path

from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.core.settings import get_settings
from foxhole_stockpiles.services.catalog_builder import (
    BlueprintExtractor,
    CatalogAssembler,
)

DEFAULT_PAK_FILE = (
    r"C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks"
    r"\War-WindowsNoEditor.pak"
)
DEFAULT_EXTRACTOR = r"C:\repak\repak.exe"
DEFAULT_CONVERTER = r"C:\UAssetGUI\UAssetGUI.exe"
DEFAULT_OUTPUT = "catalog.json"


async def main() -> None:
    """Command-line interface for catalog builder."""
    parser = argparse.ArgumentParser(
        description="Build catalog from Foxhole PAK file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--pak",
        type=Path,
        default=DEFAULT_PAK_FILE,
        help="Path to War-WindowsNoEditor.pak file",
    )
    parser.add_argument(
        "--extractor",
        type=Path,
        default=DEFAULT_EXTRACTOR,
        help="Path to repak.exe extraction tool",
    )
    parser.add_argument(
        "--converter",
        type=Path,
        default=DEFAULT_CONVERTER,
        help="Path to UAssetGUI.exe conversion tool",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output path for catalog JSON",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep temporary extraction directory",
    )
    parser.add_argument(
        "--force-extract",
        action="store_true",
        help="Force re-extraction from PAK even if JSON files exist",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel conversions",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to log file (default: console only)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (debug level)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all output except errors",
    )
    parser.add_argument(
        "--extract-dir",
        type=Path,
        help="Use existing extraction directory instead of extracting from PAK (e.g., war/)",
    )

    args = parser.parse_args()

    # Setup logging
    settings = copy(get_settings())
    logging_settings = settings.logging

    if args.quiet:
        logging_settings.log_level = "WARNING"
    elif args.verbose:
        logging_settings.log_level = "DEBUG"

    logging_settings.log_file = args.log_file
    setup_logging(logging_settings)

    logger = logging.getLogger(__name__)

    # Get extraction directory
    if args.extract_dir:
        extract_dir = args.extract_dir
        logger.debug("Using provided extraction directory: %s", extract_dir)
    else:
        # Extract from PAK
        # Use temp directory if --keep-temp, otherwise cache in "war/" directory
        extraction_dir = None if args.keep_temp else Path("war")
        extractor = BlueprintExtractor(
            pak_file=args.pak,
            extractor_tool=args.extractor,
            converter_tool=args.converter,
            max_workers=args.workers,
            force_extract=args.force_extract,
            extraction_dir=extraction_dir,
        )

        extract_dir = await extractor.extract()

        logger.debug(
            "Files extracted: %d, converted: %d",
            extractor.stats["extracted"],
            extractor.stats["converted"],
        )

    # Build catalog using service
    logger.info("Building catalog...")
    try:
        service = CatalogAssembler.from_extract_dir(extract_dir)
    except (FileNotFoundError, NotADirectoryError) as e:
        logger.error("Invalid extraction directory: %s", e)
        sys.exit(1)

    catalog = service.build_catalog()

    # Write output (sorted keys for easier comparison)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, sort_keys=True, ensure_ascii=False)

    # Print summary
    stats = service.get_stats()
    logger.info(
        "Catalog Build Summary. Files parsed: %d, Stockpilable items: %d, "
        "Errors: %d. written to %s",
        stats["parsed"],
        stats["stockpilable"],
        stats["errors"],
        args.output,
    )


if __name__ == "__main__":
    asyncio.run(main())

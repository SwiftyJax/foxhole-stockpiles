#!/usr/bin/env python3
"""CLI command to update template database to the latest format.

This command:
1. Checks if database migrations are needed
2. Applies necessary migrations (convert pickle to HDF5)
3. Reports results

Current migrations:
- Convert pickle database to HDF5 format (reduces memory usage, improves load times)

Note: Migrations create a new database file without modifying the original,
so your original database is automatically preserved.
"""

import argparse
import logging
from copy import copy
from pathlib import Path

from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.core.settings import get_settings
from foxhole_stockpiles.services.template_database import DATABASE_VERSION
from foxhole_stockpiles.services.template_manager import TemplateManager

logger = logging.getLogger(__name__)


async def main() -> int:
    """Main entry point for the update-db command.

    Returns:
        int: Exit code (0 = success, 1 = error)
    """
    parser = argparse.ArgumentParser(
        description="Update template database to the latest format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fs update-db                          # Check and apply needed migrations
  fs update-db --output /path/to/new.h5 # Specify custom output path

Migrations:
  - pickle_to_hdf5: Convert pickle database to HDF5 format
    This reduces memory usage by loading only needed resolutions,
    improves load times, and supports better compression.

Note: Migrations create a new database file without modifying the original.
Your original database is automatically preserved as a backup.
The server must be restarted after running this command.
        """,
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Custom output path for migrated database (default: <database>.h5)",
    )

    parser.add_argument(
        "--database-path",
        type=Path,
        help="Path to database file (default: from config)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (debug level)",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress all output except errors and warnings",
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to log file (default: console only)",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of worker processes for parallel migration (default: CPU count)",
    )

    args = parser.parse_args()

    # Setup logging
    settings = get_settings()
    logging_settings = copy(settings.logging)

    if args.quiet:
        logging_settings.log_level = "WARNING"
    elif args.verbose:
        logging_settings.log_level = "DEBUG"

    logging_settings.log_file = args.log_file
    setup_logging(logging_settings)

    # Get database path from config or args
    if args.database_path:
        database_path = args.database_path
    else:
        if settings.scanner.database_path is None:
            logger.error("No database path configured")
            logger.error("Set scanner.database_path in config or use --database-path")
            return 1
        database_path = settings.scanner.database_path

    # Check if database exists
    if not database_path.exists():
        logger.error("Database file not found: %s", database_path)
        logger.info("Nothing to migrate.")
        return 1

    logger.info("Checking database migrations for: %s", database_path)

    # Create TemplateManager instance
    manager = TemplateManager(database_path=database_path)

    # Determine current version first
    db_version = manager._check_database_version(database_path)

    if db_version == 0:
        logger.error("Database file is corrupted or in an unrecognized format")
        return 1

    # Check if migration is needed
    if not manager.needs_migration():
        logger.info("Database is already at current version (%d)!", DATABASE_VERSION)
        logger.info("No migrations needed.")
        return 0

    # Determine output path
    output_path = args.output if args.output else database_path.with_suffix(".h5")
    logger.info("Output: %s", output_path)

    try:
        manager.migrate_database(output_path=output_path, workers=args.workers)
    except Exception as e:
        logger.error("Migration failed: %s", e, exc_info=True)
        return 1

    # Success summary
    logger.info("Migration completed successfully!")
    logger.info("Next steps:")
    logger.info("  1. Update your configuration to use the new HDF5 database:")
    logger.info("     scanner.database_path: %s", output_path)
    logger.info("  2. Restart the server to use the new HDF5 format")
    logger.info("  3. Verify everything works correctly")

    return 0

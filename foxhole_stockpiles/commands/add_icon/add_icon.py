"""Add icon command for manually adding icons to template databases."""

import argparse
import asyncio
import logging
import pickle
import sys
from copy import copy
from pathlib import Path

import cv2
import numpy

from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.core.settings import get_settings
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.icon_template import IconTemplate
from foxhole_stockpiles.services.template_database import TemplateDatabase


class IconAdder:
    """Adds individual icons to existing template databases."""

    def __init__(self, database_path: Path) -> None:
        """Initialize icon adder.

        Args:
            database_path (Path): Path to existing database file

        Raises:
            FileNotFoundError: If database file does not exist
            ValueError: If database cannot be loaded
        """
        self._logger = logging.getLogger(__name__)
        self.database_path = database_path

        if not database_path.exists():
            raise FileNotFoundError(f"Database file not found: {database_path}")

        # Load existing databases
        self.databases = self._load_databases()
        if not self.databases:
            raise ValueError(f"No databases found in {database_path}")

    def _load_databases(self) -> dict[SupportedResolution, TemplateDatabase]:
        """Load databases from pickle file.

        Returns:
            dict[SupportedResolution, TemplateDatabase]: Loaded databases

        Raises:
            ValueError: If database file is corrupted or invalid
        """
        self._logger.debug("Loading databases from %s", self.database_path)

        try:
            with open(self.database_path, "rb") as f:
                databases: dict[SupportedResolution, TemplateDatabase] = pickle.load(f)

            self._logger.info(
                "Loaded %d resolution databases from %s",
                len(databases),
                self.database_path,
            )
            return databases

        except Exception as e:
            raise ValueError(f"Failed to load database: {e}") from e

    async def add_icon(
        self,
        icon_path: Path,
        item_code: str,
        faction: ItemFaction,
        category: ItemCategory,
        crated: bool,
        mod: str,
        resolution: SupportedResolution,
        replace: bool = False,
    ) -> None:
        """Add a single icon to the database for a specific resolution.

        Args:
            icon_path (Path): Path to icon image file
            item_code (str): Item code name
            faction (ItemFaction): Item faction
            category (ItemCategory): Item category
            crated (bool): Whether this is a crated variant
            mod (str): Mod name
            resolution (SupportedResolution): Target resolution
            replace (bool): If True, replace existing icon with same metadata; if False, error
                on duplicate

        Raises:
            FileNotFoundError: If icon file does not exist
            ValueError: If resolution not found in database, icon cannot be loaded,
                        or duplicate exists without replace flag
        """
        if not icon_path.exists():
            raise FileNotFoundError(f"Icon file not found: {icon_path}")

        if resolution not in self.databases:
            raise ValueError(
                f"Resolution {resolution.value} not found in database. "
                f"Available resolutions: {[r.value for r in self.databases.keys()]}"
            )

        # Load icon image
        self._logger.debug("Loading icon from %s", icon_path)
        icon_image = await asyncio.to_thread(cv2.imread, str(icon_path))
        if icon_image is None:
            raise ValueError(f"Failed to load icon image: {icon_path}")

        # Calculate expected icon size for this resolution
        icon_scaling_factor = 64 / 2160  # 64px at 2160p
        expected_size = int(icon_scaling_factor * int(resolution.value))

        # Validate icon dimensions
        if icon_image.shape[0] != expected_size or icon_image.shape[1] != expected_size:
            raise ValueError(
                f"Icon has incorrect dimensions {icon_image.shape[1]}x{icon_image.shape[0]}. "
                f"Expected {expected_size}x{expected_size} for resolution {resolution.value}. "
                f"Please resize the icon before adding it to the database."
            )

        # Check for existing icon with same metadata
        database = self.databases[resolution]
        existing_idx = self._find_existing_icon(
            database=database,
            item_code=item_code,
            faction=faction,
            category=category,
            crated=crated,
            mod=mod,
        )

        if existing_idx is not None:
            if not replace:
                raise ValueError(
                    f"Icon already exists for '{item_code}' "
                    f"(faction={faction.value}, category={category.value}, "
                    f"crated={crated}, mod={mod}) in resolution {resolution.value}. "
                    f"Use --replace flag to replace existing icon."
                )
            # Remove existing template
            self._logger.debug(
                "Replacing existing icon at index %d for '%s'", existing_idx, item_code
            )
            database.templates.pop(existing_idx)
            # Rebuild lookup tables after removal
            self._rebuild_lookup_tables(database)

        # Create template
        template = IconTemplate(
            image=icon_image.astype(numpy.uint8),
            code=item_code,
            crated=crated,
            resolution=resolution,
            faction=faction,
            category=category,
            mod=mod,
        )

        # Add to database
        database.add_template(template=template)

        action = "Replaced" if existing_idx is not None else "Added"
        self._logger.info(
            "%s icon for '%s' to resolution %s (crated=%s, faction=%s, category=%s, mod=%s)",
            action,
            item_code,
            resolution.value,
            crated,
            faction.value,
            category.value,
            mod,
        )

    def _find_existing_icon(
        self,
        database: TemplateDatabase,
        item_code: str,
        faction: ItemFaction,
        category: ItemCategory,
        crated: bool,
        mod: str,
    ) -> int | None:
        """Find existing icon with matching metadata.

        Args:
            database (TemplateDatabase): Database to search
            item_code (str): Item code name
            faction (ItemFaction): Item faction
            category (ItemCategory): Item category
            crated (bool): Whether this is a crated variant
            mod (str): Mod name

        Returns:
            int | None: Index of existing template, or None if not found
        """
        for idx, template in enumerate(database.templates):
            if (
                template.code == item_code
                and template.faction == faction
                and template.category == category
                and template.crated == crated
                and template.mod == mod
            ):
                return idx
        return None

    def _rebuild_lookup_tables(self, database: TemplateDatabase) -> None:
        """Rebuild database lookup tables after template removal.

        Args:
            database (TemplateDatabase): Database to rebuild
        """
        # Clear existing lookups
        database.faction_lookup.clear()
        database.mod_lookup.clear()
        database.category_lookup.clear()

        # Rebuild from templates
        for idx, template in enumerate(database.templates):
            # Update faction lookup
            if template.faction.value not in database.faction_lookup:
                database.faction_lookup[template.faction.value] = []
            database.faction_lookup[template.faction.value].append(idx)

            # Update mod lookup
            if template.mod not in database.mod_lookup:
                database.mod_lookup[template.mod] = []
            database.mod_lookup[template.mod].append(idx)

            # Update category lookup
            if template.category.value not in database.category_lookup:
                database.category_lookup[template.category.value] = []
            database.category_lookup[template.category.value].append(idx)

    async def save_databases(self) -> None:
        """Save updated databases back to file."""
        self._logger.debug("Saving databases to %s", self.database_path)

        # Create backup of original database
        backup_path = self.database_path.with_suffix(self.database_path.suffix + ".backup")
        if self.database_path.exists():
            await asyncio.to_thread(lambda: self.database_path.rename(backup_path))
            self._logger.debug("Created backup at %s", backup_path)

        try:
            # Save updated database
            def write_file() -> None:
                """Write databases to pickle file synchronously."""
                with open(self.database_path, "wb") as f:
                    pickle.dump(self.databases, f, protocol=pickle.HIGHEST_PROTOCOL)

            await asyncio.to_thread(write_file)

            # Log statistics
            total_templates = sum(len(db.templates) for db in self.databases.values())
            file_size = self.database_path.stat().st_size / (1024 * 1024)  # MB

            self._logger.info(
                "Database saved: %d resolutions, %d total templates, %.1f MB",
                len(self.databases),
                total_templates,
                file_size,
            )

            # Remove backup on success
            if backup_path.exists():
                await asyncio.to_thread(backup_path.unlink)
                self._logger.debug("Removed backup file")

        except Exception as e:
            # Restore backup on failure
            if backup_path.exists():
                await asyncio.to_thread(lambda: backup_path.rename(self.database_path))
                self._logger.error("Restored backup after save failure")
            raise ValueError(f"Failed to save database: {e}") from e


async def main() -> None:
    """Main entry point for add icon command."""
    parser = argparse.ArgumentParser(
        description="Add individual icons to template database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add a normal Colonial rifle icon at 1080p (icon must be 32x32)
  fs add-icon --database data/templates.h5 --icon rifle_32x32.png \\
    --code Rifle --faction c --category item \\
    --mod vanilla --resolution 1080

  # Add a crated Warden shippable icon at 2160p (icon must be 64x64)
  fs add-icon --database data/templates.h5 --icon crate_64x64.png \\
    --code ShippableCrate --faction w --category shippable \\
    --crated --mod vanilla --resolution 2160

  # Add a neutral item at multiple resolutions (need separate sized icons)
  fs add-icon --database data/templates.h5 --icon medkit_32x32.png \\
    --code Medkit --faction n --category item \\
    --mod vanilla --resolution 1080

  fs add-icon --database data/templates.h5 --icon medkit_43x43.png \\
    --code Medkit --faction n --category item \\
    --mod vanilla --resolution 1440

Note: Icon dimensions must exactly match the target resolution requirements.
      Use: 664p=19px, 720p=21px, 1080p=32px, 1440p=43px, 2160p=64px
        """,
    )

    parser.add_argument(
        "--database",
        type=Path,
        help="Path to existing template database (.h5 file)",
    )
    parser.add_argument(
        "--icon",
        type=Path,
        required=True,
        help="Path to icon image file",
    )
    parser.add_argument(
        "--code",
        type=str,
        required=True,
        help="Item code name (e.g., Rifle, LightTank)",
    )
    parser.add_argument(
        "--faction",
        type=str,
        required=True,
        choices=[faction.value for faction in ItemFaction],
        help="Faction for the icon. Valid factions: "
        + ", ".join([f"'{f.value}'" for f in ItemFaction]),
    )
    parser.add_argument(
        "--category",
        type=str,
        required=True,
        choices=[category.value for category in ItemCategory if category != ItemCategory.Invalid],
        help="Category for the icon. Valid categories: "
        + ", ".join([f"'{c.value}'" for c in ItemCategory if c != ItemCategory.Invalid]),
    )
    parser.add_argument(
        "--crated",
        action="store_true",
        help="Mark this icon as a crated variant",
    )
    parser.add_argument(
        "--mod",
        type=str,
        required=True,
        help="Mod name (e.g., vanilla, modname)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing icon if one already exists with same metadata. "
        "Without this flag, attempting to add a duplicate will result in an error.",
    )
    parser.add_argument(
        "--resolution",
        action="append",
        required=True,
        help=(
            "Target resolution (can be specified multiple times, e.g., "
            "--resolution 1080 --resolution 2160)"
        ),
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

    args = parser.parse_args()

    # Setup logging
    settings = get_settings()

    # Use database from args or fall back to config
    database_path = args.database if args.database is not None else settings.scanner.database_path
    if database_path is None:
        parser.error("Database path must be provided via --database or in config file")

    # Validate database file exists (fail early with clearer error)
    if not database_path.exists():
        print(f"Error: Database file not found: {database_path}", file=sys.stderr)
        sys.exit(1)
    if not database_path.is_file():
        print(f"Error: Database path is not a file: {database_path}", file=sys.stderr)
        sys.exit(1)

    logging_settings = copy(settings.logging)
    if args.quiet:
        logging_settings.log_level = "WARNING"
    elif args.verbose:
        logging_settings.log_level = "DEBUG"

    logging_settings.log_file = args.log_file
    setup_logging(logging_settings)

    # Parse faction
    faction = ItemFaction.from_string(args.faction)
    if faction == ItemFaction.NEUTRAL and args.faction.lower() not in ["neutral", "n"]:
        # Invalid input resulted in NEUTRAL
        parser.error(f"Invalid faction '{args.faction}'. {ItemFaction.get_cli_help_text()}")

    # Parse category
    try:
        category = ItemCategory(args.category)
        if category == ItemCategory.Invalid:
            parser.error(f"Invalid category '{args.category}'")
    except ValueError:
        valid_categories = [c.value for c in ItemCategory if c != ItemCategory.Invalid]
        parser.error(
            f"Invalid category '{args.category}'. "
            f"Valid categories are: {', '.join(valid_categories)}"
        )

    # Parse resolutions
    target_resolutions: list[SupportedResolution] = []
    for res_str in args.resolution:
        try:
            resolution = SupportedResolution(res_str)
            target_resolutions.append(resolution)
        except ValueError:
            valid_resolutions = [r.value for r in SupportedResolution]
            parser.error(
                f"Invalid resolution '{res_str}'. "
                f"Valid resolutions are: {', '.join(valid_resolutions)}"
            )

    # Add icon
    adder = IconAdder(database_path=database_path)

    for resolution in target_resolutions:
        await adder.add_icon(
            icon_path=args.icon,
            item_code=args.code,
            faction=faction,
            category=category,
            crated=args.crated,
            mod=args.mod,
            resolution=resolution,
            replace=args.replace,
        )

    # Save updated database
    await adder.save_databases()

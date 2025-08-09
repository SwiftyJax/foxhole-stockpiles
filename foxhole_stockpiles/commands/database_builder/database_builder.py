"""Database builder for creating resolution-specific template databases."""

import argparse
import logging
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy

from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.core.utils import load_catalog
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.catalog_item import CatalogItem
from foxhole_stockpiles.models.database_statistics import DatabaseStatistics
from foxhole_stockpiles.models.icon_template import IconTemplate
from foxhole_stockpiles.models.template_database import TemplateDatabase


class DatabaseBuilder:
    """Builds basic template databases from extracted game assets."""

    def __init__(self, catalog_path: Path, assets_path: Path, use_scaling: bool = False) -> None:
        """Initialize database builder.

        Args:
            catalog_path (Path): Path to catalog.json file
            assets_path (Path): Path to extracted assets directory
            use_scaling (bool): If True, scale from largest available size when exact size not found

        Raises:
            ValueError: If catalog is empty or cannot be loaded
        """
        self._logger = logging.getLogger(__name__)
        self.assets_path = assets_path
        self.icon_scaling_factor = 64 / 2160  # 64px at 2160p resolution
        self.use_scaling = use_scaling

        # Load catalog data directly
        self.catalog_data = load_catalog(path=catalog_path)
        if not self.catalog_data:
            raise ValueError(f"Catalog is empty or could not be loaded from {catalog_path}")

    def build_all_databases(
        self, output_path: Path, target_resolutions: list[SupportedResolution] | None = None
    ) -> None:
        """Build template databases for specified or all supported resolutions.

        Args:
            output_path (Path): Output path for binary database file
            target_resolutions (list[SupportedResolution] | None): Specific resolutions to build,
                or None to build all supported resolutions
        """
        # Determine which resolutions to build
        resolutions_to_build = target_resolutions or list(SupportedResolution)

        self._logger.info(
            "Starting database build process for %d resolutions: %s",
            len(resolutions_to_build),
            [str(r.value) for r in resolutions_to_build],
        )

        # Build databases for specified resolutions
        databases = {}
        for resolution in resolutions_to_build:
            self._logger.debug("Building database for resolution %s", resolution)
            database = self._build_resolution_database(resolution=resolution)

            if len(database.templates) > 0:
                databases[resolution] = database
                self._logger.debug(
                    "Resolution %s: %d templates created", resolution, len(database.templates)
                )
            else:
                self._logger.warning("Resolution %s: NO templates found - skipping", resolution)

        if not databases:
            raise ValueError("No templates found for any resolution! Check your icon files.")

        # Save combined database
        self._save_databases(databases=databases, output_path=output_path)
        self._logger.debug("Database build completed successfully")

    def _build_resolution_database(self, resolution: SupportedResolution) -> TemplateDatabase:
        """Build template database for specific resolution.

        Args:
            resolution (SupportedResolution): Target resolution

        Returns:
            TemplateDatabase: Built database with all templates
        """
        database = TemplateDatabase(resolution=resolution)
        resolution_height = int(resolution.value)

        # Calculate icon size for this resolution
        icon_size = int(self.icon_scaling_factor * resolution_height)

        self._logger.info(
            "Building templates for resolution %s (icon size: %dpx)", resolution, icon_size
        )

        # Process items in parallel
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []

            for item in self.catalog_data:
                future = executor.submit(
                    self._process_item_templates,
                    item=item,
                    resolution=resolution,
                    icon_size=icon_size,
                )
                futures.append(future)

            # Collect results
            for future in as_completed(futures):
                templates = future.result()
                for template in templates:
                    database.add_template(template=template)

        self._logger.debug(
            "Built %d templates for resolution %s", len(database.templates), resolution
        )

        return database

    def _process_item_templates(
        self, item: CatalogItem, resolution: SupportedResolution, icon_size: int
    ) -> list[IconTemplate]:
        """Process templates for a single item.

        Args:
            item (CatalogItem): Item definition from catalog
            resolution (SupportedResolution): Target resolution
            icon_size (int): Target icon size in pixels

        Returns:
            list[IconTemplate]: Generated templates for this item
        """
        templates: list[IconTemplate] = []
        item_code = item.code

        if not item_code:
            self._logger.warning("Item missing code: %s", item)
            return templates

        # Use faction from CatalogItem (already converted to ItemFaction)
        faction = item.faction

        # Find icon files for this item
        icon_paths = self._find_icon_files(item_code=item_code, icon_size=icon_size)

        for icon_path in icon_paths:
            # Load and process icon
            icon_image = cv2.imread(str(icon_path))
            if icon_image is None:
                self._logger.warning("Failed to load icon: %s", icon_path)
                continue

            # Resize to target size
            icon_image = cv2.resize(icon_image, (icon_size, icon_size))

            # Determine if this is a crated variant
            is_crated = "crated" in icon_path.name.lower()

            # Extract mod name from filename (first part before underscore)
            filename_parts = icon_path.stem.split("_")
            mod_name = filename_parts[0] if filename_parts else "unknown"

            # Create template using Pydantic model
            try:
                template = IconTemplate(
                    image=icon_image.astype(numpy.uint8),
                    code=item_code,
                    crated=is_crated,
                    resolution=resolution,
                    faction=faction,
                    category=item.category,
                    mod=mod_name,
                )
                template.compute_optimization_data()
                templates.append(template)
            except Exception as e:
                self._logger.error("Failed to create template for %s: %s", item_code, e)
                continue

        if not templates:
            self._logger.warning("No templates generated for item: %s", item_code)

        return templates

    def _find_icon_files(self, item_code: str, icon_size: int) -> list[Path]:
        """Find icon files for item and target icon size.

        Args:
            item_code (str): Item code name
            icon_size (int): Target icon size in pixels

        Returns:
            list[Path]: Paths to icon files with exact or scalable sizes
        """
        icon_paths = []

        self._logger.debug(
            "Looking for size %d for item %s (scaling=%s)",
            icon_size,
            item_code,
            self.use_scaling,
        )

        # Look for normal (non-crated) item folder
        item_folder = self.assets_path / item_code
        if item_folder.exists():
            icon_paths.extend(
                self._find_size_variants(
                    folder=item_folder,
                    item_code=item_code,
                    target_size=icon_size,
                    is_crated=False,
                )
            )

        # Look for crated variant folder
        crated_folder = self.assets_path / f"{item_code}_crated"
        if crated_folder.exists():
            icon_paths.extend(
                self._find_size_variants(
                    folder=crated_folder,
                    item_code=item_code,
                    target_size=icon_size,
                    is_crated=True,
                )
            )

        if not icon_paths:
            level = logging.DEBUG if self.use_scaling else logging.WARNING
            self._logger.log(level, "No icons found for item %s at size %d", item_code, icon_size)

        return icon_paths

    def _find_size_variants(
        self, folder: Path, item_code: str, target_size: int, is_crated: bool
    ) -> list[Path]:
        """Find size variants in a folder with exact match or scaling fallback.

        Args:
            folder (Path): Folder to search in
            item_code (str): Item code name
            target_size (int): Target icon size
            is_crated (bool): Whether this is a crated variant

        Returns:
            list[Path]: Found icon file paths
        """
        found_paths = []
        crated_suffix = "_crated" if is_crated else ""

        # First try: exact size match
        exact_pattern = f"*_{item_code}{crated_suffix}_{target_size}.png"
        exact_files = list(folder.glob(exact_pattern))

        if exact_files:
            found_paths.extend(exact_files)
            self._logger.debug(
                "Found %d EXACT size (%d) variants for %s%s",
                len(exact_files),
                target_size,
                item_code,
                crated_suffix,
            )
            return found_paths

        # Second try: scaling fallback (if enabled)
        if not self.use_scaling:
            self._logger.debug(
                "Exact size %d not found for %s%s, scaling disabled",
                target_size,
                item_code,
                crated_suffix,
            )
            return found_paths
        all_pattern = f"*_{item_code}{crated_suffix}_*.png"
        all_files = list(folder.glob(all_pattern))

        if not all_files:
            self._logger.debug("No files found matching pattern %s in %s", all_pattern, folder)
            return found_paths

        # Group by mod name and find largest size for each mod
        mod_files: dict[str, tuple[Path, int]] = {}
        for file_path in all_files:
            # Extract mod name and size
            parts = file_path.stem.split("_")
            if len(parts) >= 3:
                mod_name = parts[0]
                try:
                    size = int(parts[-1])
                    if mod_name not in mod_files or size > mod_files[mod_name][1]:
                        mod_files[mod_name] = (file_path, size)
                except ValueError:
                    self._logger.warning("Invalid size in filename: %s", file_path.name)
                    continue

        # Use largest available size for each mod (will be scaled during template creation)
        for file_path, source_size in mod_files.values():
            found_paths.append(file_path)
            self._logger.debug(
                "Will SCALE %s%s from size %d to %d",
                item_code,
                crated_suffix,
                source_size,
                target_size,
            )

        return found_paths

    def _save_databases(
        self, databases: dict[SupportedResolution, TemplateDatabase], output_path: Path
    ) -> None:
        """Save all databases to binary file.

        Args:
            databases (dict[SupportedResolution, TemplateDatabase]): Built databases
            output_path (Path): Output file path
        """
        self._logger.debug("Saving databases to %s", output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save as pickle file
        with open(output_path, "wb") as f:
            pickle.dump(databases, f, protocol=pickle.HIGHEST_PROTOCOL)

        # Log statistics
        total_templates = sum(len(db.templates) for db in databases.values())
        file_size = output_path.stat().st_size / (1024 * 1024)  # MB

        self._logger.info(
            "Database saved: %d resolutions, %d total templates, %.1f MB",
            len(databases),
            total_templates,
            file_size,
        )

    def validate_database(
        self, database_path: Path, expected_resolutions: list[SupportedResolution] | None = None
    ) -> bool:
        """Validate built database integrity.

        Args:
            database_path (Path): Path to database file
            expected_resolutions (list[SupportedResolution] | None): Expected resolutions to
                validate, or None to validate all supported resolutions

        Returns:
            bool: True if database is valid
        """
        self._logger.info("Validating database: %s", database_path)

        try:
            with open(database_path, "rb") as f:
                databases = pickle.load(f)

            # Determine which resolutions to validate
            resolutions_to_validate = expected_resolutions or list(SupportedResolution)

            # Check expected resolutions are present
            missing_resolutions = set(resolutions_to_validate) - set(databases.keys())
            if missing_resolutions:
                self._logger.error("Missing expected resolutions: %s", missing_resolutions)
                return False

            # Check for unexpected resolutions (if specific resolutions were expected)
            if expected_resolutions:
                unexpected_resolutions = set(databases.keys()) - set(expected_resolutions)
                if unexpected_resolutions:
                    self._logger.warning(
                        "Found unexpected resolutions in database: %s", unexpected_resolutions
                    )

            # Check template counts and get statistics for expected resolutions
            for resolution in resolutions_to_validate:
                if resolution not in databases:
                    continue  # Already logged as missing

                database = databases[resolution]
                if len(database.templates) == 0:
                    self._logger.error("Empty database for resolution %s", resolution)
                    return False

                # Get detailed statistics from the database
                stats: DatabaseStatistics = database.get_statistics()
                self._logger.debug(
                    "Resolution %s: %d templates, factions: %s, mods: %s",
                    resolution,
                    stats.total_templates,
                    stats.faction_counts,
                    stats.mod_counts,
                )

            self._logger.info("Database validation successful")
            return True

        except Exception as e:
            self._logger.error("Database validation failed: %s", e)
            return False


def main() -> None:
    """Main entry point for database builder."""
    parser = argparse.ArgumentParser(description="Build template databases")
    parser.add_argument("--catalog", type=Path, required=True, help="Path to catalog.json")
    parser.add_argument("--templates", type=Path, required=True, help="Path to extracted templates")
    parser.add_argument("--database", type=Path, required=True, help="Output database path")
    parser.add_argument("--validate", action="store_true", help="Validate database after building")
    parser.add_argument(
        "--use-scaling",
        action="store_true",
        help="Scale from largest available size when exact size not found (better quality)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging (debug level)"
    )
    parser.add_argument("--log-file", type=Path, help="Path to log file (default: console only)")
    parser.add_argument(
        "--resolution",
        action="append",
        help=(
            "Resolution to generate (can be specified multiple times, e.g., --resolution 1024"
            " --resolution 2160). If not specified, all supported resolutions will be generated."
        ),
    )

    args = parser.parse_args()

    # Parse and validate resolutions if specified
    target_resolutions = None
    if args.resolution:
        target_resolutions = []

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

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level=log_level, log_file=str(args.log_file) if args.log_file else "")

    # Build database
    builder = DatabaseBuilder(
        catalog_path=args.catalog, assets_path=args.templates, use_scaling=args.use_scaling
    )
    builder.build_all_databases(output_path=args.database, target_resolutions=target_resolutions)

    # Validate if requested
    if args.validate:
        if not builder.validate_database(
            database_path=args.database, expected_resolutions=target_resolutions
        ):
            exit(1)


if __name__ == "__main__":
    main()

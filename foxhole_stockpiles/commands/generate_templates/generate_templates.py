"""Generate training templates command for Foxhole stockpile recognition system."""

import argparse
import logging
from copy import copy
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.core.settings import get_settings
from foxhole_stockpiles.core.utils import load_catalog
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.catalog_item import CatalogItem

logger = logging.getLogger(__name__)


class TemplateGenerator:
    """Generate icon templates from extracted game assets.

    Creates normal and crated versions of icons for multiple resolutions, handles subicon overlays,
    and organizes output by CodeName.
    """

    ICON_SIZE_RATIO: float = 64 / 2160
    SUBICON_ASPECT_RATIO: float = 7 / 16
    SUBICON_ALPHA: float = 0.75
    VANILLA_MOD_NAME: str = "vanilla"

    def __init__(
        self,
        catalog_path: Path,
        assets_path: Path,
        template_path: Path,
        filter_name: str | None = None,
    ) -> None:
        """Initialize the template generator.

        Args:
            catalog_path (Path): Path to the catalog.json configuration file
            assets_path (Path): Path to extracted assets directory with mod subfolders
            template_path (Path): Path where generated templates will be saved
            filter_name (str | None): Optional filter to process only items containing this string
        """
        if not catalog_path.exists():
            raise FileNotFoundError(f"Catalog file not found: {catalog_path}")
        if not assets_path.exists():
            raise FileNotFoundError(f"Assets directory not found: {assets_path}")

        self.assets_path = assets_path
        self.template_path = template_path
        self.filter_name = filter_name

        self.template_path.mkdir(parents=True, exist_ok=True)

        self.available_mods = self._discover_mods(path=assets_path)
        self.catalog_data = load_catalog(path=catalog_path)
        self.crate_icon = self._load_crate_icon()
        self.subicon_cache: dict[str, NDArray[np.uint8] | None] = {}

        logger.info("Template generator initialized")
        logger.info("Assets path: %s", self.assets_path)
        logger.info("Output path: %s", self.template_path)
        logger.info("Available mods: %s", self.available_mods)
        logger.info("Catalog items: %d", len(self.catalog_data))
        if self.filter_name:
            logger.info("Filter applied: %s", self.filter_name)

    def _discover_mods(self, path: Path) -> list[str]:
        """Discover available mod folders in the assets directory.

        Args:
            path (Path): Path to the assets directory

        Returns:
            list[str]: List of available mod folder names, with vanilla prioritized
        """
        mod_folders = []

        for item in path.iterdir():
            if item.is_dir():
                mod_folders.append(item.name)

        # Prioritize vanilla if it exists
        if TemplateGenerator.VANILLA_MOD_NAME in mod_folders:
            mod_folders.remove(TemplateGenerator.VANILLA_MOD_NAME)
            mod_folders.insert(0, TemplateGenerator.VANILLA_MOD_NAME)

        logger.info("Discovered %d mod folders: %s", len(mod_folders), mod_folders)
        return mod_folders

    def _load_crate_icon(self) -> NDArray[np.uint8]:
        """Load the crate overlay icon, preferring vanilla folder.

        Returns:
            np.ndarray: Loaded crate icon as BGRA array

        Raises:
            FileNotFoundError: If the crate icon cannot be found in any mod folder
        """
        crate_icon_path = "War/Content/Textures/UI/Menus/IconFilterCrates"

        for mod_name in self.available_mods:
            crate_icon = self._load_icon_image(icon_path=crate_icon_path, mod_name=mod_name)
            if crate_icon is not None:
                logger.info("Loaded crate icon from %s", mod_name)
                return crate_icon

        raise FileNotFoundError(f"Crate icon not found in any mod folder: {crate_icon_path}")

    def _calculate_icon_size(self, resolution: SupportedResolution) -> int:
        """Calculate icon size for given resolution.

        Args:
            resolution (SupportedResolution): Target resolution

        Returns:
            int: Icon size in pixels for the given resolution
        """
        return int(int(resolution.value) * self.ICON_SIZE_RATIO)

    def _load_icon_image(self, icon_path: str, mod_name: str) -> NDArray[np.uint8] | None:
        """Load an icon image from the specified mod folder.

        Args:
            icon_path (str): Asset path from catalog
            mod_name (str): Name of the mod folder

        Returns:
            np.ndarray | None: Loaded image as BGRA array, or None if not found
        """
        png_path = f"{icon_path}.png"
        full_path = self.assets_path / mod_name / png_path

        logger.debug("Trying to load icon from: %s", full_path)

        if not full_path.exists():
            logger.debug("Icon not found in %s: %s", mod_name, full_path)
            return None

        try:
            image = cv2.imread(str(full_path), cv2.IMREAD_UNCHANGED)
            if image is None:
                logger.debug("Failed to load icon from %s: %s", mod_name, full_path)
                return None

            # Ensure 4 channels (BGRA)
            if len(image.shape) == 2:
                # Grayscale - convert to BGRA
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGRA)
            elif len(image.shape) == 3 and image.shape[2] == 3:
                # BGR - convert to BGRA
                image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
            # If already 4 channels, assume it's BGRA

            # Ensure the image is uint8 type
            result: NDArray[np.uint8] = image.astype(np.uint8)

            logger.debug("Successfully loaded icon from %s: %s", mod_name, full_path)
            return result

        except Exception as e:
            logger.error("Error loading icon %s from %s: %s", full_path, mod_name, e)
            return None

    def _load_subicon_cached(self, subicon_path: str, mod_name: str) -> NDArray[np.uint8] | None:
        """Load a subicon with caching to avoid repeated disk access.

        Args:
            subicon_path (str): Asset path for subicon from catalog
            mod_name (str): Name of the mod folder

        Returns:
            np.ndarray | None: Loaded subicon as BGRA array, or None if not found
        """
        cache_key = f"{mod_name}:{subicon_path}"

        # Check cache first
        if cache_key in self.subicon_cache:
            return self.subicon_cache[cache_key]

        # Try to load and cache the subicon
        subicon = self._load_icon_image(icon_path=subicon_path, mod_name=mod_name)
        if subicon is not None:
            self.subicon_cache[cache_key] = subicon
            logger.debug("Cached subicon from %s: %s", mod_name, subicon_path)
            return subicon

        # If not found and not vanilla, try vanilla fallback
        if mod_name.lower() != TemplateGenerator.VANILLA_MOD_NAME:
            subicon = self._load_subicon_cached(
                subicon_path=subicon_path,
                mod_name=TemplateGenerator.VANILLA_MOD_NAME,
            )
            if subicon is not None:
                self.subicon_cache[cache_key] = subicon
                logger.debug("Fallback to vanilla subicon for %s: %s", mod_name, subicon_path)
                return subicon

        # Not found anywhere
        self.subicon_cache[cache_key] = None
        return None

    def _filter_catalog_items(self, filter_name: str | None) -> list[CatalogItem]:
        """Filter catalog items based on filter_name if provided.

        Args:
            filter_name (str | None): String to filter items by CodeName

        Returns:
            list[CatalogItem]: Filtered catalog data
        """
        if not filter_name:
            return self.catalog_data

        filtered_items = [
            item for item in self.catalog_data if filter_name.lower() in item.code.lower()
        ]

        logger.info(
            "Filter '%s' matched %d out of %d items",
            self.filter_name,
            len(filtered_items),
            len(self.catalog_data),
        )

        if filtered_items:
            matched_names = [item.code for item in filtered_items]
            logger.info("Matched items: %s", ", ".join(matched_names))

        return filtered_items

    def _apply_subicon_effects(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Apply color tint effects to subicon without alpha modification.

        Args:
            image (np.ndarray): Original subicon image as BGRA array

        Returns:
            np.ndarray: Processed image with multiplicative color tint
        """
        # Create a copy to avoid modifying the original
        result = image.copy().astype(np.float32)

        # Only process pixels that have significant alpha (avoid transparent areas)
        alpha_mask = result[:, :, 3] > 10

        result[alpha_mask, 0] = result[alpha_mask, 0] * 145 / 255 + 82  # Blue channel
        result[alpha_mask, 1] = result[alpha_mask, 1] * 152 / 255 + 87  # Green channel
        result[alpha_mask, 2] = result[alpha_mask, 2] * 154 / 255 + 89  # Red channel

        # Clamp values and convert back to uint8
        result = np.clip(result, 0, 255)

        return result.astype(np.uint8)

    def _add_subicon(
        self,
        main_icon: NDArray[np.uint8],
        subicon: NDArray[np.uint8],
        target_size: int,
        top_left: bool = True,
    ) -> NDArray[np.uint8]:
        """Create icon with subicon overlay in top-left corner.

        Args:
            main_icon (np.ndarray): Main icon image as BGRA array
            subicon (np.ndarray): Subicon to overlay as BGRA array
            target_size (int): Target size for the final icon
            top_left (bool): If True, place subicon in top-left corner, else bottom-right

        Returns:
            np.ndarray: Combined icon with subicon overlay on black background
        """
        subicon_size = int(target_size * self.SUBICON_ASPECT_RATIO)

        # Apply color tint
        subicon_tinted = self._apply_subicon_effects(image=subicon)

        # Resize subicon
        subicon_resized = cv2.resize(
            subicon_tinted, (subicon_size, subicon_size), interpolation=cv2.INTER_LANCZOS4
        )

        # Apply alpha blending for subicon overlay
        alpha_subicon = (subicon_resized[:, :, 3:4].astype(np.float32) / 255.0) * self.SUBICON_ALPHA

        # Blend subicon in top-left corner or bottom-right corner
        if top_left:
            x_pos = 0
            y_pos = 0
        else:
            x_pos = target_size - subicon_size
            y_pos = target_size - subicon_size

        for c in range(3):  # BGR channels
            main_icon[y_pos : y_pos + subicon_size, x_pos : x_pos + subicon_size, c] = (
                1 - alpha_subicon[:, :, 0]
            ) * main_icon[y_pos : y_pos + subicon_size, x_pos : x_pos + subicon_size, c] + (
                alpha_subicon[:, :, 0] * subicon_resized[:, :, c]
            )
        return main_icon

    def _create_base_icon(
        self, main_icon: NDArray[np.uint8], subicon: NDArray[np.uint8] | None, target_size: int
    ) -> NDArray[np.uint8]:
        """Create base icon with optional subicon overlay.

        Args:
            main_icon (np.ndarray): Main icon image as BGRA array
            subicon (np.ndarray | None): Optional subicon to overlay
            target_size (int): Target size for the final icon

        Returns:
            np.ndarray: Base icon with black background and optional subicon overlay
        """
        # Create black background for normal icons
        base_icon = np.zeros((target_size, target_size, 4), dtype=np.uint8)
        base_icon[:, :, 3] = 255  # Set alpha to fully opaque
        main_resized = cv2.resize(
            main_icon, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4
        )

        # Blend main icon with black background
        alpha_main = main_resized[:, :, 3:4].astype(np.float32) / 255.0
        for c in range(3):  # BGR channels
            base_icon[:, :, c] = (1 - alpha_main[:, :, 0]) * base_icon[:, :, c] + alpha_main[
                :, :, 0
            ] * main_resized[:, :, c]

        if subicon is not None:
            return self._add_subicon(main_icon=base_icon, subicon=subicon, target_size=target_size)

        return base_icon

    def _generate_templates_for_item_and_mod(self, item: CatalogItem, mod_name: str) -> bool:
        """Generate all template variants for a single catalog item from a specific mod.

        Args:
            item (CatalogItem): Item data from catalog
            mod_name (str): Name of the mod folder

        Returns:
            bool: True if templates were generated successfully, False otherwise
        """
        code_name = item.code
        icon_path = item.icon_path
        subtype_icon_path = item.subicon_path

        if not code_name or not icon_path:
            logger.warning("Item missing CodeName or Icon: %s", item)
            return False

        logger.debug("Processing %s from mod %s (icon: %s)", code_name, mod_name, icon_path)

        # Load main icon from the specific mod
        main_icon = self._load_icon_image(icon_path=icon_path, mod_name=mod_name)
        if main_icon is None:
            logger.warning(
                "Failed to load main icon for %s from %s: %s", code_name, mod_name, icon_path
            )
            return False

        # Load subicon if present
        subicon = None
        if subtype_icon_path:
            subicon = self._load_subicon_cached(subicon_path=subtype_icon_path, mod_name=mod_name)
            if subicon is None:
                logger.debug(
                    "Failed to load subicon for %s from %s: %s",
                    code_name,
                    mod_name,
                    subtype_icon_path,
                )

        # Create output directories for this item
        normal_output_dir = self.template_path / code_name
        crated_output_dir = self.template_path / f"{code_name}_crated"
        normal_output_dir.mkdir(exist_ok=True)
        crated_output_dir.mkdir(exist_ok=True)

        success_count = 0
        total_expected = len(SupportedResolution) * 2  # 2 variants per resolution

        # Generate templates for each resolution
        for resolution in SupportedResolution:
            icon_size = self._calculate_icon_size(resolution=resolution)

            try:
                # Create base icon (with or without subicon)
                base_icon = self._create_base_icon(
                    main_icon=main_icon, subicon=subicon, target_size=icon_size
                )

                # Save normal version
                normal_filename = f"{mod_name}_{code_name}_{icon_size}.png"
                normal_path = normal_output_dir / normal_filename
                cv2.imwrite(str(normal_path), base_icon)
                success_count += 1
                logger.debug("Saved: %s", normal_path)

                # Create and save crated version
                crated_icon = self._add_subicon(
                    main_icon=base_icon,
                    subicon=self.crate_icon,
                    target_size=icon_size,
                    top_left=False,
                )
                crated_filename = f"{mod_name}_{code_name}_crated_{icon_size}.png"
                crated_path = crated_output_dir / crated_filename
                cv2.imwrite(str(crated_path), crated_icon)
                success_count += 1
                logger.debug("Saved: %s", crated_path)

                logger.debug(
                    "Generated templates for %s from %s at %dpx", code_name, mod_name, icon_size
                )

            except Exception as e:
                logger.error(
                    "Error generating templates for %s from %s at %dpx: %s",
                    code_name,
                    mod_name,
                    icon_size,
                    e,
                )

        if success_count == total_expected:
            logger.debug(
                "Successfully generated all templates for %s from %s (%d/%d)",
                code_name,
                mod_name,
                success_count,
                total_expected,
            )
            return True
        logger.warning(
            "Partial success for %s from %s (%d/%d templates generated)",
            code_name,
            mod_name,
            success_count,
            total_expected,
        )
        return success_count > 0

    def generate_all_templates(self) -> bool:
        """Generate templates for all catalog items across all available mods.

        Returns:
            bool: True if template generation completed successfully, False otherwise
        """
        if not self.available_mods:
            logger.error("No mod folders found in assets directory")
            return False

        # Apply filter if specified
        filtered_catalog = self._filter_catalog_items(filter_name=self.filter_name)
        if not filtered_catalog:
            logger.warning("No items match the filter criteria")
            return False

        total_successful_items = 0
        total_failed_items = 0
        total_processed = 0

        logger.info(
            "Starting template generation for %d items across %d mods",
            len(filtered_catalog),
            len(self.available_mods),
        )

        # Process each mod
        for mod_index, mod_name in enumerate(self.available_mods, 1):
            logger.info("Processing mod %d/%d: %s", mod_index, len(self.available_mods), mod_name)

            successful_items_in_mod = 0
            failed_items_in_mod = 0

            # Process each item in the current mod
            for item_index, item in enumerate(filtered_catalog, 1):
                total_processed += 1

                logger.debug(
                    "Processing item %d/%d in %s: %s",
                    item_index,
                    len(filtered_catalog),
                    mod_name,
                    item.code,
                )

                if self._generate_templates_for_item_and_mod(item=item, mod_name=mod_name):
                    successful_items_in_mod += 1
                    total_successful_items += 1
                else:
                    failed_items_in_mod += 1
                    total_failed_items += 1

            # Log mod summary
            logger.info(
                "Mod %s completed: %d successful, %d failed",
                mod_name,
                successful_items_in_mod,
                failed_items_in_mod,
            )

        # Log overall summary
        logger.info("Overall Template Generation Summary:")
        logger.info("Total processing attempts: %d", total_processed)
        logger.info("Successful generations: %d", total_successful_items)
        logger.info("Failed generations: %d", total_failed_items)
        logger.info(
            "Success rate: %.1f%%",
            (total_successful_items / total_processed) * 100 if total_processed > 0 else 0,
        )

        return total_failed_items == 0


def main() -> None:
    """Command-line entry point for template generation."""
    parser = argparse.ArgumentParser(
        description="Generate icon templates from extracted Foxhole game assets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Generate all templates\n"
            "  python -m foxhole_stockpiles.commands.generate_templates \\\n"
            "    --catalog training/catalog.json \\\n"
            "    --assets training/extracted_assets \\\n"
            "    --templates training/templates\n"
            "\n"
            "  # Generate templates for specific items\n"
            "  python -m foxhole_stockpiles.commands.generate_templates \\\n"
            "    --catalog training/catalog.json \\\n"
            "    --assets training/extracted_assets \\\n"
            "    --templates training/templates \\\n"
            "    --filter Rifle\n"
            "\n"
            "  # Generate with verbose logging\n"
            "  python -m foxhole_stockpiles.commands.generate_templates \\\n"
            "    --catalog training/catalog.json \\\n"
            "    --assets training/extracted_assets \\\n"
            "    --templates training/templates \\\n"
            "    --verbose --log-file generation.log"
        ),
    )

    parser.add_argument("--catalog", type=Path, required=True, help="Path to the catalog.json file")
    parser.add_argument(
        "--assets",
        type=Path,
        required=True,
        help="Path to the folder containing extracted assets (with mod subfolders)",
    )
    parser.add_argument(
        "--templates",
        type=Path,
        required=True,
        help="Path where generated templates will be saved",
    )
    parser.add_argument(
        "--filter",
        help="Filter items by CodeName containing this string (case-insensitive)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging (debug level)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress all output except errors and warnings. "
        "Only errors will be printed to console.",
    )
    parser.add_argument("--log-file", type=Path, help="Path to log file (default: console only)")

    args = parser.parse_args()

    # Setup logging
    settings = get_settings()
    logging_settings = copy(settings.logging)
    # Setup logging
    if args.quiet:
        logging_settings.log_level = "WARNING"
    elif args.verbose:
        logging_settings.log_level = "DEBUG"

    logging_settings.log_file = args.log_file
    setup_logging(logging_settings)

    # Validate input paths
    if not args.catalog.exists():
        logger.error("Catalog file not found: %s", args.catalog)
        exit(1)

    if not args.assets.exists():
        logger.error("Assets directory not found: %s", args.assets)
        exit(1)

    try:
        # Create generator and process templates
        generator = TemplateGenerator(
            catalog_path=args.catalog,
            assets_path=args.assets,
            template_path=args.templates,
            filter_name=args.filter,
        )

        success = generator.generate_all_templates()

        if success:
            logger.info("Template generation completed successfully!")
            print("✅ Template generation completed successfully!")
        else:
            logger.error("Template generation completed with errors")
            print("❌ Template generation completed with errors. Check the logs for details.")
            exit(1)

    except Exception as e:
        logger.exception("Template generation failed")
        print(f"❌ Template generation failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()

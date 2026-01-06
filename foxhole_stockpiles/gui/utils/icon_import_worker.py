"""Background worker for icon import process."""

import asyncio
import logging
import os
import re
import shutil
import subprocess
import tempfile
import traceback
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from foxhole_stockpiles.commands.database_builder.database_builder import DatabaseBuilder
from foxhole_stockpiles.commands.generate_templates.generate_templates import TemplateGenerator
from foxhole_stockpiles.commands.uasset_extractor.uasset_extractor import PakExtractor
from foxhole_stockpiles.core.settings import get_settings
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution

logger = logging.getLogger(__name__)


class IconImportWorker(QThread):
    """Worker thread for icon import process.

    Runs the complete pipeline:
    1. Extract assets from PAK files (uasset_extractor)
    2. Generate templates (generate_templates)
    3. Build/update database (database_builder)

    All intermediate files are stored in temporary directories and cleaned up automatically.
    """

    finished = pyqtSignal(bool)  # Emits True on success, False on failure/cancel
    error = pyqtSignal(str)  # Emits error message

    def __init__(
        self,
        mod_pak_files: list[str],
        mod_name: str,
        catalog_path: Path,
        overwrite: bool = False,
        vanilla_pak_file: str | None = None,
    ) -> None:
        """Initialize the icon import worker.

        Args:
            mod_pak_files (list[str]): List of mod PAK file paths
            mod_name (str): Name of the mod
            catalog_path (Path): Path to catalog.json file
            overwrite (bool): Whether to overwrite existing data
            vanilla_pak_file (str | None): Optional vanilla PAK file for dependencies

        Raises:
            ValueError: If mod_name is invalid or contains unsafe characters
        """
        super().__init__()
        self.mod_pak_files = mod_pak_files
        self.mod_name = self._validate_mod_name(mod_name)
        self.catalog_path = catalog_path
        self.overwrite = overwrite
        self.vanilla_pak_file = vanilla_pak_file
        self._should_stop = False

        # Get settings
        self.settings = get_settings()

        # Get target resolutions from settings
        self.target_resolutions = self.settings.database_builder.target_resolutions

        logger.debug(
            "IconImportWorker initialized: mod=%s, paks=%d, vanilla=%s, resolutions=%s",
            self.mod_name,
            len(mod_pak_files),
            "Yes" if vanilla_pak_file else "No",
            self.target_resolutions or "all",
        )

    @staticmethod
    def _validate_mod_name(mod_name: str) -> str:
        """Validate and normalize mod name to prevent injection attacks.

        Args:
            mod_name: The mod name to validate

        Returns:
            str: Normalized mod name

        Raises:
            ValueError: If mod_name is invalid or contains unsafe characters
        """
        # Strip whitespace
        normalized = mod_name.strip()

        # Check if empty
        if not normalized:
            raise ValueError("Mod name cannot be empty")

        # Check length (reasonable limit)
        if len(normalized) > 100:
            raise ValueError("Mod name is too long (max 100 characters)")

        # Only allow alphanumeric, spaces, underscores, and hyphens
        # This prevents path traversal (..), path separators (/, \), and injection
        if not re.match(r"^[a-zA-Z0-9_ -]+$", normalized):
            raise ValueError("Mod name can only contain alphanumeric, spaces, underscores, hyphens")

        return normalized

    def stop(self) -> None:
        """Request the worker to stop."""
        self._should_stop = True

    async def _get_existing_item_codes_from_database(self) -> set[str]:
        """Check which item codes already exist in the database by loading the HDF5 file.

        Returns:
            set[str]: Set of item codes that already have templates in the database
        """
        database_path = self.settings.scanner.database_path
        if not database_path:
            logger.warning("Database path not configured in settings")
            return set()

        if not database_path.exists():
            logger.warning("Database path does not exist: %s", database_path)
            return set()

        logger.debug("Loading database from: %s", database_path)

        from foxhole_stockpiles.services.template_manager import TemplateManager

        existing_codes: set[str] = set()

        # Check all target resolutions (or all enum resolutions if not specified)
        if self.target_resolutions:
            resolutions_to_check = [SupportedResolution(res) for res in self.target_resolutions]
            logger.debug("Using target resolutions: %s", [r.value for r in resolutions_to_check])
        else:
            # Use all supported resolutions from the enum
            resolutions_to_check = list(SupportedResolution)
            logger.debug(
                "Using all supported resolutions: %s", [r.value for r in resolutions_to_check]
            )

        # Load database and get item codes from each resolution
        template_manager = TemplateManager(database_path, cache_size=0)

        for resolution in resolutions_to_check:
            try:
                database = await template_manager.load_database(resolution)

                # Get unique item codes from templates matching this mod
                resolution_codes = {
                    template.code
                    for template in database.templates
                    if template.mod == self.mod_name
                }
                logger.debug(
                    "Found %d item codes for mod '%s' in resolution %s",
                    len(resolution_codes),
                    self.mod_name,
                    resolution.value,
                )
                existing_codes.update(resolution_codes)

            except FileNotFoundError:
                logger.debug("No database found for resolution %s", resolution.value)
                continue
            except Exception as e:
                logger.warning("Error loading database for resolution %s: %s", resolution.value, e)
                continue

        logger.info(
            "Found %d existing code(s) for mod '%s' in DB (skip if overwrite=False)",
            len(existing_codes),
            self.mod_name,
        )
        return existing_codes

    def _get_temp_dir_for_wsl(self) -> str | None:
        """Get Windows-accessible temp directory when running in WSL.

        Returns:
            str | None: Path to Windows temp directory, or None if not in WSL or failed
        """
        # Check if running in WSL
        try:
            with open("/proc/version") as f:
                version_info = f.read().lower()
                if "microsoft" not in version_info:
                    # Not in WSL, return None to use default
                    logger.debug("Not running in WSL, using default temp directory")
                    return None
        except Exception as e:
            logger.debug("Could not detect WSL: %s", e)
            return None

        logger.info("Detected WSL environment, using Windows temp directory for compatibility")

        # Try to get Windows TEMP directory
        try:
            # Use powershell.exe to get Windows TEMP variable (more reliable than cmd.exe)
            result = subprocess.run(
                ["powershell.exe", "-Command", "Write-Host $env:TEMP"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            windows_temp = result.stdout.strip()
            logger.debug("Windows TEMP from PowerShell: %s", windows_temp)

            if not windows_temp or windows_temp == "":
                raise ValueError("Empty TEMP path from PowerShell")

            # Convert Windows path to WSL path using wslpath
            result = subprocess.run(
                ["wslpath", "-u", windows_temp],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            wsl_temp_path = result.stdout.strip()
            logger.debug("WSL temp path: %s", wsl_temp_path)

            # Verify it exists and is writable
            if os.path.exists(wsl_temp_path) and os.access(wsl_temp_path, os.W_OK):
                logger.info("Using Windows temp directory: %s", wsl_temp_path)
                return wsl_temp_path
            else:
                logger.warning("Windows temp path not accessible: %s", wsl_temp_path)
        except Exception as e:
            logger.warning("Failed to get Windows temp directory: %s", e)

        return None

    def run(self) -> None:
        """Run the icon import process in background thread."""
        try:
            # Run async operations
            asyncio.run(self._run_import_pipeline())
        except Exception as e:
            logger.exception("Icon import failed with exception")
            self.error.emit(str(e))
            self.finished.emit(False)

    async def _run_import_pipeline(self) -> None:
        """Run the complete import pipeline asynchronously."""
        temp_base_dir = None
        success = False

        try:
            # Create temporary base directory
            # Use Windows temp directory if running in WSL for tool compatibility
            wsl_temp_dir = self._get_temp_dir_for_wsl()
            temp_base_dir = tempfile.mkdtemp(
                prefix=f"fs_icon_import_{self.mod_name}_", dir=wsl_temp_dir
            )
            logger.info("Created temporary directory: %s", temp_base_dir)

            temp_base_path = Path(temp_base_dir)
            extracted_assets_dir = temp_base_path / "extracted_assets" / self.mod_name
            templates_dir = temp_base_path / "templates"

            # Create subdirectories
            extracted_assets_dir.mkdir(parents=True, exist_ok=True)
            templates_dir.mkdir(parents=True, exist_ok=True)

            if self._should_stop:
                logger.info("Import cancelled before extraction")
                return

            # Step 0: Load catalog and check what needs to be extracted
            logger.info("Step 0/4: Checking catalog against database...")

            from foxhole_stockpiles.core.utils import load_catalog

            catalog = load_catalog(self.catalog_path)
            total_items = len(catalog)
            logger.info("Catalog contains %d items", total_items)

            # Get existing item codes from database
            existing_codes = await self._get_existing_item_codes_from_database()

            # Filter catalog to items that need extraction
            items_to_extract = [item for item in catalog if item.code not in existing_codes]

            if not self.overwrite:
                if not items_to_extract:
                    logger.info(
                        "All %d catalog items already exist in database. Nothing to extract.",
                        total_items,
                    )
                    success = True
                    return
                else:
                    logger.info(
                        "Need to extract %d items (%d already exist in database)",
                        len(items_to_extract),
                        len(existing_codes),
                    )
            else:
                logger.info("Overwrite enabled - will extract all %d items", total_items)
                items_to_extract = catalog

            if self._should_stop:
                logger.info("Import cancelled before extraction")
                return

            # Step 1: Extract assets from PAK files (only for items that need it)
            logger.info("Step 1/4: Extracting %d items from PAK files...", len(items_to_extract))
            await self._extract_assets(extracted_assets_dir, existing_codes)

            if self._should_stop:
                logger.info("Import cancelled after extraction")
                return

            # Check if anything was actually extracted
            extracted_count = 0
            if extracted_assets_dir.exists():
                extracted_count = len(list(extracted_assets_dir.rglob("*.png")))

            if extracted_count == 0:
                # Nothing was extracted - catalog items don't exist in PAK files
                if existing_codes:
                    logger.info(
                        "No new items extracted (catalog items not found in PAK files). "
                        "Database already contains %d items for this mod. Import completed.",
                        len(existing_codes),
                    )
                else:
                    logger.warning(
                        "No items extracted from PAK and none in DB. "
                        "Catalog items may not exist in this mod's PAK files."
                    )
                success = True
                return

            logger.info(
                "Extracted %d assets, continuing with template generation...", extracted_count
            )

            # Step 2: Generate templates
            logger.info("Step 2/4: Generating templates...")
            await self._generate_templates(
                extracted_assets_dir.parent,
                templates_dir,  # Pass parent to include mod folder
            )

            if self._should_stop:
                logger.info("Import cancelled after template generation")
                return

            # Step 3: Build database
            logger.info("Step 3/4: Building database...")
            await self._build_database(templates_dir)

            if self._should_stop:
                logger.info("Import cancelled after database build")
                return

            success = True
            logger.info("Icon import pipeline completed successfully")

        except Exception as e:
            logger.exception("Error in import pipeline")
            # Emit detailed error message with exception type and traceback
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else "No error message provided"
            tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            detailed_error = f"{error_type}: {error_msg}\n\nTraceback:\n{tb}"
            self.error.emit(detailed_error)

        finally:
            # Clean up temporary directory
            if temp_base_dir:
                try:
                    logger.info("Cleaning up temporary directory: %s", temp_base_dir)
                    shutil.rmtree(temp_base_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning("Failed to clean up temporary directory: %s", e)

            # Emit finished signal
            self.finished.emit(success and not self._should_stop)

    async def _extract_assets(self, output_dir: Path, existing_codes: set[str]) -> None:
        """Extract assets from PAK files.

        Args:
            output_dir (Path): Directory to extract assets to
            existing_codes (set[str]): Set of item codes that already exist in database (to skip)
        """
        # Get extractor and converter tool paths from database_builder settings
        db_builder = self.settings.database_builder
        extractor_tool = db_builder.extractor_tool
        converter_tool = db_builder.converter_tool

        if not extractor_tool:
            raise ValueError(
                "Extractor tool not configured.\n\n"
                "Please configure database_builder.extractor_tool in settings "
                "(File → Configuration → Database Builder tab)"
            )

        if not converter_tool:
            raise ValueError(
                "Converter tool not configured.\n\n"
                "Please configure database_builder.converter_tool in settings "
                "(File → Configuration → Database Builder tab)"
            )

        # Validate tool paths
        if not extractor_tool.exists():
            raise FileNotFoundError(
                f"Extractor tool not found: {extractor_tool}\n\n"
                f"Please update database_builder.extractor_tool in settings."
            )

        if not converter_tool.exists():
            raise FileNotFoundError(
                f"Converter tool not found: {converter_tool}\n\n"
                f"Please update database_builder.converter_tool in settings."
            )

        logger.info("Using extractor tool: %s", extractor_tool)
        logger.info("Using converter tool: %s", converter_tool)

        # Step 1: Extract from mod PAK files
        logger.info("Extracting icons from mod PAK files...")

        # Create filter based on existing item codes (if overwrite is False)
        filter_assets = None
        if not self.overwrite and existing_codes:
            # Build mapping of icon_path -> item_code from catalog
            from foxhole_stockpiles.core.utils import load_catalog

            catalog = load_catalog(self.catalog_path)
            icon_to_code: dict[str, str] = {}
            for item in catalog:
                if item.icon_path:
                    icon_to_code[f"{item.icon_path}.uasset"] = item.code
                if item.subicon_path:
                    icon_to_code[f"{item.subicon_path}.uasset"] = item.code

            # Filter out items whose code already exists in database
            def mod_filter(file_path: str) -> bool:
                item_code = icon_to_code.get(file_path)
                if item_code is None:
                    return True  # Not in catalog, extract it anyway
                return item_code not in existing_codes  # Skip if code exists in DB

            filter_assets = mod_filter
            logger.info(
                "Filtering out %d existing item code(s) from extraction", len(existing_codes)
            )

        extractor = PakExtractor(
            catalog_file=str(self.catalog_path),
            pak_files=self.mod_pak_files,
            extractor_tool=str(extractor_tool),
            converter_tool=str(converter_tool),
            output_dir=str(output_dir),
            filter_assets=filter_assets,
        )

        success = await extractor.process_files()

        if not success:
            logger.warning(
                "Some or all catalog items could not be found in the PAK files. "
                "This is normal if the mod doesn't include all catalog items."
            )
        else:
            logger.info("Mod asset extraction completed successfully")

        # Step 2: Check if anything was extracted from mod PAK
        extracted_count = 0
        if output_dir.exists():
            extracted_count = len(list(output_dir.rglob("*.png")))

        # Step 3: If mod extraction succeeded, extract vanilla dependencies (crate + subicons)
        # These are shared resources that extracted icons depend on
        if extracted_count > 0 and self.vanilla_pak_file:
            logger.info(
                "Extracted %d assets from mod PAK. Extracting dependencies from vanilla PAK...",
                extracted_count,
            )

            # Filter for vanilla dependencies (subicons + crate icon)
            def vanilla_filter(file_path: str) -> bool:
                return "Subicons/" in file_path or "IconFilterCrates" in file_path

            vanilla_extractor = PakExtractor(
                catalog_file=str(self.catalog_path),
                pak_files=[self.vanilla_pak_file],
                extractor_tool=str(extractor_tool),
                converter_tool=str(converter_tool),
                output_dir=str(output_dir),
                filter_assets=vanilla_filter,
            )

            vanilla_success = await vanilla_extractor.process_files()
            if not vanilla_success:
                logger.warning(
                    "Vanilla PAK extraction had some failures. "
                    "Template generation may fail if dependencies are missing."
                )
            else:
                logger.info("Vanilla dependencies extracted successfully")

    async def _generate_templates(self, assets_dir: Path, output_dir: Path) -> None:
        """Generate templates from extracted assets.

        Args:
            assets_dir (Path): Directory containing extracted assets (with mod subfolders)
            output_dir (Path): Directory to save templates to
        """
        generator = TemplateGenerator(
            catalog_path=self.catalog_path,
            assets_path=assets_dir,
            template_path=output_dir,
            template_settings=self.settings.templates,
        )

        logger.debug(
            "Starting template generation: assets_path=%s, template_path=%s",
            assets_dir,
            output_dir,
        )

        success = await generator.generate_all_templates()

        # Count generated templates to determine if we had ANY success
        template_count = 0
        if output_dir.exists():
            template_count = sum(1 for f in output_dir.rglob("*.png"))

        logger.info("Template generation completed: %d template files created", template_count)

        if not success:
            # Template generation had some failures, but check if we generated anything
            if template_count == 0:
                # No templates generated - this happens when catalog items don't exist in PAK files
                logger.warning(
                    "No templates were generated. This is normal if the catalog items "
                    "don't exist in the mod PAK files or are already in the database."
                )
            else:
                # Partial success - some templates generated but some items failed
                # This is normal for mods that don't override all vanilla items
                logger.warning(
                    "Template generation had some failures, but %d templates created",
                    template_count,
                )
                logger.warning(
                    "This is normal for mods - only items with custom icons are generated"
                )

        logger.info(
            "Template generation completed successfully: %d templates created", template_count
        )

    async def _build_database(self, templates_dir: Path) -> None:
        """Build database from templates.

        Args:
            templates_dir (Path): Directory containing templates
        """
        # Get database path from settings
        database_path = self.settings.scanner.database_path
        if not database_path:
            raise ValueError("No database path configured in settings")

        # Convert resolution strings to SupportedResolution enums
        target_resolutions_enum: list[SupportedResolution] | None = None
        if self.target_resolutions:
            target_resolutions_enum = []
            for res_str in self.target_resolutions:
                try:
                    resolution = SupportedResolution(res_str)
                    target_resolutions_enum.append(resolution)
                except ValueError:
                    logger.warning("Invalid resolution '%s', skipping", res_str)

        # Create builder
        builder = DatabaseBuilder(
            catalog_path=self.catalog_path,
            assets_path=templates_dir,
            use_scaling=True,  # Use scaling for better quality
        )

        # Build database
        await builder.build_all_databases(
            output_path=database_path,
            target_resolutions=target_resolutions_enum,
            overwrite=self.overwrite,
        )

        logger.info("Database build completed successfully")

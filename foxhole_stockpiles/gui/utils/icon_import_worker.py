"""Background worker for icon import process."""

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
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
        pak_files: list[str],
        mod_name: str,
        catalog_path: Path,
        overwrite: bool = False,
    ) -> None:
        """Initialize the icon import worker.

        Args:
            pak_files (list[str]): List of PAK file paths
            mod_name (str): Name of the mod
            catalog_path (Path): Path to catalog.json file
            overwrite (bool): Whether to overwrite existing data
        """
        super().__init__()
        self.pak_files = pak_files
        self.mod_name = mod_name
        self.catalog_path = catalog_path
        self.overwrite = overwrite
        self._should_stop = False

        # Get settings
        self.settings = get_settings()

        # Get target resolutions from settings
        self.target_resolutions = self.settings.database_builder.target_resolutions

        logger.debug(
            "IconImportWorker initialized: mod=%s, pak_files=%d, resolutions=%s",
            mod_name,
            len(pak_files),
            self.target_resolutions or "all",
        )

    def stop(self) -> None:
        """Request the worker to stop."""
        self._should_stop = True

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

            # Step 1: Extract assets from PAK files
            logger.info("Step 1/3: Extracting assets from PAK files...")
            await self._extract_assets(extracted_assets_dir)

            if self._should_stop:
                logger.info("Import cancelled after extraction")
                return

            # Step 2: Generate templates
            logger.info("Step 2/3: Generating templates...")
            await self._generate_templates(
                extracted_assets_dir.parent,
                templates_dir,  # Pass parent to include mod folder
            )

            if self._should_stop:
                logger.info("Import cancelled after template generation")
                return

            # Step 3: Build database
            logger.info("Step 3/3: Building database...")
            await self._build_database(templates_dir)

            if self._should_stop:
                logger.info("Import cancelled after database build")
                return

            success = True
            logger.info("Icon import pipeline completed successfully")

        except Exception as e:
            logger.exception("Error in import pipeline")
            self.error.emit(str(e))

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

    async def _extract_assets(self, output_dir: Path) -> None:
        """Extract assets from PAK files.

        Args:
            output_dir (Path): Directory to extract assets to
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

        extractor = PakExtractor(
            catalog_file=str(self.catalog_path),
            pak_files=self.pak_files,
            extractor_tool=str(extractor_tool),
            converter_tool=str(converter_tool),
            output_dir=str(output_dir),
        )

        success = await extractor.process_files()

        if not success:
            raise RuntimeError("Asset extraction failed")

        logger.info("Asset extraction completed successfully")

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

        success = await generator.generate_all_templates()

        if not success:
            raise RuntimeError("Template generation failed")

        logger.info("Template generation completed successfully")

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

"""Tests for IconImportWorker."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from foxhole_stockpiles.core.settings.app_settings import AppSettings
from foxhole_stockpiles.core.settings.sections.database_builder import DatabaseBuilderSettings
from foxhole_stockpiles.core.settings.sections.scanner import ScannerSettings
from foxhole_stockpiles.core.settings.sections.templates import TemplateSettings
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.gui.utils.icon_import_worker import IconImportWorker
from foxhole_stockpiles.models.catalog_item import CatalogItem


@pytest.fixture
def mock_settings(tmp_path: Path) -> AppSettings:
    """Create mock settings for testing.

    Args:
        tmp_path: Temporary directory path

    Returns:
        AppSettings: Mock settings
    """
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text("{}")

    extractor_tool = tmp_path / "repak.exe"
    extractor_tool.write_text("")

    converter_tool = tmp_path / "umodel.exe"
    converter_tool.write_text("")

    database_path = tmp_path / "database.h5"

    return AppSettings(
        database_builder=DatabaseBuilderSettings(
            extractor_tool=extractor_tool,
            converter_tool=converter_tool,
            catalog_file=catalog_file,
            target_resolutions=None,
        ),
        scanner=ScannerSettings(
            database_path=database_path,
        ),
        templates=TemplateSettings(),
    )


@pytest.fixture
def worker(tmp_path: Path, mock_settings: AppSettings) -> IconImportWorker:
    """Create an IconImportWorker instance.

    Args:
        tmp_path: Temporary directory path
        mock_settings: Mock settings

    Returns:
        IconImportWorker: Worker instance
    """
    pak_file = tmp_path / "test.pak"
    pak_file.write_text("")

    catalog_path = tmp_path / "catalog.json"

    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.get_settings", return_value=mock_settings
    ):
        worker = IconImportWorker(
            mod_pak_files=[str(pak_file)],
            mod_name="test_mod",
            catalog_path=catalog_path,
            overwrite=False,
        )

    return worker


# ===== Initialization Tests =====


def test_icon_import_worker_initialization(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test IconImportWorker initialization.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    assert worker.mod_pak_files == [str(tmp_path / "test.pak")]
    assert worker.mod_name == "test_mod"
    assert worker.catalog_path == tmp_path / "catalog.json"
    assert worker.overwrite is False
    assert worker.vanilla_pak_file is None
    assert worker._should_stop is False
    assert worker.settings is not None


def test_icon_import_worker_initialization_with_resolutions(tmp_path: Path) -> None:
    """Test IconImportWorker initialization with specific resolutions.

    Args:
        tmp_path: Temporary directory path
    """
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text("{}")

    settings = AppSettings(
        database_builder=DatabaseBuilderSettings(
            target_resolutions=["1080", "1440"],
        ),
    )

    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.get_settings", return_value=settings
    ):
        worker = IconImportWorker(
            mod_pak_files=["test.pak"],
            mod_name="test_mod",
            catalog_path=catalog_file,
        )

    assert worker.target_resolutions == ["1080", "1440"]


# ===== Mod Name Validation Tests =====


def test_mod_name_validation_valid_names(tmp_path: Path) -> None:
    """Test that valid mod names are accepted.

    Args:
        tmp_path: Temporary directory path
    """
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text("{}")

    valid_names = [
        "test_mod",
        "Test-Mod",
        "Mod 123",
        "my_cool_mod-v2",
        "ABC",
        "mod_with_spaces and_underscores",
    ]

    for mod_name in valid_names:
        worker = IconImportWorker(
            mod_pak_files=["test.pak"],
            mod_name=mod_name,
            catalog_path=catalog_file,
        )
        assert worker.mod_name == mod_name.strip()


def test_mod_name_validation_strips_whitespace(tmp_path: Path) -> None:
    """Test that mod name whitespace is stripped.

    Args:
        tmp_path: Temporary directory path
    """
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text("{}")

    worker = IconImportWorker(
        mod_pak_files=["test.pak"],
        mod_name="  test_mod  ",
        catalog_path=catalog_file,
    )
    assert worker.mod_name == "test_mod"


def test_mod_name_validation_empty_name(tmp_path: Path) -> None:
    """Test that empty mod names are rejected.

    Args:
        tmp_path: Temporary directory path
    """
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text("{}")

    with pytest.raises(ValueError, match="Mod name cannot be empty"):
        IconImportWorker(
            mod_pak_files=["test.pak"],
            mod_name="",
            catalog_path=catalog_file,
        )

    with pytest.raises(ValueError, match="Mod name cannot be empty"):
        IconImportWorker(
            mod_pak_files=["test.pak"],
            mod_name="   ",
            catalog_path=catalog_file,
        )


def test_mod_name_validation_too_long(tmp_path: Path) -> None:
    """Test that too-long mod names are rejected.

    Args:
        tmp_path: Temporary directory path
    """
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text("{}")

    with pytest.raises(ValueError, match="Mod name is too long"):
        IconImportWorker(
            mod_pak_files=["test.pak"],
            mod_name="a" * 101,
            catalog_path=catalog_file,
        )


def test_mod_name_validation_path_traversal(tmp_path: Path) -> None:
    """Test that path traversal attempts are blocked.

    Args:
        tmp_path: Temporary directory path
    """
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text("{}")

    invalid_names = [
        "../etc/passwd",
        "../../secret",
        "mod/../../../etc",
        "mod/subdir",
        "mod\\subdir",
        "C:\\Windows",
        "/etc/passwd",
    ]

    for mod_name in invalid_names:
        with pytest.raises(ValueError, match="can only contain alphanumeric"):
            IconImportWorker(
                mod_pak_files=["test.pak"],
                mod_name=mod_name,
                catalog_path=catalog_file,
            )


def test_mod_name_validation_special_characters(tmp_path: Path) -> None:
    """Test that special characters are rejected.

    Args:
        tmp_path: Temporary directory path
    """
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text("{}")

    invalid_names = [
        "mod<script>",
        "mod;rm -rf",
        "mod`whoami`",
        "mod$(whoami)",
        "mod&& echo test",
        "mod|cat",
        "mod\nmalicious",  # Newline in middle (not just trailing)
        "mod\x00malicious",  # Null byte in middle
        "mod@#$%",
    ]

    for mod_name in invalid_names:
        with pytest.raises(ValueError, match="can only contain alphanumeric"):
            IconImportWorker(
                mod_pak_files=["test.pak"],
                mod_name=mod_name,
                catalog_path=catalog_file,
            )


# ===== Stop Tests =====


def test_icon_import_worker_stop(worker: IconImportWorker) -> None:
    """Test stop method sets the flag.

    Args:
        worker: IconImportWorker instance
    """
    assert worker._should_stop is False
    worker.stop()
    assert worker._should_stop is True


# ===== WSL Detection Tests =====


def test_get_temp_dir_for_wsl_not_in_wsl(worker: IconImportWorker) -> None:
    """Test WSL detection when not running in WSL.

    Args:
        worker: IconImportWorker instance
    """
    with patch("builtins.open", side_effect=FileNotFoundError):
        result = worker._get_temp_dir_for_wsl()

    assert result is None


def test_get_temp_dir_for_wsl_not_microsoft(worker: IconImportWorker) -> None:
    """Test WSL detection when not Microsoft WSL.

    Args:
        worker: IconImportWorker instance
    """
    mock_file = MagicMock()
    mock_file.read.return_value = "Linux version 5.4.0"

    with patch("builtins.open", return_value=mock_file):
        result = worker._get_temp_dir_for_wsl()

    assert result is None


def test_get_temp_dir_for_wsl_success(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test successful WSL temp directory detection.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    mock_proc_version = MagicMock()
    mock_proc_version.read.return_value = "Linux version with Microsoft WSL"
    mock_proc_version.__enter__ = MagicMock(return_value=mock_proc_version)
    mock_proc_version.__exit__ = MagicMock(return_value=False)

    wsl_temp = str(tmp_path / "wsl_temp")
    Path(wsl_temp).mkdir(exist_ok=True)

    with patch("builtins.open", return_value=mock_proc_version):
        with patch("subprocess.run") as mock_run:
            # First call: PowerShell to get Windows TEMP
            # Second call: wslpath conversion
            mock_run.side_effect = [
                Mock(stdout="C:\\Users\\Test\\AppData\\Local\\Temp\n", returncode=0),
                Mock(stdout=f"{wsl_temp}\n", returncode=0),
            ]

            with patch("os.path.exists", return_value=True):
                with patch("os.access", return_value=True):
                    result = worker._get_temp_dir_for_wsl()

    assert result == wsl_temp


def test_get_temp_dir_for_wsl_powershell_fails(worker: IconImportWorker) -> None:
    """Test WSL temp directory when PowerShell fails.

    Args:
        worker: IconImportWorker instance
    """
    mock_proc_version = MagicMock()
    mock_proc_version.read.return_value = "Linux version with Microsoft WSL"

    with patch("builtins.open", return_value=mock_proc_version):
        with patch("subprocess.run", side_effect=Exception("PowerShell failed")):
            result = worker._get_temp_dir_for_wsl()

    assert result is None


def test_get_temp_dir_for_wsl_empty_temp(worker: IconImportWorker) -> None:
    """Test WSL temp directory when TEMP is empty.

    Args:
        worker: IconImportWorker instance
    """
    mock_proc_version = MagicMock()
    mock_proc_version.read.return_value = "Linux version with Microsoft WSL"

    with patch("builtins.open", return_value=mock_proc_version):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="", returncode=0)
            result = worker._get_temp_dir_for_wsl()

    assert result is None


def test_get_temp_dir_for_wsl_path_not_accessible(worker: IconImportWorker) -> None:
    """Test WSL temp directory when path is not accessible.

    Args:
        worker: IconImportWorker instance
    """
    mock_proc_version = MagicMock()
    mock_proc_version.read.return_value = "Linux version with Microsoft WSL"

    with patch("builtins.open", return_value=mock_proc_version):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(stdout="C:\\Users\\Test\\AppData\\Local\\Temp\n", returncode=0),
                Mock(stdout="/mnt/c/Users/Test/AppData/Local/Temp\n", returncode=0),
            ]

            # Path exists but not accessible
            with patch("os.path.exists", return_value=True):
                with patch("os.access", return_value=False):
                    result = worker._get_temp_dir_for_wsl()

    assert result is None


# ===== Pipeline Tests =====


@pytest.mark.asyncio
async def test_extract_assets_missing_extractor_tool(
    worker: IconImportWorker, tmp_path: Path
) -> None:
    """Test extract assets when extractor tool is not configured.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    # Set extractor_tool to None
    worker.settings.database_builder.extractor_tool = None

    with pytest.raises(ValueError, match="Extractor tool not configured"):
        await worker._extract_assets(tmp_path, set())


@pytest.mark.asyncio
async def test_extract_assets_missing_converter_tool(
    worker: IconImportWorker, tmp_path: Path
) -> None:
    """Test extract assets when converter tool is not configured.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    # Set converter_tool to None
    worker.settings.database_builder.converter_tool = None

    with pytest.raises(ValueError, match="Converter tool not configured"):
        await worker._extract_assets(tmp_path, set())


@pytest.mark.asyncio
async def test_extract_assets_extractor_not_found(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test extract assets when extractor tool file doesn't exist.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    # Set extractor_tool to non-existent file
    worker.settings.database_builder.extractor_tool = Path("/nonexistent/repak.exe")

    with pytest.raises(FileNotFoundError, match="Extractor tool not found"):
        await worker._extract_assets(tmp_path, set())


@pytest.mark.asyncio
async def test_extract_assets_converter_not_found(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test extract assets when converter tool file doesn't exist.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    # Set converter_tool to non-existent file
    worker.settings.database_builder.converter_tool = Path("/nonexistent/umodel.exe")

    with pytest.raises(FileNotFoundError, match="Converter tool not found"):
        await worker._extract_assets(tmp_path, set())


@pytest.mark.asyncio
async def test_extract_assets_success(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test successful asset extraction.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.PakExtractor"
    ) as mock_extractor_class:
        mock_extractor = AsyncMock()
        mock_extractor.process_files.return_value = True
        mock_extractor_class.return_value = mock_extractor

        await worker._extract_assets(tmp_path, set())

        mock_extractor_class.assert_called_once()
        mock_extractor.process_files.assert_called_once()


@pytest.mark.asyncio
async def test_extract_assets_failure(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test asset extraction when items can't be found in PAK files.

    This is not an error - it happens when catalog items don't exist in the mod.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.PakExtractor"
    ) as mock_extractor_class:
        mock_extractor = AsyncMock()
        mock_extractor.process_files.return_value = False
        mock_extractor_class.return_value = mock_extractor

        # Should complete without raising an error (just logs warning)
        await worker._extract_assets(tmp_path, set())


@pytest.mark.asyncio
async def test_extract_assets_with_vanilla_pak(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test asset extraction with vanilla PAK file.

    Vanilla extraction only happens AFTER mod extraction succeeds.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    vanilla_pak = tmp_path / "vanilla.pak"
    vanilla_pak.touch()
    worker.vanilla_pak_file = str(vanilla_pak)

    # Create a PNG file to simulate successful extraction
    (tmp_path / "test.png").write_text("fake png")

    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.PakExtractor"
    ) as mock_extractor_class:
        mock_mod_extractor = AsyncMock()
        mock_mod_extractor.process_files.return_value = True
        mock_vanilla_extractor = AsyncMock()
        mock_vanilla_extractor.process_files.return_value = True

        # Return different instances: mod first, then vanilla
        mock_extractor_class.side_effect = [mock_mod_extractor, mock_vanilla_extractor]

        await worker._extract_assets(tmp_path, set())

        # Should be called twice: once for mod, once for vanilla
        assert mock_extractor_class.call_count == 2

        # First call should be for mod
        mod_call = mock_extractor_class.call_args_list[0]
        assert mod_call[1]["pak_files"] == worker.mod_pak_files

        # Second call should be for vanilla with filter
        vanilla_call = mock_extractor_class.call_args_list[1]
        assert vanilla_call[1]["pak_files"] == [str(vanilla_pak)]
        assert vanilla_call[1]["filter_assets"] is not None


@pytest.mark.asyncio
async def test_extract_assets_vanilla_pak_failure_continues(
    worker: IconImportWorker, tmp_path: Path
) -> None:
    """Test that vanilla PAK extraction failure doesn't stop the pipeline.

    Vanilla extraction happens after mod extraction, and failures are logged but don't stop.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    vanilla_pak = tmp_path / "vanilla.pak"
    vanilla_pak.touch()
    worker.vanilla_pak_file = str(vanilla_pak)

    # Create a PNG file to simulate successful mod extraction
    (tmp_path / "test.png").write_text("fake png")

    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.PakExtractor"
    ) as mock_extractor_class:
        mock_mod_extractor = AsyncMock()
        mock_mod_extractor.process_files.return_value = True  # Mod succeeds
        mock_vanilla_extractor = AsyncMock()
        mock_vanilla_extractor.process_files.return_value = False  # Vanilla fails

        mock_extractor_class.side_effect = [mock_mod_extractor, mock_vanilla_extractor]

        # Should not raise, vanilla failure is just logged as warning
        await worker._extract_assets(tmp_path, set())

        # Both extractors should have been called (mod first, then vanilla)
        assert mock_extractor_class.call_count == 2


@pytest.mark.asyncio
async def test_extract_assets_with_existing_icons_filter(
    worker: IconImportWorker, tmp_path: Path
) -> None:
    """Test asset extraction filters out existing item codes when overwrite is False.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    worker.overwrite = False
    existing_codes = {"ITEM001", "ITEM002"}

    # Mock catalog with items
    mock_items = [
        CatalogItem(
            code="ITEM001",
            category=ItemCategory.Item,
            icon_path="War/Content/Icons/Icon1",
            subicon_path="",
        ),
        CatalogItem(
            code="ITEM002",
            category=ItemCategory.Item,
            icon_path="War/Content/Icons/Icon2",
            subicon_path="",
        ),
        CatalogItem(
            code="ITEM003",
            category=ItemCategory.Item,
            icon_path="War/Content/Icons/Icon3",
            subicon_path="",
        ),
    ]

    with patch("foxhole_stockpiles.core.utils.load_catalog", return_value=mock_items):
        with patch(
            "foxhole_stockpiles.gui.utils.icon_import_worker.PakExtractor"
        ) as mock_extractor_class:
            mock_extractor = AsyncMock()
            mock_extractor.process_files.return_value = True
            mock_extractor_class.return_value = mock_extractor

            await worker._extract_assets(tmp_path, existing_codes)

            # Should pass a filter function
            call_kwargs = mock_extractor_class.call_args[1]
            assert call_kwargs["filter_assets"] is not None
            assert callable(call_kwargs["filter_assets"])

            # Test the filter function
            filter_func = call_kwargs["filter_assets"]
            # ITEM001 exists in DB, should be filtered out
            assert filter_func("War/Content/Icons/Icon1.uasset") is False
            # ITEM003 doesn't exist in DB, should be included
            assert filter_func("War/Content/Icons/Icon3.uasset") is True


@pytest.mark.asyncio
async def test_extract_assets_with_overwrite_no_filter(
    worker: IconImportWorker, tmp_path: Path
) -> None:
    """Test asset extraction doesn't filter when overwrite is True.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    worker.overwrite = True
    existing_icons = {"War/Content/Icons/Icon1.uasset"}

    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.PakExtractor"
    ) as mock_extractor_class:
        mock_extractor = AsyncMock()
        mock_extractor.process_files.return_value = True
        mock_extractor_class.return_value = mock_extractor

        await worker._extract_assets(tmp_path, existing_icons)

        # Should not pass a filter when overwrite is True
        call_kwargs = mock_extractor_class.call_args[1]
        assert call_kwargs["filter_assets"] is None


async def test_get_existing_icons_no_database(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test get_existing_icons when database doesn't exist.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    worker.settings.scanner.database_path = tmp_path / "nonexistent_db"

    existing = await worker._get_existing_item_codes_from_database()

    assert existing == set()


async def test_get_existing_icons_empty_catalog(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test get_existing_icons with empty catalog.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    # Create empty database directory
    db_path = tmp_path / "database"
    db_path.mkdir()
    worker.settings.scanner.database_path = db_path

    # Empty catalog
    worker.catalog_path.write_text("[]")

    existing = await worker._get_existing_item_codes_from_database()

    assert existing == set()


async def test_get_existing_icons_with_existing_templates(
    worker: IconImportWorker, tmp_path: Path
) -> None:
    """Test get_existing_icons finds existing templates from HDF5 database.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    db_path = tmp_path / "database.h5"
    db_path.touch()  # Create empty file
    worker.settings.scanner.database_path = db_path
    worker.overwrite = False

    # Mock TemplateDatabase with templates
    import numpy as np

    from foxhole_stockpiles.models.icon_template import IconTemplate
    from foxhole_stockpiles.services.template_database import TemplateDatabase

    mock_template = IconTemplate(
        code="TEST001",
        image=np.zeros((64, 64, 3), dtype=np.uint8),
        phash=0,
        crated=False,
        faction=ItemFaction.NEUTRAL,
        category=ItemCategory.Item,
        mod="test_mod",
        resolution=SupportedResolution.R_1080,
    )

    mock_db = TemplateDatabase(SupportedResolution.R_1080)
    mock_db.add_template(mock_template)

    # Mock TemplateManager.load_database
    async def mock_load_database(self: Any, resolution: SupportedResolution) -> TemplateDatabase:
        return mock_db

    with patch(
        "foxhole_stockpiles.services.template_manager.TemplateManager.load_database",
        new=mock_load_database,
    ):
        existing = await worker._get_existing_item_codes_from_database()

    # Should find the item code
    assert "TEST001" in existing
    assert len(existing) == 1


async def test_get_existing_icons_with_overwrite_enabled(
    worker: IconImportWorker, tmp_path: Path
) -> None:
    """Test get_existing_item_codes still returns codes even when overwrite is True.

    The overwrite check happens during filter creation, not during database check.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    db_path = tmp_path / "database.h5"
    db_path.touch()
    worker.settings.scanner.database_path = db_path
    worker.overwrite = True  # Overwrite enabled

    # Mock TemplateDatabase with templates
    import numpy as np

    from foxhole_stockpiles.models.icon_template import IconTemplate
    from foxhole_stockpiles.services.template_database import TemplateDatabase

    mock_template = IconTemplate(
        code="TEST001",
        image=np.zeros((64, 64, 3), dtype=np.uint8),
        phash=0,
        crated=False,
        faction=ItemFaction.NEUTRAL,
        category=ItemCategory.Item,
        mod="test_mod",
        resolution=SupportedResolution.R_1080,
    )

    mock_db = TemplateDatabase(SupportedResolution.R_1080)
    mock_db.add_template(mock_template)

    async def mock_load_database(self: Any, resolution: SupportedResolution) -> TemplateDatabase:
        return mock_db

    with patch(
        "foxhole_stockpiles.services.template_manager.TemplateManager.load_database",
        new=mock_load_database,
    ):
        existing = await worker._get_existing_item_codes_from_database()

    # Should still find the code (overwrite check happens during filter creation)
    assert "TEST001" in existing


async def test_get_existing_icons_with_target_resolutions(
    worker: IconImportWorker, tmp_path: Path
) -> None:
    """Test get_existing_item_codes uses target_resolutions from settings.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    db_path = tmp_path / "database.h5"
    db_path.touch()
    worker.settings.scanner.database_path = db_path
    worker.overwrite = False
    worker.target_resolutions = ["1440"]  # Only check this resolution

    # Mock TemplateDatabase with templates for 1440 resolution
    import numpy as np

    from foxhole_stockpiles.models.icon_template import IconTemplate
    from foxhole_stockpiles.services.template_database import TemplateDatabase

    mock_template = IconTemplate(
        code="TEST001",
        image=np.zeros((64, 64, 3), dtype=np.uint8),
        phash=0,
        crated=False,
        faction=ItemFaction.NEUTRAL,
        category=ItemCategory.Item,
        mod="test_mod",
        resolution=SupportedResolution.R_1440,
    )

    mock_db = TemplateDatabase(SupportedResolution.R_1440)
    mock_db.add_template(mock_template)

    async def mock_load_database(
        self: Any, resolution: SupportedResolution
    ) -> TemplateDatabase | None:
        if resolution == SupportedResolution.R_1440:
            return mock_db
        raise FileNotFoundError("Resolution not found")

    with patch(
        "foxhole_stockpiles.services.template_manager.TemplateManager.load_database",
        new=mock_load_database,
    ):
        existing = await worker._get_existing_item_codes_from_database()

    # Should find the item code
    assert "TEST001" in existing


async def test_get_existing_icons_filters_by_mod(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test get_existing_item_codes only returns codes for the current mod.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    db_path = tmp_path / "database.h5"
    db_path.touch()
    worker.settings.scanner.database_path = db_path
    worker.overwrite = False

    # Mock TemplateDatabase with templates from different mods
    import numpy as np

    from foxhole_stockpiles.models.icon_template import IconTemplate
    from foxhole_stockpiles.services.template_database import TemplateDatabase

    # Template from the same mod (should be included)
    template_same_mod = IconTemplate(
        code="SAME_MOD",
        image=np.zeros((64, 64, 3), dtype=np.uint8),
        phash=0,
        crated=False,
        faction=ItemFaction.NEUTRAL,
        category=ItemCategory.Item,
        mod="test_mod",  # Same as worker.mod_name
        resolution=SupportedResolution.R_1080,
    )

    # Template from a different mod (should NOT be included)
    template_other_mod = IconTemplate(
        code="OTHER_MOD",
        image=np.zeros((64, 64, 3), dtype=np.uint8),
        phash=0,
        crated=False,
        faction=ItemFaction.NEUTRAL,
        category=ItemCategory.Item,
        mod="other_mod",  # Different mod
        resolution=SupportedResolution.R_1080,
    )

    mock_db = TemplateDatabase(SupportedResolution.R_1080)
    mock_db.add_template(template_same_mod)
    mock_db.add_template(template_other_mod)

    async def mock_load_database(self: Any, resolution: SupportedResolution) -> TemplateDatabase:
        return mock_db

    with patch(
        "foxhole_stockpiles.services.template_manager.TemplateManager.load_database",
        new=mock_load_database,
    ):
        existing = await worker._get_existing_item_codes_from_database()

    # Should only find the item from the same mod
    assert "SAME_MOD" in existing
    assert "OTHER_MOD" not in existing
    assert len(existing) == 1


@pytest.mark.asyncio
async def test_generate_templates_success(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test successful template generation.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    assets_dir = tmp_path / "assets"
    output_dir = tmp_path / "templates"

    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.TemplateGenerator"
    ) as mock_gen_class:
        mock_generator = AsyncMock()
        mock_generator.generate_all_templates.return_value = True
        mock_gen_class.return_value = mock_generator

        await worker._generate_templates(assets_dir, output_dir)

        mock_gen_class.assert_called_once_with(
            catalog_path=worker.catalog_path,
            assets_path=assets_dir,
            template_path=output_dir,
            template_settings=worker.settings.templates,
        )
        mock_generator.generate_all_templates.assert_called_once()


@pytest.mark.asyncio
async def test_generate_templates_failure(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test template generation when no templates are created.

    This is not an error - it happens when catalog items don't exist in PAK files.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    assets_dir = tmp_path / "assets"
    output_dir = tmp_path / "templates"

    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.TemplateGenerator"
    ) as mock_gen_class:
        mock_generator = AsyncMock()
        mock_generator.generate_all_templates.return_value = False
        mock_gen_class.return_value = mock_generator

        # Should complete without raising an error (just logs warning)
        await worker._generate_templates(assets_dir, output_dir)


@pytest.mark.asyncio
async def test_generate_templates_partial_success(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test template generation with partial success (some templates created).

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    assets_dir = tmp_path / "assets"
    output_dir = tmp_path / "templates"

    # Create output directory with some templates
    output_dir.mkdir(parents=True)
    (output_dir / "template1.png").touch()
    (output_dir / "template2.png").touch()

    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.TemplateGenerator"
    ) as mock_gen_class:
        mock_generator = AsyncMock()
        # Return False (some items failed) but templates exist
        mock_generator.generate_all_templates.return_value = False
        mock_gen_class.return_value = mock_generator

        # Should NOT raise error when templates were created
        await worker._generate_templates(assets_dir, output_dir)


@pytest.mark.asyncio
async def test_build_database_no_database_path(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test database build when database path is not configured.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    worker.settings.scanner.database_path = None

    with pytest.raises(ValueError, match="No database path configured"):
        await worker._build_database(tmp_path)


@pytest.mark.asyncio
async def test_build_database_success(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test successful database build.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    templates_dir = tmp_path / "templates"

    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.DatabaseBuilder"
    ) as mock_builder_class:
        mock_builder = AsyncMock()
        mock_builder.build_all_databases.return_value = None
        mock_builder_class.return_value = mock_builder

        await worker._build_database(templates_dir)

        mock_builder_class.assert_called_once_with(
            catalog_path=worker.catalog_path,
            assets_path=templates_dir,
            use_scaling=True,
        )
        mock_builder.build_all_databases.assert_called_once()


@pytest.mark.asyncio
async def test_build_database_with_target_resolutions(
    worker: IconImportWorker, tmp_path: Path
) -> None:
    """Test database build with specific target resolutions.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    worker.target_resolutions = ["1080", "1440"]
    templates_dir = tmp_path / "templates"

    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.DatabaseBuilder"
    ) as mock_builder_class:
        mock_builder = AsyncMock()
        mock_builder.build_all_databases.return_value = None
        mock_builder_class.return_value = mock_builder

        await worker._build_database(templates_dir)

        # Check that target_resolutions were converted to enums
        call_args = mock_builder.build_all_databases.call_args
        target_resolutions = call_args.kwargs["target_resolutions"]
        assert len(target_resolutions) == 2
        assert SupportedResolution.R_1080 in target_resolutions
        assert SupportedResolution.R_1440 in target_resolutions


@pytest.mark.asyncio
async def test_build_database_invalid_resolution(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test database build with invalid resolution string.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    worker.target_resolutions = ["1080", "invalid", "1440"]
    templates_dir = tmp_path / "templates"

    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.DatabaseBuilder"
    ) as mock_builder_class:
        mock_builder = AsyncMock()
        mock_builder.build_all_databases.return_value = None
        mock_builder_class.return_value = mock_builder

        await worker._build_database(templates_dir)

        # Invalid resolution should be skipped
        call_args = mock_builder.build_all_databases.call_args
        target_resolutions = call_args.kwargs["target_resolutions"]
        assert len(target_resolutions) == 2


# ===== Full Pipeline Tests =====


@pytest.mark.asyncio
async def test_run_import_pipeline_success(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test successful full pipeline execution.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    test_import_dir = tmp_path / "test_import"
    extracted_assets_dir = test_import_dir / "extracted_assets" / "test_mod"
    extracted_assets_dir.mkdir(parents=True, exist_ok=True)

    # Mock catalog with some items
    mock_catalog = [
        CatalogItem(
            code="ITEM001",
            category=ItemCategory.Item,
            icon_path="War/Content/Icons/Icon1",
            subicon_path="",
        ),
        CatalogItem(
            code="ITEM002",
            category=ItemCategory.Item,
            icon_path="War/Content/Icons/Icon2",
            subicon_path="",
        ),
    ]

    with patch.object(worker, "_get_temp_dir_for_wsl", return_value=None):
        with patch("tempfile.mkdtemp") as mock_mkdtemp:
            with patch("shutil.rmtree") as mock_rmtree:
                mock_mkdtemp.return_value = str(test_import_dir)

                # Mock database check to return empty set (nothing exists)
                with patch.object(
                    worker, "_get_existing_item_codes_from_database", return_value=set()
                ):
                    # Mock catalog loading
                    with patch(
                        "foxhole_stockpiles.core.utils.load_catalog", return_value=mock_catalog
                    ):
                        # Simulate extraction creating some PNG files
                        async def mock_extract_side_effect(*args: Any, **kwargs: Any) -> None:
                            (extracted_assets_dir / "icon1.png").touch()
                            (extracted_assets_dir / "icon2.png").touch()

                        with patch.object(
                            worker,
                            "_extract_assets",
                            new_callable=AsyncMock,
                            side_effect=mock_extract_side_effect,
                        ) as mock_extract:
                            with patch.object(
                                worker, "_generate_templates", new_callable=AsyncMock
                            ) as mock_generate:
                                with patch.object(
                                    worker, "_build_database", new_callable=AsyncMock
                                ) as mock_build:
                                    # Mock the finished signal
                                    worker.finished = MagicMock()  # type: ignore[misc]

                                    await worker._run_import_pipeline()

                                    # Verify all steps were called
                                    mock_extract.assert_called_once()
                                    mock_generate.assert_called_once()
                                    mock_build.assert_called_once()

                                    # Verify cleanup
                                    mock_rmtree.assert_called_once_with(
                                        str(test_import_dir), ignore_errors=True
                                    )

                                    # Verify success signal
                                    worker.finished.emit.assert_called_once_with(True)


@pytest.mark.asyncio
async def test_run_import_pipeline_stop_before_extraction(worker: IconImportWorker) -> None:
    """Test pipeline stops before extraction when requested.

    Args:
        worker: IconImportWorker instance
    """
    worker._should_stop = True

    with patch.object(worker, "_get_temp_dir_for_wsl", return_value=None):
        with patch("tempfile.mkdtemp", return_value="/tmp/test_import"):
            with patch("shutil.rmtree"):
                with patch.object(
                    worker, "_extract_assets", new_callable=AsyncMock
                ) as mock_extract:
                    worker.finished = MagicMock()  # type: ignore[misc]

                    await worker._run_import_pipeline()

                    # Extract should not be called
                    mock_extract.assert_not_called()

                    # Should emit failure
                    worker.finished.emit.assert_called_once_with(False)


@pytest.mark.asyncio
async def test_run_import_pipeline_stop_after_extraction(worker: IconImportWorker) -> None:
    """Test pipeline stops after extraction when requested.

    Args:
        worker: IconImportWorker instance
    """
    # Mock catalog
    mock_catalog = [
        CatalogItem(
            code="ITEM001",
            category=ItemCategory.Item,
            icon_path="War/Content/Icons/Icon1",
            subicon_path="",
        ),
    ]

    async def stop_after_extract(*args: Any, **kwargs: Any) -> None:
        worker._should_stop = True

    with patch.object(worker, "_get_temp_dir_for_wsl", return_value=None):
        with patch("tempfile.mkdtemp", return_value="/tmp/test_import"):
            with patch("shutil.rmtree"):
                with patch.object(
                    worker, "_get_existing_item_codes_from_database", return_value=set()
                ):
                    with patch(
                        "foxhole_stockpiles.core.utils.load_catalog", return_value=mock_catalog
                    ):
                        with patch.object(
                            worker,
                            "_extract_assets",
                            new_callable=AsyncMock,
                            side_effect=stop_after_extract,
                        ):
                            with patch.object(
                                worker, "_generate_templates", new_callable=AsyncMock
                            ) as mock_generate:
                                worker.finished = MagicMock()  # type: ignore[misc]

                                await worker._run_import_pipeline()

                                # Generate should not be called
                                mock_generate.assert_not_called()

                                # Should emit failure
                                worker.finished.emit.assert_called_once_with(False)


@pytest.mark.asyncio
async def test_run_import_pipeline_skip_when_nothing_extracted(
    worker: IconImportWorker, tmp_path: Path
) -> None:
    """Test pipeline skips template generation when no assets were extracted.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    worker.overwrite = False  # Don't overwrite existing

    with patch.object(worker, "_get_temp_dir_for_wsl", return_value=None):
        with patch("tempfile.mkdtemp", return_value=str(tmp_path / "test_import")):
            with patch("shutil.rmtree"):
                with patch.object(
                    worker, "_get_existing_item_codes_from_database", return_value=set()
                ):
                    with patch.object(worker, "_extract_assets", new_callable=AsyncMock):
                        # Create temp dirs but don't add PNGs (filtered extraction)
                        extracted_dir = tmp_path / "test_import" / "extracted_assets" / "testmod"
                        extracted_dir.mkdir(parents=True, exist_ok=True)

                        with patch.object(
                            worker, "_generate_templates", new_callable=AsyncMock
                        ) as mock_generate:
                            with patch.object(
                                worker, "_build_database", new_callable=AsyncMock
                            ) as mock_build:
                                worker.finished = MagicMock()  # type: ignore[misc]

                                await worker._run_import_pipeline()

                                # Should NOT call generate or build when nothing extracted
                                mock_generate.assert_not_called()
                                mock_build.assert_not_called()

                                # Should emit success (nothing to do is success)
                                worker.finished.emit.assert_called_once_with(True)


@pytest.mark.asyncio
async def test_run_import_pipeline_error_handling(worker: IconImportWorker) -> None:
    """Test pipeline error handling.

    Args:
        worker: IconImportWorker instance
    """
    # Mock catalog
    mock_catalog = [
        CatalogItem(
            code="ITEM001",
            category=ItemCategory.Item,
            icon_path="War/Content/Icons/Icon1",
            subicon_path="",
        ),
    ]

    with patch.object(worker, "_get_temp_dir_for_wsl", return_value=None):
        with patch("tempfile.mkdtemp", return_value="/tmp/test_import"):
            with patch("shutil.rmtree"):
                with patch.object(
                    worker, "_get_existing_item_codes_from_database", return_value=set()
                ):
                    with patch(
                        "foxhole_stockpiles.core.utils.load_catalog", return_value=mock_catalog
                    ):
                        with patch.object(
                            worker,
                            "_extract_assets",
                            new_callable=AsyncMock,
                            side_effect=Exception("Test error"),
                        ):
                            worker.finished = MagicMock()  # type: ignore[misc]
                            worker.error = MagicMock()

                            await worker._run_import_pipeline()

                            # Should emit error and failure
                            worker.error.emit.assert_called_once()
                            # Check that the error message contains the original error
                            emitted_error = worker.error.emit.call_args[0][0]
                            assert "Test error" in emitted_error
                            assert "Exception:" in emitted_error
                            worker.finished.emit.assert_called_once_with(False)


@pytest.mark.asyncio
async def test_run_import_pipeline_cleanup_error(worker: IconImportWorker) -> None:
    """Test pipeline cleanup handles errors gracefully.

    Args:
        worker: IconImportWorker instance
    """
    with patch.object(worker, "_get_temp_dir_for_wsl", return_value=None):
        with patch("tempfile.mkdtemp", return_value="/tmp/test_import"):
            with patch("shutil.rmtree", side_effect=Exception("Cleanup failed")):
                with patch.object(worker, "_extract_assets", new_callable=AsyncMock):
                    with patch.object(worker, "_generate_templates", new_callable=AsyncMock):
                        with patch.object(worker, "_build_database", new_callable=AsyncMock):
                            worker.finished = MagicMock()  # type: ignore[misc]

                            # Should not raise exception despite cleanup error
                            await worker._run_import_pipeline()

                            # Should still emit success
                            worker.finished.emit.assert_called_once_with(True)


def test_run_method(worker: IconImportWorker) -> None:
    """Test the run method calls asyncio.run.

    Args:
        worker: IconImportWorker instance
    """
    with patch("asyncio.run") as mock_asyncio_run:
        worker.run()

        mock_asyncio_run.assert_called_once()


def test_run_method_exception_handling(worker: IconImportWorker) -> None:
    """Test run method handles exceptions.

    Args:
        worker: IconImportWorker instance
    """
    worker.error = MagicMock()
    worker.finished = MagicMock()  # type: ignore[misc]

    with patch("asyncio.run", side_effect=Exception("Test error")):
        worker.run()

        worker.error.emit.assert_called_once_with("Test error")
        worker.finished.emit.assert_called_once_with(False)


# ===== Additional Coverage Tests =====


@pytest.mark.asyncio
async def test_get_existing_icons_no_database_path(worker: IconImportWorker) -> None:
    """Test get_existing_item_codes when database path is not configured.

    Args:
        worker: IconImportWorker instance
    """
    worker.settings.scanner.database_path = None

    existing = await worker._get_existing_item_codes_from_database()

    assert existing == set()


@pytest.mark.asyncio
async def test_pipeline_with_overwrite_enabled(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test pipeline when overwrite is enabled (extracts all items).

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    worker.overwrite = True
    worker.catalog_path.write_text('[{"code": "TEST", "icon_path": "test"}]')

    # Create a fake PNG to simulate extraction
    extracted_dir = tmp_path / "extracted"
    extracted_dir.mkdir()
    (extracted_dir / "test.png").write_text("fake")

    with patch.object(worker, "_extract_assets", new=AsyncMock()) as mock_extract:
        with patch.object(worker, "_generate_templates", new=AsyncMock()):
            with patch.object(worker, "_build_database", new=AsyncMock()):
                with patch("tempfile.mkdtemp", return_value=str(tmp_path)):
                    await worker._run_import_pipeline()

                    # Should call extract_assets with empty existing_codes (overwrite mode)
                    mock_extract.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_early_exit_with_existing_items(
    worker: IconImportWorker, tmp_path: Path
) -> None:
    """Test pipeline exits early when nothing extracted but items exist in DB.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    worker.overwrite = False
    worker.catalog_path.write_text('[{"code": "TEST", "icon_path": "test"}]')

    # Mock database check to return existing items
    async def mock_get_existing() -> set[str]:
        return {"TEST"}

    worker._get_existing_item_codes_from_database = mock_get_existing  # type: ignore[method-assign]

    # Mock extraction that extracts nothing
    async def mock_extract(output_dir: Path, existing_codes: set[str]) -> None:
        pass  # Don't create any files

    worker._extract_assets = mock_extract  # type: ignore[method-assign]

    with patch("tempfile.mkdtemp", return_value=str(tmp_path)):
        with patch.object(worker, "_generate_templates", new=AsyncMock()) as mock_gen:
            with patch.object(worker, "_build_database", new=AsyncMock()) as mock_db:
                await worker._run_import_pipeline()

                # Should not call template generation or database building
                mock_gen.assert_not_called()
                mock_db.assert_not_called()


@pytest.mark.asyncio
async def test_pipeline_early_exit_without_existing_items(
    worker: IconImportWorker, tmp_path: Path
) -> None:
    """Test pipeline exits early when nothing extracted and no items in DB.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    worker.overwrite = False
    worker.catalog_path.write_text('[{"code": "TEST", "icon_path": "test"}]')

    # Mock database check to return no items
    async def mock_get_existing() -> set[str]:
        return set()

    worker._get_existing_item_codes_from_database = mock_get_existing  # type: ignore[method-assign]

    # Mock extraction that extracts nothing
    async def mock_extract(output_dir: Path, existing_codes: set[str]) -> None:
        pass  # Don't create any files

    worker._extract_assets = mock_extract  # type: ignore[method-assign]

    with patch("tempfile.mkdtemp", return_value=str(tmp_path)):
        with patch.object(worker, "_generate_templates", new=AsyncMock()) as mock_gen:
            with patch.object(worker, "_build_database", new=AsyncMock()) as mock_db:
                await worker._run_import_pipeline()

                # Should not call template generation or database building
                mock_gen.assert_not_called()
                mock_db.assert_not_called()


@pytest.mark.asyncio
async def test_vanilla_extraction_with_overwrite_enabled(
    worker: IconImportWorker, tmp_path: Path
) -> None:
    """Test vanilla extraction when overwrite is enabled.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    worker.overwrite = True
    vanilla_pak = tmp_path / "vanilla.pak"
    vanilla_pak.touch()
    worker.vanilla_pak_file = str(vanilla_pak)

    # Create PNG to simulate mod extraction
    (tmp_path / "test.png").write_text("fake")

    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.PakExtractor"
    ) as mock_extractor_class:
        mock_mod_extractor = AsyncMock()
        mock_mod_extractor.process_files.return_value = True
        mock_vanilla_extractor = AsyncMock()
        mock_vanilla_extractor.process_files.return_value = True

        mock_extractor_class.side_effect = [mock_mod_extractor, mock_vanilla_extractor]

        await worker._extract_assets(tmp_path, set())

        # Vanilla extractor should be called with simple filter (no existing_codes check)
        assert mock_extractor_class.call_count == 2
        vanilla_call = mock_extractor_class.call_args_list[1]
        filter_func = vanilla_call[1]["filter_assets"]
        # Test the filter function
        assert filter_func("War/Content/Textures/UI/Menus/IconFilterCrates.uasset") is True
        assert filter_func("War/Content/Textures/UI/Subicons/test.uasset") is True
        assert filter_func("War/Content/Other/File.uasset") is False


@pytest.mark.asyncio
async def test_extraction_filter_not_in_catalog(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test extraction filter returns True for files not in catalog.

    Args:
        worker: IconImportWorker instance
        tmp_path: Temporary directory path
    """
    worker.overwrite = False
    worker.catalog_path.write_text('[{"code": "TEST", "icon_path": "test"}]')

    with patch(
        "foxhole_stockpiles.gui.utils.icon_import_worker.PakExtractor"
    ) as mock_extractor_class:
        mock_extractor = AsyncMock()
        mock_extractor.process_files.return_value = True
        mock_extractor_class.return_value = mock_extractor

        # Pass existing_codes to trigger filter creation
        await worker._extract_assets(tmp_path, {"EXISTING"})

        # Check that filter was created
        call_args = mock_extractor_class.call_args
        filter_func = call_args[1]["filter_assets"]

        # File not in catalog should pass through (return True)
        assert filter_func("other_file.uasset") is True

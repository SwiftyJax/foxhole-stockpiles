"""Tests for IconImportWorker."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from foxhole_stockpiles.core.settings.app_settings import AppSettings
from foxhole_stockpiles.core.settings.sections.database_builder import DatabaseBuilderSettings
from foxhole_stockpiles.core.settings.sections.scanner import ScannerSettings
from foxhole_stockpiles.core.settings.sections.templates import TemplateSettings
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.gui.utils.icon_import_worker import IconImportWorker


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
            pak_files=[str(pak_file)],
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
    assert worker.pak_files == [str(tmp_path / "test.pak")]
    assert worker.mod_name == "test_mod"
    assert worker.catalog_path == tmp_path / "catalog.json"
    assert worker.overwrite is False
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
            pak_files=["test.pak"],
            mod_name="test_mod",
            catalog_path=catalog_file,
        )

    assert worker.target_resolutions == ["1080", "1440"]


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
        await worker._extract_assets(tmp_path)


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
        await worker._extract_assets(tmp_path)


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
        await worker._extract_assets(tmp_path)


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
        await worker._extract_assets(tmp_path)


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

        await worker._extract_assets(tmp_path)

        mock_extractor_class.assert_called_once()
        mock_extractor.process_files.assert_called_once()


@pytest.mark.asyncio
async def test_extract_assets_failure(worker: IconImportWorker, tmp_path: Path) -> None:
    """Test asset extraction failure.

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

        with pytest.raises(RuntimeError, match="Asset extraction failed"):
            await worker._extract_assets(tmp_path)


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
    """Test template generation failure.

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

        with pytest.raises(RuntimeError, match="Template generation failed"):
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
async def test_run_import_pipeline_success(worker: IconImportWorker) -> None:
    """Test successful full pipeline execution.

    Args:
        worker: IconImportWorker instance
    """
    with patch.object(worker, "_get_temp_dir_for_wsl", return_value=None):
        with patch("tempfile.mkdtemp") as mock_mkdtemp:
            with patch("shutil.rmtree") as mock_rmtree:
                mock_mkdtemp.return_value = "/tmp/test_import"

                with patch.object(
                    worker, "_extract_assets", new_callable=AsyncMock
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
                                "/tmp/test_import", ignore_errors=True
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

    async def stop_after_extract(*args: Any, **kwargs: Any) -> None:
        worker._should_stop = True

    with patch.object(worker, "_get_temp_dir_for_wsl", return_value=None):
        with patch("tempfile.mkdtemp", return_value="/tmp/test_import"):
            with patch("shutil.rmtree"):
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
async def test_run_import_pipeline_error_handling(worker: IconImportWorker) -> None:
    """Test pipeline error handling.

    Args:
        worker: IconImportWorker instance
    """
    with patch.object(worker, "_get_temp_dir_for_wsl", return_value=None):
        with patch("tempfile.mkdtemp", return_value="/tmp/test_import"):
            with patch("shutil.rmtree"):
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
                    worker.error.emit.assert_called_once_with("Test error")
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

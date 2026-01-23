"""Tests for CatalogBuilderWorker."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from foxhole_stockpiles.gui.utils.catalog_builder_worker import CatalogBuilderWorker


@pytest.fixture
def worker(tmp_path: Path) -> CatalogBuilderWorker:
    """Create a CatalogBuilderWorker instance.

    Args:
        tmp_path: Temporary directory path

    Returns:
        CatalogBuilderWorker: Worker instance
    """
    pak_file = tmp_path / "test.pak"
    pak_file.touch()

    output_path = tmp_path / "catalog.json"

    extractor_tool = tmp_path / "repak.exe"
    extractor_tool.touch()

    converter_tool = tmp_path / "uassetgui.exe"
    converter_tool.touch()

    return CatalogBuilderWorker(
        pak_file=pak_file,
        output_path=output_path,
        extractor_tool=extractor_tool,
        converter_tool=converter_tool,
        workers=2,
    )


# ===== Initialization Tests =====


def test_initialization(worker: CatalogBuilderWorker, tmp_path: Path) -> None:
    """Test CatalogBuilderWorker initialization.

    Args:
        worker: CatalogBuilderWorker instance
        tmp_path: Temporary directory path
    """
    assert worker.pak_file == tmp_path / "test.pak"
    assert worker.output_path == tmp_path / "catalog.json"
    assert worker.extractor_tool == tmp_path / "repak.exe"
    assert worker.converter_tool == tmp_path / "uassetgui.exe"
    assert worker.workers == 2
    assert worker._should_stop is False


def test_initialization_default_workers(tmp_path: Path) -> None:
    """Test CatalogBuilderWorker uses default workers.

    Args:
        tmp_path: Temporary directory path
    """
    worker = CatalogBuilderWorker(
        pak_file=tmp_path / "test.pak",
        output_path=tmp_path / "catalog.json",
        extractor_tool=tmp_path / "repak.exe",
        converter_tool=tmp_path / "uassetgui.exe",
    )

    assert worker.workers == 4


# ===== Stop Tests =====


def test_stop(worker: CatalogBuilderWorker) -> None:
    """Test stop method sets the flag.

    Args:
        worker: CatalogBuilderWorker instance
    """
    assert worker._should_stop is False
    worker.stop()
    assert worker._should_stop is True


# ===== Run Tests =====


def test_run_calls_asyncio_run(worker: CatalogBuilderWorker) -> None:
    """Test run method calls asyncio.run.

    Args:
        worker: CatalogBuilderWorker instance
    """
    with patch("asyncio.run") as mock_asyncio_run:
        worker.run()

        mock_asyncio_run.assert_called_once()


def test_run_exception_handling(worker: CatalogBuilderWorker) -> None:
    """Test run method handles exceptions.

    Args:
        worker: CatalogBuilderWorker instance
    """
    mock_error = MagicMock()
    mock_finished = MagicMock()

    with patch.object(worker, "error", mock_error):
        with patch.object(worker, "finished", mock_finished):
            with patch("asyncio.run", side_effect=Exception("Test error")):
                worker.run()

                mock_error.emit.assert_called_once_with("Test error")
                mock_finished.emit.assert_called_once_with(False)


# ===== Build Catalog Tests =====


@pytest.mark.asyncio
async def test_build_catalog_success(worker: CatalogBuilderWorker, tmp_path: Path) -> None:
    """Test successful catalog build.

    Args:
        worker: CatalogBuilderWorker instance
        tmp_path: Temporary directory path
    """
    mock_finished = MagicMock()
    mock_progress = MagicMock()

    mock_extractor = MagicMock()
    mock_extractor.extract = AsyncMock(return_value=tmp_path / "extracted")
    mock_extractor.stats = {"extracted": 10, "converted": 8}

    mock_assembler = MagicMock()
    mock_assembler.build_catalog.return_value = {"item1": {"name": "Item 1"}}
    mock_assembler.get_stats.return_value = {"parsed": 10, "stockpilable": 5, "errors": 0}

    with patch.object(worker, "finished", mock_finished):
        with patch.object(worker, "progress", mock_progress):
            with patch(
                "foxhole_stockpiles.gui.utils.catalog_builder_worker.BlueprintExtractor"
            ) as mock_bp_class:
                mock_bp_class.return_value = mock_extractor
                with patch(
                    "foxhole_stockpiles.gui.utils.catalog_builder_worker.CatalogAssembler"
                ) as mock_ca_class:
                    mock_ca_class.from_extract_dir.return_value = mock_assembler

                    await worker._build_catalog()

                    mock_finished.emit.assert_called_once_with(True)
                    # Progress should be emitted multiple times
                    assert mock_progress.emit.call_count >= 3


@pytest.mark.asyncio
async def test_build_catalog_cancelled_during_extraction_setup(
    worker: CatalogBuilderWorker,
) -> None:
    """Test build cancelled during extraction setup.

    Args:
        worker: CatalogBuilderWorker instance
    """
    worker._should_stop = True
    mock_finished = MagicMock()

    with patch.object(worker, "finished", mock_finished):
        await worker._build_catalog()

        mock_finished.emit.assert_called_once_with(False)


@pytest.mark.asyncio
async def test_build_catalog_cancelled_after_extraction(
    worker: CatalogBuilderWorker, tmp_path: Path
) -> None:
    """Test build cancelled after extraction.

    Args:
        worker: CatalogBuilderWorker instance
        tmp_path: Temporary directory path
    """
    mock_finished = MagicMock()

    mock_extractor = MagicMock()

    async def set_stop_and_return(*args: object, **kwargs: object) -> Path:
        worker._should_stop = True
        return tmp_path / "extracted"

    mock_extractor.extract = AsyncMock(side_effect=set_stop_and_return)
    mock_extractor.stats = {"extracted": 10, "converted": 8}

    with patch.object(worker, "finished", mock_finished):
        with patch(
            "foxhole_stockpiles.gui.utils.catalog_builder_worker.BlueprintExtractor"
        ) as mock_bp_class:
            mock_bp_class.return_value = mock_extractor

            await worker._build_catalog()

            mock_finished.emit.assert_called_once_with(False)


@pytest.mark.asyncio
async def test_build_catalog_cancelled_before_assembly(
    worker: CatalogBuilderWorker, tmp_path: Path
) -> None:
    """Test build cancelled before catalog assembly.

    Args:
        worker: CatalogBuilderWorker instance
        tmp_path: Temporary directory path
    """
    mock_finished = MagicMock()
    mock_progress = MagicMock()

    mock_extractor = MagicMock()
    mock_extractor.extract = AsyncMock(return_value=tmp_path / "extracted")
    mock_extractor.stats = {"extracted": 10, "converted": 8}

    call_count = [0]

    def progress_side_effect(*args: object) -> None:
        call_count[0] += 1
        if call_count[0] >= 2:  # After extraction progress
            worker._should_stop = True

    mock_progress.emit.side_effect = progress_side_effect

    with patch.object(worker, "finished", mock_finished):
        with patch.object(worker, "progress", mock_progress):
            with patch(
                "foxhole_stockpiles.gui.utils.catalog_builder_worker.BlueprintExtractor"
            ) as mock_bp_class:
                mock_bp_class.return_value = mock_extractor

                await worker._build_catalog()

                mock_finished.emit.assert_called_once_with(False)


@pytest.mark.asyncio
async def test_build_catalog_cancelled_after_assembly(
    worker: CatalogBuilderWorker, tmp_path: Path
) -> None:
    """Test build cancelled after catalog assembly.

    Args:
        worker: CatalogBuilderWorker instance
        tmp_path: Temporary directory path
    """
    mock_finished = MagicMock()

    mock_extractor = MagicMock()
    mock_extractor.extract = AsyncMock(return_value=tmp_path / "extracted")
    mock_extractor.stats = {"extracted": 10, "converted": 8}

    mock_assembler = MagicMock()

    def build_and_stop() -> dict[str, dict[str, str]]:
        worker._should_stop = True
        return {"item1": {"name": "Item 1"}}

    mock_assembler.build_catalog.side_effect = build_and_stop
    mock_assembler.get_stats.return_value = {"parsed": 10, "stockpilable": 5, "errors": 0}

    with patch.object(worker, "finished", mock_finished):
        with patch(
            "foxhole_stockpiles.gui.utils.catalog_builder_worker.BlueprintExtractor"
        ) as mock_bp_class:
            mock_bp_class.return_value = mock_extractor
            with patch(
                "foxhole_stockpiles.gui.utils.catalog_builder_worker.CatalogAssembler"
            ) as mock_ca_class:
                mock_ca_class.from_extract_dir.return_value = mock_assembler

                await worker._build_catalog()

                mock_finished.emit.assert_called_once_with(False)


@pytest.mark.asyncio
async def test_build_catalog_exception(worker: CatalogBuilderWorker) -> None:
    """Test build catalog exception handling.

    Args:
        worker: CatalogBuilderWorker instance
    """
    mock_finished = MagicMock()
    mock_error = MagicMock()

    with patch.object(worker, "finished", mock_finished):
        with patch.object(worker, "error", mock_error):
            with patch(
                "foxhole_stockpiles.gui.utils.catalog_builder_worker.BlueprintExtractor"
            ) as mock_bp_class:
                mock_bp_class.side_effect = Exception("Extraction failed")

                await worker._build_catalog()

                mock_error.emit.assert_called_once()
                assert "Extraction failed" in mock_error.emit.call_args[0][0]
                mock_finished.emit.assert_called_once_with(False)


@pytest.mark.asyncio
async def test_build_catalog_writes_output_file(
    worker: CatalogBuilderWorker, tmp_path: Path
) -> None:
    """Test build catalog writes output file.

    Args:
        worker: CatalogBuilderWorker instance
        tmp_path: Temporary directory path
    """
    mock_finished = MagicMock()

    mock_extractor = MagicMock()
    mock_extractor.extract = AsyncMock(return_value=tmp_path / "extracted")
    mock_extractor.stats = {"extracted": 10, "converted": 8}

    mock_assembler = MagicMock()
    mock_assembler.build_catalog.return_value = {"item1": {"name": "Test Item"}}
    mock_assembler.get_stats.return_value = {"parsed": 10, "stockpilable": 1, "errors": 0}

    with patch.object(worker, "finished", mock_finished):
        with patch(
            "foxhole_stockpiles.gui.utils.catalog_builder_worker.BlueprintExtractor"
        ) as mock_bp_class:
            mock_bp_class.return_value = mock_extractor
            with patch(
                "foxhole_stockpiles.gui.utils.catalog_builder_worker.CatalogAssembler"
            ) as mock_ca_class:
                mock_ca_class.from_extract_dir.return_value = mock_assembler

                await worker._build_catalog()

                # Check output file was written
                assert worker.output_path.exists()
                content = worker.output_path.read_text()
                assert "Test Item" in content


@pytest.mark.asyncio
async def test_build_catalog_creates_output_directory(
    tmp_path: Path,
) -> None:
    """Test build catalog creates output directory if needed.

    Args:
        tmp_path: Temporary directory path
    """
    nested_output = tmp_path / "nested" / "dir" / "catalog.json"

    worker = CatalogBuilderWorker(
        pak_file=tmp_path / "test.pak",
        output_path=nested_output,
        extractor_tool=tmp_path / "repak.exe",
        converter_tool=tmp_path / "uassetgui.exe",
    )

    mock_finished = MagicMock()

    mock_extractor = MagicMock()
    mock_extractor.extract = AsyncMock(return_value=tmp_path / "extracted")
    mock_extractor.stats = {"extracted": 10, "converted": 8}

    mock_assembler = MagicMock()
    mock_assembler.build_catalog.return_value = {"item1": {}}
    mock_assembler.get_stats.return_value = {"parsed": 1, "stockpilable": 1, "errors": 0}

    with patch.object(worker, "finished", mock_finished):
        with patch(
            "foxhole_stockpiles.gui.utils.catalog_builder_worker.BlueprintExtractor"
        ) as mock_bp_class:
            mock_bp_class.return_value = mock_extractor
            with patch(
                "foxhole_stockpiles.gui.utils.catalog_builder_worker.CatalogAssembler"
            ) as mock_ca_class:
                mock_ca_class.from_extract_dir.return_value = mock_assembler

                await worker._build_catalog()

                # Check output directory was created
                assert nested_output.parent.exists()

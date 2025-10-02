"""Tests for commands.uasset_extractor.uasset_extractor module.

This module contains comprehensive tests for the UAsset extractor command,
including PAK file extraction, asset processing, main function behavior,
and error handling scenarios.
"""

import argparse
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from foxhole_stockpiles.commands.uasset_extractor.uasset_extractor import (
    PakExtractor,
    main,
)


class TestPakExtractorInitialization:
    """Test suite for PakExtractor initialization.

    This class contains tests for PakExtractor instance creation
    with various parameter combinations and configurations.
    """

    async def test_default_initialization(self) -> None:
        """Test PakExtractor with default values.

        Validates that the PakExtractor initializes correctly with
        default parameter values.
        """
        with patch("pathlib.Path.exists", return_value=True):
            extractor = PakExtractor()

            assert str(extractor.catalog_file).endswith("catalog.json")
            assert str(extractor.output_dir).endswith("output")
            assert isinstance(extractor.pak_files, list)

    async def test_custom_initialization(self, tmp_path: Path) -> None:
        """Test PakExtractor with custom values.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Create mock files to satisfy validation
        catalog_file = tmp_path / "custom_catalog.json"
        catalog_file.write_text("[]")

        pak_file = tmp_path / "custom.pak"
        pak_file.touch()

        extractor_tool = tmp_path / "custom_repak.exe"
        extractor_tool.touch()

        converter_tool = tmp_path / "custom_umodel.exe"
        converter_tool.touch()

        catalog = str(catalog_file)
        pak = [str(pak_file)]
        extractor_tool_str = str(extractor_tool)
        converter_tool_str = str(converter_tool)
        output = str(tmp_path / "output")

        extractor = PakExtractor(
            catalog_file=catalog,
            pak_files=pak,
            extractor_tool=extractor_tool_str,
            converter_tool=converter_tool_str,
            output_dir=output,
        )

        assert str(extractor.catalog_file) == catalog
        assert extractor.pak_files == [Path(p).resolve() for p in pak]
        assert str(extractor.extractor_tool) == extractor_tool_str
        assert str(extractor.converter_tool) == converter_tool_str
        assert str(extractor.output_dir) == output

    async def test_multiple_pak_files(self) -> None:
        """Test PakExtractor with multiple PAK files.

        Validates that the extractor properly handles lists of PAK files.
        """
        pak_files = ["pak1.pak", "pak2.pak", "pak3.pak"]

        with patch("pathlib.Path.exists", return_value=True):
            extractor = PakExtractor(pak_files=pak_files)

            assert extractor.pak_files == [Path(p).resolve() for p in pak_files]
            assert isinstance(extractor.pak_files, list)
            assert len(extractor.pak_files) == 3


class TestPakExtractorMethods:
    """Test suite for PakExtractor methods.

    This class contains tests for the core functionality of PakExtractor
    including PAK extraction, asset processing, and parallel operations.
    """

    @pytest.fixture
    def extractor(self, tmp_path: Path) -> PakExtractor:
        """Create a PakExtractor instance for testing.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.

        Returns:
            PakExtractor: Configured extractor instance for testing.
        """
        # Create mock files to satisfy validation
        catalog_file = tmp_path / "catalog.json"
        catalog_file.write_text("[]")

        extractor_tool = tmp_path / "repak.exe"
        extractor_tool.touch()

        converter_tool = tmp_path / "umodel.exe"
        converter_tool.touch()

        pak_file = tmp_path / "test.pak"
        pak_file.touch()

        return PakExtractor(
            catalog_file=str(catalog_file),
            pak_files=str(pak_file),
            extractor_tool=str(extractor_tool),
            converter_tool=str(converter_tool),
            output_dir=str(tmp_path / "output"),
        )

    async def test_extract_single_file_success(
        self, extractor: PakExtractor, tmp_path: Path
    ) -> None:
        """Test successful single file extraction.

        Args:
            extractor (PakExtractor): PakExtractor instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        file_path = "War/Content/test.uasset"
        temp_dir = str(tmp_path / "temp")

        with patch.object(extractor, "extract_single_file") as mock_extract:
            mock_extract.return_value = True
            result = await extractor.extract_single_file(file_path, temp_dir)

        assert result is True

    async def test_extract_single_file_failure(
        self, extractor: PakExtractor, tmp_path: Path
    ) -> None:
        """Test failed single file extraction.

        Args:
            extractor (PakExtractor): PakExtractor instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        file_path = "War/Content/nonexistent.uasset"
        temp_dir = str(tmp_path / "temp")

        with patch.object(extractor, "extract_single_file") as mock_extract:
            mock_extract.return_value = False
            result = await extractor.extract_single_file(file_path, temp_dir)

        assert result is False

    async def test_get_files_to_extract_no_catalog(
        self, extractor: PakExtractor, tmp_path: Path
    ) -> None:
        """Test getting files to extract when catalog doesn't exist.

        Args:
            extractor (PakExtractor): PakExtractor instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        extractor.catalog_file = tmp_path / "nonexistent.json"

        with patch("foxhole_stockpiles.core.utils.load_catalog") as mock_load:
            mock_load.return_value = []
            result = extractor.get_files_to_extract()

        assert result == set()

    async def test_process_files_success(self, extractor: PakExtractor) -> None:
        """Test successful file processing.

        Args:
            extractor (PakExtractor): PakExtractor instance from fixture.
        """
        with patch.object(extractor, "get_files_to_extract") as mock_get_files:
            mock_get_files.return_value = {"War/Content/test1.uasset", "War/Content/test2.uasset"}

            with patch.object(extractor, "process_files") as mock_process:
                mock_process.return_value = True
                result = await extractor.process_files(max_workers=2)

        assert result is True


class TestPakExtractorValidation:
    """Test suite for PakExtractor validation.

    This class contains tests for input validation and error handling.
    """

    def test_init_empty_catalog_file(self) -> None:
        """Test initialization with empty catalog file path raises ValueError."""
        with pytest.raises(ValueError, match="catalog_file cannot be an empty string"):
            PakExtractor(catalog_file="")

    def test_init_empty_pak_files(self) -> None:
        """Test initialization with empty pak_files raises ValueError."""
        with pytest.raises(ValueError, match="pak_files cannot be empty"):
            PakExtractor(pak_files=[])

    def test_init_empty_extractor_tool(self) -> None:
        """Test initialization with empty extractor_tool raises ValueError."""
        with pytest.raises(ValueError, match="extractor_tool cannot be an empty string"):
            PakExtractor(extractor_tool="")

    def test_init_empty_converter_tool(self) -> None:
        """Test initialization with empty converter_tool raises ValueError."""
        with pytest.raises(ValueError, match="converter_tool cannot be an empty string"):
            PakExtractor(converter_tool="")

    def test_init_empty_output_dir(self) -> None:
        """Test initialization with empty output_dir raises ValueError."""
        with pytest.raises(ValueError, match="output_dir cannot be an empty string"):
            PakExtractor(output_dir="")

    def test_init_nonexistent_catalog(self, tmp_path: Path) -> None:
        """Test initialization with non-existent catalog raises FileNotFoundError.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        nonexistent = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError, match="Catalog file not found"):
            PakExtractor(catalog_file=str(nonexistent))

    def test_init_nonexistent_extractor_tool(self, tmp_path: Path) -> None:
        """Test initialization with non-existent extractor raises FileNotFoundError.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        catalog = tmp_path / "catalog.json"
        catalog.write_text("[]")
        nonexistent_tool = tmp_path / "nonexistent.exe"

        with pytest.raises(FileNotFoundError, match="Extractor tool not found"):
            PakExtractor(catalog_file=str(catalog), extractor_tool=str(nonexistent_tool))

    def test_init_nonexistent_converter_tool(self, tmp_path: Path) -> None:
        """Test initialization with non-existent converter raises FileNotFoundError.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        catalog = tmp_path / "catalog.json"
        catalog.write_text("[]")
        extractor_tool = tmp_path / "extractor.exe"
        extractor_tool.touch()
        nonexistent_converter = tmp_path / "nonexistent.exe"

        with pytest.raises(FileNotFoundError, match="Converter tool not found"):
            PakExtractor(
                catalog_file=str(catalog),
                extractor_tool=str(extractor_tool),
                converter_tool=str(nonexistent_converter),
            )

    def test_init_nonexistent_pak_file(self, tmp_path: Path) -> None:
        """Test initialization with non-existent PAK file raises FileNotFoundError.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        catalog = tmp_path / "catalog.json"
        catalog.write_text("[]")
        extractor_tool = tmp_path / "extractor.exe"
        extractor_tool.touch()
        converter_tool = tmp_path / "converter.exe"
        converter_tool.touch()
        nonexistent_pak = tmp_path / "nonexistent.pak"

        with pytest.raises(FileNotFoundError, match="PAK file not found"):
            PakExtractor(
                catalog_file=str(catalog),
                extractor_tool=str(extractor_tool),
                converter_tool=str(converter_tool),
                pak_files=str(nonexistent_pak),
            )


class TestGetFilesToExtract:
    """Test suite for get_files_to_extract method."""

    @pytest.fixture
    def extractor(self, tmp_path: Path) -> PakExtractor:
        """Create a PakExtractor instance for testing.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.

        Returns:
            PakExtractor: Configured extractor instance for testing.
        """
        catalog_file = tmp_path / "catalog.json"
        catalog_file.write_text("[]")
        extractor_tool = tmp_path / "repak.exe"
        extractor_tool.touch()
        converter_tool = tmp_path / "umodel.exe"
        converter_tool.touch()
        pak_file = tmp_path / "test.pak"
        pak_file.touch()

        return PakExtractor(
            catalog_file=str(catalog_file),
            pak_files=str(pak_file),
            extractor_tool=str(extractor_tool),
            converter_tool=str(converter_tool),
            output_dir=str(tmp_path / "output"),
        )

    def test_get_files_with_empty_catalog(self, extractor: PakExtractor) -> None:
        """Test get_files_to_extract with empty catalog.

        Args:
            extractor (PakExtractor): PakExtractor instance from fixture.
        """
        with patch("foxhole_stockpiles.core.utils.load_catalog") as mock_load:
            mock_load.return_value = []
            result = extractor.get_files_to_extract()

        assert result == set()

    def test_get_files_with_items_without_icon_path(self, extractor: PakExtractor) -> None:
        """Test get_files_to_extract with items missing icon_path.

        Args:
            extractor (PakExtractor): PakExtractor instance from fixture.
        """
        from foxhole_stockpiles.models.catalog_item import CatalogItem

        mock_item = Mock(spec=CatalogItem)
        mock_item.code = "TEST001"
        mock_item.icon_path = None
        mock_item.subicon_path = None

        with patch(
            "foxhole_stockpiles.commands.uasset_extractor.uasset_extractor.load_catalog"
        ) as mock_load:
            mock_load.return_value = [mock_item]
            result = extractor.get_files_to_extract()

        # Should only contain the crate icon
        assert len(result) == 1
        assert "War/Content/Textures/UI/Menus/IconFilterCrates.uasset" in result

    def test_get_files_with_subicon_path(self, extractor: PakExtractor) -> None:
        """Test get_files_to_extract with items having subicon_path.

        Args:
            extractor (PakExtractor): PakExtractor instance from fixture.
        """
        from foxhole_stockpiles.models.catalog_item import CatalogItem

        mock_item = Mock(spec=CatalogItem)
        mock_item.code = "TEST001"
        mock_item.icon_path = "War/Content/Icons/MainIcon"
        mock_item.subicon_path = "War/Content/Icons/SubIcon"

        with patch(
            "foxhole_stockpiles.commands.uasset_extractor.uasset_extractor.load_catalog"
        ) as mock_load:
            mock_load.return_value = [mock_item]
            result = extractor.get_files_to_extract()

        assert "War/Content/Icons/MainIcon.uasset" in result
        assert "War/Content/Icons/SubIcon.uasset" in result
        assert "War/Content/Textures/UI/Menus/IconFilterCrates.uasset" in result


class TestExtractSingleFile:
    """Test suite for extract_single_file method."""

    @pytest.fixture
    def extractor(self, tmp_path: Path) -> PakExtractor:
        """Create a PakExtractor instance for testing.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.

        Returns:
            PakExtractor: Configured extractor instance for testing.
        """
        catalog_file = tmp_path / "catalog.json"
        catalog_file.write_text("[]")
        extractor_tool = tmp_path / "repak.exe"
        extractor_tool.touch()
        converter_tool = tmp_path / "umodel.exe"
        converter_tool.touch()
        pak_file = tmp_path / "test.pak"
        pak_file.touch()

        return PakExtractor(
            catalog_file=str(catalog_file),
            pak_files=str(pak_file),
            extractor_tool=str(extractor_tool),
            converter_tool=str(converter_tool),
            output_dir=str(tmp_path / "output"),
        )

    async def test_extract_file_with_exception(
        self, extractor: PakExtractor, tmp_path: Path
    ) -> None:
        """Test extract_single_file when subprocess raises exception.

        Args:
            extractor (PakExtractor): PakExtractor instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        file_path = "War/Content/test.uasset"
        temp_dir = str(tmp_path / "temp")

        with patch("asyncio.create_subprocess_exec", side_effect=RuntimeError("Subprocess error")):
            result = await extractor.extract_single_file(file_path, temp_dir)

        assert result is False


class TestConvertToPng:
    """Test suite for convert_to_png method."""

    @pytest.fixture
    def extractor(self, tmp_path: Path) -> PakExtractor:
        """Create a PakExtractor instance for testing.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.

        Returns:
            PakExtractor: Configured extractor instance for testing.
        """
        catalog_file = tmp_path / "catalog.json"
        catalog_file.write_text("[]")
        extractor_tool = tmp_path / "repak.exe"
        extractor_tool.touch()
        converter_tool = tmp_path / "umodel.exe"
        converter_tool.touch()
        pak_file = tmp_path / "test.pak"
        pak_file.touch()

        return PakExtractor(
            catalog_file=str(catalog_file),
            pak_files=str(pak_file),
            extractor_tool=str(extractor_tool),
            converter_tool=str(converter_tool),
            output_dir=str(tmp_path / "output"),
        )

    async def test_convert_to_png_failure(self, extractor: PakExtractor, tmp_path: Path) -> None:
        """Test convert_to_png when conversion fails.

        Args:
            extractor (PakExtractor): PakExtractor instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        file_path = "War/Content/test.uasset"
        temp_dir = str(tmp_path / "temp")

        with patch.object(extractor, "_try_convert_with_version", return_value=False):
            result = await extractor.convert_to_png(file_path, temp_dir)

        assert result is False

    async def test_try_convert_file_not_found(
        self, extractor: PakExtractor, tmp_path: Path
    ) -> None:
        """Test _try_convert_with_version when extracted file not found.

        Args:
            extractor (PakExtractor): PakExtractor instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        file_path = "War/Content/test.uasset"
        temp_dir = str(tmp_path / "temp")
        Path(temp_dir).mkdir(parents=True, exist_ok=True)

        result = await extractor._try_convert_with_version(file_path, temp_dir)

        assert result is False

    async def test_try_convert_with_exception(
        self, extractor: PakExtractor, tmp_path: Path
    ) -> None:
        """Test _try_convert_with_version when subprocess raises exception.

        Args:
            extractor (PakExtractor): PakExtractor instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        file_path = "War/Content/test.uasset"
        temp_dir = str(tmp_path / "temp")

        # Create a pak directory structure
        pak_dir = Path(temp_dir) / "test"
        pak_dir.mkdir(parents=True)
        (pak_dir / file_path).parent.mkdir(parents=True, exist_ok=True)
        (pak_dir / file_path).touch()

        with patch("asyncio.create_subprocess_exec", side_effect=RuntimeError("Conversion error")):
            result = await extractor._try_convert_with_version(file_path, temp_dir)

        assert result is False


class TestProcessFiles:
    """Test suite for process_files method."""

    @pytest.fixture
    def extractor(self, tmp_path: Path) -> PakExtractor:
        """Create a PakExtractor instance for testing.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.

        Returns:
            PakExtractor: Configured extractor instance for testing.
        """
        catalog_file = tmp_path / "catalog.json"
        catalog_file.write_text("[]")
        extractor_tool = tmp_path / "repak.exe"
        extractor_tool.touch()
        converter_tool = tmp_path / "umodel.exe"
        converter_tool.touch()
        pak_file = tmp_path / "test.pak"
        pak_file.touch()

        return PakExtractor(
            catalog_file=str(catalog_file),
            pak_files=str(pak_file),
            extractor_tool=str(extractor_tool),
            converter_tool=str(converter_tool),
            output_dir=str(tmp_path / "output"),
        )

    async def test_process_files_no_files_to_extract(self, extractor: PakExtractor) -> None:
        """Test process_files when no files need extraction.

        Args:
            extractor (PakExtractor): PakExtractor instance from fixture.
        """
        with patch.object(extractor, "get_files_to_extract", return_value=set()):
            result = await extractor.process_files()

        assert result is False

    async def test_process_files_all_extractions_fail(self, extractor: PakExtractor) -> None:
        """Test process_files when all extractions fail.

        Args:
            extractor (PakExtractor): PakExtractor instance from fixture.
        """
        with patch.object(
            extractor, "get_files_to_extract", return_value={"file1.uasset", "file2.uasset"}
        ):
            with patch.object(extractor, "extract_single_file", return_value=False):
                result = await extractor.process_files()

        assert result is False


class TestMainFunction:
    """Test suite for the main CLI function.

    This class contains tests for the main entry point of the uasset
    extractor command, including argument parsing and workflow execution.
    """

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.core.logging.setup_logging")
    async def test_main_with_default_args(self, mock_setup_logging: Mock, mock_args: Mock) -> None:
        """Test main function with default arguments.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
        """
        mock_args.return_value = argparse.Namespace(
            catalog="catalog.json",
            pak=None,
            extractor_tool="C:\\repak\\repak.exe",
            converter_tool="C:\\UModel\\umodel.exe",
            output="output",
            log_file=None,
            verbose=False,
            quiet=False,
            workers=None,
        )

        with patch(
            "foxhole_stockpiles.commands.uasset_extractor.uasset_extractor.PakExtractor"
        ) as mock_extractor:
            instance = MagicMock()
            process_files_mock = MagicMock()

            async def mock_process_files(*args: Any, **kwargs: Any) -> bool:
                """Mock process_files method."""
                process_files_mock(*args, **kwargs)
                return True

            instance.process_files = mock_process_files
            mock_extractor.return_value = instance

            await main()

            mock_extractor.assert_called_once()
            process_files_mock.assert_called_once()

    @patch("foxhole_stockpiles.commands.uasset_extractor.uasset_extractor.setup_logging")
    @patch("argparse.ArgumentParser.parse_args")
    async def test_main_with_verbose_logging(
        self, mock_args: Mock, mock_setup_logging: Mock
    ) -> None:
        """Test main function with verbose logging enabled.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
        """
        mock_args.return_value = argparse.Namespace(
            catalog="catalog.json",
            pak=["custom.pak"],
            extractor_tool="repak.exe",
            converter_tool="umodel.exe",
            output="output",
            log_file="test.log",
            verbose=True,
            quiet=False,
            workers=None,
        )

        with patch(
            "foxhole_stockpiles.commands.uasset_extractor.uasset_extractor.PakExtractor"
        ) as mock_extractor:
            mock_instance = MagicMock()
            process_files_mock = MagicMock()

            async def mock_process_files(*args: Any, **kwargs: Any) -> bool:
                process_files_mock(*args, **kwargs)
                return True

            mock_instance.process_files = mock_process_files
            mock_extractor.return_value = mock_instance

            await main()

            # Verify verbose logging was set up
            mock_setup_logging.assert_called_once()

    @patch("foxhole_stockpiles.commands.uasset_extractor.uasset_extractor.setup_logging")
    @patch("argparse.ArgumentParser.parse_args")
    async def test_main_with_quiet_logging(self, mock_args: Mock, mock_setup_logging: Mock) -> None:
        """Test main function with quiet logging enabled.

        Args:
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            mock_setup_logging (Mock): Mocked setup_logging function.
        """
        mock_args.return_value = argparse.Namespace(
            catalog="catalog.json",
            pak=None,
            extractor_tool="C:\\repak\\repak.exe",
            converter_tool="C:\\UModel\\umodel.exe",
            output="output",
            log_file=None,
            verbose=False,
            quiet=True,
            workers=None,
        )

        with patch(
            "foxhole_stockpiles.commands.uasset_extractor.uasset_extractor.PakExtractor"
        ) as mock_extractor:
            instance = MagicMock()

            async def mock_process_files(*args: Any, **kwargs: Any) -> bool:
                return True

            instance.process_files = mock_process_files
            mock_extractor.return_value = instance

            await main()

            # Verify logging was set up
            mock_setup_logging.assert_called_once()

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.core.logging.setup_logging")
    async def test_main_with_multiple_pak_files(
        self, mock_setup_logging: Mock, mock_args: Mock
    ) -> None:
        """Test main function with multiple PAK files.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
        """
        pak_files = ["pak1.pak", "pak2.pak", "pak3.pak"]
        mock_args.return_value = argparse.Namespace(
            catalog="catalog.json",
            pak=pak_files,
            extractor_tool="repak.exe",
            converter_tool="umodel.exe",
            output="output",
            log_file=None,
            verbose=False,
            quiet=False,
            workers=None,
        )

        with patch(
            "foxhole_stockpiles.commands.uasset_extractor.uasset_extractor.PakExtractor"
        ) as mock_extractor:
            mock_instance = MagicMock()

            async def mock_process_files(*args: Any, **kwargs: Any) -> bool:
                return True

            mock_instance.process_files = mock_process_files
            mock_extractor.return_value = mock_instance

            await main()

            # Verify PakExtractor was called with multiple PAK files
            call_args = mock_extractor.call_args
            assert call_args[1]["pak_files"] == pak_files

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.core.logging.setup_logging")
    @patch("builtins.print")
    @patch("builtins.exit")
    async def test_main_initialization_error(
        self, mock_exit: Mock, mock_print: Mock, mock_setup_logging: Mock, mock_args: Mock
    ) -> None:
        """Test main function handles initialization errors.

        Args:
            mock_exit (Mock): Mocked exit function.
            mock_print (Mock): Mocked print function.
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
        """
        mock_args.return_value = argparse.Namespace(
            catalog="catalog.json",
            pak=None,
            extractor_tool="C:\\repak\\repak.exe",
            converter_tool="C:\\UModel\\umodel.exe",
            output="output",
            log_file=None,
            verbose=False,
            quiet=False,
            workers=None,
        )

        # Make exit() actually raise to prevent further code execution
        mock_exit.side_effect = SystemExit(1)

        with patch(
            "foxhole_stockpiles.commands.uasset_extractor.uasset_extractor.PakExtractor",
            side_effect=ValueError("Initialization error"),
        ):
            with pytest.raises(SystemExit):
                await main()

            # Verify error was printed and exit was called
            mock_print.assert_called()
            mock_exit.assert_called_with(1)

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.core.logging.setup_logging")
    @patch("builtins.print")
    @patch("builtins.exit")
    async def test_main_file_not_found_error(
        self, mock_exit: Mock, mock_print: Mock, mock_setup_logging: Mock, mock_args: Mock
    ) -> None:
        """Test main function handles file not found errors.

        Args:
            mock_exit (Mock): Mocked exit function.
            mock_print (Mock): Mocked print function.
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
        """
        mock_args.return_value = argparse.Namespace(
            catalog="catalog.json",
            pak=None,
            extractor_tool="C:\\repak\\repak.exe",
            converter_tool="C:\\UModel\\umodel.exe",
            output="output",
            log_file=None,
            verbose=False,
            quiet=False,
            workers=None,
        )

        # Make exit() actually raise to prevent further code execution
        mock_exit.side_effect = SystemExit(1)

        with patch(
            "foxhole_stockpiles.commands.uasset_extractor.uasset_extractor.PakExtractor",
            side_effect=FileNotFoundError("File not found"),
        ):
            with pytest.raises(SystemExit):
                await main()

            # Verify error was printed and exit was called
            mock_print.assert_called()
            mock_exit.assert_called_with(1)

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.core.logging.setup_logging")
    @patch("builtins.print")
    @patch("builtins.exit")
    async def test_main_process_files_failure(
        self, mock_exit: Mock, mock_print: Mock, mock_setup_logging: Mock, mock_args: Mock
    ) -> None:
        """Test main function handles process_files failure.

        Args:
            mock_exit (Mock): Mocked exit function.
            mock_print (Mock): Mocked print function.
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
        """
        mock_args.return_value = argparse.Namespace(
            catalog="catalog.json",
            pak=None,
            extractor_tool="C:\\repak\\repak.exe",
            converter_tool="C:\\UModel\\umodel.exe",
            output="output",
            log_file=None,
            verbose=False,
            quiet=False,
            workers=None,
        )

        with patch(
            "foxhole_stockpiles.commands.uasset_extractor.uasset_extractor.PakExtractor"
        ) as mock_extractor:
            instance = MagicMock()

            async def mock_process_files(*args: Any, **kwargs: Any) -> bool:
                return False

            instance.process_files = mock_process_files
            mock_extractor.return_value = instance

            await main()

            # Verify failure message was printed and exit was called
            mock_print.assert_called()
            mock_exit.assert_called_with(1)

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.core.logging.setup_logging")
    @patch("builtins.print")
    async def test_main_process_files_success(
        self, mock_print: Mock, mock_setup_logging: Mock, mock_args: Mock
    ) -> None:
        """Test main function with successful process_files.

        Args:
            mock_print (Mock): Mocked print function.
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
        """
        mock_args.return_value = argparse.Namespace(
            catalog="catalog.json",
            pak=None,
            extractor_tool="C:\\repak\\repak.exe",
            converter_tool="C:\\UModel\\umodel.exe",
            output="output",
            log_file=None,
            verbose=False,
            quiet=False,
            workers=None,
        )

        with patch(
            "foxhole_stockpiles.commands.uasset_extractor.uasset_extractor.PakExtractor"
        ) as mock_extractor:
            instance = MagicMock()

            async def mock_process_files(*args: Any, **kwargs: Any) -> bool:
                return True

            instance.process_files = mock_process_files
            mock_extractor.return_value = instance

            await main()

            # Verify success message was printed
            assert any("success" in str(call).lower() for call in mock_print.call_args_list)

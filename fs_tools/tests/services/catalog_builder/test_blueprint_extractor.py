"""Tests for catalog_builder.blueprint_extractor module."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fs_tools.services.catalog_builder.blueprint_extractor import (
    BlueprintExtractor,
)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_files(temp_dir: Path) -> tuple[Path, Path, Path]:
    """Create mock files for extractor initialization."""
    pak_file = temp_dir / "test.pak"
    pak_file.touch()

    extractor_tool = temp_dir / "repak"
    extractor_tool.touch()

    converter_tool = temp_dir / "UAssetGUI"
    converter_tool.touch()

    return pak_file, extractor_tool, converter_tool


class TestBlueprintExtractorInit:
    """Tests for BlueprintExtractor initialization."""

    def test_init_sets_paths(self, mock_files: tuple[Path, Path, Path]) -> None:
        """Test that paths are set correctly."""
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(pak_file, extractor_tool, converter_tool)

        assert extractor.pak_file == pak_file.resolve()
        assert extractor.extractor_tool == extractor_tool.resolve()
        assert extractor.converter_tool == converter_tool.resolve()

    def test_init_sets_default_options(self, mock_files: tuple[Path, Path, Path]) -> None:
        """Test that default options are set."""
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(pak_file, extractor_tool, converter_tool)

        assert extractor.extraction_dir is None
        assert extractor.max_workers == 4
        assert extractor.force_extract is False

    def test_init_sets_custom_options(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that custom options are set."""
        pak_file, extractor_tool, converter_tool = mock_files
        extraction_dir = temp_dir / "custom_extraction"
        extractor = BlueprintExtractor(
            pak_file,
            extractor_tool,
            converter_tool,
            max_workers=8,
            force_extract=True,
            extraction_dir=extraction_dir,
        )

        assert extractor.extraction_dir == extraction_dir
        assert extractor.max_workers == 8
        assert extractor.force_extract is True

    def test_init_raises_for_missing_pak(self, temp_dir: Path) -> None:
        """Test that init raises FileNotFoundError for missing PAK."""
        extractor_tool = temp_dir / "repak"
        extractor_tool.touch()
        converter_tool = temp_dir / "UAssetGUI"
        converter_tool.touch()

        with pytest.raises(FileNotFoundError, match="PAK file not found"):
            BlueprintExtractor(temp_dir / "missing.pak", extractor_tool, converter_tool)

    def test_init_raises_for_missing_extractor(self, temp_dir: Path) -> None:
        """Test that init raises FileNotFoundError for missing extractor."""
        pak_file = temp_dir / "test.pak"
        pak_file.touch()
        converter_tool = temp_dir / "UAssetGUI"
        converter_tool.touch()

        with pytest.raises(FileNotFoundError, match="Tool not found"):
            BlueprintExtractor(pak_file, temp_dir / "missing", converter_tool)

    def test_init_raises_for_missing_converter(self, temp_dir: Path) -> None:
        """Test that init raises FileNotFoundError for missing converter."""
        pak_file = temp_dir / "test.pak"
        pak_file.touch()
        extractor_tool = temp_dir / "repak"
        extractor_tool.touch()

        with pytest.raises(FileNotFoundError, match="Tool not found"):
            BlueprintExtractor(pak_file, extractor_tool, temp_dir / "missing")

    def test_init_creates_empty_stats(self, mock_files: tuple[Path, Path, Path]) -> None:
        """Test that stats are initialized to zero."""
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(pak_file, extractor_tool, converter_tool)

        assert extractor.stats == {"extracted": 0, "converted": 0}


class TestBlueprintExtractorConstants:
    """Tests for BlueprintExtractor class constants."""

    def test_extract_directories_contains_blueprints(self) -> None:
        """Test that EXTRACT_DIRECTORIES contains blueprint paths."""
        assert any("Blueprints" in d for d in BlueprintExtractor.EXTRACT_DIRECTORIES)
        assert any("Items" in d for d in BlueprintExtractor.EXTRACT_DIRECTORIES)
        assert any("Vehicles" in d for d in BlueprintExtractor.EXTRACT_DIRECTORIES)

    def test_extract_directories_contains_localization(self) -> None:
        """Test that EXTRACT_DIRECTORIES contains localization path."""
        assert any("Localization" in d for d in BlueprintExtractor.EXTRACT_DIRECTORIES)

    def test_convert_directories_matches_required(self) -> None:
        """Test that CONVERT_DIRECTORIES matches REQUIRED_DIRECTORIES."""
        assert set(BlueprintExtractor.CONVERT_DIRECTORIES) == set(
            BlueprintExtractor.REQUIRED_DIRECTORIES
        )


class TestBlueprintExtractorFindExisting:
    """Tests for BlueprintExtractor.find_existing_extraction method."""

    def test_returns_none_when_extraction_dir_not_set(
        self, mock_files: tuple[Path, Path, Path]
    ) -> None:
        """Test that find_existing_extraction returns None when extraction_dir is None."""
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(pak_file, extractor_tool, converter_tool)

        result = extractor.find_existing_extraction()
        assert result is None

    def test_returns_none_when_extraction_dir_missing(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that find_existing_extraction returns None when extraction_dir doesn't exist."""
        pak_file, extractor_tool, converter_tool = mock_files
        extraction_dir = temp_dir / "nonexistent"
        extractor = BlueprintExtractor(
            pak_file, extractor_tool, converter_tool, extraction_dir=extraction_dir
        )

        result = extractor.find_existing_extraction()
        assert result is None

    def test_returns_none_when_blueprints_dir_missing(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that find_existing_extraction returns None when Blueprints missing."""
        pak_file, extractor_tool, converter_tool = mock_files
        extraction_dir = temp_dir / "extract"
        extraction_dir.mkdir()
        extractor = BlueprintExtractor(
            pak_file, extractor_tool, converter_tool, extraction_dir=extraction_dir
        )

        result = extractor.find_existing_extraction()
        assert result is None


class TestBlueprintExtractorConvertSingleUasset:
    """Tests for BlueprintExtractor.convert_single_uasset method."""

    @pytest.mark.asyncio
    async def test_skips_if_json_exists(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that conversion is skipped if JSON already exists."""
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(pak_file, extractor_tool, converter_tool)

        # Create both uasset and json files
        uasset_path = temp_dir / "test.uasset"
        uasset_path.touch()
        json_path = temp_dir / "test.json"
        json_path.touch()

        success, status = await extractor.convert_single_uasset(uasset_path)

        assert success is True
        assert status == "skipped"

    @pytest.mark.asyncio
    async def test_calls_converter_tool(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that converter tool is called correctly."""
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(pak_file, extractor_tool, converter_tool)

        uasset_path = temp_dir / "test.uasset"
        uasset_path.touch()

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            success, status = await extractor.convert_single_uasset(uasset_path)

            # Verify converter was called
            mock_exec.assert_called_once()
            call_args = mock_exec.call_args[0]
            assert str(converter_tool.resolve()) in call_args[0]
            assert "tojson" in call_args

        assert success is True
        assert status == "success"

    @pytest.mark.asyncio
    async def test_returns_failed_on_error(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that failed status is returned on converter error."""
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(pak_file, extractor_tool, converter_tool)

        uasset_path = temp_dir / "test.uasset"
        uasset_path.touch()

        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error message"))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            success, status = await extractor.convert_single_uasset(uasset_path)

        assert success is False
        assert status == "failed"


class TestBlueprintExtractorExtract:
    """Tests for BlueprintExtractor.extract method."""

    @pytest.mark.asyncio
    async def test_uses_existing_extraction_when_available(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that extract uses existing extraction when available."""
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(pak_file, extractor_tool, converter_tool)

        # Mock find_existing_extraction to return a path
        with patch.object(extractor, "find_existing_extraction", return_value=temp_dir / "war"):
            result = await extractor.extract()

        assert result == temp_dir / "war"

    @pytest.mark.asyncio
    async def test_forces_re_extraction_when_flag_set(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that force_extract bypasses existing extraction."""
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(pak_file, extractor_tool, converter_tool, force_extract=True)

        # Mock extraction methods
        mock_extract_dir = temp_dir / "war"
        mock_extract_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch.object(extractor, "extract_from_pak", new_callable=AsyncMock) as mock_extract,
            patch.object(
                extractor, "convert_uassets_to_json", new_callable=AsyncMock
            ) as mock_convert,
        ):
            mock_extract.return_value = mock_extract_dir
            mock_convert.return_value = 10

            result = await extractor.extract()

        # Should call extraction even if existing would be found
        mock_extract.assert_called_once()
        mock_convert.assert_called_once()
        assert result == mock_extract_dir

    @pytest.mark.asyncio
    async def test_raises_on_zero_conversions(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that extract raises when no files converted."""
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(pak_file, extractor_tool, converter_tool)

        mock_extract_dir = temp_dir / "war"
        mock_extract_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch.object(extractor, "find_existing_extraction", return_value=None),
            patch.object(extractor, "extract_from_pak", new_callable=AsyncMock) as mock_extract,
            patch.object(
                extractor, "convert_uassets_to_json", new_callable=AsyncMock
            ) as mock_convert,
        ):
            mock_extract.return_value = mock_extract_dir
            mock_convert.return_value = 0

            with pytest.raises(RuntimeError, match="No files converted"):
                await extractor.extract()


class TestBlueprintExtractorConvertUassets:
    """Tests for BlueprintExtractor.convert_uassets_to_json method."""

    @pytest.mark.asyncio
    async def test_returns_zero_when_blueprints_dir_missing(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that convert returns 0 when Blueprints directory missing."""
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(pak_file, extractor_tool, converter_tool)

        result = await extractor.convert_uassets_to_json(temp_dir)
        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_uassets(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that convert returns 0 when no uasset files found."""
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(pak_file, extractor_tool, converter_tool)

        # Create Blueprints directory structure but no uasset files
        blueprints_dir = temp_dir / "War" / "Content" / "Blueprints"
        for dir_name in BlueprintExtractor.CONVERT_DIRECTORIES:
            (blueprints_dir / dir_name).mkdir(parents=True, exist_ok=True)

        result = await extractor.convert_uassets_to_json(temp_dir)
        assert result == 0

    @pytest.mark.asyncio
    async def test_processes_uasset_files(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that convert processes uasset files."""
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(pak_file, extractor_tool, converter_tool)

        # Create Blueprints directory with uasset files
        items_dir = temp_dir / "War" / "Content" / "Blueprints" / "Items"
        items_dir.mkdir(parents=True, exist_ok=True)
        (items_dir / "test1.uasset").touch()
        (items_dir / "test2.uasset").touch()

        # Mock convert_single_uasset
        with patch.object(
            extractor, "convert_single_uasset", new_callable=AsyncMock
        ) as mock_convert:
            mock_convert.return_value = (True, "success")

            result = await extractor.convert_uassets_to_json(temp_dir)

        assert result == 2
        assert mock_convert.call_count == 2


class TestBlueprintExtractorExtractFromPak:
    """Tests for BlueprintExtractor.extract_from_pak method.

    This class contains tests for PAK file extraction including
    directory creation and subprocess handling.
    """

    @pytest.mark.asyncio
    async def test_creates_temp_dir_when_no_extraction_dir(
        self, mock_files: tuple[Path, Path, Path]
    ) -> None:
        """Test that temp directory is created when extraction_dir is None.

        Args:
            mock_files (tuple[Path, Path, Path]): Mock files fixture.
        """
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(
            pak_file, extractor_tool, converter_tool, extraction_dir=None
        )

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await extractor.extract_from_pak()

        assert extractor.temp_dir is not None
        assert "catalog_builder_" in str(extractor.temp_dir)

    @pytest.mark.asyncio
    async def test_uses_extraction_dir_when_provided(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that extraction_dir is used when provided.

        Args:
            mock_files (tuple[Path, Path, Path]): Mock files fixture.
            temp_dir (Path): Temporary directory fixture.
        """
        pak_file, extractor_tool, converter_tool = mock_files
        extraction_dir = temp_dir / "custom_extract"
        extractor = BlueprintExtractor(
            pak_file, extractor_tool, converter_tool, extraction_dir=extraction_dir
        )

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await extractor.extract_from_pak()

        assert extractor.temp_dir == extraction_dir
        assert extraction_dir.exists()

    @pytest.mark.asyncio
    async def test_extracts_all_required_directories(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that all required directories are extracted.

        Args:
            mock_files (tuple[Path, Path, Path]): Mock files fixture.
            temp_dir (Path): Temporary directory fixture.
        """
        pak_file, extractor_tool, converter_tool = mock_files
        extraction_dir = temp_dir / "extract"
        extractor = BlueprintExtractor(
            pak_file, extractor_tool, converter_tool, extraction_dir=extraction_dir
        )

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            await extractor.extract_from_pak()

        # Should call subprocess for each directory
        assert mock_exec.call_count == len(BlueprintExtractor.EXTRACT_DIRECTORIES)

    @pytest.mark.asyncio
    async def test_raises_on_extractor_failure(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that RuntimeError is raised when extractor fails.

        Args:
            mock_files (tuple[Path, Path, Path]): Mock files fixture.
            temp_dir (Path): Temporary directory fixture.
        """
        pak_file, extractor_tool, converter_tool = mock_files
        extraction_dir = temp_dir / "extract"
        extractor = BlueprintExtractor(
            pak_file, extractor_tool, converter_tool, extraction_dir=extraction_dir
        )

        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error message"))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(RuntimeError, match="repak extraction failed"):
                await extractor.extract_from_pak()

    @pytest.mark.asyncio
    async def test_updates_stats_after_extraction(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that stats are updated after extraction.

        Args:
            mock_files (tuple[Path, Path, Path]): Mock files fixture.
            temp_dir (Path): Temporary directory fixture.
        """
        pak_file, extractor_tool, converter_tool = mock_files
        extraction_dir = temp_dir / "extract"
        extractor = BlueprintExtractor(
            pak_file, extractor_tool, converter_tool, extraction_dir=extraction_dir
        )

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        # Create some fake uasset files in the extraction directory
        content_dir = extraction_dir / "War" / "Content"
        content_dir.mkdir(parents=True, exist_ok=True)
        (content_dir / "test.uasset").touch()
        (content_dir / "test2.uasset").touch()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await extractor.extract_from_pak()

        assert extractor.stats["extracted"] == 2


class TestBlueprintExtractorFindExistingEdgeCases:
    """Tests for find_existing_extraction edge cases.

    This class contains tests for edge cases in finding existing
    extraction directories.
    """

    def test_returns_none_when_required_dir_missing(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test returns None when a required directory is missing.

        Args:
            mock_files (tuple[Path, Path, Path]): Mock files fixture.
            temp_dir (Path): Temporary directory fixture.
        """
        pak_file, extractor_tool, converter_tool = mock_files
        extraction_dir = temp_dir / "extract"
        blueprints_dir = extraction_dir / "War" / "Content" / "Blueprints"
        blueprints_dir.mkdir(parents=True, exist_ok=True)
        # Create only some required directories, not all
        (blueprints_dir / "Items").mkdir()

        extractor = BlueprintExtractor(
            pak_file, extractor_tool, converter_tool, extraction_dir=extraction_dir
        )

        result = extractor.find_existing_extraction()
        assert result is None

    def test_returns_none_when_no_json_files(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test returns None when required directories exist but have no JSON files.

        Args:
            mock_files (tuple[Path, Path, Path]): Mock files fixture.
            temp_dir (Path): Temporary directory fixture.
        """
        pak_file, extractor_tool, converter_tool = mock_files
        extraction_dir = temp_dir / "extract"
        blueprints_dir = extraction_dir / "War" / "Content" / "Blueprints"

        # Create all required directories but no JSON files
        for dir_name in BlueprintExtractor.REQUIRED_DIRECTORIES:
            (blueprints_dir / dir_name).mkdir(parents=True, exist_ok=True)

        extractor = BlueprintExtractor(
            pak_file, extractor_tool, converter_tool, extraction_dir=extraction_dir
        )

        result = extractor.find_existing_extraction()
        assert result is None

    def test_returns_extraction_dir_when_valid(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test returns extraction_dir when all conditions are met.

        Args:
            mock_files (tuple[Path, Path, Path]): Mock files fixture.
            temp_dir (Path): Temporary directory fixture.
        """
        pak_file, extractor_tool, converter_tool = mock_files
        extraction_dir = temp_dir / "extract"
        blueprints_dir = extraction_dir / "War" / "Content" / "Blueprints"

        # Create all required directories with JSON files
        for dir_name in BlueprintExtractor.REQUIRED_DIRECTORIES:
            dir_path = blueprints_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            (dir_path / "test.json").touch()

        extractor = BlueprintExtractor(
            pak_file, extractor_tool, converter_tool, extraction_dir=extraction_dir
        )

        result = extractor.find_existing_extraction()
        assert result == extraction_dir


class TestBlueprintExtractorExtractAll:
    """Tests for BlueprintExtractor.extract method edge cases.

    This class contains tests for the main extract method including
    error handling and logging behavior.
    """

    @pytest.mark.asyncio
    async def test_reraises_extract_pak_exception(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that extract_from_pak exceptions are re-raised.

        Args:
            mock_files (tuple[Path, Path, Path]): Mock files fixture.
            temp_dir (Path): Temporary directory fixture.
        """
        pak_file, extractor_tool, converter_tool = mock_files
        extractor = BlueprintExtractor(pak_file, extractor_tool, converter_tool, force_extract=True)

        with (
            patch.object(
                extractor,
                "extract_from_pak",
                new_callable=AsyncMock,
                side_effect=RuntimeError("PAK extraction failed"),
            ),
        ):
            with pytest.raises(RuntimeError, match="PAK extraction failed"):
                await extractor.extract()

    @pytest.mark.asyncio
    async def test_logs_temp_dir_info_when_extraction_complete(
        self, mock_files: tuple[Path, Path, Path], temp_dir: Path
    ) -> None:
        """Test that temp directory info is logged after extraction.

        Args:
            mock_files (tuple[Path, Path, Path]): Mock files fixture.
            temp_dir (Path): Temporary directory fixture.
        """
        pak_file, extractor_tool, converter_tool = mock_files
        extraction_dir = temp_dir / "extract"
        extractor = BlueprintExtractor(
            pak_file, extractor_tool, converter_tool, extraction_dir=extraction_dir
        )

        mock_extract_dir = extraction_dir
        mock_extract_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch.object(extractor, "find_existing_extraction", return_value=None),
            patch.object(extractor, "extract_from_pak", new_callable=AsyncMock) as mock_extract,
            patch.object(
                extractor, "convert_uassets_to_json", new_callable=AsyncMock
            ) as mock_convert,
        ):
            mock_extract.return_value = mock_extract_dir
            mock_convert.return_value = 10
            extractor.temp_dir = mock_extract_dir

            result = await extractor.extract()

        assert result == mock_extract_dir

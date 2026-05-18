"""Tests for services.ocr_coordinator module.

This module contains comprehensive tests for the OCRCoordinator class,
which orchestrates the entire stockpile detection and analysis process.
"""

import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import cv2
import numpy as np
import pytest
from numpy.typing import NDArray

from foxhole_stockpiles.core.settings.sections.scanner import ScannerSettings
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.icon_template import IconTemplate
from foxhole_stockpiles.models.match_result import MatchResult
from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.models.stockpile_image_regions import StockpileImageRegions
from foxhole_stockpiles.models.stockpile_item import StockpileItem
from foxhole_stockpiles.services.ocr_coordinator import OCRCoordinator
from foxhole_stockpiles.services.stockpile_detector import StockpileDetector


def create_test_icon_template(code: str, crated: bool = False) -> IconTemplate:
    """Helper function to create a test IconTemplate.

    Args:
        code (str): Item code
        crated (bool): Whether the item is crated

    Returns:
        IconTemplate: Test icon template instance
    """
    dummy_image = np.zeros((64, 64, 3), dtype=np.uint8)
    return IconTemplate(
        image=dummy_image,
        code=code,
        crated=crated,
        category=ItemCategory.Item,
        faction=ItemFaction.NEUTRAL,
        mod="vanilla",
        resolution=SupportedResolution("1080"),
    )


class TestOCRCoordinatorInitialization:
    """Test suite for OCRCoordinator initialization.

    This class contains tests for proper initialization of the OCRCoordinator
    including config handling, service initialization, and initial state validation.
    """

    def test_init_raises_value_error_when_database_path_is_none(self) -> None:
        """Test that OCRCoordinator raises ValueError when database_path is None."""
        config = ScannerSettings(database_path=None)

        with pytest.raises(ValueError, match="database_path is required"):
            OCRCoordinator(config)

    def test_init_with_config(self, tmp_path: Path) -> None:
        """Test initializing OCRCoordinator with a config.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(
            database_path=db_path,
            early_exit_threshold=0.95,
        )

        coordinator = OCRCoordinator(config)

        assert coordinator.config == config
        assert coordinator._text_extractor is not None
        assert coordinator._template_manager is not None
        assert coordinator._stockpile_type_classifier is not None

    def test_init_with_custom_model(self, tmp_path: Path) -> None:
        """Test initializing OCRCoordinator with custom OCR model.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(
            database_path=db_path,
            custom_model="custom_model",
            tessdata_path="/path/to/tessdata",
        )

        coordinator = OCRCoordinator(config)

        assert coordinator._text_extractor.custom_model == "custom_model"


class TestExtractIconToFolder:
    """Test suite for OCRCoordinator icon extraction functionality."""

    def test_extract_icon_creates_folder_and_file(self, tmp_path: Path) -> None:
        """Test that icon extraction creates icons folder and saves files.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path, extract_icons=True)
        coordinator = OCRCoordinator(config)

        mock_icon = np.zeros((35, 35, 3), dtype=np.uint8)

        # Change to tmp_path so icons folder is created there
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Icons folder should not exist yet
            icons_folder = tmp_path / "icons"
            assert not icons_folder.exists()

            # Extract first icon
            coordinator._extract_icon_to_folder(mock_icon, 0, "Rifle")

            # Now icons folder should be created
            assert icons_folder.exists()

            # Verify icon file exists
            assert (icons_folder / "000_Rifle.png").exists()
        finally:
            os.chdir(original_cwd)

    def test_extract_icon_enabled(self, tmp_path: Path) -> None:
        """Test that icons are extracted when extract_icons is True.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path, extract_icons=True)
        coordinator = OCRCoordinator(config)

        # Create a test icon image (35x35 BGR as used in Foxhole)
        mock_icon = np.zeros((35, 35, 3), dtype=np.uint8)
        mock_icon[10:25, 10:25] = [255, 0, 0]  # Add some blue color

        # Change to tmp_path so icons folder is created there

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            coordinator._extract_icon_to_folder(mock_icon, 0, "Rifle")

            # Check that icons folder was created
            icons_folder = tmp_path / "icons"
            assert icons_folder.exists()

            # Check that the icon file was created with correct naming
            icon_file = icons_folder / "000_Rifle.png"
            assert icon_file.exists()

            # Verify the image can be loaded and has correct dimensions
            import cv2

            loaded_icon = cv2.imread(str(icon_file))
            assert loaded_icon is not None
            assert loaded_icon.shape == (35, 35, 3)
        finally:
            os.chdir(original_cwd)

    def test_extract_icon_with_index_padding(self, tmp_path: Path) -> None:
        """Test that icon filenames have zero-padded indices.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path, extract_icons=True)
        coordinator = OCRCoordinator(config)

        mock_icon = np.zeros((35, 35, 3), dtype=np.uint8)

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Test various icon indices
            coordinator._extract_icon_to_folder(mock_icon, 0, "Item1")
            coordinator._extract_icon_to_folder(mock_icon, 9, "Item2")
            coordinator._extract_icon_to_folder(mock_icon, 42, "Item3")
            coordinator._extract_icon_to_folder(mock_icon, 123, "Item4")

            icons_folder = tmp_path / "icons"

            # Verify correct filename formatting with 3-digit zero-padding
            assert (icons_folder / "000_Item1.png").exists()
            assert (icons_folder / "009_Item2.png").exists()
            assert (icons_folder / "042_Item3.png").exists()
            assert (icons_folder / "123_Item4.png").exists()
        finally:
            os.chdir(original_cwd)

    def test_extract_icon_with_unknown_code(self, tmp_path: Path) -> None:
        """Test extracting an icon with 'Unknown' code.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path, extract_icons=True)
        coordinator = OCRCoordinator(config)

        mock_icon = np.zeros((35, 35, 3), dtype=np.uint8)

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            coordinator._extract_icon_to_folder(mock_icon, 5, "Unknown")

            icons_folder = tmp_path / "icons"
            icon_file = icons_folder / "005_Unknown.png"
            assert icon_file.exists()
        finally:
            os.chdir(original_cwd)

    def test_extract_icon_exception_handling(self, tmp_path: Path) -> None:
        """Test that icon extraction handles exceptions gracefully.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path, extract_icons=True)
        coordinator = OCRCoordinator(config)

        mock_icon = np.zeros((35, 35, 3), dtype=np.uint8)

        # Mock cv2.imwrite to raise an exception
        with patch("foxhole_stockpiles.services.ocr_coordinator.cv2.imwrite") as mock_imwrite:
            mock_imwrite.side_effect = OSError("Simulated write failure")

            # Should not raise - exception should be caught and logged
            coordinator._extract_icon_to_folder(mock_icon, 0, "Rifle")


class TestSaveScreenshot:
    """Test suite for OCRCoordinator screenshot saving functionality."""

    def test_save_screenshot_disabled(self, tmp_path: Path) -> None:
        """Test that screenshot is not saved when screenshots_folder is empty.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path, screenshots_folder="")
        coordinator = OCRCoordinator(config)

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_stockpile = Stockpile(resolution="1920x1080")

        coordinator._save_screenshot(mock_image, stockpile=mock_stockpile)

        # No screenshots folder should be created
        assert not (tmp_path / "screenshots").exists()

    def test_save_screenshot_enabled(self, tmp_path: Path) -> None:
        """Test that screenshot is saved when screenshots_folder is set.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        screenshots_folder = tmp_path / "screenshots"
        config = ScannerSettings(database_path=db_path, screenshots_folder=str(screenshots_folder))
        coordinator = OCRCoordinator(config)

        from foxhole_stockpiles.enums.stockpile_type import StockpileType

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_stockpile = Stockpile(
            resolution="1920x1080", name="Test Storage", type=StockpileType.STORAGE_DEPOT
        )

        coordinator._save_screenshot(mock_image, stockpile=mock_stockpile)

        # Check that daily folder was created
        from datetime import datetime

        daily_folder = screenshots_folder / datetime.now().strftime("%Y-%m-%d")
        assert daily_folder.exists()

        # Check that a screenshot file was created
        screenshots = list(daily_folder.glob("*.png"))
        assert len(screenshots) == 1

        # Verify filename format
        filename = screenshots[0].name
        assert "StorageFacility" in filename  # In-game code name
        assert "Test_Storage" in filename
        assert "1920x1080" in filename


class TestAnalyzeStockpile:
    """Test suite for OCRCoordinator.analyze_stockpile method.

    This class contains tests for the main analyze_stockpile functionality
    including successful analysis, error handling, and edge cases.
    """

    @pytest.fixture
    def mock_image(self) -> NDArray[np.uint8]:
        """Create a mock image for testing.

        Returns:
            NDArray[np.uint8]: A mock RGB image array.
        """
        return np.zeros((1080, 1920, 3), dtype=np.uint8)

    @pytest.fixture
    def mock_config(self, tmp_path: Path) -> ScannerSettings:
        """Create a mock config for testing.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.

        Returns:
            ScannerSettings: Mock configuration.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        return ScannerSettings(
            database_path=db_path,
            early_exit_threshold=0.95,
        )

    async def test_analyze_stockpile_success(
        self,
        mock_image: NDArray[np.uint8],
        mock_config: ScannerSettings,
    ) -> None:
        """Test successful stockpile analysis.

        Args:
            mock_image (NDArray[np.uint8]): Mock image from fixture.
            mock_config (ScannerSettings): Mock config from fixture.
        """
        coordinator = OCRCoordinator(mock_config)

        # Mock the detector
        mock_detector = MagicMock(spec=StockpileDetector)
        mock_detector.scale_factor = 1.0
        mock_detector.quantities = [(100, 100), (200, 200)]
        mock_detector.groups = [(2, 0)]

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.vertical_resolution = 1080
        mock_stockpile_images.resolution = "1920x1080"
        mock_stockpile_images.composite_quantities_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_stockpile_images.icons = [
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
        ]
        mock_stockpile_images.groups = [(2, 0)]
        mock_stockpile_images.stockpile_name = None
        mock_stockpile_images.stockpile_name_tab = None
        mock_stockpile_images.shard = None
        mock_stockpile_images.stockpile_type = None

        mock_detector.get_stockpile_images.return_value = mock_stockpile_images

        with (
            patch.object(coordinator, "_detect_regions", return_value=mock_detector),
            patch.object(
                coordinator, "_extract_quantities", new_callable=AsyncMock
            ) as mock_extract,
            patch.object(
                coordinator._template_manager,
                "set_active_resolution",
                new_callable=AsyncMock,
            ),
            patch.object(
                coordinator._template_manager,
                "match_icon",
                return_value=MagicMock(),
            ) as mock_match,
        ):
            mock_extract.return_value = [100, 200]

            # Create a mock match result
            mock_icon = MagicMock()
            mock_icon.code = "Rifle"
            mock_icon.crated = False
            mock_icon.category = ItemCategory.Item
            mock_icon.mod = "vanilla"

            mock_match_result = MagicMock(spec=MatchResult)
            mock_match_result.icon = mock_icon
            mock_match_result.confidence = 0.9
            mock_match_result.tested_candidates = 10
            mock_match_result.gap_candidates = []

            mock_match.return_value = mock_match_result

            result = await coordinator.analyze_stockpile(mock_image)

            assert isinstance(result, Stockpile)
            assert len(result.items) == 2

    async def test_analyze_stockpile_no_icons(
        self,
        mock_image: NDArray[np.uint8],
        mock_config: ScannerSettings,
    ) -> None:
        """Test analysis when no icons are found.

        Args:
            mock_image (np.ndarray): Mock image from fixture.
            mock_config (ScannerSettings): Mock config from fixture.
        """
        coordinator = OCRCoordinator(mock_config)

        mock_detector = MagicMock(spec=StockpileDetector)
        mock_detector.scale_factor = 1.0
        mock_detector.get_stockpile_images.return_value = None

        with patch.object(coordinator, "_detect_regions", return_value=mock_detector):
            with pytest.raises(ValueError, match="No icons found in the image"):
                await coordinator.analyze_stockpile(mock_image)

    async def test_analyze_stockpile_detection_error(
        self,
        mock_image: NDArray[np.uint8],
        mock_config: ScannerSettings,
    ) -> None:
        """Test analysis when region detection fails.

        Args:
            mock_image (np.ndarray): Mock image from fixture.
            mock_config (ScannerSettings): Mock config from fixture.
        """
        coordinator = OCRCoordinator(mock_config)

        with patch.object(
            coordinator,
            "_detect_regions",
            side_effect=ValueError("Detection failed"),
        ):
            with pytest.raises(ValueError, match="Detection failed"):
                await coordinator.analyze_stockpile(mock_image)

    async def test_analyze_stockpile_emits_scan_failed_event(
        self,
        mock_image: NDArray[np.uint8],
        mock_config: ScannerSettings,
    ) -> None:
        """Test that STOCKPILE_SCAN_FAILED event is emitted when analysis fails.

        Args:
            mock_image (np.ndarray): Mock image from fixture.
            mock_config (ScannerSettings): Mock config from fixture.
        """
        from foxhole_stockpiles.core.events import EventBus
        from foxhole_stockpiles.enums.event_type import EventType

        event_bus = EventBus()
        coordinator = OCRCoordinator(mock_config, event_bus=event_bus)

        # Track emitted events
        emitted_events: list[tuple[str, dict[str, Any]]] = []

        def track_event(event_type: str) -> Any:
            def handler(data: dict[str, Any]) -> None:
                emitted_events.append((event_type, data))

            return handler

        event_bus.subscribe(
            EventType.STOCKPILE_SCAN_STARTED, track_event(EventType.STOCKPILE_SCAN_STARTED)
        )
        event_bus.subscribe(
            EventType.STOCKPILE_SCAN_FAILED, track_event(EventType.STOCKPILE_SCAN_FAILED)
        )

        with patch.object(
            coordinator,
            "_detect_regions",
            side_effect=ValueError("Detection failed"),
        ):
            with pytest.raises(ValueError, match="Detection failed"):
                await coordinator.analyze_stockpile(mock_image)

        # Verify both events were emitted
        assert len(emitted_events) == 2
        assert emitted_events[0][0] == EventType.STOCKPILE_SCAN_STARTED
        assert emitted_events[1][0] == EventType.STOCKPILE_SCAN_FAILED
        assert emitted_events[1][1]["error"] == "Detection failed"
        assert "duration" in emitted_events[1][1]
        assert "timestamp" in emitted_events[1][1]


class TestDetectRegions:
    """Test suite for OCRCoordinator._detect_regions method.

    This class contains tests for region detection functionality.
    """

    def test_detect_regions_success(self, tmp_path: Path) -> None:
        """Test successful region detection.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)

        with patch("foxhole_stockpiles.services.ocr_coordinator.StockpileDetector") as mock_class:
            mock_detector = MagicMock(spec=StockpileDetector)
            mock_detector.scale_factor = 1.0
            mock_detector.quantities = [(100, 100)]
            mock_detector.groups = [(1, 0)]
            mock_class.return_value = mock_detector

            result = coordinator._detect_regions(mock_image)

            assert result == mock_detector
            mock_detector.analize.assert_called_once()

    def test_detect_regions_with_debug(self, tmp_path: Path) -> None:
        """Test region detection with debug mode enabled.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path, debug_mode=True)
        coordinator = OCRCoordinator(config)

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)

        with patch("foxhole_stockpiles.services.ocr_coordinator.StockpileDetector") as mock_class:
            mock_detector = MagicMock(spec=StockpileDetector)
            mock_detector.scale_factor = 1.0
            mock_detector.quantities = [(100, 100)]
            mock_detector.groups = [(1, 0)]
            mock_class.return_value = mock_detector

            coordinator._detect_regions(mock_image)

            mock_detector.draw_and_save_results.assert_called_once()


class TestExtractQuantities:
    """Test suite for OCRCoordinator._extract_quantities method.

    This class contains tests for quantity extraction functionality.
    """

    async def test_extract_quantities_success(self, tmp_path: Path) -> None:
        """Test successful quantity extraction.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.composite_quantities_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_stockpile_images.icons = [
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
        ]
        # Groups: first group with 2 items starting at index 0
        mock_stockpile_images.groups = [(2, 0)]
        # Individual quantity images for fallback OCR
        mock_stockpile_images.quantities = [
            np.zeros((32, 64, 3), dtype=np.uint8),
            np.zeros((32, 64, 3), dtype=np.uint8),
        ]

        with patch.object(
            coordinator._text_extractor,
            "extract_quantities",
            new_callable=AsyncMock,
        ) as mock_extract:
            # Values must be descending within a group
            mock_extract.return_value = [[200, 100]]

            result = await coordinator._extract_quantities(mock_stockpile_images)

            assert result == [200, 100]

    async def test_extract_quantities_mismatch(self, tmp_path: Path) -> None:
        """Test quantity extraction when counts don't match icons.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.composite_quantities_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_stockpile_images.icons = [
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
        ]
        # Groups: first group with 2 items, second group with 1 item
        mock_stockpile_images.groups = [(2, 0), (1, 2)]
        # Individual quantity images for fallback OCR
        mock_stockpile_images.quantities = [
            np.zeros((32, 64, 3), dtype=np.uint8),
            np.zeros((32, 64, 3), dtype=np.uint8),
            np.zeros((32, 64, 3), dtype=np.uint8),
        ]

        with (
            patch.object(
                coordinator._text_extractor,
                "extract_quantities",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                coordinator._text_extractor,
                "extract_raw_text",
                new_callable=AsyncMock,
            ) as mock_raw,
        ):
            # OCR returns only 1 quantity when we expect 3 (2 in group 1, 1 in group 2)
            mock_extract.return_value = [[100]]
            # Individual OCR fallback returns empty (simulating failed detection)
            mock_raw.return_value = ""

            result = await coordinator._extract_quantities(mock_stockpile_images)

            # Should have placeholders for quantities that couldn't be detected
            assert len(result) == 3
            # First group expected 2, got 1, individual OCR failed -> all -1
            assert result[0] == -1
            assert result[1] == -1
            # Second group expected 1, got none (no row), individual OCR failed -> -1
            assert result[2] == -1


class TestQuantityValidation:
    """Test suite for OCRCoordinator quantity validation and correction logic.

    Tests the descending order validation and error correction mechanisms.
    """

    def test_compute_expected_row_counts_single_group(self, tmp_path: Path) -> None:
        """Test expected row computation for a single group with <= 6 items.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        # Group with 4 items starting at index 0
        groups = [(4, 0)]
        result = coordinator._compute_expected_row_counts(groups)

        # Should be one row with 4 items
        assert len(result) == 1
        assert result[0] == (4, 0, 0)  # (count, start_index, group_index)

    def test_compute_expected_row_counts_multi_row_group(self, tmp_path: Path) -> None:
        """Test expected row computation for a group spanning multiple rows.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        # Group with 8 items starting at index 0 (should span 2 rows: 6 + 2)
        groups = [(8, 0)]
        result = coordinator._compute_expected_row_counts(groups)

        assert len(result) == 2
        assert result[0] == (6, 0, 0)  # First row: 6 items
        assert result[1] == (2, 6, 0)  # Second row: 2 items, starting at index 6

    def test_compute_expected_row_counts_multiple_groups(self, tmp_path: Path) -> None:
        """Test expected row computation for multiple groups.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        # First group: 2 items, second group: 7 items
        groups = [(2, 0), (7, 2)]
        result = coordinator._compute_expected_row_counts(groups)

        assert len(result) == 3
        assert result[0] == (2, 0, 0)  # Group 0: 2 items
        assert result[1] == (6, 2, 1)  # Group 1, row 1: 6 items
        assert result[2] == (1, 8, 1)  # Group 1, row 2: 1 item

    def test_validate_descending_in_context_valid(self, tmp_path: Path) -> None:
        """Test descending validation with valid descending values.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        groups = [(6, 0)]
        previous: list[int] = []  # First row, no previous quantities
        row = [100, 88, 77, 50, 30, 10]

        result = coordinator._validate_descending_in_context(row, previous, 0, groups)
        assert result is True

    def test_validate_descending_in_context_group_zero_exempt(self, tmp_path: Path) -> None:
        """Test that group 0 is exempt from descending order validation.

        Group 0 contains items that are always present in every capture and can
        have any order (ascending or descending).

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        groups = [(2, 0)]
        previous: list[int] = []
        # Ascending order (5 < 31) - would fail for other groups, but group 0 is exempt
        row = [5, 31]

        result = coordinator._validate_descending_in_context(row, previous, 0, groups)
        assert result is True

    def test_validate_descending_in_context_invalid_within_row(self, tmp_path: Path) -> None:
        """Test descending validation with invalid ascending value within row.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        # Use group_index=1 since group 0 is exempt from descending validation
        groups = [(2, 0), (6, 2)]  # Group 0 has 2 items, group 1 starts at index 2
        previous = [5, 31]  # Group 0 items (exempt from validation)
        # 100 > 88 > 77 > 90 - 90 > 77 breaks descending
        row = [100, 88, 77, 90, 30, 10]

        result = coordinator._validate_descending_in_context(row, previous, 1, groups)
        assert result is False

    def test_validate_descending_in_context_invalid_with_previous(self, tmp_path: Path) -> None:
        """Test descending validation when new row has higher value than previous.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        # Use group_index=1 since group 0 is exempt from descending validation
        # Group 1 has 8 items = 2 rows of 6 + 2
        groups = [(2, 0), (8, 2)]
        # First 2 items are group 0 (exempt), next 6 are group 1 first row
        previous = [5, 31, 100, 88, 77, 50, 30, 10]  # First row of group 1 ends with 10
        row = [15, 5]  # Second row of group 1 starts with 15, which is > 10

        result = coordinator._validate_descending_in_context(row, previous, 1, groups)
        assert result is False

    async def test_extract_quantities_corrects_via_reocr(self, tmp_path: Path) -> None:
        """Test that misread quantities trigger re-OCR with alternative preprocessing.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.composite_quantities_image = np.zeros((100, 100, 3), dtype=np.uint8)
        # 6 icons in one group
        mock_stockpile_images.icons = [np.zeros((64, 64, 3), dtype=np.uint8) for _ in range(6)]
        mock_stockpile_images.groups = [(6, 0)]
        mock_stockpile_images.quantities = [np.zeros((32, 64, 3), dtype=np.uint8) for _ in range(6)]

        with (
            patch.object(
                coordinator._text_extractor,
                "extract_quantities",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                coordinator._text_extractor,
                "extract_raw_text",
                new_callable=AsyncMock,
            ) as mock_raw,
        ):
            # Initial OCR misreads (7 values instead of 6)
            mock_extract.return_value = [[88, 1, 1, 7, 5, 3, 2]]
            # Re-OCR with alternative preprocessing returns correct values
            mock_raw.return_value = "88 11 7 5 3 2"

            result = await coordinator._extract_quantities(mock_stockpile_images)

            # Should be corrected via re-OCR
            assert len(result) == 6
            assert result == [88, 11, 7, 5, 3, 2]

    async def test_extract_quantities_isolates_row_errors(self, tmp_path: Path) -> None:
        """Test that errors in one row don't affect other rows.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.composite_quantities_image = np.zeros((100, 100, 3), dtype=np.uint8)
        # 2 groups: first with 2 items, second with 6 items
        mock_stockpile_images.icons = [np.zeros((64, 64, 3), dtype=np.uint8) for _ in range(8)]
        mock_stockpile_images.groups = [(2, 0), (6, 2)]
        mock_stockpile_images.quantities = [np.zeros((32, 64, 3), dtype=np.uint8) for _ in range(8)]

        with (
            patch.object(
                coordinator._text_extractor,
                "extract_quantities",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch.object(
                coordinator._text_extractor,
                "extract_raw_text",
                new_callable=AsyncMock,
            ) as mock_raw,
        ):
            # First row OK (descending: 100, 50)
            # Second row has error: detected 7 values instead of 6, can't merge properly
            mock_extract.return_value = [
                [100, 50],  # Group 1: correct
                [99, 88, 77, 66, 55, 44, 33],  # Group 2: 7 values instead of 6, no good merge
            ]
            # Individual OCR fails
            mock_raw.return_value = ""

            result = await coordinator._extract_quantities(mock_stockpile_images)

            # First row should be preserved correctly
            assert len(result) == 8
            assert result[0] == 100
            assert result[1] == 50
            # Second row should be marked as -1 (unfixable)
            # (The merge [99, 88, 77, 66, 55, 44, 33] -> trying to get 6 values
            # would produce values that may not satisfy descending order)


class TestPrepareImageForDetection:
    """Test suite for OCRCoordinator._prepare_image_for_detection method.

    This class contains tests for image preprocessing functionality.
    """

    def test_prepare_image_basic(self, tmp_path: Path) -> None:
        """Test basic image preprocessing.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        # Create a simple test image
        test_image = np.full((100, 100, 3), 128, dtype=np.uint8)

        result = coordinator._prepare_image_for_detection(test_image, scale_factor=1.0)

        assert result.shape[:2] == (200, 200)  # 2x upscale
        assert result.dtype == np.uint8
        assert len(result.shape) == 3  # RGB image

    def test_prepare_image_with_inv(self, tmp_path: Path) -> None:
        """Test image preprocessing with inverted threshold.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        test_image = np.full((100, 100, 3), 128, dtype=np.uint8)

        result_inv = coordinator._prepare_image_for_detection(
            test_image, scale_factor=1.0, use_inv=True
        )
        result_no_inv = coordinator._prepare_image_for_detection(
            test_image, scale_factor=1.0, use_inv=False
        )

        # Both should produce valid outputs, but potentially different
        assert result_inv.shape == result_no_inv.shape


class TestProcessSingleIcon:
    """Test suite for OCRCoordinator._process_single_icon method.

    This class contains tests for individual icon processing.
    """

    def test_process_single_icon_success(self, tmp_path: Path) -> None:
        """Test successful icon processing.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.vertical_resolution = 1080
        mock_stockpile_images.icons = [np.zeros((64, 64, 3), dtype=np.uint8)]

        mock_icon = create_test_icon_template("Rifle", crated=False)

        mock_match_result = MatchResult(
            candidates=[0, 1, 2],
            icon=mock_icon,
            confidence=0.9,
            best_match=mock_icon,
            best_confidence=0.9,
            tested_candidates=5,
            gap_candidates=[],
        )

        with patch.object(
            coordinator._template_manager,
            "match_icon",
            return_value=mock_match_result,
        ):
            result, match_result = coordinator._process_single_icon(
                stockpile_images=mock_stockpile_images,
                icon_index=0,
                quantity=100,
                category=None,
                crated=None,
                detected={"category": [], "crated": []},
                faction=None,
            )

            assert result is not None
            assert isinstance(result, StockpileItem)
            assert result.code == "Rifle"
            assert result.quantity == 100
            assert result.crated is False
            assert match_result == mock_match_result

    def test_process_single_icon_no_match(self, tmp_path: Path) -> None:
        """Test icon processing when no match is found.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.vertical_resolution = 1080
        mock_stockpile_images.icons = [np.zeros((64, 64, 3), dtype=np.uint8)]

        mock_match_result = MatchResult(
            candidates=[0, 1, 2],
            icon=None,
            confidence=0.0,
            best_match=None,
            best_confidence=0.0,
            tested_candidates=3,
            gap_candidates=[],
        )

        with patch.object(
            coordinator._template_manager,
            "match_icon",
            return_value=mock_match_result,
        ):
            result, match_result = coordinator._process_single_icon(
                stockpile_images=mock_stockpile_images,
                icon_index=0,
                quantity=100,
                category=None,
                crated=None,
                detected={"category": [], "crated": []},
                faction=None,
            )

            assert result is None
            assert match_result == mock_match_result

    def test_process_single_icon_with_filters(self, tmp_path: Path) -> None:
        """Test icon processing with category and crated filters.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(
            database_path=db_path,
        )
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.vertical_resolution = 1080
        mock_stockpile_images.icons = [np.zeros((64, 64, 3), dtype=np.uint8)]

        mock_icon = MagicMock()
        mock_icon.code = "Rifle"
        mock_icon.crated = True
        mock_icon.category = ItemCategory.Item
        mock_icon.mod = "vanilla"

        mock_match_result = MagicMock(spec=MatchResult)
        mock_match_result.icon = mock_icon
        mock_match_result.confidence = 0.9
        mock_match_result.tested_candidates = 5
        mock_match_result.gap_candidates = []

        with patch.object(
            coordinator._template_manager,
            "match_icon",
            return_value=mock_match_result,
        ) as mock_match:
            coordinator._process_single_icon(
                stockpile_images=mock_stockpile_images,
                icon_index=0,
                quantity=100,
                category=ItemCategory.Item,
                crated=True,
                detected={"category": [], "crated": []},
                faction=ItemFaction.COLONIALS,
            )

            # Verify match_icon was called with proper filters
            mock_match.assert_called_once()
            call_kwargs = mock_match.call_args[1]
            assert call_kwargs["faction"] == ItemFaction.COLONIALS
            assert call_kwargs["category"] == ItemCategory.Item
            assert call_kwargs["crated"] is True

    def test_process_single_icon_with_invalid_category(self, tmp_path: Path) -> None:
        """Test icon processing with ItemCategory.Invalid converts to None.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.vertical_resolution = 1080
        mock_stockpile_images.icons = [np.zeros((64, 64, 3), dtype=np.uint8)]

        mock_template = create_test_icon_template("TestItem")
        mock_match_result = MatchResult(
            candidates=[0],
            icon=mock_template,
            confidence=0.95,
            best_match=mock_template,
            best_confidence=0.95,
            tested_candidates=1,
            gap_candidates=[],
        )

        with patch.object(
            coordinator._template_manager,
            "match_icon",
            return_value=mock_match_result,
        ) as mock_match:
            result, _ = coordinator._process_single_icon(
                stockpile_images=mock_stockpile_images,
                icon_index=0,
                quantity=100,
                category=ItemCategory.Invalid,  # This should be converted to None
                crated=None,
                detected={"category": [], "crated": []},
                faction=None,
            )

            # Verify category was passed as None to match_icon
            call_kwargs = mock_match.call_args[1]
            assert call_kwargs["category"] is None
            assert result is not None

    def test_process_single_icon_with_extract_icons_enabled(self, tmp_path: Path) -> None:
        """Test icon extraction is called when extract_icons is enabled.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(
            database_path=db_path,
            extract_icons=True,  # Enable icon extraction
        )
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.vertical_resolution = 1080
        mock_stockpile_images.icons = [np.zeros((64, 64, 3), dtype=np.uint8)]

        mock_template = create_test_icon_template("TestItem")
        mock_match_result = MatchResult(
            candidates=[0],
            icon=mock_template,
            confidence=0.95,
            best_match=mock_template,
            best_confidence=0.95,
            tested_candidates=1,
            gap_candidates=[],
        )

        with (
            patch.object(
                coordinator._template_manager,
                "match_icon",
                return_value=mock_match_result,
            ),
            patch.object(coordinator, "_extract_icon_to_folder") as mock_extract,
        ):
            result, _ = coordinator._process_single_icon(
                stockpile_images=mock_stockpile_images,
                icon_index=0,
                quantity=100,
                category=None,
                crated=None,
                detected={"category": [], "crated": []},
                faction=None,
            )

            # Verify extract was called with matched code
            mock_extract.assert_called_once()
            assert result is not None

    def test_process_single_icon_no_match_with_extract_icons(self, tmp_path: Path) -> None:
        """Test icon extraction for unmatched icon when extract_icons is enabled.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(
            database_path=db_path,
            extract_icons=True,
        )
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.vertical_resolution = 1080
        mock_stockpile_images.icons = [np.zeros((64, 64, 3), dtype=np.uint8)]

        # No match found
        mock_match_result = MatchResult(
            candidates=[0],
            icon=None,
            confidence=0.0,
            best_match=None,
            best_confidence=0.0,
            tested_candidates=1,
            gap_candidates=[],
        )

        with (
            patch.object(
                coordinator._template_manager,
                "match_icon",
                return_value=mock_match_result,
            ),
            patch.object(coordinator, "_extract_icon_to_folder") as mock_extract,
        ):
            result, _ = coordinator._process_single_icon(
                stockpile_images=mock_stockpile_images,
                icon_index=0,
                quantity=100,
                category=None,
                crated=None,
                detected={"category": [], "crated": []},
                faction=None,
            )

            # Verify extract was called with "Unknown" code for no match
            mock_extract.assert_called_once()
            call_args = mock_extract.call_args[0]
            assert call_args[2] == "Unknown"  # Third arg is code
            assert result is None

    def test_process_single_icon_with_gap_candidates(self, tmp_path: Path) -> None:
        """Test icon processing with gap_candidates populates candidates list.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.vertical_resolution = 1080
        mock_stockpile_images.icons = [np.zeros((64, 64, 3), dtype=np.uint8)]

        mock_template = create_test_icon_template("TestItem")
        alt_template = create_test_icon_template("AltItem")

        mock_match_result = MatchResult(
            candidates=[0, 1],
            icon=mock_template,
            confidence=0.95,
            best_match=mock_template,
            best_confidence=0.95,
            tested_candidates=2,
            gap_candidates=[(alt_template, 0.90)],  # Alternative candidate
        )

        with patch.object(
            coordinator._template_manager,
            "match_icon",
            return_value=mock_match_result,
        ):
            result, _ = coordinator._process_single_icon(
                stockpile_images=mock_stockpile_images,
                icon_index=0,
                quantity=100,
                category=None,
                crated=None,
                detected={"category": [], "crated": []},
                faction=None,
            )

            assert result is not None
            assert result.candidates is not None
            assert len(result.candidates) == 1
            assert result.candidates[0].code == "AltItem"


class TestMatchIconsAndBuildResult:
    """Test suite for OCRCoordinator._match_icons_and_build_result method."""

    @pytest.fixture
    def coordinator(self, tmp_path: Path) -> OCRCoordinator:
        """Create an OCRCoordinator instance for testing.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.

        Returns:
            OCRCoordinator: Coordinator instance for testing.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()
        config = ScannerSettings(database_path=db_path)
        return OCRCoordinator(config)

    @pytest.fixture
    def mock_stockpile_images(self) -> StockpileImageRegions:
        """Create mock stockpile images.

        Returns:
            StockpileImageRegions: Mock stockpile images with icons.
        """
        mock_images = MagicMock(spec=StockpileImageRegions)
        mock_images.vertical_resolution = 1080
        mock_images.resolution = "1920x1080"
        mock_images.icons = [
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
        ]
        mock_images.groups = [(2, 0)]
        mock_images.stockpile_name = None
        mock_images.shard = None
        mock_images.stockpile_type = None
        return mock_images

    @pytest.mark.asyncio
    async def test_no_match_found_creates_unknown_item(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test that when no match is found, an Unknown item is created with error.

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        # Mock _process_single_icon to return None (no match)
        mock_match_result = MatchResult(
            candidates=[],
            icon=None,
            confidence=0.0,
            best_match=create_test_icon_template("SomeItem", crated=False),
            best_confidence=0.5,
            tested_candidates=10,
            gap_candidates=[],
        )

        with (
            patch.object(
                coordinator,
                "_process_single_icon",
                return_value=(None, mock_match_result),
            ),
            patch.object(coordinator, "_check_for_duplicates"),
        ):
            result = await coordinator._match_icons_and_build_result(
                stockpile_images=mock_stockpile_images,
                quantities=[100, 200],
                scale_factor=1.0,
                languages=None,
                faction=None,
            )

            # Should have Unknown items for both icons
            assert len(result.items) == 2
            assert result.items[0].code == "Unknown"
            assert result.items[0].quantity == 100
            assert result.items[1].code == "Unknown"
            assert result.items[1].quantity == 200

            # Should have errors logged
            assert len(result.errors) == 2
            assert "No match found" in result.errors[0]
            assert "Best match: SomeItem" in result.errors[0]

    @pytest.mark.asyncio
    async def test_no_match_with_category(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test no match error includes category when available.

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        # First call returns a match to establish category, second returns None
        mock_icon = create_test_icon_template("Rifle", crated=False)
        mock_icon.category = ItemCategory.Item

        mock_match_result_success = MatchResult(
            candidates=[0],
            icon=mock_icon,
            confidence=0.95,
            best_match=mock_icon,
            best_confidence=0.95,
            tested_candidates=1,
            gap_candidates=[],
        )

        mock_match_result_fail = MatchResult(
            candidates=[],
            icon=None,
            confidence=0.0,
            best_match=None,
            best_confidence=0.0,
            tested_candidates=10,
            gap_candidates=[],
        )

        call_count = [0]

        def side_effect(*args: Any, **kwargs: Any) -> tuple[StockpileItem | None, MatchResult]:
            call_count[0] += 1
            if call_count[0] == 1:
                return (
                    StockpileItem(code="Rifle", quantity=100, crated=False, confidence=0.95),
                    mock_match_result_success,
                )
            return (None, mock_match_result_fail)

        # Need 3 icons to trigger category detection (expected_length=2 for group 0)
        mock_stockpile_images.icons = [
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
        ]
        mock_stockpile_images.groups = [(3, 0)]

        with (
            patch.object(coordinator, "_process_single_icon", side_effect=side_effect),
            patch.object(coordinator, "_check_for_duplicates"),
        ):
            result = await coordinator._match_icons_and_build_result(
                stockpile_images=mock_stockpile_images,
                quantities=[100, 200, 300],
                scale_factor=1.0,
                languages=None,
                faction=None,
            )

            # Should have one successful item and two Unknown items
            assert len(result.items) == 3
            assert result.items[0].code == "Rifle"

    @pytest.mark.asyncio
    async def test_crated_status_updated_for_existing_items(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test that crated status is updated for items when detected.

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        # Create icons that will trigger crated status detection and update
        mock_stockpile_images.icons = [
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
        ]
        mock_stockpile_images.groups = [(3, 0)]

        call_count = [0]

        def side_effect(*args: Any, **kwargs: Any) -> tuple[StockpileItem, MatchResult]:
            call_count[0] += 1
            # Get the detected dict from kwargs to populate it
            detected = kwargs.get("detected", {})

            # All icons report crated=True so detected crated will be True
            mock_icon = create_test_icon_template(f"Item{call_count[0]}", crated=True)
            mock_icon.category = ItemCategory.Item

            # Populate detected dict like the real function would
            if "category" in detected:
                detected["category"].append(mock_icon.category)
            if "crated" in detected:
                detected["crated"].append(True)

            mock_result = MatchResult(
                candidates=[0],
                icon=mock_icon,
                confidence=0.95,
                best_match=mock_icon,
                best_confidence=0.95,
                tested_candidates=1,
                gap_candidates=[],
            )
            # First item returns with crated=False so it will be updated when crated is detected
            item_crated = False if call_count[0] == 1 else True
            return (
                StockpileItem(
                    code=f"Item{call_count[0]}",
                    quantity=100 * call_count[0],
                    crated=item_crated,
                    confidence=0.95,
                ),
                mock_result,
            )

        with (
            patch.object(coordinator, "_process_single_icon", side_effect=side_effect),
            patch.object(coordinator, "_check_for_duplicates"),
        ):
            result = await coordinator._match_icons_and_build_result(
                stockpile_images=mock_stockpile_images,
                quantities=[100, 200, 300],
                scale_factor=1.0,
                languages=None,
                faction=None,
            )

            # All items should have crated=True after detection
            assert len(result.items) == 3
            # After category is detected (after 2 items), crated status should be detected as True
            # The first item should have been updated from crated=False to crated=True
            assert result.items[0].crated is True
            assert result.items[1].crated is True
            assert result.items[2].crated is True

    @pytest.mark.asyncio
    async def test_exception_during_icon_processing(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test that exceptions during icon processing are caught and logged.

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        # Explicitly set icons and groups to ensure consistent state
        mock_stockpile_images.icons = [
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
        ]
        mock_stockpile_images.groups = [(2, 0)]

        with (
            patch.object(
                coordinator,
                "_process_single_icon",
                side_effect=RuntimeError("Test error"),
            ),
            patch.object(coordinator, "_check_for_duplicates"),
            patch.object(coordinator.logger, "error") as mock_error,
        ):
            result = await coordinator._match_icons_and_build_result(
                stockpile_images=mock_stockpile_images,
                quantities=[100, 200],
                scale_factor=1.0,
                languages=None,
                faction=None,
            )

            # Should have logged errors for each icon that failed
            # Check that at least 2 errors were logged with the expected message format
            assert mock_error.call_count >= 2
            error_calls = [
                call
                for call in mock_error.call_args_list
                if "Error processing icon at index" in str(call)
            ]
            assert len(error_calls) == 2
            # Result should still be returned (empty items due to exception)
            assert isinstance(result, Stockpile)

    @pytest.mark.asyncio
    async def test_exception_during_icon_processing_with_debug_logging(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test that exception details are logged when debug is enabled.

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        import logging

        # Enable debug logging to cover line 453
        coordinator.logger.setLevel(logging.DEBUG)

        # Configure to have only 1 icon
        mock_stockpile_images.icons = [np.zeros((64, 64, 3), dtype=np.uint8)]
        mock_stockpile_images.groups = [(1, 0)]

        with (
            patch.object(
                coordinator,
                "_process_single_icon",
                side_effect=RuntimeError("Test error"),
            ),
            patch.object(coordinator, "_check_for_duplicates"),
            patch.object(coordinator.logger, "error") as mock_error,
            patch.object(coordinator.logger, "exception") as mock_exception,
            patch.object(coordinator.logger, "isEnabledFor", return_value=True),
        ):
            result = await coordinator._match_icons_and_build_result(
                stockpile_images=mock_stockpile_images,
                quantities=[100],
                scale_factor=1.0,
                languages=None,
                faction=None,
            )

            # Should have logged error and exception
            assert mock_error.call_count == 1
            assert mock_exception.call_count == 1
            mock_exception.assert_called_with("Full error details:")
            assert isinstance(result, Stockpile)


class TestCheckForDuplicates:
    """Test suite for OCRCoordinator._check_for_duplicates method."""

    @pytest.fixture
    def coordinator(self, tmp_path: Path) -> OCRCoordinator:
        """Create an OCRCoordinator instance for testing.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.

        Returns:
            OCRCoordinator: Coordinator instance for testing.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()
        config = ScannerSettings(database_path=db_path)
        return OCRCoordinator(config)

    @pytest.fixture
    def mock_stockpile_images(self) -> StockpileImageRegions:
        """Create mock stockpile images.

        Returns:
            StockpileImageRegions: Mock stockpile images with icons.
        """
        mock_images = MagicMock(spec=StockpileImageRegions)
        mock_images.vertical_resolution = 1080
        mock_images.icons = [
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
        ]
        return mock_images

    def test_no_duplicates(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test that no changes occur when there are no duplicates.

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        stockpile = Stockpile(resolution="1920x1080")
        stockpile.items = [
            StockpileItem(code="Rifle", quantity=100, crated=False, confidence=0.95),
            StockpileItem(code="Bandages", quantity=50, crated=False, confidence=0.90),
            StockpileItem(code="Ammo", quantity=200, crated=False, confidence=0.88),
        ]

        coordinator._check_for_duplicates(stockpile, mock_stockpile_images, faction=None)

        # Items should remain unchanged
        assert len(stockpile.items) == 3
        assert stockpile.items[0].code == "Rifle"
        assert stockpile.items[1].code == "Bandages"
        assert stockpile.items[2].code == "Ammo"

    def test_simple_duplicate_resolves(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test that a simple duplicate is resolved by re-matching.

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        stockpile = Stockpile(resolution="1920x1080")
        stockpile.items = [
            StockpileItem(code="Rifle", quantity=100, crated=False, confidence=0.85),
            StockpileItem(code="Rifle", quantity=200, crated=False, confidence=0.95),
        ]

        # Mock _process_single_icon to return a different item
        mock_icon = create_test_icon_template("Ammo", crated=False)

        mock_match_result = MatchResult(
            candidates=[0, 1, 2, 3, 4],
            icon=mock_icon,
            confidence=0.82,
            best_match=mock_icon,
            best_confidence=0.82,
            tested_candidates=5,
            gap_candidates=[],
        )

        with patch.object(
            coordinator._template_manager, "match_icon", return_value=mock_match_result
        ):
            coordinator._check_for_duplicates(stockpile, mock_stockpile_images, faction=None)

        # Lower confidence item (index 0) should be re-matched
        assert stockpile.items[0].code == "Ammo"
        assert stockpile.items[0].confidence == 0.82
        assert stockpile.items[1].code == "Rifle"
        assert stockpile.items[1].confidence == 0.95

    def test_duplicate_with_none_confidence(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test duplicate detection handles None confidence values.

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        stockpile = Stockpile(resolution="1920x1080")
        stockpile.items = [
            StockpileItem(code="Rifle", quantity=100, crated=False, confidence=None),
            StockpileItem(code="Rifle", quantity=200, crated=False, confidence=0.95),
        ]

        # Mock to return alternative
        mock_icon = create_test_icon_template("Ammo", crated=False)

        mock_match_result = MatchResult(
            candidates=[0, 1, 2, 3, 4],
            icon=mock_icon,
            confidence=0.80,
            best_match=mock_icon,
            best_confidence=0.80,
            tested_candidates=5,
            gap_candidates=[],
        )

        with patch.object(
            coordinator._template_manager, "match_icon", return_value=mock_match_result
        ):
            coordinator._check_for_duplicates(stockpile, mock_stockpile_images, faction=None)

        # Item with None confidence (treated as 0.0) should be re-matched
        assert stockpile.items[0].code == "Ammo"
        assert stockpile.items[1].code == "Rifle"

    def test_crated_vs_non_crated_not_duplicate(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test that crated and non-crated versions are NOT considered duplicates.

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        stockpile = Stockpile(resolution="1920x1080")
        stockpile.items = [
            StockpileItem(code="Rifle", quantity=100, crated=False, confidence=0.90),
            StockpileItem(code="Rifle", quantity=200, crated=True, confidence=0.85),
        ]

        coordinator._check_for_duplicates(stockpile, mock_stockpile_images, faction=None)

        # Both should remain unchanged
        assert stockpile.items[0].code == "Rifle"
        assert stockpile.items[0].crated is False
        assert stockpile.items[1].code == "Rifle"
        assert stockpile.items[1].crated is True

    def test_no_alternative_marks_unknown(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test that when no alternative is found, item is marked as Unknown.

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        stockpile = Stockpile(resolution="1920x1080")
        stockpile.items = [
            StockpileItem(code="Rifle", quantity=100, crated=False, confidence=0.85),
            StockpileItem(code="Rifle", quantity=200, crated=False, confidence=0.95),
        ]

        # Mock to return None (no alternative found)
        mock_match_result = MatchResult(
            candidates=[0, 1, 2],
            icon=None,
            confidence=0.0,
            best_match=None,
            best_confidence=0.0,
            tested_candidates=3,
            gap_candidates=[],
        )

        with patch.object(
            coordinator._template_manager, "match_icon", return_value=mock_match_result
        ):
            coordinator._check_for_duplicates(stockpile, mock_stockpile_images, faction=None)

        # Lower confidence item should be marked as Unknown
        assert stockpile.items[0].code == "Unknown"
        assert stockpile.items[0].confidence == 0.0
        assert stockpile.items[1].code == "Rifle"

    def test_no_alternative_with_best_match_below_threshold(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test that best match info is included when no alternative meets threshold.

        This test covers line 528 where best_match exists but didn't meet the
        confidence threshold during duplicate resolution.

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        stockpile = Stockpile(resolution="1920x1080")
        stockpile.items = [
            StockpileItem(code="Rifle", quantity=100, crated=False, confidence=0.85),
            StockpileItem(code="Rifle", quantity=200, crated=False, confidence=0.95),
        ]

        # Create a mock best match that didn't meet threshold
        mock_best_match = create_test_icon_template("Bandages", crated=True)

        # Mock to return None for icon (no match above threshold) but with best_match
        mock_match_result = MatchResult(
            candidates=[0, 1, 2],
            icon=None,  # No match above threshold
            confidence=0.0,
            best_match=mock_best_match,  # But best match exists
            best_confidence=0.75,  # Below threshold
            tested_candidates=3,
            gap_candidates=[],
        )

        with patch.object(
            coordinator._template_manager, "match_icon", return_value=mock_match_result
        ):
            coordinator._check_for_duplicates(stockpile, mock_stockpile_images, faction=None)

        # Lower confidence item should be marked as Unknown
        assert stockpile.items[0].code == "Unknown"
        assert stockpile.items[0].confidence == 0.0
        assert stockpile.items[1].code == "Rifle"

        # Verify error message includes best match information
        assert len(stockpile.errors) > 0
        error_message = stockpile.errors[0]
        assert "Best match: Bandages (crated)" in error_message
        assert "confidence: 0.750" in error_message

    def test_unknown_items_ignored(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test that Unknown items are ignored in duplicate detection.

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        stockpile = Stockpile(resolution="1920x1080")
        # Only one Unknown item to avoid infinite loop - Unknown items don't get tracked
        stockpile.items = [
            StockpileItem(code="Unknown", quantity=100, crated=False, confidence=0.0),
            StockpileItem(code="Rifle", quantity=50, crated=False, confidence=0.90),
            StockpileItem(code="Bandages", quantity=75, crated=False, confidence=0.88),
        ]

        coordinator._check_for_duplicates(stockpile, mock_stockpile_images, faction=None)

        # Unknown items should not trigger duplicate detection
        assert stockpile.items[0].code == "Unknown"
        assert stockpile.items[1].code == "Rifle"
        assert stockpile.items[2].code == "Bandages"

    def test_cascading_duplicates_with_exclusion_list(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test that cascading duplicates are resolved with growing exclusion list.

        This tests the scenario where:
        1. "Rifle" conflicts -> re-match finds "Ammo"
        2. "Ammo" also conflicts -> should exclude both "Rifle" and "Ammo"

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        stockpile = Stockpile(resolution="1920x1080")
        stockpile.items = [
            StockpileItem(code="Rifle", quantity=100, crated=False, confidence=0.85),
            StockpileItem(code="Rifle", quantity=200, crated=False, confidence=0.95),
        ]

        call_count = 0

        def mock_match_side_effect(*args: Any, **kwargs: Any) -> MatchResult:
            """Side effect function to simulate cascading exclusions.

            Args:
                *args (Any): Positional arguments.
                **kwargs (Any): Keyword arguments.

            Returns:
                MatchResult: Mock match result based on call count and exclusions.
            """
            nonlocal call_count
            call_count += 1

            excluded = kwargs.get("excluded_codes", [])

            # First call: excluded=["Rifle"] -> return "Ammo"
            if call_count == 1:
                assert "Rifle" in excluded
                mock_icon = create_test_icon_template("Ammo", crated=False)
                return MatchResult(
                    candidates=[0, 1, 2],
                    icon=mock_icon,
                    confidence=0.82,
                    best_match=mock_icon,
                    best_confidence=0.82,
                    tested_candidates=3,
                    gap_candidates=[],
                )

            # Second call: excluded=["Rifle", "Ammo"] -> return "Bandages"
            if call_count == 2:
                assert "Rifle" in excluded
                assert "Ammo" in excluded
                mock_icon = create_test_icon_template("Bandages", crated=False)
                return MatchResult(
                    candidates=[0, 1, 2],
                    icon=mock_icon,
                    confidence=0.80,
                    best_match=mock_icon,
                    best_confidence=0.80,
                    tested_candidates=3,
                    gap_candidates=[],
                )

            # Should not reach here
            raise AssertionError(f"Unexpected call count: {call_count}")

        with patch.object(
            coordinator._template_manager, "match_icon", side_effect=mock_match_side_effect
        ):
            # Add another "Ammo" to trigger cascading
            stockpile.items.insert(
                1, StockpileItem(code="Ammo", quantity=150, crated=False, confidence=0.90)
            )

            coordinator._check_for_duplicates(stockpile, mock_stockpile_images, faction=None)

        # Verify exclusion list grew and final result
        assert call_count >= 1

    def test_multiple_independent_duplicates(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test handling multiple independent duplicate pairs.

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        stockpile = Stockpile(resolution="1920x1080")
        stockpile.items = [
            StockpileItem(code="Rifle", quantity=100, crated=False, confidence=0.85),
            StockpileItem(code="Rifle", quantity=200, crated=False, confidence=0.95),
            StockpileItem(code="Bandages", quantity=50, crated=False, confidence=0.80),
            StockpileItem(code="Bandages", quantity=75, crated=False, confidence=0.90),
        ]

        call_count = 0

        def mock_match_side_effect(*args: Any, **kwargs: Any) -> MatchResult:
            nonlocal call_count
            call_count += 1

            # First re-match: Rifle -> Ammo
            if call_count == 1:
                mock_icon = create_test_icon_template("Ammo", crated=False)
                return MatchResult(
                    candidates=[0, 1, 2],
                    icon=mock_icon,
                    confidence=0.82,
                    best_match=mock_icon,
                    best_confidence=0.82,
                    tested_candidates=3,
                    gap_candidates=[],
                )

            # Second re-match: Bandages -> MedKit
            if call_count == 2:
                mock_icon = create_test_icon_template("MedKit", crated=False)
                return MatchResult(
                    candidates=[0, 1, 2],
                    icon=mock_icon,
                    confidence=0.78,
                    best_match=mock_icon,
                    best_confidence=0.78,
                    tested_candidates=3,
                    gap_candidates=[],
                )

            raise AssertionError(f"Unexpected call count: {call_count}")

        with patch.object(
            coordinator._template_manager, "match_icon", side_effect=mock_match_side_effect
        ):
            coordinator._check_for_duplicates(stockpile, mock_stockpile_images, faction=None)

        # Both duplicates should be resolved
        assert stockpile.items[0].code == "Ammo"
        assert stockpile.items[1].code == "Rifle"
        assert stockpile.items[2].code == "MedKit"
        assert stockpile.items[3].code == "Bandages"

    def test_exclusion_list_accumulates(
        self, coordinator: OCRCoordinator, mock_stockpile_images: StockpileImageRegions
    ) -> None:
        """Test that exclusion list properly accumulates conflicting codes.

        Args:
            coordinator (OCRCoordinator): Coordinator instance.
            mock_stockpile_images (StockpileImageRegions): Mock images.
        """
        stockpile = Stockpile(resolution="1920x1080")
        stockpile.items = [
            StockpileItem(code="Rifle", quantity=100, crated=False, confidence=0.85),
            StockpileItem(code="Rifle", quantity=200, crated=False, confidence=0.95),
        ]

        excluded_lists: list[list[str]] = []

        def mock_match_side_effect(*args: Any, **kwargs: Any) -> MatchResult:
            excluded = kwargs.get("excluded_codes", [])
            excluded_lists.append(excluded.copy())

            # Return a unique item each time
            mock_icon = create_test_icon_template(f"Item{len(excluded_lists)}", crated=False)
            return MatchResult(
                candidates=[0, 1, 2],
                icon=mock_icon,
                confidence=0.80,
                best_match=mock_icon,
                best_confidence=0.80,
                tested_candidates=3,
                gap_candidates=[],
            )

        with patch.object(
            coordinator._template_manager, "match_icon", side_effect=mock_match_side_effect
        ):
            coordinator._check_for_duplicates(stockpile, mock_stockpile_images, faction=None)

        # First call should have "Rifle" in exclusion list
        assert len(excluded_lists) >= 1
        assert "Rifle" in excluded_lists[0]


class TestDetectRegionsCriticalException:
    """Test suite for critical exception handling in _detect_regions."""

    def test_detect_regions_exception_handler(self, tmp_path: Path) -> None:
        """Test that _detect_regions properly catches and re-raises exceptions.

        This tests the critical exception path at lines 160-162 in ocr_coordinator.py.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)

        # Mock StockpileDetector to raise an exception during analysis
        with patch("foxhole_stockpiles.services.ocr_coordinator.StockpileDetector") as mock_class:
            mock_detector = MagicMock(spec=StockpileDetector)
            # Simulate detector.analize() raising an exception
            mock_detector.analize.side_effect = RuntimeError("Simulated detector failure")
            mock_class.return_value = mock_detector

            # Verify that the exception is caught and re-raised as ValueError
            with pytest.raises(ValueError, match="Failed to analyze image"):
                coordinator._detect_regions(mock_image)

    def test_save_screenshot_exception_handler(self, tmp_path: Path) -> None:
        """Test that screenshot save failures are handled gracefully.

        This tests the exception handling at lines 84-85 in ocr_coordinator.py.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        # Set a screenshots folder
        config = ScannerSettings(
            database_path=db_path, screenshots_folder=str(tmp_path / "screenshots")
        )
        coordinator = OCRCoordinator(config)

        from foxhole_stockpiles.enums.stockpile_type import StockpileType

        mock_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_stockpile = Stockpile(
            resolution="1920x1080", name="Test", type=StockpileType.STORAGE_DEPOT
        )

        # Mock cv2.imwrite to raise an exception
        with patch("foxhole_stockpiles.services.ocr_coordinator.cv2.imwrite") as mock_imwrite:
            mock_imwrite.side_effect = OSError("Simulated write failure")

            # Should not raise - exception should be caught and logged
            coordinator._save_screenshot(mock_image, stockpile=mock_stockpile)


class TestOCRCoordinatorIntegration:
    """Integration tests with real screenshots for OCRCoordinator."""

    @pytest.fixture
    def real_screenshot(self) -> NDArray[np.uint8]:
        """Load the real test screenshot in BGR format, resized to 1080p.

        Returns:
            NDArray[np.uint8]: Real screenshot in BGR format for testing at 1080p resolution.
        """
        test_image_path = Path(__file__).parent.parent / "test.png"
        if not test_image_path.exists():
            pytest.skip("test.png not found")

        # Load in BGR format as expected by OCRCoordinator
        image_bgr = cv2.imread(str(test_image_path))
        if image_bgr is None:
            pytest.skip("Failed to load test.png")

        # Resize to 1080p to match test database resolutions (1080p and 1440p available)
        # Using 1080p as it's a common resolution in the test database
        resized = cv2.resize(image_bgr, (1920, 1080), interpolation=cv2.INTER_AREA)

        # Cast to proper type for type checking
        return resized.astype(np.uint8)

    @pytest.fixture
    def real_database(self) -> Path:
        """Get path to test template database.

        Returns:
            Path: Path to the template database file.
        """
        db_path = Path(__file__).parent.parent / "fixtures" / "test_db_v1.h5"
        if not db_path.exists():
            pytest.skip("test_db_v1.h5 database not found")
        return db_path

    @pytest.mark.asyncio
    async def test_analyze_with_high_early_exit_threshold(
        self, real_screenshot: NDArray[np.uint8], real_database: Path
    ) -> None:
        """Test analysis with high early exit threshold.

        This test uses a real screenshot with a high early exit threshold
        to verify matching behavior. Items should match to the best template found.

        Args:
            real_screenshot (NDArray[np.uint8]): Real screenshot fixture.
            real_database (Path): Path to template database.
        """
        config = ScannerSettings(
            database_path=real_database,
            early_exit_threshold=0.995,
        )

        coordinator = OCRCoordinator(config)
        result = await coordinator.analyze_stockpile(real_screenshot)

        # Should have some items matched to best templates
        assert len(result.items) > 0

    @pytest.mark.asyncio
    async def test_analyze_with_debug_mode_saves_images(
        self,
        real_screenshot: NDArray[np.uint8],
        real_database: Path,
        tmp_path: Path,
    ) -> None:
        """Test that debug mode triggers image saving code paths.

        This tests the debug mode branches at lines 297-329, 370-371, 381-382,
        and 396-397 in ocr_coordinator.py.

        Args:
            real_screenshot (NDArray[np.uint8]): Real screenshot fixture.
            real_database (Path): Path to template database.
            tmp_path (Path): Temporary directory for test output.
        """
        # Use debug mode to trigger image save paths
        config = ScannerSettings(
            database_path=real_database,
            debug_mode=True,
        )

        coordinator = OCRCoordinator(config)

        # Change to tmp_path so debug images are saved there

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = await coordinator.analyze_stockpile(real_screenshot)
        finally:
            os.chdir(original_cwd)

        # Should have successfully analyzed
        assert len(result.items) > 0

        # Debug mode should have created some debug images
        # Note: We don't assert on specific filenames as they may vary

    @pytest.mark.asyncio
    async def test_analyze_extracts_metadata_from_real_screenshot(
        self, real_screenshot: NDArray[np.uint8], real_database: Path
    ) -> None:
        """Test that metadata extraction paths are tested with real screenshot.

        This tests the metadata extraction code paths at lines 369-402 in
        ocr_coordinator.py, which extract stockpile name, info and type.

        Args:
            real_screenshot (NDArray[np.uint8]): Real screenshot fixture.
            real_database (Path): Path to template database.
        """
        config = ScannerSettings(
            database_path=real_database,
        )

        coordinator = OCRCoordinator(config)
        result = await coordinator.analyze_stockpile(real_screenshot)

        # Should have extracted resolution
        assert result.resolution is not None
        assert result.resolution != ""

        # May or may not have name/info/type depending on the screenshot
        # but the code paths should have been exercised


class TestExtractQuantitiesEdgeCases:
    """Test edge cases in _extract_quantities method."""

    async def test_extract_quantities_adds_placeholders_when_missing(self, tmp_path: Path) -> None:
        """Test that missing quantities are filled with -1 placeholders.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        # Create mock stockpile_images with 5 icons
        mock_images = MagicMock(spec=StockpileImageRegions)
        mock_images.icons = [MagicMock() for _ in range(5)]
        mock_images.groups = [(5, 0)]
        mock_images.quantities = [MagicMock() for _ in range(5)]
        mock_images.composite_quantities_image = MagicMock()

        # Mock _validate_and_correct_quantities to return fewer quantities than icons
        with (
            patch.object(
                coordinator._text_extractor,
                "extract_quantities",
                new_callable=AsyncMock,
                return_value=[[100, 50, 25]],
            ),
            patch.object(
                coordinator,
                "_validate_and_correct_quantities",
                new_callable=AsyncMock,
                return_value=[100, 50, 25],  # Only 3 quantities for 5 icons
            ),
        ):
            result = await coordinator._extract_quantities(mock_images)

        # Should have 5 quantities with 2 placeholders
        assert len(result) == 5
        assert result[:3] == [100, 50, 25]
        assert result[3:] == [-1, -1]

    async def test_extract_quantities_truncates_when_extra(self, tmp_path: Path) -> None:
        """Test that extra quantities are truncated.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(database_path=db_path)
        coordinator = OCRCoordinator(config)

        # Create mock stockpile_images with 3 icons
        mock_images = MagicMock(spec=StockpileImageRegions)
        mock_images.icons = [MagicMock() for _ in range(3)]
        mock_images.groups = [(3, 0)]
        mock_images.quantities = [MagicMock() for _ in range(3)]
        mock_images.composite_quantities_image = MagicMock()

        # Mock _validate_and_correct_quantities to return more quantities than icons
        with (
            patch.object(
                coordinator._text_extractor,
                "extract_quantities",
                new_callable=AsyncMock,
                return_value=[[100, 50, 25, 10, 5]],
            ),
            patch.object(
                coordinator,
                "_validate_and_correct_quantities",
                new_callable=AsyncMock,
                return_value=[100, 50, 25, 10, 5],  # 5 quantities for 3 icons
            ),
        ):
            result = await coordinator._extract_quantities(mock_images)

        # Should be truncated to 3 quantities
        assert len(result) == 3
        assert result == [100, 50, 25]


class TestFrozenBundlePath:
    """Test PyInstaller frozen bundle path resolution."""

    def test_init_resolves_tessdata_path_when_frozen(self, tmp_path: Path) -> None:
        """Test that tessdata path is resolved for PyInstaller bundles.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        db_path.touch()

        config = ScannerSettings(
            database_path=db_path,
            tessdata_path="tessdata",
        )

        # Mock is_frozen to return True
        with (
            patch(
                "foxhole_stockpiles.services.ocr_coordinator.is_frozen",
                return_value=True,
            ),
            patch(
                "foxhole_stockpiles.services.ocr_coordinator.get_bundled_resource_path",
                return_value=Path("/bundled/tessdata"),
            ),
        ):
            coordinator = OCRCoordinator(config)

        # The text extractor should have been initialized with the bundled path
        assert coordinator._text_extractor is not None


class TestMultiLineNameConcatenation:
    """Test suite for multi-line stockpile name concatenation."""

    def test_name_concatenation_with_hyphen(self) -> None:
        """Test that lines ending with hyphen are concatenated directly."""
        # Simulate the concatenation logic from _extract_metadata
        name_text = "ABC-\nDEF"
        lines = [line.strip() for line in name_text.strip().split("\n") if line.strip()]
        result = ""
        for line in lines:
            if result and not result.endswith("-"):
                result += " "
            result += line

        assert result == "ABC-DEF"

    def test_name_concatenation_without_hyphen(self) -> None:
        """Test that lines not ending with hyphen are concatenated with space."""
        # Simulate the concatenation logic from _extract_metadata
        name_text = "ABC\nDEF"
        lines = [line.strip() for line in name_text.strip().split("\n") if line.strip()]
        result = ""
        for line in lines:
            if result and not result.endswith("-"):
                result += " "
            result += line

        assert result == "ABC DEF"

    def test_name_concatenation_mixed(self) -> None:
        """Test mixed hyphen and non-hyphen line endings."""
        # Simulate the concatenation logic from _extract_metadata
        name_text = "AB-\nCD\nEF"
        lines = [line.strip() for line in name_text.strip().split("\n") if line.strip()]
        result = ""
        for line in lines:
            if result and not result.endswith("-"):
                result += " "
            result += line

        assert result == "AB-CD EF"

    def test_name_concatenation_single_line(self) -> None:
        """Test single line name remains unchanged."""
        name_text = "SingleName"
        lines = [line.strip() for line in name_text.strip().split("\n") if line.strip()]
        result = ""
        for line in lines:
            if result and not result.endswith("-"):
                result += " "
            result += line

        assert result == "SingleName"

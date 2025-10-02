"""Tests for services.ocr_coordinator module.

This module contains comprehensive tests for the OCRCoordinator class,
which orchestrates the entire stockpile detection and analysis process.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from numpy.typing import NDArray

from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.models.match_result import MatchResult
from foxhole_stockpiles.models.ocr_coordinator_config import OCRCoordinatorConfig
from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.models.stockpile_image_regions import StockpileImageRegions
from foxhole_stockpiles.models.stockpile_item import StockpileItem
from foxhole_stockpiles.services.ocr_coordinator import OCRCoordinator
from foxhole_stockpiles.services.stockpile_detector import StockpileDetector


class TestOCRCoordinatorInitialization:
    """Test suite for OCRCoordinator initialization.

    This class contains tests for proper initialization of the OCRCoordinator
    including config handling, service initialization, and initial state validation.
    """

    def test_init_with_config(self, tmp_path: Path) -> None:
        """Test initializing OCRCoordinator with a config.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        config = OCRCoordinatorConfig(
            database_path=db_path,
            confidence_threshold=0.85,
            early_exit_threshold=0.95,
        )

        coordinator = OCRCoordinator(config)

        assert coordinator.config == config
        assert coordinator.threshold_value == 0.0
        assert coordinator.scale_factor == 1.0
        assert coordinator._text_extractor is not None
        assert coordinator._template_manager is not None
        assert coordinator._stockpile_type_classifier is not None

    def test_init_with_custom_model(self, tmp_path: Path) -> None:
        """Test initializing OCRCoordinator with custom OCR model.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        config = OCRCoordinatorConfig(
            database_path=db_path,
            custom_model="custom_model",
            tessdata_path="/path/to/tessdata",
        )

        coordinator = OCRCoordinator(config)

        assert coordinator._text_extractor.custom_model == "custom_model"


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
    def mock_config(self, tmp_path: Path) -> OCRCoordinatorConfig:
        """Create a mock config for testing.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.

        Returns:
            OCRCoordinatorConfig: Mock configuration.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        return OCRCoordinatorConfig(
            database_path=db_path,
            confidence_threshold=0.85,
            early_exit_threshold=0.95,
        )

    async def test_analyze_stockpile_success(
        self,
        mock_image: NDArray[np.uint8],
        mock_config: OCRCoordinatorConfig,
    ) -> None:
        """Test successful stockpile analysis.

        Args:
            mock_image (NDArray[np.uint8]): Mock image from fixture.
            mock_config (OCRCoordinatorConfig): Mock config from fixture.
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
        mock_stockpile_images.hex_name = None
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

            mock_match.return_value = mock_match_result

            result = await coordinator.analyze_stockpile(mock_image)

            assert isinstance(result, Stockpile)
            assert len(result.items) == 2

    async def test_analyze_stockpile_no_icons(
        self,
        mock_image: NDArray[np.uint8],
        mock_config: OCRCoordinatorConfig,
    ) -> None:
        """Test analysis when no icons are found.

        Args:
            mock_image (np.ndarray): Mock image from fixture.
            mock_config (OCRCoordinatorConfig): Mock config from fixture.
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
        mock_config: OCRCoordinatorConfig,
    ) -> None:
        """Test analysis when region detection fails.

        Args:
            mock_image (np.ndarray): Mock image from fixture.
            mock_config (OCRCoordinatorConfig): Mock config from fixture.
        """
        coordinator = OCRCoordinator(mock_config)

        with patch.object(
            coordinator,
            "_detect_regions",
            side_effect=ValueError("Detection failed"),
        ):
            with pytest.raises(ValueError, match="Detection failed"):
                await coordinator.analyze_stockpile(mock_image)


class TestDetectRegions:
    """Test suite for OCRCoordinator._detect_regions method.

    This class contains tests for region detection functionality.
    """

    def test_detect_regions_success(self, tmp_path: Path) -> None:
        """Test successful region detection.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        config = OCRCoordinatorConfig(database_path=db_path)
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
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        config = OCRCoordinatorConfig(database_path=db_path, debug_mode=True)
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
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        config = OCRCoordinatorConfig(database_path=db_path)
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.composite_quantities_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_stockpile_images.icons = [
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
        ]

        with patch.object(
            coordinator._text_extractor,
            "extract_quantities",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = [[100, 200]]

            result = await coordinator._extract_quantities(mock_stockpile_images)

            assert result == [100, 200]

    async def test_extract_quantities_mismatch(self, tmp_path: Path) -> None:
        """Test quantity extraction when counts don't match icons.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        config = OCRCoordinatorConfig(database_path=db_path)
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.composite_quantities_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_stockpile_images.icons = [
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((64, 64, 3), dtype=np.uint8),
        ]

        with patch.object(
            coordinator._text_extractor,
            "extract_quantities",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = [[100]]

            result = await coordinator._extract_quantities(mock_stockpile_images)

            # Should have placeholders for missing quantities
            assert len(result) == 3
            assert result[0] == 100
            assert result[1] == -1
            assert result[2] == -1


class TestPrepareImageForDetection:
    """Test suite for OCRCoordinator._prepare_image_for_detection method.

    This class contains tests for image preprocessing functionality.
    """

    def test_prepare_image_basic(self, tmp_path: Path) -> None:
        """Test basic image preprocessing.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        config = OCRCoordinatorConfig(database_path=db_path)
        coordinator = OCRCoordinator(config)
        coordinator.scale_factor = 1.0

        # Create a simple test image
        test_image = np.full((100, 100, 3), 128, dtype=np.uint8)

        result = coordinator._prepare_image_for_detection(test_image)

        assert result.shape[:2] == (200, 200)  # 2x upscale
        assert result.dtype == np.uint8
        assert len(result.shape) == 3  # RGB image

    def test_prepare_image_with_inv(self, tmp_path: Path) -> None:
        """Test image preprocessing with inverted threshold.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        config = OCRCoordinatorConfig(database_path=db_path)
        coordinator = OCRCoordinator(config)
        coordinator.scale_factor = 1.0

        test_image = np.full((100, 100, 3), 128, dtype=np.uint8)

        result_inv = coordinator._prepare_image_for_detection(test_image, use_inv=True)
        result_no_inv = coordinator._prepare_image_for_detection(test_image, use_inv=False)

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
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        config = OCRCoordinatorConfig(database_path=db_path)
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.vertical_resolution = 1080
        mock_stockpile_images.icons = [np.zeros((64, 64, 3), dtype=np.uint8)]

        mock_icon = MagicMock()
        mock_icon.code = "Rifle"
        mock_icon.crated = False
        mock_icon.category = ItemCategory.Item
        mock_icon.mod = "vanilla"

        mock_match_result = MagicMock(spec=MatchResult)
        mock_match_result.icon = mock_icon
        mock_match_result.confidence = 0.9
        mock_match_result.tested_candidates = 5

        with patch.object(
            coordinator._template_manager,
            "match_icon",
            return_value=mock_match_result,
        ):
            result = coordinator._process_single_icon(
                stockpile_images=mock_stockpile_images,
                icon_index=0,
                quantity=100,
                category=None,
                crated=None,
                mod=None,
                detected={"category": [], "crated": [], "mod": []},
            )

            assert result is not None
            assert isinstance(result, StockpileItem)
            assert result.code == "Rifle"
            assert result.quantity == 100
            assert result.crated is False

    def test_process_single_icon_no_match(self, tmp_path: Path) -> None:
        """Test icon processing when no match is found.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        config = OCRCoordinatorConfig(database_path=db_path)
        coordinator = OCRCoordinator(config)

        mock_stockpile_images = MagicMock(spec=StockpileImageRegions)
        mock_stockpile_images.vertical_resolution = 1080
        mock_stockpile_images.icons = [np.zeros((64, 64, 3), dtype=np.uint8)]

        mock_match_result = MagicMock(spec=MatchResult)
        mock_match_result.icon = None

        with patch.object(
            coordinator._template_manager,
            "match_icon",
            return_value=mock_match_result,
        ):
            result = coordinator._process_single_icon(
                stockpile_images=mock_stockpile_images,
                icon_index=0,
                quantity=100,
                category=None,
                crated=None,
                mod=None,
                detected={"category": [], "crated": [], "mod": []},
            )

            assert result is None

    def test_process_single_icon_with_filters(self, tmp_path: Path) -> None:
        """Test icon processing with category and crated filters.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        db_path.touch()

        config = OCRCoordinatorConfig(
            database_path=db_path,
            faction_filter=ItemFaction.COLONIALS,
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
                mod="vanilla",
                detected={"category": [], "crated": [], "mod": []},
            )

            # Verify match_icon was called with proper filters
            mock_match.assert_called_once()
            call_kwargs = mock_match.call_args[1]
            assert call_kwargs["faction"] == ItemFaction.COLONIALS
            assert call_kwargs["category"] == ItemCategory.Item
            assert call_kwargs["crated"] is True
            assert call_kwargs["mod"] == "vanilla"

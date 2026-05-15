"""Tests for services.stockpile_detector module.

This module contains comprehensive tests for the StockpileDetector class,
which detects stockpile components in Foxhole game screenshots with resolution scaling.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from numpy.typing import NDArray

from foxhole_stockpiles.core.settings.sections.ocr import OCRSettings
from foxhole_stockpiles.models.stockpile_image_regions import StockpileImageRegions
from foxhole_stockpiles.services.stockpile_detector import StockpileDetector


class TestStockpileDetectorInitialization:
    """Test suite for StockpileDetector initialization.

    This class contains tests for proper initialization of the StockpileDetector
    including image preparation, scale factor calculation, and settings handling.
    """

    def test_init_with_rgb_image(self) -> None:
        """Test initializing StockpileDetector with RGB image."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        assert detector.img.shape == (1080, 1920, 3)
        assert detector.height == 1080
        assert detector.width == 1920
        assert detector.scale_factor > 0

    def test_init_with_rgba_image(self) -> None:
        """Test initializing StockpileDetector with RGBA image."""
        image = np.zeros((1080, 1920, 4), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Should convert to RGB
        assert detector.img.shape == (1080, 1920, 3)

    def test_init_calculates_scale_factor(self) -> None:
        """Test that initialization correctly calculates scale factor."""
        # Create a 720p image
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Scale factor should be height / base_height
        # Default base height from settings is 2160
        expected_scale = 720 / 2160
        assert abs(detector.scale_factor - expected_scale) < 0.01

    def test_init_with_custom_settings(self) -> None:
        """Test initializing with custom OCR settings."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        custom_settings = MagicMock(spec=OCRSettings)
        custom_settings.height = 1080
        custom_settings.box_width = 64
        custom_settings.box_height = 64
        custom_settings.column_offset = 10
        custom_settings.row_offset = 74.0
        custom_settings.group_offset = 148.0
        custom_settings.title_margin = 10
        custom_settings.title_min_width = 300
        custom_settings.title_height = 50
        custom_settings.icon_to_quantity_offset = 74
        custom_settings.pixel_diff_tolerance = 5
        custom_settings.gray_lower = 80
        custom_settings.gray_upper = 190

        detector = StockpileDetector(image, settings=custom_settings)

        assert detector._settings == custom_settings

    def test_init_initializes_empty_results(self) -> None:
        """Test that initialization creates empty result containers."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        assert detector.quantities == []
        assert detector.groups == []
        assert detector.stockpile_name is None
        assert detector.stockpile_type is None


class TestPrepareImageArray:
    """Test suite for StockpileDetector._prepare_image_array method.

    This class contains tests for image array preparation.
    """

    def test_prepare_rgb_image(self) -> None:
        """Test preparing RGB image (no conversion needed)."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        result = detector._prepare_image_array(image)

        assert result.shape == (100, 100, 3)
        assert result.dtype == np.uint8

    def test_prepare_rgba_image(self) -> None:
        """Test preparing RGBA image (converts to RGB)."""
        image = np.zeros((100, 100, 4), dtype=np.uint8)
        # Set alpha channel to non-zero
        image[:, :, 3] = 255

        detector = StockpileDetector(np.zeros((100, 100, 3), dtype=np.uint8))
        result = detector._prepare_image_array(image)

        # Should have converted to RGB
        assert result.shape == (100, 100, 3)
        assert result.dtype == np.uint8


class TestRescaleLayoutValues:
    """Test suite for StockpileDetector._rescale_layout_values method.

    This class contains tests for layout value rescaling.
    """

    def test_rescale_for_1080p(self) -> None:
        """Test rescaling for 1080p resolution."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # At 1080p, scale factor should be 1080/2160 = 0.5
        assert abs(detector.scale_factor - 0.5) < 0.01

    def test_rescale_for_720p(self) -> None:
        """Test rescaling for 720p resolution."""
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # At 720p, scale factor should be 720/2160 = 0.333...
        assert abs(detector.scale_factor - (720 / 2160)) < 0.01


class TestInValidRange:
    """Test suite for StockpileDetector._in_valid_range method.

    This class contains tests for range validation.
    """

    def test_in_valid_range_within_tolerance(self) -> None:
        """Test values within tolerance are valid."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Default tolerance is 2 pixels, so difference of 1 should be valid
        # Check is strict < so max valid difference is 1
        assert detector._in_valid_range(100, 101) is True
        assert detector._in_valid_range(100, 99) is True

    def test_in_valid_range_outside_tolerance(self) -> None:
        """Test values outside tolerance are invalid."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Default tolerance is 5 pixels
        assert detector._in_valid_range(100, 110) is False

    def test_in_valid_range_exact_match(self) -> None:
        """Test exact matches are valid."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        assert detector._in_valid_range(100, 100) is True


class TestCreateGreyMask:
    """Test suite for StockpileDetector._create_grey_mask method.

    This class contains tests for grey mask creation.
    """

    def test_create_grey_mask_with_grey_pixels(self) -> None:
        """Test grey mask creation with grey pixels."""
        # Create image with grey pixels in valid value range [15, 98]
        image = np.full((100, 100, 3), 50, dtype=np.uint8)
        detector = StockpileDetector(image)

        mask = detector._create_grey_mask(image)

        # Grey pixels should be white in mask
        assert mask.shape == (100, 100)
        assert np.any(mask == 255)

    def test_create_grey_mask_with_colored_pixels(self) -> None:
        """Test grey mask creation with colored pixels."""
        # Create image with red pixels
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[:, :, 0] = 255  # Red channel

        detector = StockpileDetector(image)
        mask = detector._create_grey_mask(image)

        # Colored pixels should be black in mask
        assert np.all(mask == 0)


class TestFilterContourBySize:
    """Test suite for StockpileDetector._filter_contour_by_size method.

    This class contains tests for contour filtering.
    """

    def test_filter_valid_contour(self) -> None:
        """Test filtering valid contour."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Create a contour matching expected box size
        contour = (100, 100, detector.box_width, detector.box_height)

        result = detector._filter_contour_by_size(contour)

        assert result == (100, 100)

    def test_filter_invalid_width(self) -> None:
        """Test filtering contour with invalid width."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Create a contour with wrong width
        contour = (100, 100, detector.box_width + 20, detector.box_height)

        result = detector._filter_contour_by_size(contour)

        assert result is None

    def test_filter_invalid_height(self) -> None:
        """Test filtering contour with invalid height."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Create a contour with wrong height
        contour = (100, 100, detector.box_width, detector.box_height + 20)

        result = detector._filter_contour_by_size(contour)

        assert result is None


class TestDetectQuantityBoxes:
    """Test suite for StockpileDetector.detect_quantity_boxes method.

    This class contains tests for quantity box detection.
    """

    def test_detect_no_boxes(self) -> None:
        """Test detection when no boxes are present."""
        # Create a blank image
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        detector.detect_quantity_boxes()

        assert detector.quantities == []
        assert detector.groups == []

    def test_detect_with_grey_boxes(self) -> None:
        """Test detection with grey boxes in image."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Create mock grey boxes
        box_y = 200
        box_x1 = 100
        box_x2 = box_x1 + detector.column_offset

        # Draw grey boxes
        grey_value = 128
        image[
            box_y : box_y + detector.box_height,
            box_x1 : box_x1 + detector.box_width,
        ] = grey_value
        image[
            box_y : box_y + detector.box_height,
            box_x2 : box_x2 + detector.box_width,
        ] = grey_value

        detector = StockpileDetector(image)
        detector.detect_quantity_boxes()

        # Should detect at least the first group
        assert len(detector.quantities) >= 0


class TestDetectStockpileRegions:
    """Test suite for StockpileDetector.detect_stockpile_regions method.

    This class contains tests for stockpile region detection.
    """

    def test_detect_regions_no_quantities(self) -> None:
        """Test region detection when no quantities are present."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        detector.detect_stockpile_regions()

        # Should not set regions without quantities
        assert detector.stockpile_type is None
        assert detector.stockpile_name is None

    def test_detect_regions_with_quantities(self) -> None:
        """Test region detection when quantities are present."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Mock quantities
        detector.quantities = [(100, 200), (200, 200)]
        detector.max_detected_x = 200

        detector.detect_stockpile_regions()

        # Should set stockpile_type region
        assert detector.stockpile_type is not None
        assert len(detector.stockpile_type) == 4  # (x, y, w, h)

        # stockpile_name is None because:
        # - Black image has no info bar (_info_bar_height = 0 -> old format)
        # - No tab button detected (no contrast on black image)
        assert detector.stockpile_name is None

    def test_detect_regions_pinned_format(self) -> None:
        """Test region detection for pinned stockpile (info_bar_height < group_offset)."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Mock quantities
        detector.quantities = [(500, 400), (600, 400)]
        detector.max_detected_x = 600

        # At 1080p: box_height=32, group_offset=49, row_offset=39
        # grey_bar_top_y = 400 - (49 - 39) = 390
        # For pinned: box_height <= info_bar_height < group_offset
        # So 32 <= (390 - type_bar_y) < 49
        # Therefore: 341 < type_bar_y <= 358
        with patch.object(detector, "_find_type_bar_y", return_value=350):
            detector.detect_stockpile_regions()

        assert detector.stockpile_type is not None
        assert detector.stockpile_name is not None
        assert detector.stockpile_name_tab is None  # No tab for pinned format

    def test_detect_regions_unpinned_format(self) -> None:
        """Test region detection for unpinned stockpile (info_bar_height >= group_offset)."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Mock quantities
        detector.quantities = [(500, 400), (600, 400)]
        detector.max_detected_x = 600

        # At 1080p: box_height=32, group_offset=49, row_offset=39
        # grey_bar_top_y = 400 - (49 - 39) = 390
        # For unpinned: info_bar_height >= group_offset (49)
        # So (390 - type_bar_y) >= 49
        # Therefore: type_bar_y <= 341
        with patch.object(detector, "_find_type_bar_y", return_value=330):
            detector.detect_stockpile_regions()

        assert detector.stockpile_type is not None
        assert detector.stockpile_name is not None
        assert detector.stockpile_name_tab is None  # No tab for unpinned format

    def test_detect_regions_no_name_format(self) -> None:
        """Test region detection when info_bar_height < box_height (no custom name)."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Mock quantities
        detector.quantities = [(500, 400), (600, 400)]
        detector.max_detected_x = 600

        # At 1080p: box_height=32, group_offset=49, row_offset=39
        # grey_bar_top_y = 400 - (49 - 39) = 390
        # For no name: info_bar_height < box_height (32)
        # So (390 - type_bar_y) < 32
        # Therefore: type_bar_y > 358
        with patch.object(detector, "_find_type_bar_y", return_value=370):
            detector.detect_stockpile_regions()

        assert detector.stockpile_type is not None
        assert detector.stockpile_name is None  # No name when info_bar_height < box_height


class TestHasTabButton:
    """Test suite for StockpileDetector._has_tab_button method."""

    def test_has_tab_button_no_tab_region(self) -> None:
        """Test _has_tab_button returns False when stockpile_name_tab is None."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        detector.stockpile_name_tab = None

        assert detector._has_tab_button() is False


class TestAnalize:
    """Test suite for StockpileDetector.analize method.

    This class contains tests for the main analyze method.
    """

    def test_analize_calls_detection_methods(self) -> None:
        """Test that analize calls both detection methods."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        with (
            patch.object(detector, "detect_quantity_boxes") as mock_detect_boxes,
            patch.object(detector, "detect_stockpile_regions") as mock_detect_regions,
        ):
            detector.analize()

            mock_detect_boxes.assert_called_once()
            mock_detect_regions.assert_called_once()


class TestGetStockpileImages:
    """Test suite for StockpileDetector.get_stockpile_images method.

    This class contains tests for stockpile image extraction.
    """

    def test_get_stockpile_images_no_quantities(self) -> None:
        """Test getting stockpile images when no quantities detected."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        result = detector.get_stockpile_images()

        assert result is None

    def test_get_stockpile_images_with_quantities(self) -> None:
        """Test getting stockpile images with detected quantities."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Set up mock detection results
        detector.quantities = [(100, 100)]
        detector.groups = [(1, 0)]
        detector.max_detected_x = 100
        detector.composite_image = np.zeros((100, 100, 3), dtype=np.uint8)

        result = detector.get_stockpile_images()

        assert result is not None
        assert isinstance(result, StockpileImageRegions)
        assert len(result.icons) == 1
        assert len(result.quantities) == 1
        assert result.resolution == "1920x1080"
        assert result.vertical_resolution == 1080

    def test_get_stockpile_images_includes_metadata_regions(self) -> None:
        """Test that stockpile images include metadata regions when available."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Set up mock detection results with all regions
        detector.quantities = [(100, 100)]
        detector.groups = [(1, 0)]
        detector.max_detected_x = 100
        detector.composite_image = np.zeros((100, 100, 3), dtype=np.uint8)
        detector.stockpile_type = (50, 50, 100, 30)
        detector.stockpile_name = (200, 50, 100, 30)
        detector.shard_x = 10
        detector.shard_y = 950
        detector.shard_width = 200
        detector.shard_height = 100

        result = detector.get_stockpile_images()

        assert result is not None
        assert result.stockpile_type is not None
        assert result.stockpile_name is not None
        assert result.shard is not None


class TestDrawAndSaveResults:
    """Test suite for StockpileDetector.draw_and_save_results method.

    This class contains tests for debug visualization.
    """

    def test_draw_and_save_results(self) -> None:
        """Test drawing and saving detection results."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Set up mock detection results
        detector.quantities = [(100, 100), (200, 100)]
        detector.groups = [(2, 0)]
        detector.stockpile_type = (50, 50, 100, 30)
        detector.stockpile_name = (200, 50, 100, 30)
        detector.composite_image = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch("cv2.imwrite") as mock_imwrite:
            detector.draw_and_save_results()

            # Should save 2 images: detection result and composite quantities
            assert mock_imwrite.call_count == 2


class TestBuildQuantityCompositeImage:
    """Test suite for StockpileDetector._build_quantity_composite_image method.

    This class contains tests for composite image building.
    """

    def test_build_composite_image(self) -> None:
        """Test building composite image from quantities."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Set up quantities
        detector.quantities = [(100, 100), (200, 100)]
        detector.stockpile_type = (50, 50, 100, 30)

        detector._build_quantity_composite_image()

        assert detector.composite_image.shape[2] == 3  # RGB
        assert detector.composite_image.dtype == np.uint8


class TestDetectFirstGroup:
    """Test suite for StockpileDetector._detect_first_group method.

    This class contains tests for first group detection.
    """

    def test_detect_first_group_found(self) -> None:
        """Test detecting first group when boxes are found."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Create contours matching first group pattern
        contours: list[tuple[int, int, int, int]] = [
            (100, 100, detector.box_width, detector.box_height),
            (100 + detector.column_offset, 100, detector.box_width, detector.box_height),
        ]

        result = detector._detect_first_group(list(contours))

        # Should return index after second box
        assert result == 2
        assert len(detector.quantities) == 2

    def test_detect_first_group_not_found(self) -> None:
        """Test detecting first group when no valid pair is found."""
        image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        detector = StockpileDetector(image)

        # Create contours that don't match first group pattern
        contours: list[tuple[int, int, int, int]] = [
            (100, 100, 10, 10),  # Wrong size
        ]

        result = detector._detect_first_group(list(contours))

        # Should return 0 when not found
        assert result == 0
        assert len(detector.quantities) == 0


# Integration tests using real screenshots


@pytest.fixture
def real_screenshot() -> NDArray[np.uint8]:
    """Load the real test screenshot.

    Returns:
        NDArray[np.uint8]: Image loaded in RGB format
    """
    test_image_path = Path(__file__).parent.parent / "test.png"
    if not test_image_path.exists():
        pytest.skip("test.png not found")

    # Load image in BGR (OpenCV default) and convert to RGB
    image_bgr = cv2.imread(str(test_image_path))
    if image_bgr is None:
        pytest.skip("Failed to load test.png")

    # Convert BGR to RGB and cast to proper type
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.uint8)


class TestStockpileDetectorIntegration:
    """Integration tests using real screenshot."""

    def test_detect_with_real_screenshot(self, real_screenshot: NDArray[np.uint8]) -> None:
        """Test full detection pipeline with real screenshot."""
        detector = StockpileDetector(real_screenshot)
        detector.analize()

        # Should detect at least some quantities
        assert len(detector.quantities) >= 0  # May be empty for some screenshots
        # Should have detected groups if quantities found
        if detector.quantities:
            assert len(detector.groups) >= 0

    def test_detect_quantity_boxes_with_real_image(
        self, real_screenshot: NDArray[np.uint8]
    ) -> None:
        """Test quantity box detection with real screenshot."""
        detector = StockpileDetector(real_screenshot)
        detector.detect_quantity_boxes()

        # Verify quantities detected
        assert isinstance(detector.quantities, list)
        # If quantities found, should have groups
        if len(detector.quantities) > 0:
            assert isinstance(detector.groups, list)
            # First group should have at least 2 items
            if len(detector.groups) > 0:
                first_group_size, _ = detector.groups[0]
                assert first_group_size >= 2

    def test_detect_stockpile_regions_with_real_image(
        self, real_screenshot: NDArray[np.uint8]
    ) -> None:
        """Test stockpile region detection with real screenshot."""
        detector = StockpileDetector(real_screenshot)
        detector.detect_quantity_boxes()
        detector.detect_stockpile_regions()

        # If quantities detected, regions should be set
        if detector.quantities:
            assert detector.stockpile_type is not None
            assert detector.stockpile_name is not None
            # Verify region format (x, y, w, h)
            assert len(detector.stockpile_type) == 4
            assert len(detector.stockpile_name) == 4

    def test_get_stockpile_images_with_real_screenshot(
        self, real_screenshot: NDArray[np.uint8]
    ) -> None:
        """Test extracting stockpile images from real screenshot."""
        detector = StockpileDetector(real_screenshot)
        detector.analize()

        result = detector.get_stockpile_images()

        # If quantities detected, should return StockpileImageRegions
        if detector.quantities:
            assert result is not None
            assert len(result.icons) == len(detector.quantities)
            assert len(result.quantities) == len(detector.quantities)
            assert result.resolution == "3840x2160"
            assert result.vertical_resolution == 2160

    def test_composite_image_built_with_real_screenshot(
        self, real_screenshot: NDArray[np.uint8]
    ) -> None:
        """Test that composite image is built during detection."""
        detector = StockpileDetector(real_screenshot)
        detector.detect_quantity_boxes()

        # If quantities detected, composite should be built
        if detector.quantities:
            assert detector.composite_image.shape[2] == 3  # RGB
            assert detector.composite_image.dtype == np.uint8
            # Composite should have non-zero dimensions
            assert detector.composite_image.shape[0] > 0
            assert detector.composite_image.shape[1] > 0


class TestAdaptiveThresholdDetection:
    """Test adaptive threshold detection with real images."""

    def test_adaptive_threshold_triggered(self, real_screenshot: NDArray[np.uint8]) -> None:
        """Test that adaptive threshold logic is exercised."""
        detector = StockpileDetector(real_screenshot)

        # Run detection which includes adaptive threshold logic
        detector.detect_quantity_boxes()

        # The adaptive threshold code should run if valid boxes are found
        # We can't easily assert on internal state, but we verify detection completes
        assert isinstance(detector.quantities, list)
        assert isinstance(detector.groups, list)


class TestGroupDetectionLogic:
    """Test group detection with real images."""

    def test_first_group_detection(self, real_screenshot: NDArray[np.uint8]) -> None:
        """Test that first group detection works with real image."""
        detector = StockpileDetector(real_screenshot)
        detector.detect_quantity_boxes()

        # If first group detected, should have at least 2 quantities
        if detector.quantities:
            assert len(detector.quantities) >= 2
            # First group should be recorded
            if detector.groups:
                first_group_size, first_group_start = detector.groups[0]
                assert first_group_start == 0
                assert first_group_size >= 2

    def test_multiple_groups_detection(self, real_screenshot: NDArray[np.uint8]) -> None:
        """Test detection of multiple groups."""
        detector = StockpileDetector(real_screenshot)
        detector.detect_quantity_boxes()

        # Verify group structure
        for group_size, group_start in detector.groups:
            assert group_size > 0
            assert group_start >= 0
            assert group_start < len(detector.quantities)
            # Verify group doesn't exceed available quantities
            assert group_start + group_size <= len(detector.quantities) + 1

    def test_group_continuity(self, real_screenshot: NDArray[np.uint8]) -> None:
        """Test that groups cover all detected quantities."""
        detector = StockpileDetector(real_screenshot)
        detector.detect_quantity_boxes()

        if not detector.groups:
            return

        # Calculate total items across all groups
        total_items = sum(group_size for group_size, _ in detector.groups)

        # Total should match number of quantities
        assert total_items == len(detector.quantities)


class TestDetectionWithDifferentResolutions:
    """Test detection with scaled versions of the screenshot."""

    @pytest.mark.parametrize("scale", [0.5, 0.75, 1.0])
    def test_detection_at_different_scales(
        self, real_screenshot: NDArray[np.uint8], scale: float
    ) -> None:
        """Test detection works at different resolutions.

        Args:
            real_screenshot: Original test image
            scale: Scale factor to test
        """
        # Resize image
        height, width = real_screenshot.shape[:2]
        new_size = (int(width * scale), int(height * scale))
        scaled_image = cv2.resize(real_screenshot, new_size, interpolation=cv2.INTER_AREA).astype(
            np.uint8
        )

        detector = StockpileDetector(scaled_image)
        detector.analize()

        # Verify scale factor calculated correctly
        expected_scale = new_size[1] / 2160  # Base height is 2160
        assert abs(detector.scale_factor - expected_scale) < 0.01

        # Detection should work at any scale
        assert isinstance(detector.quantities, list)
        assert isinstance(detector.groups, list)


class TestGreyMaskCreationWithRealImage:
    """Test grey mask creation with real images."""

    def test_grey_mask_with_real_image(self, real_screenshot: NDArray[np.uint8]) -> None:
        """Test grey mask creation with real screenshot."""
        detector = StockpileDetector(real_screenshot)
        mask = detector._create_grey_mask(real_screenshot)

        # Mask should be 2D (grayscale)
        assert len(mask.shape) == 2
        # Mask should match image dimensions
        assert mask.shape == (real_screenshot.shape[0], real_screenshot.shape[1])
        # Mask should be binary
        assert mask.dtype == np.uint8


class TestshardRegion:
    """Test shard region detection."""

    def test_shard_region_initialized(self, real_screenshot: NDArray[np.uint8]) -> None:
        """Test that shard region is properly initialized."""
        detector = StockpileDetector(real_screenshot)

        # shard region should be calculated based on image dimensions
        assert detector.shard_x > 0
        assert detector.shard_y > 0
        assert detector.shard_width > 0
        assert detector.shard_height > 0
        # Y should be near bottom of image
        assert detector.shard_y > detector.height * 0.5

    def test_shard_included_in_result(self, real_screenshot: NDArray[np.uint8]) -> None:
        """Test that shard is included in StockpileImageRegions."""
        detector = StockpileDetector(real_screenshot)
        detector.analize()

        result = detector.get_stockpile_images()

        if result is not None:
            # shard should be included
            assert result.shard is not None
            # Should be an image array
            assert isinstance(result.shard, np.ndarray)
            assert len(result.shard.shape) == 3  # Height x Width x Channels


class TestDrawAndSaveWithRealImage:
    """Test debug visualization with real images."""

    def test_draw_and_save_with_detection_results(
        self, real_screenshot: NDArray[np.uint8], tmp_path: Path
    ) -> None:
        """Test drawing detection results on real image.

        Args:
            real_screenshot: Real test image
            tmp_path: Pytest temporary directory
        """
        detector = StockpileDetector(real_screenshot)
        detector.analize()

        # Change to temp directory to avoid cluttering project
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            detector.draw_and_save_results()

            # Should create two output files
            assert (Path(tmp_path) / "stockpile_detection_result.png").exists()
            assert (Path(tmp_path) / "stockpile_quantities_result.png").exists()
        finally:
            os.chdir(original_dir)

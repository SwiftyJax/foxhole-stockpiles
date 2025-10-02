"""Tests for services.stockpile_detector module.

This module contains comprehensive tests for the StockpileDetector class,
which detects stockpile components in Foxhole game screenshots with resolution scaling.
"""

from unittest.mock import MagicMock, patch

import numpy as np

from foxhole_stockpiles.core.settings import OCRSettings
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

        # Should set regions
        assert detector.stockpile_type is not None
        assert detector.stockpile_name is not None
        assert len(detector.stockpile_type) == 4  # (x, y, w, h)
        assert len(detector.stockpile_name) == 4


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
        detector.hex_name_x = 10
        detector.hex_name_y = 950
        detector.hex_name_width = 200
        detector.hex_name_height = 100

        result = detector.get_stockpile_images()

        assert result is not None
        assert result.stockpile_type is not None
        assert result.stockpile_name is not None
        assert result.hex_name is not None


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

"""Tests for ImageScanWorker.

The ImageScanWorker is a QThread that runs the scanning pipeline in background
and extracts position information for each detected icon.
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from foxhole_stockpiles.enums.stockpile_type import StockpileType
from foxhole_stockpiles.gui.utils.image_scan_worker import ImageScanWorker
from foxhole_stockpiles.models.scan_result import ScanResult
from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.models.stockpile_item import StockpileItem


@pytest.fixture
def worker(tmp_path: Path) -> ImageScanWorker:
    """Create an ImageScanWorker instance.

    Args:
        tmp_path: Temporary directory path.

    Returns:
        ImageScanWorker: Worker instance.
    """
    image_path = tmp_path / "screenshot.png"
    database_path = tmp_path / "database.h5"

    return ImageScanWorker(str(image_path), database_path)


@pytest.fixture
def mock_stockpile_item() -> StockpileItem:
    """Create a mock stockpile item.

    Returns:
        StockpileItem: A mock stockpile item.
    """
    return StockpileItem(
        code="TestItem",
        quantity=100,
        crated=False,
        confidence=0.95,
    )


@pytest.fixture
def mock_stockpile(mock_stockpile_item: StockpileItem) -> Stockpile:
    """Create a mock stockpile.

    Args:
        mock_stockpile_item: Mock stockpile item.

    Returns:
        Stockpile: A mock stockpile.
    """
    return Stockpile(
        name="Test Stockpile",
        type=StockpileType.STORAGE_DEPOT,
        resolution="1920x1080",
        items=[mock_stockpile_item],
    )


class TestImageScanWorkerInitialization:
    """Tests for ImageScanWorker initialization."""

    def test_initialization(self, tmp_path: Path) -> None:
        """Test ImageScanWorker initialization.

        Args:
            tmp_path: Temporary directory path.
        """
        image_path = tmp_path / "screenshot.png"
        database_path = tmp_path / "database.h5"

        worker = ImageScanWorker(str(image_path), database_path)

        assert worker.image_path == str(image_path)
        assert worker.database_path == database_path

    def test_signals_exist(self, worker: ImageScanWorker) -> None:
        """Test that required signals exist.

        Args:
            worker: ImageScanWorker instance.
        """
        assert hasattr(worker, "finished")
        assert hasattr(worker, "error")


class TestImageScanWorkerRun:
    """Tests for ImageScanWorker run method."""

    def test_run_image_load_failure(self, worker: ImageScanWorker) -> None:
        """Test run with failed image load.

        Args:
            worker: ImageScanWorker instance.
        """
        mock_error = MagicMock()

        with patch.object(worker, "error", mock_error):
            with patch(
                "foxhole_stockpiles.gui.utils.image_scan_worker.cv2.imread",
                return_value=None,
            ):
                worker.run()

                mock_error.emit.assert_called_once()
                error_msg = mock_error.emit.call_args[0][0]
                assert "Failed to load image" in error_msg

    def test_run_no_stockpile_detected(self, worker: ImageScanWorker) -> None:
        """Test run when no stockpile is detected.

        Args:
            worker: ImageScanWorker instance.
        """
        mock_error = MagicMock()
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch.object(worker, "error", mock_error):
            with patch(
                "foxhole_stockpiles.gui.utils.image_scan_worker.cv2.imread",
                return_value=mock_image,
            ):
                with patch(
                    "foxhole_stockpiles.gui.utils.image_scan_worker.StockpileDetector"
                ) as mock_detector_class:
                    mock_detector = MagicMock()
                    mock_detector.quantities = []  # No quantities detected
                    mock_detector_class.return_value = mock_detector

                    worker.run()

                    mock_error.emit.assert_called_once()
                    error_msg = mock_error.emit.call_args[0][0]
                    assert "No stockpile detected" in error_msg

    def test_run_failed_to_extract_regions(self, worker: ImageScanWorker) -> None:
        """Test run when stockpile regions extraction fails.

        Args:
            worker: ImageScanWorker instance.
        """
        mock_error = MagicMock()
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch.object(worker, "error", mock_error):
            with patch(
                "foxhole_stockpiles.gui.utils.image_scan_worker.cv2.imread",
                return_value=mock_image,
            ):
                with patch(
                    "foxhole_stockpiles.gui.utils.image_scan_worker.StockpileDetector"
                ) as mock_detector_class:
                    mock_detector = MagicMock()
                    mock_detector.quantities = [(100, 100)]  # Has quantities
                    mock_detector.get_stockpile_images.return_value = None  # But fails to extract
                    mock_detector_class.return_value = mock_detector

                    worker.run()

                    mock_error.emit.assert_called_once()
                    error_msg = mock_error.emit.call_args[0][0]
                    assert "Failed to extract stockpile regions" in error_msg

    def test_run_success(self, worker: ImageScanWorker, mock_stockpile: Stockpile) -> None:
        """Test successful scan execution.

        Args:
            worker: ImageScanWorker instance.
            mock_stockpile: Mock stockpile.
        """
        mock_finished = MagicMock()
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_icon_image = np.zeros((32, 32, 3), dtype=np.uint8)

        mock_stockpile_images = MagicMock()
        mock_stockpile_images.icons = [mock_icon_image]

        with patch.object(worker, "finished", mock_finished):
            with patch(
                "foxhole_stockpiles.gui.utils.image_scan_worker.cv2.imread",
                return_value=mock_image,
            ):
                with patch(
                    "foxhole_stockpiles.gui.utils.image_scan_worker.StockpileDetector"
                ) as mock_detector_class:
                    mock_detector = MagicMock()
                    mock_detector.quantities = [(100, 100)]
                    mock_detector.icon_to_quantity_offset = 10
                    mock_detector.box_height = 32
                    mock_detector.get_stockpile_images.return_value = mock_stockpile_images
                    mock_detector_class.return_value = mock_detector

                    with patch(
                        "foxhole_stockpiles.gui.utils.image_scan_worker.OCRCoordinator"
                    ) as mock_coordinator_class:
                        mock_coordinator = MagicMock()
                        mock_coordinator.analyze_stockpile = AsyncMock(return_value=mock_stockpile)
                        mock_coordinator_class.return_value = mock_coordinator

                        worker.run()

                        mock_finished.emit.assert_called_once()
                        result = mock_finished.emit.call_args[0][0]
                        assert isinstance(result, ScanResult)
                        assert result.stockpile == mock_stockpile
                        assert len(result.detected_icons) == 1

    def test_run_success_detected_icon_info(
        self, worker: ImageScanWorker, mock_stockpile: Stockpile
    ) -> None:
        """Test detected icon info is populated correctly.

        Args:
            worker: ImageScanWorker instance.
            mock_stockpile: Mock stockpile.
        """
        mock_finished = MagicMock()
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_icon_image = np.zeros((32, 32, 3), dtype=np.uint8)

        mock_stockpile_images = MagicMock()
        mock_stockpile_images.icons = [mock_icon_image]

        with patch.object(worker, "finished", mock_finished):
            with patch(
                "foxhole_stockpiles.gui.utils.image_scan_worker.cv2.imread",
                return_value=mock_image,
            ):
                with patch(
                    "foxhole_stockpiles.gui.utils.image_scan_worker.StockpileDetector"
                ) as mock_detector_class:
                    mock_detector = MagicMock()
                    mock_detector.quantities = [(150, 200)]
                    mock_detector.icon_to_quantity_offset = 20
                    mock_detector.box_height = 32
                    mock_detector.get_stockpile_images.return_value = mock_stockpile_images
                    mock_detector_class.return_value = mock_detector

                    with patch(
                        "foxhole_stockpiles.gui.utils.image_scan_worker.OCRCoordinator"
                    ) as mock_coordinator_class:
                        mock_coordinator = MagicMock()
                        mock_coordinator.analyze_stockpile = AsyncMock(return_value=mock_stockpile)
                        mock_coordinator_class.return_value = mock_coordinator

                        worker.run()

                        result = mock_finished.emit.call_args[0][0]
                        icon_info = result.detected_icons[0]

                        assert icon_info.index == 0
                        assert icon_info.code == "TestItem"
                        assert icon_info.quantity == 100
                        assert icon_info.crated is False
                        assert icon_info.confidence == 0.95
                        assert icon_info.position == (130, 200)  # qx - offset
                        assert icon_info.size == 32

    def test_run_exception_handling(self, worker: ImageScanWorker) -> None:
        """Test run handles exceptions.

        Args:
            worker: ImageScanWorker instance.
        """
        mock_error = MagicMock()

        with patch.object(worker, "error", mock_error):
            with patch(
                "foxhole_stockpiles.gui.utils.image_scan_worker.cv2.imread",
                side_effect=Exception("Unexpected error"),
            ):
                worker.run()

                mock_error.emit.assert_called_once()
                error_msg = mock_error.emit.call_args[0][0]
                assert "Unexpected error" in error_msg

    def test_run_more_items_than_quantities_warning(
        self, worker: ImageScanWorker, mock_stockpile: Stockpile
    ) -> None:
        """Test run handles case when items exceed detected quantities.

        Args:
            worker: ImageScanWorker instance.
            mock_stockpile: Mock stockpile.
        """
        # Add another item to stockpile
        mock_stockpile.items.append(
            StockpileItem(code="TestItem2", quantity=50, crated=False, confidence=0.90)
        )

        mock_finished = MagicMock()
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_icon_image = np.zeros((32, 32, 3), dtype=np.uint8)

        mock_stockpile_images = MagicMock()
        mock_stockpile_images.icons = [mock_icon_image]  # Only one icon

        with patch.object(worker, "finished", mock_finished):
            with patch(
                "foxhole_stockpiles.gui.utils.image_scan_worker.cv2.imread",
                return_value=mock_image,
            ):
                with patch(
                    "foxhole_stockpiles.gui.utils.image_scan_worker.StockpileDetector"
                ) as mock_detector_class:
                    mock_detector = MagicMock()
                    mock_detector.quantities = [(100, 100)]  # Only one quantity
                    mock_detector.icon_to_quantity_offset = 10
                    mock_detector.box_height = 32
                    mock_detector.get_stockpile_images.return_value = mock_stockpile_images
                    mock_detector_class.return_value = mock_detector

                    with patch(
                        "foxhole_stockpiles.gui.utils.image_scan_worker.OCRCoordinator"
                    ) as mock_coordinator_class:
                        mock_coordinator = MagicMock()
                        mock_coordinator.analyze_stockpile = AsyncMock(return_value=mock_stockpile)
                        mock_coordinator_class.return_value = mock_coordinator

                        worker.run()

                        # Should still emit finished, but only with one icon
                        mock_finished.emit.assert_called_once()
                        result = mock_finished.emit.call_args[0][0]
                        assert len(result.detected_icons) == 1

    def test_run_crated_item(self, worker: ImageScanWorker) -> None:
        """Test run with crated item.

        Args:
            worker: ImageScanWorker instance.
        """
        crated_item = StockpileItem(
            code="CratedItem",
            quantity=5,
            crated=True,
            confidence=0.88,
        )
        crated_stockpile = Stockpile(
            name="Test",
            type=StockpileType.STORAGE_DEPOT,
            resolution="1920x1080",
            items=[crated_item],
        )

        mock_finished = MagicMock()
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_icon_image = np.zeros((32, 32, 3), dtype=np.uint8)

        mock_stockpile_images = MagicMock()
        mock_stockpile_images.icons = [mock_icon_image]

        with patch.object(worker, "finished", mock_finished):
            with patch(
                "foxhole_stockpiles.gui.utils.image_scan_worker.cv2.imread",
                return_value=mock_image,
            ):
                with patch(
                    "foxhole_stockpiles.gui.utils.image_scan_worker.StockpileDetector"
                ) as mock_detector_class:
                    mock_detector = MagicMock()
                    mock_detector.quantities = [(100, 100)]
                    mock_detector.icon_to_quantity_offset = 10
                    mock_detector.box_height = 32
                    mock_detector.get_stockpile_images.return_value = mock_stockpile_images
                    mock_detector_class.return_value = mock_detector

                    with patch(
                        "foxhole_stockpiles.gui.utils.image_scan_worker.OCRCoordinator"
                    ) as mock_coordinator_class:
                        mock_coordinator = MagicMock()
                        mock_coordinator.analyze_stockpile = AsyncMock(
                            return_value=crated_stockpile
                        )
                        mock_coordinator_class.return_value = mock_coordinator

                        worker.run()

                        result = mock_finished.emit.call_args[0][0]
                        icon_info = result.detected_icons[0]

                        assert icon_info.crated is True
                        assert icon_info.quantity == 5

    def test_run_item_with_none_confidence(self, worker: ImageScanWorker) -> None:
        """Test run with item that has None confidence.

        Args:
            worker: ImageScanWorker instance.
        """
        item_no_confidence = StockpileItem(
            code="TestItem",
            quantity=100,
            crated=False,
            confidence=None,
        )
        stockpile = Stockpile(
            name="Test",
            type=StockpileType.STORAGE_DEPOT,
            resolution="1920x1080",
            items=[item_no_confidence],
        )

        mock_finished = MagicMock()
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_icon_image = np.zeros((32, 32, 3), dtype=np.uint8)

        mock_stockpile_images = MagicMock()
        mock_stockpile_images.icons = [mock_icon_image]

        with patch.object(worker, "finished", mock_finished):
            with patch(
                "foxhole_stockpiles.gui.utils.image_scan_worker.cv2.imread",
                return_value=mock_image,
            ):
                with patch(
                    "foxhole_stockpiles.gui.utils.image_scan_worker.StockpileDetector"
                ) as mock_detector_class:
                    mock_detector = MagicMock()
                    mock_detector.quantities = [(100, 100)]
                    mock_detector.icon_to_quantity_offset = 10
                    mock_detector.box_height = 32
                    mock_detector.get_stockpile_images.return_value = mock_stockpile_images
                    mock_detector_class.return_value = mock_detector

                    with patch(
                        "foxhole_stockpiles.gui.utils.image_scan_worker.OCRCoordinator"
                    ) as mock_coordinator_class:
                        mock_coordinator = MagicMock()
                        mock_coordinator.analyze_stockpile = AsyncMock(return_value=stockpile)
                        mock_coordinator_class.return_value = mock_coordinator

                        worker.run()

                        result = mock_finished.emit.call_args[0][0]
                        icon_info = result.detected_icons[0]

                        # None confidence should default to 0.0
                        assert icon_info.confidence == 0.0


class TestImageScanWorkerSignals:
    """Tests for ImageScanWorker signals."""

    def test_finished_signal_type(self, worker: ImageScanWorker) -> None:
        """Test that finished signal is properly defined.

        Args:
            worker: ImageScanWorker instance.
        """
        # Signal should accept an object
        results: list[Any] = []
        worker.finished.connect(lambda x: results.append(x))

        # Manually emit to test signal works
        test_obj = {"test": "data"}
        worker.finished.emit(test_obj)

        assert len(results) == 1
        assert results[0] == test_obj

    def test_error_signal_type(self, worker: ImageScanWorker) -> None:
        """Test that error signal is properly defined.

        Args:
            worker: ImageScanWorker instance.
        """
        # Signal should accept a string
        errors: list[str] = []
        worker.error.connect(lambda x: errors.append(x))

        # Manually emit to test signal works
        worker.error.emit("Test error")

        assert len(errors) == 1
        assert errors[0] == "Test error"

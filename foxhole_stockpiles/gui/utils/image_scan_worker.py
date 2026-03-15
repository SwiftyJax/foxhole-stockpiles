"""Worker thread for scanning a screenshot directly for debug viewer."""

import asyncio
import logging
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray
from PyQt6.QtCore import QThread, pyqtSignal

from foxhole_stockpiles.core.settings.sections.scanner import ScannerSettings
from foxhole_stockpiles.models.detected_icon_info import DetectedIconInfo
from foxhole_stockpiles.models.scan_result import ScanResult
from foxhole_stockpiles.services.ocr_coordinator import OCRCoordinator
from foxhole_stockpiles.services.stockpile_detector import StockpileDetector

logger = logging.getLogger(__name__)


class ImageScanWorker(QThread):
    """Background thread for scanning a screenshot directly.

    This worker runs the scanning pipeline and extracts additional position
    information for each detected icon, suitable for the debug viewer.
    """

    finished = pyqtSignal(object)  # ScanResult
    error = pyqtSignal(str)

    def __init__(self, image_path: str, database_path: Path) -> None:
        """Initialize the image scan worker.

        Args:
            image_path (str): Path to the screenshot file to scan.
            database_path (Path): Path to the template database file.
        """
        super().__init__()
        self.image_path = image_path
        self.database_path = database_path

    def run(self) -> None:
        """Run the scan in background thread.

        Emits:
            finished: Signal with ScanResult on success.
            error: Signal with error message on failure.
        """
        try:
            # Load image
            loaded = cv2.imread(self.image_path)
            if loaded is None:
                self.error.emit(f"Failed to load image: {self.image_path}")
                return
            image: NDArray[np.uint8] = np.asarray(loaded, dtype=np.uint8)

            # Get positions from detector
            detector = StockpileDetector(image)
            detector.analize()

            if not detector.quantities:
                self.error.emit("No stockpile detected in the image")
                return

            stockpile_images = detector.get_stockpile_images()
            if stockpile_images is None:
                self.error.emit("Failed to extract stockpile regions")
                return

            # Run scan using OCRCoordinator
            config = ScannerSettings(database_path=self.database_path)
            coordinator = OCRCoordinator(config=config)
            stockpile = asyncio.run(coordinator.analyze_stockpile(image))

            # Build DetectedIconInfo list
            detected_icons: list[DetectedIconInfo] = []
            for i, item in enumerate(stockpile.items):
                if i >= len(detector.quantities):
                    logger.warning("Item index %d exceeds detected quantities", i)
                    break

                qx, qy = detector.quantities[i]
                icon_x = qx - detector.icon_to_quantity_offset

                detected_icons.append(
                    DetectedIconInfo(
                        index=i,
                        code=item.code,
                        quantity=item.quantity,
                        crated=item.crated,
                        confidence=item.confidence or 0.0,
                        icon_image=stockpile_images.icons[i],
                        position=(icon_x, qy),
                        size=detector.box_height,
                    )
                )

            self.finished.emit(
                ScanResult(
                    stockpile=stockpile,
                    detected_icons=detected_icons,
                    original_image=image,
                )
            )

        except Exception as e:
            logger.exception("Failed to scan image")
            self.error.emit(str(e))

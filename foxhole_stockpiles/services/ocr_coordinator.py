"""OCR Coordinator service for orchestrating stockpile detection."""

import logging
from typing import Any, ClassVar

import cv2
import numpy as np
from numpy.typing import NDArray

from foxhole_stockpiles.core.utils import extract_day_and_hour, most_frequent
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.models.ocr_coordinator_config import OCRCoordinatorConfig
from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.models.stockpile_image_regions import StockpileImageRegions
from foxhole_stockpiles.models.stockpile_item import StockpileItem
from foxhole_stockpiles.services.stockpile_detector import StockpileDetector
from foxhole_stockpiles.services.stockpile_text_extractor import StockpileTextExtractor
from foxhole_stockpiles.services.stockpile_type_classifier import StockpileTypeClassifier
from foxhole_stockpiles.services.template_manager import TemplateManager


class OCRCoordinator:
    """Coordinates the entire stockpile detection and analysis process."""

    TESSERACT_BINARY_THRESHOLD: ClassVar[int] = 127

    def __init__(self, config: OCRCoordinatorConfig) -> None:
        """Initialize the model."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.threshold_value: float = 0.0

        # Initialize services
        self._text_extractor = StockpileTextExtractor(
            custom_model=config.custom_model, tessdata_path=config.tessdata_path
        )
        self._template_manager = TemplateManager(database_path=config.database_path)
        self._stockpile_type_classifier = StockpileTypeClassifier()

    def analyze_stockpile(self, image: NDArray[np.uint8]) -> Stockpile:
        """Analyze a stockpile image and return detected items with quantities.

        Args:
            image (NDArray[np.uint8]): Image data as numpy array (RGB format)

        Returns:
            Stockpile: Stockpile with the detected items and metadata

        Raises:
            ValueError: If image analysis fails
        """
        detector = self._detect_regions(image)
        stockpile_images = self._extract_stockpile_images(detector)
        quantities = self._extract_quantities(stockpile_images)
        self._template_manager.set_active_resolution(stockpile_images.vertical_resolution)
        scanned_stockpile = self._match_icons_and_build_result(
            stockpile_images=stockpile_images, quantities=quantities
        )

        return scanned_stockpile

    def _detect_regions(self, image: NDArray[np.uint8]) -> StockpileDetector:
        """Detect regions in the stockpile image.

        Args:
            image (NDArray[np.uint8]): Image data as numpy array

        Returns:
            StockpileDetector: Configured detector with analyzed regions

        Raises:
            ValueError: If image analysis fails
        """
        try:
            detector = StockpileDetector(image)
            detector.analize()

            if self.config.debug_mode:
                detector.draw_and_save_results()

            self.logger.info("- Resolution scale factor: %.3f", detector.scale_factor)
            self.logger.info("- Detected %d quantity boxes", len(detector.quantities))
            self.logger.info("- Detected %d icon groups", len(detector.groups))

            return detector

        except Exception as e:
            self.logger.error("Error during region detection: %s", e)
            raise ValueError(f"Failed to analyze image: {e}") from e

    def _extract_stockpile_images(self, detector: StockpileDetector) -> StockpileImageRegions:
        """Extract stockpile image regions from detector results.

        Args:
            detector (StockpileDetector): Configured detector with analyzed regions

        Returns:
            StockpileImageRegions: Extracted image regions containing icons and metadata

        Raises:
            ValueError: If no icons found in the image
        """
        stockpile_images = detector.get_stockpile_images()
        if not stockpile_images:
            raise ValueError("No icons found in the image")
        return stockpile_images

    def _extract_quantities(self, stockpile_images: StockpileImageRegions) -> list[int]:
        """Extract quantities from the composite quantities image.

        Args:
            stockpile_images (StockpileImageRegions): Image regions containing quantity data

        Returns:
            list[int]: Flattened list of quantities matching icon positions
        """
        quantities_nested = self._text_extractor.extract_quantities(
            stockpile_images.composite_quantities_image
        )

        flat_quantities = [item for sublist in quantities_nested for item in sublist]
        quantities_count = len(flat_quantities)
        icons_count = len(stockpile_images.icons)

        # Handle mismatch between quantities and icons
        missing_count = icons_count - quantities_count
        if missing_count > 0:
            self.logger.warning(
                "Quantities detected (%d) don't match the number of icons (%d). "
                "Adding %d placeholder values.",
                quantities_count,
                icons_count,
                missing_count,
            )
            flat_quantities.extend([-1] * missing_count)

        return flat_quantities

    def _prepare_image_for_detection(
        self, image: NDArray[np.uint8], use_inv: bool = True
    ) -> NDArray[np.uint8]:
        """Apply preprocessing to the image for better text detection.

        Args:
            image (NDArray[np.uint8]): Image to preprocess
            use_inv (bool): Whether to use inverted thresholding

        Return:
            NDArray[np.uint8]: processed image
        """
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        upscale_factor = 3

        upscaled = cv2.resize(
            gray, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC
        )

        if not self.threshold_value:
            unique_values, counts = np.unique(upscaled, return_counts=True)
            most_common_value = unique_values[np.argmax(counts)]
            self.threshold_value = most_common_value + 120 * (1 - most_common_value / 255)

        threshold_value = self.threshold_value
        if use_inv:
            threshold_mode = cv2.THRESH_BINARY_INV
        else:
            threshold_mode = cv2.THRESH_BINARY
            threshold_value -= 30

        upscaled[upscaled < threshold_value] = 0

        _, binary = cv2.threshold(upscaled, self.TESSERACT_BINARY_THRESHOLD, 255, threshold_mode)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary = cv2.dilate(binary, kernel, iterations=1)

        post_cleaned = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)

        return np.asarray(post_cleaned, dtype=np.uint8)

    def _match_icons_and_build_result(
        self, stockpile_images: StockpileImageRegions, quantities: list[int]
    ) -> Stockpile:
        """Match icons against templates and build the final result.

        Args:
            stockpile_images (StockpileImageRegions): Image regions containing icons
            quantities (list[int]): Extracted quantities for each icon

        Returns:
            dict[str, Any]: Complete stockpile analysis result with items and metadata
        """
        stockpile = Stockpile(resolution=stockpile_images.resolution)

        mod: str | None = None

        for group_index, (group_amount, group_start_index) in enumerate(stockpile_images.groups):
            self.logger.info(
                "Processing group %d with %d icons starting at index %d",
                group_index,
                group_amount,
                group_start_index,
            )

            category: ItemCategory | None = None
            crated: bool | None = None
            detected: dict[str, list[Any]] = {"category": [], "crated": [], "mod": []}
            current_icons = []

            for icon_index in range(group_start_index, group_start_index + group_amount):
                try:
                    quantity = quantities[icon_index]
                    stockpile_item = self._process_single_icon(
                        stockpile_images=stockpile_images,
                        icon_index=icon_index,
                        quantity=quantity,
                        category=category,
                        crated=crated,
                        mod=mod,
                        detected=detected,
                    )

                    if stockpile_item is None:
                        mod_text = f", mod: {mod}" if mod else ""
                        category_text = f", category: {category.value}" if category else ""
                        stockpile.errors.append(
                            f"Group {group_index}, index {icon_index}: No match found. "
                            f"Quantity: {quantity}, crated: {crated}{mod_text}{category_text}"
                        )
                        continue

                    stockpile.items.append(stockpile_item)
                    current_icons.append(stockpile_item)

                    # Update detected properties for future icons
                    expected_length = 2 if group_index == 0 else 5
                    if category is None and len(detected["category"]) >= expected_length:
                        category = most_frequent(detected["category"])
                        crated = most_frequent(detected["crated"])
                        if mod is None:
                            mod = most_frequent(detected["mod"])
                        self.logger.debug(
                            "Detected category: %s, crated: %s, mod: %s",
                            category,
                            crated,
                            mod,
                        )

                        # Make sure all the icons have the correct crated status
                        if crated is not None:
                            for item in current_icons:
                                if item.crated != crated:
                                    self.logger.debug(
                                        "Item %s: changing crated from %s to %s",
                                        item,
                                        item.crated,
                                        crated,
                                    )
                                    item.crated = crated
                except Exception as e:
                    self.logger.error("Error processing icon at index %d: %s", icon_index, e)
                    if self.logger.isEnabledFor(logging.DEBUG):
                        self.logger.exception("Full error details:")

        # detect the stockpile metadata from the other regions
        name_image = stockpile_images.stockpile_name
        if name_image is not None:
            source_image = self._prepare_image_for_detection(image=name_image)
            text = self._text_extractor._extract_raw_text(image=source_image, numbers_only=False)
            stockpile.name = text.strip()

        hex_image = stockpile_images.hex_name
        if hex_image is not None:
            source_image = self._prepare_image_for_detection(image=hex_image, use_inv=False)
            text = self._text_extractor._extract_raw_text(image=source_image, numbers_only=False)
            text = text.strip() + "\n\n"
            lines = text.splitlines()
            stockpile.hex_name = lines[0]
            stockpile.ingame_timestamp = extract_day_and_hour(lines[1])
            stockpile.shard = lines[2]

        type_image = stockpile_images.stockpile_type
        if type_image is not None:
            source_image = self._prepare_image_for_detection(image=type_image)
            text = self._text_extractor._extract_raw_text(image=source_image, numbers_only=False)
            stockpile.type = self._stockpile_type_classifier.classify_from_text(text)

        return stockpile

    def _process_single_icon(
        self,
        stockpile_images: StockpileImageRegions,
        icon_index: int,
        quantity: int,
        category: ItemCategory | None,
        crated: bool | None,
        mod: str | None,
        detected: dict[str, list[Any]],
    ) -> StockpileItem | None:
        """Process a single icon and return its code if matched.

        Args:
            stockpile_images (StockpileImageRegions): Image regions containing the icon
            icon_index (int): Index of the icon to process
            quantity (int): Quantity value for this icon
            category (ItemCategory | None): Current category filter for matching
            crated (bool | None): Current crated filter for matching
            mod (str | None): Current mod filter for matching
            detected (dict[str, list[Any]]): Accumulator for detected properties

        Returns:
            StockpileItem | None: Matched item code and crated status, or None if no match found
        """
        category = category or ItemCategory.Invalid
        image = stockpile_images.icons[icon_index]

        if image is None:
            self.logger.warning("Icon image at index %d is None, skipping", icon_index)
            return None

        self.logger.debug("Processing icon at index %d", icon_index)

        match_result = self._template_manager.match_icon(
            icon_image=image,
            confidence_threshold=self.config.confidence_threshold,
            early_exit_threshold=self.config.early_exit_threshold,
            max_ncc_candidates=self.config.max_ncc_candidates,
            phash_threshold=self.config.phash_threshold,
            faction=self.config.faction_filter,
            category=category,
            crated=crated,
            mod=mod,
        )

        icon_match = match_result.icon
        if not icon_match:
            self.logger.warning(
                "[%d] No match found with confidence %.2f",
                icon_index,
                self.config.confidence_threshold,
            )
            return None

        # Update detected properties for future matching
        detected["category"].append(icon_match.category)
        detected["crated"].append(icon_match.crated)
        detected["mod"].append(icon_match.mod)

        self.logger.info(
            "[%d] '%s%s', quantity: %d (confidence: %.2f) after testing %d candidates",
            icon_index,
            icon_match.code,
            " (crated)" if icon_match.crated else "",
            quantity,
            match_result.confidence,
            match_result.tested_candidates,
        )

        return StockpileItem(
            code=icon_match.code,
            crated=icon_match.crated,
            quantity=quantity,
            confidence=match_result.confidence,
        )

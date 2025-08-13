"""OCR Coordinator service for orchestrating stockpile detection."""

import logging
from typing import Any

from foxhole_stockpiles.core.utils import most_frequent
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.models.ocr_coordinator_config import OCRCoordinatorConfig
from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.models.stockpile_image_regions import StockpileImageRegions
from foxhole_stockpiles.models.stockpile_item import StockpileItem
from foxhole_stockpiles.services.stockpile_detector import StockpileDetector
from foxhole_stockpiles.services.stockpile_text_extractor import StockpileTextExtractor
from foxhole_stockpiles.services.template_manager import TemplateManager


class OCRCoordinator:
    """Coordinates the entire stockpile detection and analysis process."""

    def __init__(self, config: OCRCoordinatorConfig) -> None:
        """Initialize the model."""
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize services
        self._text_extractor = StockpileTextExtractor(
            custom_model=config.custom_model, tessdata_path=config.tessdata_path
        )
        self._template_manager = TemplateManager(database_path=config.database_path)

    def analyze_stockpile(self, image_path: str) -> Stockpile:
        """Analyze a stockpile image and return detected items with quantities.

        Args:
            image_path (str): Path to the stockpile image

        Returns:
            Stockpile: Stockpile with the detected items and metadata

        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If image analysis fails
        """
        detector = self._detect_regions(image_path)
        stockpile_images = self._extract_stockpile_images(detector)
        quantities = self._extract_quantities(stockpile_images)
        self._template_manager.set_active_resolution(stockpile_images.vertical_resolution)
        scanned_stockpile = self._match_icons_and_build_result(
            stockpile_images=stockpile_images, quantities=quantities
        )

        return scanned_stockpile

    def _detect_regions(self, image_path: str) -> StockpileDetector:
        """Detect regions in the stockpile image.

        Args:
            image_path (str): Path to the stockpile image

        Returns:
            StockpileDetector: Configured detector with analyzed regions

        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If image analysis fails
        """
        try:
            detector = StockpileDetector(image_path)
            detector.analize()

            if self.config.debug_mode:
                detector.draw_and_save_results()

            self.logger.info("- Resolution scale factor: %.3f", detector.scale_factor)
            self.logger.info("- Detected %d quantity boxes", len(detector.quantities))
            self.logger.info("- Detected %d icon groups", len(detector.groups))

            return detector

        except FileNotFoundError as e:
            self.logger.error("Image file not found: %s", e)
            raise
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
        stockpile = Stockpile()

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

            for icon_index in range(group_start_index, group_start_index + group_amount):
                try:
                    quantity = quantities[icon_index]
                    _item = self._process_single_icon(
                        stockpile_images=stockpile_images,
                        icon_index=icon_index,
                        quantity=quantity,
                        category=category,
                        crated=crated,
                        mod=mod,
                        detected=detected,
                    )

                    if _item is None:
                        continue

                    item_code, crated = _item
                    stockpile_item = StockpileItem(code=item_code, quantity=quantity, crated=crated)
                    stockpile.items.append(stockpile_item)

                    # Update detected properties for future icons
                    expected_length = 2 if group_index == 0 else 5
                    if len(detected["category"]) >= expected_length:
                        category = most_frequent(detected["category"])
                        crated = most_frequent(detected["crated"])
                        if mod is None:
                            mod = most_frequent(detected["mod"])

                except Exception as e:
                    self.logger.error("Error processing icon at index %d: %s", icon_index, e)
                    if self.logger.isEnabledFor(logging.DEBUG):
                        self.logger.exception("Full error details:")

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
    ) -> tuple[str, bool] | None:
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
            str | None: Item code if successfully matched, None if no match found
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
            self.logger.warning("Candidates: %s", match_result.candidates)
            return None

        # Update detected properties for future matching
        detected["category"].append(icon_match.category)
        detected["crated"].append(icon_match.crated)
        detected["mod"].append(icon_match.mod)

        self.logger.info(
            "[%d] '%s%s', quantity: %d (confidence: %.2f)",
            icon_index,
            icon_match.code,
            " (crated)" if icon_match.crated else "",
            quantity,
            match_result.confidence,
        )

        return icon_match.code, icon_match.crated

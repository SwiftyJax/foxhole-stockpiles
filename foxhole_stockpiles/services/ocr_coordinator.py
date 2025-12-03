"""OCR Coordinator service for orchestrating stockpile detection."""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

import cv2
import numpy as np
from numpy.typing import NDArray

from foxhole_stockpiles.core.events import EventBus, get_event_bus
from foxhole_stockpiles.core.settings.sections.scanner import ScannerSettings
from foxhole_stockpiles.core.utils import extract_day_and_hour, most_frequent
from foxhole_stockpiles.enums.event_type import EventType
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_language import SupportedLanguage
from foxhole_stockpiles.models.item_candidate import ItemCandidate
from foxhole_stockpiles.models.match_result import MatchResult
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

    def __init__(self, config: ScannerSettings, event_bus: EventBus | None = None) -> None:
        """Initialize the model.

        Args:
            config (ScannerSettings): Configuration for the coordinator
            event_bus (EventBus | None): Event bus for notifications (defaults to singleton)

        Raises:
            ValueError: If database_path is None (required for OCRCoordinator)
        """
        if config.database_path is None:
            raise ValueError("database_path is required for OCRCoordinator")

        self.config = config
        self._event_bus = event_bus or get_event_bus()
        self.logger = logging.getLogger(__name__)

        # Initialize services
        self._text_extractor = StockpileTextExtractor(
            custom_model=config.custom_model,
            tessdata_path=config.tessdata_path,
        )
        self._template_manager = TemplateManager(
            database_path=config.database_path, cache_size=config.template_cache_size
        )
        self._stockpile_type_classifier = StockpileTypeClassifier()

    def _extract_icon_to_folder(
        self, icon_image: NDArray[np.uint8], icon_index: int, code: str
    ) -> None:
        """Extract icon to icons folder for debugging.

        Args:
            icon_image (NDArray[np.uint8]): Icon image to save (BGR format)
            icon_index (int): Index of the icon in the stockpile
            code (str): Detected item code or "processing" if not yet matched
        """
        try:
            # Create icons folder if it doesn't exist
            icons_folder = Path("icons")
            icons_folder.mkdir(exist_ok=True)

            # Filename: index_code.png (with 3-digit zero-padded index)
            filename = f"{icon_index:03d}_{code}.png"
            filepath = icons_folder / filename

            # Save icon image (already in BGR format)
            cv2.imwrite(str(filepath), icon_image)

            self.logger.debug("Extracted icon to: %s", filepath)

        except Exception as e:
            self.logger.error("Failed to extract icon %d: %s", icon_index, e)

    def _save_screenshot_with_metadata(
        self, image: NDArray[np.uint8], stockpile: Stockpile
    ) -> None:
        """Save screenshot with metadata to folder.

        Args:
            image (NDArray[np.uint8]): Image to save (BGR format)
            stockpile (Stockpile): Stockpile with metadata for filename
        """
        if not self.config.screenshots_folder:
            return

        try:
            # Create base folder and daily subfolder
            base_folder = Path(self.config.screenshots_folder)
            daily_folder = base_folder / datetime.now().strftime("%Y-%m-%d")
            daily_folder.mkdir(parents=True, exist_ok=True)

            # Generate filename: Date_HourWithSeconds_StorageType_Name_Resolution.png
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            storage_type = stockpile.type if stockpile.type else "Unknown"
            name = stockpile.name if stockpile.name else "Unknown"
            # Sanitize storage type and name for filename
            storage_type = "".join(
                c if c.isalnum() or c in (" ", "-", "_") else "_" for c in storage_type
            )
            storage_type = storage_type.replace(" ", "_")
            name = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in name)
            name = name.replace(" ", "_")
            resolution = stockpile.resolution
            filename = f"{timestamp}_{storage_type}_{name}_{resolution}.png"
            filepath = daily_folder / filename

            # Image is already in BGR format (OpenCV default)
            cv2.imwrite(str(filepath), image)

            self.logger.debug("Screenshot saved to: %s", filepath)

        except Exception as e:
            self.logger.error("Failed to save screenshot: %s", e)

    async def analyze_stockpile(
        self,
        image: NDArray[np.uint8],
        language: SupportedLanguage | None = None,
        faction: ItemFaction | None = None,
    ) -> Stockpile:
        """Analyze a stockpile image and return detected items with quantities.

        Args:
            image (NDArray[np.uint8]): Image data as numpy array (BGR format)
            language (SupportedLanguage | None): Language for text detection (stockpile name,
                type, hex_name). If None, uses all supported languages.
            faction (ItemFaction | None): Faction filter for icon matching. If None, no faction
                filtering is applied.

        Returns:
            Stockpile: Stockpile with the detected items and metadata

        Raises:
            ValueError: If image analysis fails
        """
        start_time = time.perf_counter()

        # Emit scan started event
        self._event_bus.emit(
            EventType.STOCKPILE_SCAN_STARTED, {"timestamp": datetime.now().isoformat()}
        )

        detector = self._detect_regions(image)
        scale_factor = detector.scale_factor
        stockpile_images = self._extract_stockpile_images(detector)
        quantities = await self._extract_quantities(stockpile_images)
        await self._template_manager.set_active_resolution(stockpile_images.vertical_resolution)
        scanned_stockpile = await self._match_icons_and_build_result(
            stockpile_images=stockpile_images,
            quantities=quantities,
            scale_factor=scale_factor,
            language=language,
            faction=faction,
        )

        elapsed_time = time.perf_counter() - start_time

        # Save screenshot with metadata if enabled
        self._save_screenshot_with_metadata(image, scanned_stockpile)

        # Log summary
        stockpile_type = scanned_stockpile.type.value if scanned_stockpile.type else "Unknown"
        stockpile_name = scanned_stockpile.name if scanned_stockpile.name else "Unknown"

        # Calculate average confidence (excluding unknown items)
        matched_items = [item for item in scanned_stockpile.items if item.code != "Unknown"]
        total_items = len(scanned_stockpile.items)
        unmatched_items = total_items - len(matched_items)
        avg_confidence = (
            sum(item.confidence or 0.0 for item in matched_items) / len(matched_items)
            if matched_items
            else 0.0
        )

        self.logger.info(
            "%s:%s (%s). Scanned %d items (%d unmatched) with avg confidence: %.3f in %.2fs",
            stockpile_type,
            stockpile_name,
            scanned_stockpile.resolution,
            len(scanned_stockpile.items),
            unmatched_items,
            avg_confidence,
            elapsed_time,
        )

        # Emit scan completed event
        self._event_bus.emit(
            EventType.STOCKPILE_SCANNED,
            {
                "stockpile_name": stockpile_name,
                "stockpile_type": stockpile_type,
                "resolution": scanned_stockpile.resolution,
                "item_count": total_items,
                "matched_items": len(matched_items),
                "unmatched_items": unmatched_items,
                "avg_confidence": avg_confidence,
                "duration": elapsed_time,
                "timestamp": datetime.now().isoformat(),
            },
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

            self.logger.debug("- Resolution scale factor: %.3f", detector.scale_factor)
            self.logger.debug("- Detected %d quantity boxes", len(detector.quantities))
            self.logger.debug("- Detected %d icon groups", len(detector.groups))

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

    async def _extract_quantities(self, stockpile_images: StockpileImageRegions) -> list[int]:
        """Extract quantities from the composite quantities image.

        Args:
            stockpile_images (StockpileImageRegions): Image regions containing quantity data

        Returns:
            list[int]: Flattened list of quantities matching icon positions
        """
        quantities_nested = await self._text_extractor.extract_quantities(
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
        self,
        image: NDArray[np.uint8],
        scale_factor: float,
        use_inv: bool = True,
    ) -> NDArray[np.uint8]:
        """Apply preprocessing to the image for better text detection.

        Calculates region-specific threshold from pixel distribution for optimal OCR accuracy.
        Each region (name, shard, type) gets its own threshold based on its characteristics.

        Args:
            image (NDArray[np.uint8]): Image region to preprocess
            scale_factor (float): Resolution scale factor from detector
            use_inv (bool): Whether to use inverted thresholding

        Returns:
            NDArray[np.uint8]: Processed image ready for OCR
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        upscale_factor = 2 / scale_factor

        upscaled = cv2.resize(
            gray, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC
        )

        # Calculate threshold from this region's pixel distribution
        unique_values, counts = np.unique(upscaled, return_counts=True)
        most_common_value = unique_values[np.argmax(counts)]
        threshold_value = most_common_value + 120 * (1 - most_common_value / 255)

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

    async def _match_icons_and_build_result(
        self,
        stockpile_images: StockpileImageRegions,
        quantities: list[int],
        scale_factor: float,
        language: SupportedLanguage | None,
        faction: ItemFaction | None,
    ) -> Stockpile:
        """Match icons against templates and build the final result.

        Args:
            stockpile_images (StockpileImageRegions): Image regions containing icons
            quantities (list[int]): Extracted quantities for each icon
            scale_factor (float): Resolution scale factor for image preprocessing
            language (SupportedLanguage | None): Language for text detection
            faction (ItemFaction | None): Faction filter for icon matching

        Returns:
            Stockpile: Complete stockpile analysis result with items and metadata
        """
        stockpile = Stockpile(resolution=stockpile_images.resolution)

        for group_index, (group_amount, group_start_index) in enumerate(stockpile_images.groups):
            self.logger.debug(
                "Processing group %d with %d icons starting at index %d",
                group_index,
                group_amount,
                group_start_index,
            )

            category: ItemCategory | None = None
            crated: bool | None = None
            detected: dict[str, list[Any]] = {"category": [], "crated": []}
            current_icons: list[StockpileItem] = []

            for icon_index in range(group_start_index, group_start_index + group_amount):
                try:
                    quantity = quantities[icon_index]
                    stockpile_item, match_result = self._process_single_icon(
                        stockpile_images=stockpile_images,
                        icon_index=icon_index,
                        quantity=quantity,
                        category=category,
                        crated=crated,
                        detected=detected,
                        faction=faction,
                    )

                    if stockpile_item is None:
                        category_text = f", category: {category.value}" if category else ""

                        # Include best match information if available
                        best_match_text = ""
                        if match_result and match_result.best_match:
                            best_match = match_result.best_match
                            best_match_text = (
                                f" Best match: {best_match.code}"
                                f"{' (crated)' if best_match.crated else ''}"
                                f" (confidence: {match_result.best_confidence:.3f})"
                            )

                        stockpile.errors.append(
                            f"Group {group_index}, index {icon_index}: No match found. "
                            f"Quantity: {quantity}, crated: "
                            f"{crated}{category_text}.{best_match_text}"
                        )
                        unkown_item = StockpileItem(
                            code="Unknown",
                            quantity=quantity,
                            crated=crated or False,
                            confidence=0.0,
                        )
                        stockpile.items.append(unkown_item)
                        continue

                    stockpile.items.append(stockpile_item)
                    current_icons.append(stockpile_item)

                    # Update detected properties for future icons
                    expected_length = 2 if group_index == 0 else 5
                    if category is None and len(detected["category"]) >= expected_length:
                        category = most_frequent(detected["category"])
                        crated = most_frequent(detected["crated"])
                        self.logger.debug("Detected category: %s, crated: %s", category, crated)

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

        self._check_for_duplicates(
            stockpile=stockpile, stockpile_images=stockpile_images, faction=faction
        )

        # detect the stockpile metadata from the other regions
        name_image = stockpile_images.stockpile_name
        if name_image is not None:
            source_image = self._prepare_image_for_detection(
                image=name_image,
                scale_factor=scale_factor,
            )
            if self.config.debug_mode:
                cv2.imwrite("stockpile_name_region.png", source_image)

            text = await self._text_extractor.extract_raw_text(
                image=source_image, numbers_only=False, language=language
            )
            stockpile.name = text.strip()

        shard_image = stockpile_images.shard
        if shard_image is not None:
            source_image = self._prepare_image_for_detection(
                image=shard_image,
                scale_factor=scale_factor,
                use_inv=False,
            )
            if self.config.debug_mode:
                cv2.imwrite("stockpile_shard.png", source_image)

            text = await self._text_extractor.extract_raw_text(
                image=source_image, numbers_only=False, language=language
            )
            text = text.strip() + "\n\n"
            lines = text.splitlines()
            stockpile.ingame_timestamp = extract_day_and_hour(lines[0])
            stockpile.shard = lines[1]

        type_image = stockpile_images.stockpile_type
        if type_image is not None:
            source_image = self._prepare_image_for_detection(
                image=type_image,
                scale_factor=scale_factor,
            )
            if self.config.debug_mode:
                cv2.imwrite("stockpile_type_region.png", source_image)

            text = await self._text_extractor.extract_raw_text(
                image=source_image, numbers_only=False, language=language
            )
            stockpile.type = self._stockpile_type_classifier.classify_from_text(text)

        return stockpile

    def _check_for_duplicates(
        self,
        stockpile: Stockpile,
        stockpile_images: StockpileImageRegions,
        faction: ItemFaction | None,
    ) -> None:
        """Check for duplicate items in the stockpile and attempt to re-match them.

        Args:
            stockpile (Stockpile): Stockpile to check for duplicates
            stockpile_images (StockpileImageRegions): Image regions containing the icons
            faction (ItemFaction | None): Faction filter for icon matching
        """
        # stockpiles can't repeat a code more than once with the same crated status
        unique_items = {(item.code, item.crated) for item in stockpile.items}
        non_unknown_items = [item for item in stockpile.items if item.code != "Unknown"]

        excluded_codes = []
        retries = 1

        while len(unique_items) < len(non_unknown_items) and retries <= 10:
            retries += 1
            # Find which item is duplicated
            seen: dict[tuple[str, bool], int] = {}
            conflicting_code = ""
            index = -1
            item = stockpile.items[0]

            existing_index: int | None = None
            while existing_index is None:
                index += 1
                item = stockpile.items[index]
                key = (item.code, item.crated)
                if item.code != "Unknown":
                    existing_index = seen.get(key)
                    seen[key] = index

            # Found the duplicate - determine which one to re-match (lower confidence)
            conflicting_code = item.code
            excluded_codes.append(conflicting_code)
            existing_item = stockpile.items[existing_index]

            existing_confidence = existing_item.confidence or 0.0
            current_confidence = item.confidence or 0.0

            duplicate_index = index if current_confidence < existing_confidence else existing_index
            duplicate_item = stockpile.items[duplicate_index]

            self.logger.debug(
                "Duplicate detected: %s (crated: %s) at indices %d and %d. "
                "Re-matching index %d (lower confidence: %.3f)",
                duplicate_item.code,
                duplicate_item.crated,
                existing_index,
                index,
                duplicate_index,
                min(existing_confidence, current_confidence),
            )

            # Re-match using _process_single_icon with exclusion

            quantity = duplicate_item.quantity
            rematched_item, rematch_result = self._process_single_icon(
                stockpile_images=stockpile_images,
                icon_index=duplicate_index,
                quantity=quantity,
                category=None,
                crated=None,
                detected={"category": [], "crated": []},
                faction=faction,
                excluded_codes=excluded_codes,
            )

            if rematched_item is not None:
                stockpile.items[duplicate_index] = rematched_item
                self.logger.debug(
                    "Re-matched index %d: %s -> %s (confidence: %.3f)",
                    duplicate_index,
                    conflicting_code,
                    rematched_item.code,
                    rematched_item.confidence or 0.0,
                )
            else:
                # No alternative found, mark as Unknown
                stockpile.items[duplicate_index].code = "Unknown"
                stockpile.items[duplicate_index].confidence = 0.0

                # Add error with best match info if available
                best_match_text = ""
                if rematch_result and rematch_result.best_match:
                    best_match = rematch_result.best_match
                    best_match_text = (
                        f" Best match: {best_match.code}"
                        f"{' (crated)' if best_match.crated else ''}"
                        f" (confidence: {rematch_result.best_confidence:.3f})"
                    )

                stockpile.errors.append(
                    f"Duplicate resolution failed at index {duplicate_index}: "
                    f"Conflicting with '{conflicting_code}'. "
                    f"No valid alternative found.{best_match_text}"
                )

                self.logger.debug(
                    "No alternative found for index %d, marking as Unknown. %s",
                    duplicate_index,
                    best_match_text,
                )

            # Recalculate unique items for next iteration
            unique_items = {(item.code, item.crated) for item in stockpile.items}
            non_unknown_items = [item for item in stockpile.items if item.code != "Unknown"]

    def _process_single_icon(
        self,
        stockpile_images: StockpileImageRegions,
        icon_index: int,
        quantity: int,
        category: ItemCategory | None,
        crated: bool | None,
        detected: dict[str, list[Any]],
        faction: ItemFaction | None,
        excluded_codes: list[str] | None = None,
    ) -> tuple[StockpileItem | None, MatchResult]:
        """Process a single icon and return its code if matched.

        Args:
            stockpile_images (StockpileImageRegions): Image regions containing the icon
            icon_index (int): Index of the icon to process
            quantity (int): Quantity value for this icon
            category (ItemCategory | None): Current category filter for matching
            crated (bool | None): Current crated filter for matching
            detected (dict[str, list[Any]]): Accumulator for detected properties
            faction (ItemFaction | None): Faction filter for icon matching
            excluded_codes (list[str] | None): Optional list of item codes to exclude from matching

        Returns:
            tuple[StockpileItem | None, MatchResult]: Matched item and match result with best match
                info
        """
        if category == ItemCategory.Invalid:
            category = None

        image = stockpile_images.icons[icon_index]
        self.logger.debug("Processing icon at index %d", icon_index)

        self.logger.debug(
            "Using early exit threshold %.3f for resolution %d",
            self.config.early_exit_threshold,
            stockpile_images.vertical_resolution,
        )

        match_result = self._template_manager.match_icon(
            icon_image=image,
            early_exit_threshold=self.config.early_exit_threshold,
            confidence_gap=self.config.confidence_gap,
            max_ncc_candidates=self.config.max_ncc_candidates,
            phash_threshold=self.config.phash_threshold,
            faction=faction,
            category=category,
            crated=crated,
            excluded_codes=excluded_codes,
        )

        icon_match = match_result.icon
        if not icon_match:
            # Log best match if available for debugging
            if match_result.best_match:
                self.logger.warning(
                    "[%d] No match found (best: %s with %.3f)",
                    icon_index,
                    match_result.best_match.code,
                    match_result.best_confidence,
                )
            else:
                self.logger.warning("[%d] No match found", icon_index)

            # Extract failed icon with best match code if available
            if self.config.extract_icons:
                code = match_result.best_match.code if match_result.best_match else "Unknown"
                self._extract_icon_to_folder(image, icon_index, code)

            return None, match_result

        # Update detected properties for future matching
        detected["category"].append(icon_match.category)
        detected["crated"].append(icon_match.crated)

        self.logger.debug(
            "[%d] '%s%s', quantity: %d (confidence: %.2f) after testing %d candidates",
            icon_index,
            icon_match.code,
            " (crated)" if icon_match.crated else "",
            quantity,
            match_result.confidence,
            match_result.tested_candidates,
        )

        # Extract matched icon to folder with detected code if enabled
        if self.config.extract_icons:
            self._extract_icon_to_folder(image, icon_index, icon_match.code)

        # Build candidates list from gap_candidates
        candidates = None
        if match_result.gap_candidates:
            candidates = [
                ItemCandidate(code=template.code, confidence=conf)
                for template, conf in match_result.gap_candidates
            ]

        return (
            StockpileItem(
                code=icon_match.code,
                crated=icon_match.crated,
                quantity=quantity,
                confidence=match_result.confidence,
                candidates=candidates,
            ),
            match_result,
        )

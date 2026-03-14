"""OCR Coordinator service for orchestrating stockpile detection."""

import asyncio
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
from foxhole_stockpiles.core.utils import (
    extract_day_and_hour,
    get_bundled_resource_path,
    is_frozen,
    most_frequent,
)
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

        # Resolve tessdata path for PyInstaller bundles
        tessdata_path = config.tessdata_path
        if is_frozen() and tessdata_path in ("./tessdata", "tessdata"):
            tessdata_path = str(get_bundled_resource_path("tessdata"))

        # Initialize services
        self._text_extractor = StockpileTextExtractor(
            custom_model=config.custom_model,
            tessdata_path=tessdata_path,
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

        try:
            detector = self._detect_regions(image)
            scale_factor = detector.scale_factor
            stockpile_images = self._extract_stockpile_images(detector)

            quantities, metadata = await self._extract_all_ocr_parallel(
                stockpile_images=stockpile_images,
                scale_factor=scale_factor,
                language=language,
            )

            await self._template_manager.set_active_resolution(stockpile_images.vertical_resolution)
            scanned_stockpile = await self._match_icons_and_build_result(
                stockpile_images=stockpile_images,
                quantities=quantities,
                scale_factor=scale_factor,
                language=language,
                faction=faction,
            )

            if metadata["type"] is not None:
                scanned_stockpile.type = metadata["type"]
            if metadata["name"] is not None:
                scanned_stockpile.name = metadata["name"]
            if metadata["shard"] is not None:
                scanned_stockpile.shard = metadata["shard"]
            if metadata["ingame_timestamp"] is not None:
                scanned_stockpile.ingame_timestamp = metadata["ingame_timestamp"]
        except Exception as e:
            elapsed_time = time.perf_counter() - start_time
            # Emit scan failed event
            self._event_bus.emit(
                EventType.STOCKPILE_SCAN_FAILED,
                {
                    "error": str(e),
                    "duration": elapsed_time,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            raise

        elapsed_time = time.perf_counter() - start_time

        # Save screenshot with metadata if enabled
        self._save_screenshot_with_metadata(image, scanned_stockpile)

        # Log summary
        stockpile_type = scanned_stockpile.type.value if scanned_stockpile.type else "Unknown"
        stockpile_name = scanned_stockpile.name if scanned_stockpile.name else "Unknown"

        # Calculate average confidence and gap statistics (excluding unknown items)
        matched_items = [item for item in scanned_stockpile.items if item.code != "Unknown"]
        total_items = len(scanned_stockpile.items)
        unmatched_items = total_items - len(matched_items)

        # Gap statistics: unique vs with alternatives
        with_alternatives = sum(1 for item in matched_items if item.candidates)
        unique = len(matched_items) - with_alternatives

        avg_confidence = (
            sum(item.confidence or 0.0 for item in matched_items) / len(matched_items)
            if matched_items
            else 0.0
        )

        self.logger.info(
            "%s:%s (%s). Scanned %d items (%d unmatched) with avg confidence: %.3f in %.2fs. "
            "Quality: %d unique, %d with alternatives (gap≤%.1f)",
            stockpile_type,
            stockpile_name,
            scanned_stockpile.resolution,
            len(scanned_stockpile.items),
            unmatched_items,
            avg_confidence,
            elapsed_time,
            unique,
            with_alternatives,
            self.config.confidence_gap,
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
        """Extract quantities from the composite quantities image with validation.

        Uses group structure to validate quantities per row and applies descending
        order rule within groups to detect and correct OCR errors. Errors in one
        row don't propagate to other rows.

        Args:
            stockpile_images (StockpileImageRegions): Image regions containing quantity data

        Returns:
            list[int]: Flattened list of quantities matching icon positions
        """
        quantities_nested = await self._text_extractor.extract_quantities(
            stockpile_images.composite_quantities_image
        )

        # Compute expected items per row based on groups structure
        expected_per_row = self._compute_expected_row_counts(stockpile_images.groups)

        # Validate and correct quantities row by row
        corrected_quantities = await self._validate_and_correct_quantities(
            ocr_rows=quantities_nested,
            expected_per_row=expected_per_row,
            quantity_images=stockpile_images.quantities,
            groups=stockpile_images.groups,
        )

        # Handle any remaining mismatch (shouldn't happen after correction, but safety check)
        icons_count = len(stockpile_images.icons)
        if len(corrected_quantities) < icons_count:
            missing = icons_count - len(corrected_quantities)
            self.logger.warning(
                "After correction, still missing %d quantities. Adding placeholders.", missing
            )
            corrected_quantities.extend([-1] * missing)
        elif len(corrected_quantities) > icons_count:
            self.logger.warning(
                "After correction, have %d extra quantities. Truncating.",
                len(corrected_quantities) - icons_count,
            )
            corrected_quantities = corrected_quantities[:icons_count]

        return corrected_quantities

    async def _extract_all_ocr_parallel(
        self,
        stockpile_images: StockpileImageRegions,
        scale_factor: float,
        language: SupportedLanguage | None,
    ) -> tuple[list[int], dict[str, Any]]:
        """Extract all OCR data in parallel: quantities + type + shard + name.

        Args:
            stockpile_images (StockpileImageRegions): Image regions to process
            scale_factor (float): Scale factor for image preprocessing
            language (SupportedLanguage | None): Language for text detection

        Returns:
            tuple[list[int], dict[str, Any]]: (quantities, metadata_dict)
                metadata_dict contains: type, name, shard, ingame_timestamp
        """
        # Prepare all images for OCR
        type_source = None
        shard_source = None
        name_source = None

        if stockpile_images.stockpile_type is not None:
            type_source = self._prepare_image_for_detection(
                image=stockpile_images.stockpile_type,
                scale_factor=scale_factor,
            )
            if self.config.debug_mode:
                cv2.imwrite("stockpile_type_region.png", type_source)

        if stockpile_images.shard is not None:
            shard_source = self._prepare_image_for_detection(
                image=stockpile_images.shard,
                scale_factor=scale_factor,
                use_inv=False,
            )
            if self.config.debug_mode:
                cv2.imwrite("stockpile_shard.png", shard_source)

        if stockpile_images.stockpile_name is not None:
            name_source = self._prepare_image_for_detection(
                image=stockpile_images.stockpile_name,
                scale_factor=scale_factor,
                extra_upscale=True,
            )
            if self.config.debug_mode:
                cv2.imwrite("stockpile_name_region.png", name_source)

        # Define async OCR tasks
        async def extract_quantities_task() -> list[int]:
            return await self._extract_quantities(stockpile_images)

        async def extract_type_task() -> str | None:
            if type_source is None:
                return None
            return await self._text_extractor.extract_raw_text(
                image=type_source, numbers_only=False, language=language, single_line=True
            )

        async def extract_shard_task() -> str | None:
            if shard_source is None:
                return None
            return await self._text_extractor.extract_raw_text(
                image=shard_source, numbers_only=False, language=language
            )

        async def extract_name_task() -> str | None:
            if name_source is None:
                return None
            return await self._text_extractor.extract_raw_text(
                image=name_source, numbers_only=False, language=language
            )

        # Run all OCR in parallel
        quantities, type_text, shard_text, name_text = await asyncio.gather(
            extract_quantities_task(),
            extract_type_task(),
            extract_shard_task(),
            extract_name_task(),
        )

        # Process results into metadata dict
        metadata: dict[str, Any] = {
            "type": None,
            "name": None,
            "shard": None,
            "ingame_timestamp": None,
        }

        # Process type
        if type_text is not None:
            metadata["type"] = self._stockpile_type_classifier.classify_from_text(type_text)

        # Process shard + timestamp
        if shard_text is not None:
            shard_text = shard_text.strip() + "\n\n"
            lines = shard_text.splitlines()
            metadata["ingame_timestamp"] = extract_day_and_hour(lines[0])
            if len(lines) > 1:
                metadata["shard"] = lines[1]

        # Process name (only if type supports custom names)
        stockpile_type = metadata["type"]
        if name_text is not None and stockpile_type and stockpile_type.has_custom_name():
            metadata["name"] = name_text.strip()

        return quantities, metadata

    def _compute_expected_row_counts(
        self, groups: list[tuple[int, int]]
    ) -> list[tuple[int, int, int]]:
        """Compute expected items per visual row from groups structure.

        Each group fills rows with max 6 items per row.

        Args:
            groups (list[tuple[int, int]]): List of (size, start_index) tuples

        Returns:
            list[tuple[int, int, int]]: List of (expected_count, start_index, group_index) per row
        """
        expected_rows: list[tuple[int, int, int]] = []
        current_index = 0

        for group_index, (size, _start_index) in enumerate(groups):
            remaining = size
            while remaining > 0:
                items_in_row = min(remaining, 6)
                expected_rows.append((items_in_row, current_index, group_index))
                current_index += items_in_row
                remaining -= items_in_row

        return expected_rows

    async def _validate_and_correct_quantities(
        self,
        ocr_rows: list[list[int]],
        expected_per_row: list[tuple[int, int, int]],
        quantity_images: list[NDArray[np.uint8]],
        groups: list[tuple[int, int]],
    ) -> list[int]:
        """Validate OCR quantities against expected structure and correct errors.

        Uses descending order rule within groups to detect error positions.
        Each row is validated independently to prevent error propagation.

        Args:
            ocr_rows (list[list[int]]): OCR results organized by visual row
            expected_per_row (list[tuple[int, int, int]]): Expected (count, start_idx, group_idx)
            quantity_images (list[NDArray[np.uint8]]): Individual quantity box images
            groups (list[tuple[int, int]]): Group structure (size, start_index)

        Returns:
            list[int]: Corrected flat list of quantities
        """
        result: list[int] = []
        ocr_row_idx = 0

        for row_idx, (expected_count, start_index, group_index) in enumerate(expected_per_row):
            # Get OCR results for this row (if available)
            if ocr_row_idx < len(ocr_rows):
                row_quantities = ocr_rows[ocr_row_idx]
                ocr_row_idx += 1
            else:
                row_quantities = []

            actual_count = len(row_quantities)

            if actual_count == expected_count:
                # Count matches - validate descending order within group context
                if self._validate_descending_in_context(
                    row_quantities, result, group_index, groups
                ):
                    result.extend(row_quantities)
                    continue
                else:
                    self.logger.debug(
                        "Row %d: count OK but descending order violated, attempting correction",
                        row_idx,
                    )

            # Count mismatch or descending violation - attempt correction
            self.logger.debug(
                "Row %d: expected %d quantities, got %d. Attempting correction.",
                row_idx,
                expected_count,
                actual_count,
            )

            corrected = await self._correct_row_quantities(
                row_quantities=row_quantities,
                expected_count=expected_count,
                start_index=start_index,
                quantity_images=quantity_images,
                previous_quantities=result,
                group_index=group_index,
                groups=groups,
            )

            result.extend(corrected)

        return result

    def _validate_descending_in_context(
        self,
        row_quantities: list[int],
        previous_quantities: list[int],
        group_index: int,
        groups: list[tuple[int, int]],
    ) -> bool:
        """Validate that quantities maintain descending order within group context.

        The first group (index 0) is exempt from descending order validation as it
        contains items that are always present in every capture and can have any order.

        Args:
            row_quantities (list[int]): Quantities in current row
            previous_quantities (list[int]): All quantities processed so far
            group_index (int): Current group index
            groups (list[tuple[int, int]]): Group structure

        Returns:
            bool: True if descending order is maintained (or group 0)
        """
        if not row_quantities:
            return True

        # First group (index 0) can have any order - skip descending validation
        if group_index == 0:
            return True

        # Get the last quantity from the same group (if any)
        group_start = groups[group_index][1]
        quantities_in_group = [q for i, q in enumerate(previous_quantities) if i >= group_start]

        # Check descending within the row itself
        for i in range(1, len(row_quantities)):
            if row_quantities[i] > row_quantities[i - 1]:
                return False

        # Check continuity with previous quantities in the same group
        if quantities_in_group:
            last_in_group = quantities_in_group[-1]
            if row_quantities[0] > last_in_group:
                return False

        return True

    async def _correct_row_quantities(
        self,
        row_quantities: list[int],
        expected_count: int,
        start_index: int,
        quantity_images: list[NDArray[np.uint8]],
        previous_quantities: list[int],
        group_index: int,
        groups: list[tuple[int, int]],
    ) -> list[int]:
        """Attempt to correct quantities for a single row.

        Re-processes the row with alternative preprocessing or individual OCR.
        No guessing or merging - only actual OCR results.

        Args:
            row_quantities (list[int]): OCR results for this row
            expected_count (int): Expected number of quantities
            start_index (int): Starting index in the flat quantity list
            quantity_images (list[NDArray[np.uint8]]): Individual quantity images
            previous_quantities (list[int]): Previously processed quantities
            group_index (int): Current group index
            groups (list[tuple[int, int]]): Group structure

        Returns:
            list[int]: Corrected quantities for this row (or -1 placeholders if unfixable)
        """
        # Get the individual images for this row
        row_images = []
        for i in range(expected_count):
            img_index = start_index + i
            if img_index < len(quantity_images):
                row_images.append(quantity_images[img_index])

        if len(row_images) != expected_count:
            self.logger.warning(
                "Row at index %d: expected %d images but got %d",
                start_index,
                expected_count,
                len(row_images),
            )
            return [-1] * expected_count

        # Strategy 1: Re-OCR the row as a composite with alternative preprocessing
        self.logger.debug(
            "Row correction: re-processing row at index %d with alternative preprocessing",
            start_index,
        )
        row_composite = self._build_row_composite(row_images, use_alternative=True)
        row_text = await self._text_extractor.extract_raw_text(row_composite, numbers_only=True)
        alt_row_result = self._text_extractor.parse_text_to_lists(row_text)

        if alt_row_result and len(alt_row_result) == 1:
            alt_quantities = alt_row_result[0]
            if len(alt_quantities) == expected_count and self._validate_descending_in_context(
                alt_quantities, previous_quantities, group_index, groups
            ):
                self.logger.debug("Row re-OCR succeeded: %s -> %s", row_quantities, alt_quantities)
                return alt_quantities

        # Strategy 2: Re-OCR with different scale
        self.logger.debug("Trying row re-OCR with different scale")
        row_composite_scaled = self._build_row_composite(row_images, scale_factor=3)
        row_text = await self._text_extractor.extract_raw_text(
            row_composite_scaled, numbers_only=True
        )
        scaled_row_result = self._text_extractor.parse_text_to_lists(row_text)

        if scaled_row_result and len(scaled_row_result) == 1:
            scaled_quantities = scaled_row_result[0]
            if len(scaled_quantities) == expected_count and self._validate_descending_in_context(
                scaled_quantities, previous_quantities, group_index, groups
            ):
                self.logger.debug(
                    "Row re-OCR with scale succeeded: %s -> %s", row_quantities, scaled_quantities
                )
                return scaled_quantities

        # Strategy 3: OCR each quantity individually (parallel)
        self.logger.debug(
            "Attempting individual OCR for indices %d to %d",
            start_index,
            start_index + expected_count - 1,
        )

        individual_results = list(
            await asyncio.gather(*[self._ocr_single_quantity(img) for img in row_images])
        )

        if self._validate_descending_in_context(
            individual_results, previous_quantities, group_index, groups
        ):
            self.logger.debug("Individual OCR succeeded: %s", individual_results)
            return individual_results

        # Strategy 4: Individual OCR with alternative preprocessing (parallel)
        self.logger.debug("Trying individual OCR with alternative preprocessing")
        alt_results = list(
            await asyncio.gather(
                *[self._ocr_single_quantity(img, use_alternative=True) for img in row_images]
            )
        )

        if self._validate_descending_in_context(
            alt_results, previous_quantities, group_index, groups
        ):
            self.logger.debug("Alternative individual OCR succeeded: %s", alt_results)
            return alt_results

        # Last resort: mark all as -1
        self.logger.warning(
            "Could not correct row at index %d. Marking %d quantities as unknown.",
            start_index,
            expected_count,
        )
        return [-1] * expected_count

    def _build_row_composite(
        self,
        row_images: list[NDArray[np.uint8]],
        use_alternative: bool = False,
        scale_factor: int = 2,
    ) -> NDArray[np.uint8]:
        """Build a composite image from individual quantity images for a row.

        Args:
            row_images (list[NDArray[np.uint8]]): Individual quantity box images
            use_alternative (bool): Use alternative preprocessing (Otsu threshold)
            scale_factor (int): Scale factor for upscaling

        Returns:
            NDArray[np.uint8]: Composite row image ready for OCR
        """
        if not row_images:
            return np.zeros((32, 64, 3), dtype=np.uint8)

        # Get dimensions from first image
        box_height, box_width = row_images[0].shape[:2]
        gap = 10  # Gap between quantities for OCR separation

        # Calculate composite dimensions
        total_width = len(row_images) * box_width + (len(row_images) - 1) * gap
        composite_height = box_height

        # Create black background
        composite = np.zeros((composite_height, total_width, 3), dtype=np.uint8)

        # Place each quantity image
        x_offset = 0
        for img in row_images:
            h, w = img.shape[:2]
            composite[0:h, x_offset : x_offset + w] = img
            x_offset += w + gap

        # Upscale
        upscaled = cv2.resize(
            composite,
            None,
            fx=scale_factor,
            fy=scale_factor,
            interpolation=cv2.INTER_CUBIC,
        )

        # Convert to grayscale
        gray = cv2.cvtColor(upscaled, cv2.COLOR_RGB2GRAY)

        if use_alternative:
            # Otsu thresholding
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            processed = cv2.dilate(binary, kernel, iterations=1)
        else:
            # Standard preprocessing
            _, binary = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            inverted = cv2.bitwise_not(cleaned)
            eroded = cv2.erode(inverted, kernel, iterations=1)
            processed = cv2.bitwise_not(eroded)

        # Convert back to RGB
        result = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
        return np.asarray(result, dtype=np.uint8)

    async def _ocr_single_quantity(
        self, quantity_image: NDArray[np.uint8], use_alternative: bool = False
    ) -> int:
        """OCR a single quantity image.

        Args:
            quantity_image (NDArray[np.uint8]): Single quantity box image
            use_alternative (bool): Use alternative preprocessing

        Returns:
            int: Detected quantity or -1 if detection failed
        """
        # Preprocess the single quantity image
        if use_alternative:
            processed = self._preprocess_quantity_alternative(quantity_image)
        else:
            processed = self._preprocess_quantity_standard(quantity_image)

        # Run OCR
        text = await self._text_extractor.extract_raw_text(processed, numbers_only=True)
        text = text.strip()

        if not text:
            return -1

        # Parse the result
        try:
            if text.endswith("k+"):
                return int(text[:-2]) * 1000
            return int(text)
        except ValueError:
            self.logger.debug("Failed to parse single quantity OCR result: '%s'", text)
            return -1

    def _preprocess_quantity_standard(self, quantity_image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Standard preprocessing for single quantity image.

        Matches the preprocessing used in _build_quantity_composite_image.

        Args:
            quantity_image (NDArray[np.uint8]): Raw quantity box image

        Returns:
            NDArray[np.uint8]: Preprocessed image ready for OCR
        """
        # Upscale
        upscaled = cv2.resize(quantity_image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Convert to binary
        gray = cv2.cvtColor(upscaled, cv2.COLOR_RGB2GRAY)
        _, binary = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)

        # Morphological close
        kernel = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # Erosion (as in composite processing)
        inverted = cv2.bitwise_not(cleaned)
        eroded = cv2.erode(inverted, kernel, iterations=1)
        final = cv2.bitwise_not(eroded)

        # Convert back to RGB
        result = cv2.cvtColor(final, cv2.COLOR_GRAY2RGB)
        return np.asarray(result, dtype=np.uint8)

    def _preprocess_quantity_alternative(
        self, quantity_image: NDArray[np.uint8]
    ) -> NDArray[np.uint8]:
        """Alternative preprocessing for single quantity image.

        Uses Otsu thresholding and dilation instead of fixed threshold and erosion.

        Args:
            quantity_image (NDArray[np.uint8]): Raw quantity box image

        Returns:
            NDArray[np.uint8]: Preprocessed image ready for OCR
        """
        # Upscale more aggressively
        upscaled = cv2.resize(quantity_image, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

        # Convert to grayscale and apply Otsu thresholding
        gray = cv2.cvtColor(upscaled, cv2.COLOR_RGB2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Dilation instead of erosion
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        dilated = cv2.dilate(binary, kernel, iterations=1)

        # Convert back to RGB
        result = cv2.cvtColor(dilated, cv2.COLOR_GRAY2RGB)
        return np.asarray(result, dtype=np.uint8)

    def _prepare_image_for_detection(
        self,
        image: NDArray[np.uint8],
        scale_factor: float,
        use_inv: bool = True,
        extra_upscale: bool = False,
    ) -> NDArray[np.uint8]:
        """Apply preprocessing to the image for better text detection.

        Uses Otsu's thresholding to automatically determine optimal threshold based on
        the image histogram, providing robust detection across different image conditions.

        Args:
            image (NDArray[np.uint8]): Image region to preprocess
            scale_factor (float): Resolution scale factor from detector
            use_inv (bool): Whether to use inverted thresholding
            extra_upscale (bool): Apply additional 2x upscale for better OCR accuracy.
                Useful for alphanumeric text where "1" can be confused with "]".

        Returns:
            NDArray[np.uint8]: Processed image ready for OCR
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        upscale_factor = 2 / scale_factor
        if extra_upscale:
            upscale_factor *= 2

        upscaled = cv2.resize(
            gray, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC
        )

        if use_inv:
            threshold_mode = cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        else:
            threshold_mode = cv2.THRESH_BINARY + cv2.THRESH_OTSU

        _, binary = cv2.threshold(upscaled, 0, 255, threshold_mode)

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

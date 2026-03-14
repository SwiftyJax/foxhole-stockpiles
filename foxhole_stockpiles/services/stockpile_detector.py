"""Foxhole Stockpiles - Stockpile Detector Module."""

import logging

import cv2
import numpy as np
from numpy.typing import NDArray

from foxhole_stockpiles.core.settings import get_settings
from foxhole_stockpiles.core.settings.sections.ocr import OCRSettings
from foxhole_stockpiles.models.stockpile_image_regions import StockpileImageRegions

type Coordinates = tuple[int, int]  # (x, y) coordinates of the top-left corner of a quantity box
type BoundingBox = tuple[int, int, int, int]  # (x, y, width, height) of a stockpile region
type GroupResult = tuple[int, int]  # amount, index


class StockpileDetector:
    """Detects stockpile components in Foxhole game screenshots with resolution scaling."""

    def __init__(self, image: NDArray[np.uint8], settings: OCRSettings | None = None) -> None:
        """Initialize detector with image data and calculate scale factor.

        Args:
            image: Image data as numpy array (RGB format)
            settings: OCR settings or None
        """
        self._settings = settings if settings else get_settings().ocr

        self._logger = logging.getLogger(__name__)

        # Prepare and store image
        self.img = self._prepare_image_array(image)

        self.scale_factor = 1.0

        # Icon size
        self.box_width: int = 0
        self.box_height: int = 0

        # Distance between boxes
        self.column_offset: int = 0
        self.row_offset: float = 0.0
        self.group_offset: float = 0

        # Title region (stockpile type and name)
        self.title_margin: int = 0
        self.title_min_width: int = 0
        self.title_height: int = 0
        self.stockpile_type_width: int = 0
        self.stockpile_name_width: int = 0

        # Screenshot information. Shard and ingame timestamp
        self.shard_x: int = 0
        self.shard_y: int = 0
        self.shard_width: int = 0
        self.shard_height: int = 0

        # Detected quantities locations
        self.quantities: list[Coordinates] = []

        # Detected stockpile name and type  locations
        self.stockpile_name: BoundingBox | None = None
        self.stockpile_type: BoundingBox | None = None

        # Detected groups for icons
        self.groups: list[GroupResult] = []

        # BMS Longhook has a single item in the first row
        self.has_single_item_first_row: bool = False

        self.icon_to_quantity_offset: int = 0

        self.composite_image: NDArray[np.uint8] = np.empty((0, 0, 3), dtype=np.uint8)
        self.height, self.width = self.img.shape[:2]

        self.valid_x_positions: list[int] = []  # valid column positions (absolute)
        self.valid_x_positions_offsets: list[int] = []  # valid column positions (offsets)
        self.first_quantity_x: int = -1
        self.first_quantity_y: int = -1
        self.max_detected_x: int = -1

        self._rescale_layout_values()

    def _prepare_image_array(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Prepare image array for processing by converting RGBA to RGB if needed.

        Args:
            image (NDArray[np.uint8]): Input image array

        Returns:
            NDArray[np.uint8]: Image array in RGB format
        """
        # Convert RGBA to RGB if necessary
        if image.shape[2] == 4:
            return np.asarray(cv2.cvtColor(image, cv2.COLOR_RGBA2RGB), dtype=np.uint8)

        return image

    def _rescale_layout_values(self) -> None:
        """Rescale layout values based on the image height."""
        height, width = self.img.shape[:2]

        # Calculate scale factor based on image height relative to base resolution
        self.scale_factor = height / self._settings.height

        # Scale all dimensions
        self.box_width = int(self._settings.box_width * self.scale_factor)
        self.box_height = int(self._settings.box_height * self.scale_factor)
        column_offset: float = (
            self._settings.column_offset + self._settings.box_width
        ) * self.scale_factor
        self.column_offset = int(column_offset)
        self.valid_x_positions_offsets = [round(column_offset * i) for i in range(6)]
        self.row_offset = self._settings.row_offset * self.scale_factor
        self.group_offset = self._settings.group_offset * self.scale_factor

        self.title_margin = int(self._settings.title_margin * self.scale_factor)
        self.title_min_width = int(self._settings.title_min_width * self.scale_factor)
        self.title_height = int(self._settings.title_height * self.scale_factor)
        self.stockpile_type_width = int(4 * self.box_width)
        self.stockpile_name_width = int(2.5 * self.box_width)

        # Shard and ingame timestamp regions
        self.shard_x = self.box_height
        self.shard_y = self.height - int(self._settings.box_height * self.scale_factor * 3)
        self.shard_height = int(self.box_height)
        self.shard_width = int(self.box_width * 3.5)

        # Icon shift to quantity box
        self.icon_to_quantity_offset = int(
            self._settings.icon_to_quantity_offset * self.scale_factor
        )

        self._logger.debug(
            "Image resolution: %dx%d. Scale factor: %.3f", width, height, self.scale_factor
        )

        self._logger.debug("Scaled box size: %dx%d", self.box_width, self.box_height)

    def _in_valid_range(self, first: int, second: int) -> bool:
        """Check if two numbers are in the valid range.

        Args:
            first (int): First point
            second (int): Second point

        Returns:
            bool: If the points are in the valid range
        """
        return abs(second - first) <= self._settings.pixel_diff_tolerance

    def _create_grey_mask(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Create binary mask for pixels in grey range.

        Args:
            image (NDArray[np.uint8]): RGB image array

        Returns:
            NDArray[np.uint8]: Binary mask where grey pixels are white (255) and others are
                black (0)
        """
        # Convert to HSV for better grey detection
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

        # Create mask for low saturation (grey) pixels. Any hue, low saturation, value in range
        lower_bound = np.array([0, 0, self._settings.gray_lower])
        upper_bound = np.array([179, 30, self._settings.gray_upper])

        hsv_mask = cv2.inRange(hsv, lower_bound, upper_bound)

        # Also create RGB mask for more precise control
        lower_rgb = np.array(
            [self._settings.gray_lower, self._settings.gray_lower, self._settings.gray_lower]
        )
        upper_rgb = np.array(
            [self._settings.gray_upper, self._settings.gray_upper, self._settings.gray_upper]
        )
        rgb_mask = cv2.inRange(image, lower_rgb, upper_rgb)

        # Combine both masks (intersection)
        return np.asarray(cv2.bitwise_and(hsv_mask, rgb_mask), dtype=np.uint8)

    def _filter_contour_by_size(self, contour: cv2.typing.Rect) -> Coordinates | None:
        """Analyze a contour to see if it matches our square criteria.

        Args:
            contour (cv2.typing.Rect): Contour to analyze

        Returns:
            Coordinates of the square if it matches criteria, otherwise None
        """
        # Get bounding rectangle
        x, y, w, h = contour

        # Check if dimensions are approximately correct
        if not self._in_valid_range(first=w, second=self.box_width) or not self._in_valid_range(
            first=h, second=self.box_height
        ):
            return None

        return (x, y)

    def _detect_first_group(self, contours: list[cv2.typing.Rect]) -> int:
        """Detect the first group (1 or 2 boxes) and establish grid.

        Args:
            contours (Rect): Detected points

        Returns:
            int: the index to continue processing from, or 0 if first group not found.
        """
        first_box_index = 0

        while first_box_index < len(contours) - 1:
            coords1 = self._filter_contour_by_size(contours[first_box_index])
            if coords1 is None:
                first_box_index += 1
                continue

            x1, y1 = coords1

            # Look for second box in same row
            second_box_index = first_box_index + 1
            while second_box_index < len(contours):
                coords2 = self._filter_contour_by_size(contours[second_box_index])
                if coords2 is None:
                    second_box_index += 1
                    continue

                x2, y2 = coords2
                x_diff = abs(x2 - x1)

                # Check if in same row
                if self._in_valid_range(y1, y2):
                    if self._in_valid_range(x_diff, self.column_offset):
                        # Found 2-box pair
                        self.first_column_x = min(x1, x2)
                        self.first_column_y = y1
                        self.valid_x_positions = [
                            self.first_column_x + offset
                            for offset in self.valid_x_positions_offsets
                        ]
                        self.quantities = [(x1, y1), (x2, y2)]
                        return second_box_index + 1
                    second_box_index += 1
                    continue

                # Second box is in different row - first box is alone
                # Check if second box could be start of a valid grid (BMS Longhook)
                if self._in_valid_range(x1, x2):
                    # Same column - this is a single-item first row
                    self.first_column_x = x1
                    self.first_column_y = y1
                    self.valid_x_positions = [
                        self.first_column_x + offset for offset in self.valid_x_positions_offsets
                    ]
                    self.quantities = [(x1, y1)]
                    self.has_single_item_first_row = True
                    return first_box_index + 1

                # Different column in different row - skip this second box and keep looking
                second_box_index += 1

            first_box_index += 1

        return 0

    def detect_quantity_boxes(self) -> None:
        """Detect quantities and groups from a stockpile image."""
        grey_mask = self._create_grey_mask(self.img)

        # Apply morphological operations to separate merged boxes
        # Use larger kernel for opening to break connections between quantity boxes and background
        close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        grey_mask_close = cv2.morphologyEx(grey_mask, cv2.MORPH_CLOSE, close_kernel)

        # Larger opening kernel to separate merged regions
        open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        grey_mask_open = cv2.morphologyEx(grey_mask_close, cv2.MORPH_OPEN, open_kernel)

        # Find and filter contours - FIRST PASS to detect adaptive threshold
        _contours, _ = cv2.findContours(grey_mask_open, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Analyze grey values from detected boxes to refine the threshold
        background_greys = []
        for _contour in _contours:
            rect = cv2.boundingRect(_contour)
            x, y, w, h = rect
            if self._filter_contour_by_size(rect) is not None:
                roi = cv2.cvtColor(self.img[y : y + h, x : x + w], cv2.COLOR_RGB2GRAY)
                mask_pixels = roi[grey_mask_open[y : y + h, x : x + w] > 0]
                if mask_pixels.size > 0:
                    # Use median to get background grey (ignores text pixels)
                    background_greys.append(int(np.median(mask_pixels)))

        # If we found at least 2 boxes, refine grey range based on measured values
        if len(background_greys) >= 2:
            measured_median = int(np.median(background_greys))

            # Adaptive range: median ± 5 margin (bounded by configured limits)
            margin = 5
            adaptive_lower = max(measured_median - margin, self._settings.gray_lower)
            adaptive_upper = min(measured_median + margin, self._settings.gray_upper)

            self._logger.debug(
                "Adaptive grey: median=%d -> range [%d-%d] (configured: [%d-%d])",
                measured_median,
                adaptive_lower,
                adaptive_upper,
                self._settings.gray_lower,
                self._settings.gray_upper,
            )

            # Recreate mask if adaptive range is tighter than configured
            if (
                adaptive_lower > self._settings.gray_lower
                or adaptive_upper < self._settings.gray_upper
            ):
                original_gray_lower = self._settings.gray_lower
                original_gray_upper = self._settings.gray_upper
                self._settings.gray_lower = adaptive_lower
                self._settings.gray_upper = adaptive_upper
                grey_mask = self._create_grey_mask(self.img)
                self._settings.gray_lower = original_gray_lower
                self._settings.gray_upper = original_gray_upper

                # Reapply morphological operations
                grey_mask_close = cv2.morphologyEx(grey_mask, cv2.MORPH_CLOSE, close_kernel)
                grey_mask_open = cv2.morphologyEx(grey_mask_close, cv2.MORPH_OPEN, open_kernel)

                # Find contours again with adaptive threshold
                _contours, _ = cv2.findContours(
                    grey_mask_open, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

        # Filter contours by size immediately using existing method
        contours = []
        for _contour in _contours:
            rect = cv2.boundingRect(_contour)
            if self._filter_contour_by_size(rect) is not None:
                contours.append(rect)

        # Reorder the contours to make Soldier and Maintentance Supplies the first ones
        # Group boxes by row (within tolerance), then sort by x within each row
        tolerance = self._settings.pixel_diff_tolerance

        # First sort by y to get initial grouping
        contours.sort(key=lambda box: box[1])

        # Group contours into rows based on y-coordinate tolerance
        # Since contours are sorted by y, we only need to check the last row
        rows: list[list[cv2.typing.Rect]] = []
        for contour in contours:
            _, y, _, _ = contour
            if rows and abs(rows[-1][0][1] - y) < tolerance:
                rows[-1].append(contour)
            else:
                rows.append([contour])

        # Sort each row by x, then flatten back to single list
        contours = []
        for row in rows:
            row.sort(key=lambda box: box[0])
            contours.extend(row)

        # Find first group and establish grid
        start_index = self._detect_first_group(contours)
        if not start_index:
            self.quantities = []
            self.groups = []
            return

        # Initialize group tracking
        first_group_size = len(self.quantities)  # 1 for BMS Longhook, 2 for standard
        current_group_count = first_group_size
        current_group_start_idx = 0
        last_y = self.first_column_y
        current_x_idx = first_group_size
        current_group_idx = 0
        self.max_detected_x = self.quantities[-1][0]

        # Process remaining boxes
        contour_index = start_index
        while contour_index < len(contours):
            current_contour = contours[contour_index]
            contour_index += 1
            # All contours are already filtered by size, just extract coordinates
            x, y, _, _ = current_contour

            # Determine expected x positions
            expected_column_index = current_x_idx % 6

            y_diff_last = abs(y - last_y)
            # New group: group_offset gap or first group with larger gap
            is_new_group = self._in_valid_range(y_diff_last, int(self.group_offset)) or (
                current_group_idx == 0
                and (
                    # Bunkers with one row of orange icons
                    self._in_valid_range(y_diff_last, int(self.group_offset * 2))
                    # Bunkers with two rows of orange icons
                    or self._in_valid_range(
                        y_diff_last, int(self.group_offset * 2 + self.row_offset)
                    )
                )
            )
            is_same_row = self._in_valid_range(y_diff_last, 0)
            is_next_row = self._in_valid_range(y_diff_last, int(self.row_offset))

            # Check if this box matches expected next column position
            if not self._in_valid_range(x, self.valid_x_positions[expected_column_index]):
                if not self._in_valid_range(x, self.valid_x_positions[0]):
                    self._logger.debug(
                        "Box %d at (%d,%d) doesn't match expected column coords (%d) or (%d)",
                        contour_index,
                        x,
                        y,
                        self.valid_x_positions[expected_column_index],
                        self.valid_x_positions[0],
                    )
                    # Doesn't match expected column - skip
                    continue
                # Reset to column 0 for new row
                expected_column_index = 0
                current_x_idx = 0

            if is_new_group:
                self.groups.append((current_group_count, current_group_start_idx))
                current_group_start_idx = len(self.quantities)
                current_group_count = 0
                current_x_idx = 0
                current_group_idx += 1
            elif not is_same_row and not is_next_row:
                # Invalid row - skip
                self._logger.debug(
                    "Box at (%d,%d) doesn't match expected row in group %d",
                    x,
                    y,
                    current_group_idx,
                )
                continue

            # Add current box to group
            self.quantities.append((x, y))
            self.max_detected_x = max(self.max_detected_x, x)
            current_group_count += 1
            last_y = y
            current_x_idx += 1

        # Add final group if it has boxes
        if current_group_count > 0:
            self.groups.append((current_group_count, current_group_start_idx))

        self._build_quantity_composite_image()

    def detect_stockpile_regions(self) -> None:
        """Detect stockpile type and name from the quantities detected."""
        if not self.quantities:
            self._logger.warning("No quantity boxes detected, skipping stockpile region detection.")
            return

        x, y = self.quantities[0]

        title_min_x = x - self.column_offset + self.box_width
        title_y = y - int(self.row_offset)

        title_max_x = max(
            self.max_detected_x + self.box_width + self.title_margin,
            title_min_x + self.title_min_width,
        )

        # Calculate stockpile name region
        name_x = title_max_x - self.stockpile_name_width - self.box_width

        self.stockpile_type = (
            title_min_x + self.title_margin * 3 // 4,
            title_y + self.title_height // 8,
            self.stockpile_type_width,
            self.title_height * 3 // 4,
        )
        self.stockpile_name = (name_x, title_y, self.stockpile_name_width, self.title_height)

    def analize(self) -> None:
        """Detect quantity boxes, stockpile type regions, and stockpile name regions."""
        self.detect_quantity_boxes()
        self.detect_stockpile_regions()

    def draw_and_save_results(self) -> None:
        """Draw rectangles around detected components and save the result.

        Args:
            detection_result: Detection results containing boxes and regions
        """
        # Create a copy for drawing
        result_img = self.img.copy()

        # Draw red rectangles around each detected quantity box
        for x, y in self.quantities:
            cv2.rectangle(
                result_img,
                (x, y),
                (x + self.box_width, y + self.box_height),
                (0, 0, 255),
                max(1, int(2 * self.scale_factor)),  # Scale line thickness
            )

        # Draw blue rectangles around each detected stockpile type region
        if self.stockpile_type is not None:
            x, y, w, h = self.stockpile_type
            cv2.rectangle(
                result_img,
                (x, y),
                (x + w, y + h),
                (255, 0, 0),
                max(1, int(2 * self.scale_factor)),  # Scale line thickness
            )

        # Draw green rectangles around each detected stockpile name region
        if self.stockpile_name is not None:
            x, y, w, h = self.stockpile_name
            cv2.rectangle(
                result_img,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                max(1, int(2 * self.scale_factor)),  # Scale line thickness
            )

        if self.groups:
            # Draw groups as text on the image
            for index, (size, start) in enumerate(self.groups):
                x, y = self.quantities[start]
                cv2.putText(
                    result_img,
                    f"Group {index}: {size} icon(s)",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5 * self.scale_factor,
                    (255, 255, 0),
                    max(1, int(1 * self.scale_factor)),
                )

        if self.shard_x and self.shard_y:
            cv2.rectangle(
                result_img,
                (self.shard_x, self.shard_y),
                (self.shard_x + self.shard_width, self.shard_y + self.shard_height),
                (0, 255, 255),  # Cyan for shard
                max(1, int(2 * self.scale_factor)),
            )

        # Save the result
        output_path = "stockpile_detection_result.png"
        cv2.imwrite(output_path, result_img)
        self._logger.info("Result saved to: %s", output_path)

        output_path = "stockpile_quantities_result.png"
        cv2.imwrite(output_path, self.composite_image)
        self._logger.info("Composite quantitites saved to: %s", output_path)
        self._logger.debug("Color legend: Red=Quantity boxes, Blue=Type region, Green=Name region")

    def _build_quantity_composite_image(self) -> None:
        """Create a composite image with all the quantities, preprocessed for OCR."""
        quantities = [
            self.img[y : y + self.box_height, x : x + self.box_width] for x, y in self.quantities
        ]
        min_coords_x, min_coords_y = (
            (self.stockpile_type[0], self.stockpile_type[1])
            if self.stockpile_type
            else self.quantities[0]
        )

        composite_width = self.title_min_width * 2 + self.box_width
        last_y = self.quantities[-1][1] - min_coords_y
        composite_height = last_y + self.box_height * 2

        # Black background image with the grey quantities on top
        composite = np.full((composite_height, composite_width, 3), 0, dtype=np.uint8)
        for index, (x, y) in enumerate(self.quantities):
            rel_x, rel_y = x - min_coords_x, y - min_coords_y
            composite[rel_y : rel_y + self.box_height, rel_x : rel_x + self.box_width] = quantities[
                index
            ]

        # Apply upscaling adjusted by the current scale factor
        upscale_factor = 2 / self.scale_factor
        upscaled = cv2.resize(
            composite, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC
        )

        # Convert to binary and apply morphological operations
        gray = cv2.cvtColor(upscaled, cv2.COLOR_RGB2GRAY)
        _, binary = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)
        kernel = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # Invert to black text on white, apply erosion to thin text, invert back
        # This improves OCR accuracy for certain number combinations (e.g., "57")
        inverted = cv2.bitwise_not(cleaned)
        eroded = cv2.erode(inverted, kernel, iterations=1)
        final = cv2.bitwise_not(eroded)

        # Convert back to RGB
        post_cleaned = cv2.cvtColor(final, cv2.COLOR_GRAY2RGB)

        self.composite_image = np.asarray(post_cleaned, dtype=np.uint8)

    def get_stockpile_images(self) -> StockpileImageRegions | None:
        """Get detected stockpile images as a StockpileImages model.

        Returns:
            StockpileImages: Model containing detected stockpile regions or None if no quantities
        """
        if not self.quantities:
            return None

        quantities = [
            self.img[y : y + self.box_height, x : x + self.box_width] for x, y in self.quantities
        ]

        # icons are shifted to the left of the quantity box by "icon_to_quantity_offset"
        offset = self.icon_to_quantity_offset
        icons = [
            self.img[y : y + self.box_height, x - offset : x - offset + self.box_height]
            for x, y in self.quantities
        ]

        stockpile_type = (
            self.img[
                self.stockpile_type[1] : self.stockpile_type[1] + self.stockpile_type[3],
                self.stockpile_type[0] : self.stockpile_type[0] + self.stockpile_type[2],
            ]
            if self.stockpile_type
            else None
        )

        stockpile_name = (
            self.img[
                self.stockpile_name[1] : self.stockpile_name[1] + self.stockpile_name[3],
                self.stockpile_name[0] : self.stockpile_name[0] + self.stockpile_name[2],
            ]
            if self.stockpile_name
            else None
        )

        # Ingame shard and timestamp
        shard = (
            self.img[
                self.shard_y : self.shard_y + self.shard_height,
                self.shard_x : self.shard_x + self.shard_width,
            ]
            if self.shard_x and self.shard_y
            else None
        )

        return StockpileImageRegions(
            quantities=quantities,
            composite_quantities_image=self.composite_image,
            icons=icons,
            stockpile_type=stockpile_type,
            stockpile_name=stockpile_name,
            shard=shard,
            resolution=f"{self.width}x{self.height}",
            vertical_resolution=self.height,
            groups=self.groups,
        )

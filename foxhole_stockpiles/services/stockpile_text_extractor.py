"""Foxhole Stockpiles - Stockpile Text Extractor Module."""

import asyncio
import logging
import os

import cv2
import numpy as np
import pytesseract
from numpy.typing import NDArray

from foxhole_stockpiles.enums.supported_language import SupportedLanguage


class StockpileTextExtractor:
    """Extract quantities from composite images created by the stockpile detector.

    Handles numbers with 'k' suffix and '+' suffix (e.g., "500k", "999+").
    """

    def __init__(
        self,
        tessdata_path: str | None = None,
        custom_model: str | None = None,
    ) -> None:
        """Initialize the OCR extractor.

        Args:
            tessdata_path (str | None): Path to tessdata directory for custom models (optional)
            custom_model (str | None): Name of the custom trained model to use for number
                recognition (e.g., renner_numbers). This replaces English for numbers.
        """
        self._logger = logging.getLogger(__name__)
        self.tessdata_path = os.path.abspath(tessdata_path) if tessdata_path else None
        self.custom_model = custom_model

    async def extract_raw_text(
        self,
        image: NDArray[np.uint8],
        numbers_only: bool = True,
        language: SupportedLanguage | None = None,
    ) -> str:
        """Extract raw text using custom trained model.

        Args:
            image (NDArray[np.uint8]): Processed image
            numbers_only (bool): Limit caracter detection to quantities (True) or all chars (False)
            language (SupportedLanguage | None): Language for text detection. If None, uses all
                supported languages. Only used when numbers_only=False.

        Returns:
            str: Raw OCR text output
        """
        # Use custom trained model for better Renner font recognition
        config = self.get_tesseract_config(numbers_only=numbers_only, language=language)
        result = await asyncio.to_thread(pytesseract.image_to_string, image, config=config)
        if result is None:
            return ""

        detected = str(result).rstrip()
        self._logger.debug("Extracted raw text from image: %s", detected)

        return detected

    async def extract_quantities(self, composite_image: NDArray[np.uint8]) -> list[list[int]]:
        """Extract all quantities from a composite image maintaining row/column structure.

        Uses custom model first, then tries with an eroded image to handle cases where the
        custom model has blind spots for certain number combinations (e.g., "57"). Erosion
        makes text slightly thinner which can help OCR distinguish certain characters.

        Args:
            composite_image (NDArray[np.uint8]): Processed composite image (black text on white
                background)

        Returns:
            list[list[int]]: List of quantities detected by row
        """
        # Extract text with custom trained model
        raw_text = await self.extract_raw_text(composite_image)
        primary_result = self.parse_text_to_lists(raw_text)

        # If using a custom model, also try with eroded image for missed detections
        if self.custom_model:
            eroded_image = self._apply_erosion(composite_image)
            fallback_text = await self.extract_raw_text(eroded_image)
            fallback_result = self.parse_text_to_lists(fallback_text)

            # Merge results: use eroded result line when it detected more numbers
            primary_result = self._merge_ocr_results(primary=primary_result, eroded=fallback_result)

        return primary_result

    def _apply_erosion(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Apply erosion to make text slightly thinner for better OCR recognition.

        This helps handle cases where the custom model fails to recognize certain number
        combinations due to font rendering characteristics.

        Args:
            image (NDArray[np.uint8]): Input image (RGB format, black text on white background)

        Returns:
            NDArray[np.uint8]: Eroded image in RGB format
        """
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        # Invert so text is white (for erosion to thin it)
        _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
        # Erode with 2x2 kernel to thin the text
        kernel = np.ones((2, 2), np.uint8)
        eroded = cv2.erode(binary, kernel, iterations=1)
        # Invert back to black text on white background
        eroded_inv = cv2.bitwise_not(eroded)
        # Convert back to RGB
        return np.asarray(cv2.cvtColor(eroded_inv, cv2.COLOR_GRAY2RGB), dtype=np.uint8)

    def _merge_ocr_results(
        self, primary: list[list[int]], eroded: list[list[int]]
    ) -> list[list[int]]:
        """Merge OCR results from primary and eroded image passes.

        For each line, use the result that detected more numbers. This handles cases where
        the custom model misses certain number combinations (e.g., "57") on the original
        image but detects them correctly on the eroded version.

        Args:
            primary (list[list[int]]): Results from the original image
            eroded (list[list[int]]): Results from the eroded image

        Returns:
            list[list[int]]: Merged results with best detection per line
        """
        merged: list[list[int]] = []
        max_lines = max(len(primary), len(eroded))

        for i in range(max_lines):
            primary_line = primary[i] if i < len(primary) else []
            eroded_line = eroded[i] if i < len(eroded) else []

            # Use the line that detected more numbers
            if len(eroded_line) > len(primary_line):
                self._logger.debug(
                    "Line %d: using eroded (%d numbers) over primary (%d numbers)",
                    i,
                    len(eroded_line),
                    len(primary_line),
                )
                merged.append(eroded_line)
            else:
                merged.append(primary_line)

        return merged

    def parse_text_to_lists(self, text: str) -> list[list[int]]:
        r"""Parse text containing space-separated numbers into list of lists of integers.

        Args:
            text (str): Text with numbers separated by spaces, lines separated by \n
                Numbers can have "k+" suffix meaning multiply by 1000

        Returns:
            list[list[int]]: List of lists containing parsed integers
        """
        result: list[list[int]] = []

        # Split by newlines and process each line
        lines = text.strip().split("\n")
        self._logger.debug("Processing %d lines from text", len(lines))

        for line_idx, line in enumerate(lines):
            if not line.strip():
                result.append([])
                continue

            numbers: list[int] = []
            tokens = line.strip().split()
            self._logger.debug("Processing line %d with %d tokens", line_idx, len(tokens))

            for token in tokens:
                if token.endswith("k+"):
                    # Remove 'k+' and multiply by 1000
                    try:
                        base_number = int(token[:-2])
                    except ValueError:
                        self._logger.warning("Invalid k+ token: %s", token)
                        base_number = -1
                    numbers.append(base_number * 1000)
                    self._logger.debug("Parsed k+ token %s as %d", token, base_number * 1000)
                else:
                    try:
                        parsed_number = int(token)
                        numbers.append(parsed_number)
                    except ValueError:
                        # Skip invalid tokens
                        self._logger.warning("Skipping invalid token: %s", token)
                        continue

            if numbers:  # Only add non-empty lists
                result.append(numbers)
                self._logger.debug("Added %d numbers to result for line %d", len(numbers), line_idx)

        self._logger.debug("Successfully parsed %d rows from text", len(result))
        return result

    def get_tesseract_config(
        self, numbers_only: bool = True, language: SupportedLanguage | None = None
    ) -> str:
        """Get the Tesseract configuration string used.

        Args:
            numbers_only (bool): Detect quantities (numbers, k+)
            language (SupportedLanguage | None): Language for text detection

        Returns:
            str: Tesseract configuration string
        """
        numbers = ""
        tessdata_dir = ""

        if numbers_only:
            # For numbers, always use custom model if specified (e.g., renner_numbers)
            # The custom model is trained to replace English for number recognition
            if self.custom_model:
                model = f"-l {self.custom_model}"
            else:
                # Fallback to all languages if no custom model
                model = f"-l {SupportedLanguage.get_all_languages_string()}"

            # Add tessdata directory if specified (per-call, not global)
            if self.tessdata_path:
                tessdata_dir = f"--tessdata-dir {self.tessdata_path}"

            numbers = "-c tessedit_char_whitelist=0123456789k+"
        else:
            # For text detection (stockpile name, type, hex_name)
            if language:
                # Use specified language for text detection
                # Convert i18n code to Tesseract code
                model = f"-l {language.get_tesseract_code()}"
            else:
                # Default to all supported languages for text detection
                model = f"-l {SupportedLanguage.get_all_languages_string()}"

        return f"--psm 6 {model} {tessdata_dir} {numbers} --oem 3".strip()

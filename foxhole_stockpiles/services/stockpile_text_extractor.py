"""Foxhole Stockpiles - Stockpile Text Extractor Module."""

import logging
import os

import numpy as np
import pytesseract
from numpy.typing import NDArray


class StockpileTextExtractor:
    """Extract quantities from composite images created by the stockpile detector.

    Handles numbers with 'k' suffix and '+' suffix (e.g., "500k", "999+").
    """

    def __init__(self, tessdata_path: str | None = None, custom_model: str | None = None) -> None:
        """Initialize the OCR extractor.

        Parameters:
            tessdata_path (str | None): Path to tesseract executable (optional)
            custom_model (str | None): Name of the custom trained model to use (default: "custom")
        """
        self._logger = logging.getLogger(__name__)
        self.custom_model = custom_model
        if tessdata_path:
            os.environ["TESSDATA_PREFIX"] = os.path.abspath(tessdata_path)

    def _extract_raw_text(self, image: NDArray[np.uint8]) -> str:
        """Extract raw text using custom trained model.

        Parameters:
            image (NDArray[np.uint8]): Processed image

        Returns:
            str: Raw OCR text output
        """
        # Use custom trained model for better Renner font recognition
        config = self.get_tesseract_config()
        return str(pytesseract.image_to_string(image, config=config) or "")

    def extract_quantities(self, composite_image: NDArray[np.uint8]) -> list[list[int]]:
        """Extract all quantities from a composite image maintaining row/column structure.

        Parameters:
            composite_image (NDArray[np.uint8]): Processed composite image (black text on white
                background)

        Returns:
            list[list[int]]: List of quantities detected by row
        """
        # Extract text with custom trained model
        raw_text = self._extract_raw_text(composite_image)
        self._logger.debug("Extracted raw text from image: %s", raw_text.strip())

        return self.parse_text_to_lists(raw_text)

    def parse_text_to_lists(self, text: str) -> list[list[int]]:
        r"""Parse text containing space-separated numbers into list of lists of integers.

        Parameters:
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

            numbers = []
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
                        self._logger.debug("Parsed token %s as %d", token, parsed_number)
                    except ValueError:
                        # Skip invalid tokens
                        self._logger.warning("Skipping invalid token: %s", token)
                        continue

            if numbers:  # Only add non-empty lists
                result.append(numbers)
                self._logger.debug("Added %d numbers to result for line %d", len(numbers), line_idx)

        self._logger.info("Successfully parsed %d rows from text", len(result))
        return result

    def get_tesseract_config(self) -> str:
        """Get the Tesseract configuration string used.

        Returns:
            str: Tesseract configuration string
        """
        model = f"-l {self.custom_model}" if self.custom_model else ""
        return f"--psm 6 {model} -c tessedit_char_whitelist=0123456789k+ --oem 3"

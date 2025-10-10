"""Stockpile Classifier Service."""

import logging

from foxhole_stockpiles.core.settings import get_settings
from foxhole_stockpiles.enums.stockpile_type import StockpileType


class StockpileTypeClassifier:
    """Service for classifying stockpile types given some text."""

    def __init__(self) -> None:
        """Initialize the classifier service."""
        self._logger = logging.getLogger(__name__)
        self._settings = get_settings()

        # Cache the stockpile type translations for performance
        self._type_translations: dict[str, list[str]] = self._settings.stockpile_types.model_dump()

    def classify_from_text(self, text: str) -> StockpileType:
        """Classify stockpile type from extracted text.

        Args:
            text (str): Extracted text from OCR

        Returns:
            StockpileType: Classified type or UNDEFINED
        """
        if not text:
            return StockpileType.UNDEFINED

        # Clean the text for better matching
        cleaned_text = text.strip()

        # Search through all type translations
        matching_type = self._find_matching_type(cleaned_text)

        if matching_type:
            try:
                return StockpileType(matching_type)
            except ValueError:
                self._logger.warning("Invalid stockpile type found: '%s'", matching_type)
                return StockpileType.UNDEFINED

        # Try fuzzy matching for common OCR errors
        fuzzy_match = self._fuzzy_match_type(cleaned_text)
        if fuzzy_match:
            try:
                return StockpileType(fuzzy_match)
            except ValueError:
                return StockpileType.UNDEFINED

        self._logger.warning("No matching stockpile type for text: '%s'", cleaned_text)
        return StockpileType.UNDEFINED

    def _find_matching_type(self, text: str) -> str | None:
        """Find exact matching stockpile type from text.

        Args:
            text (str): Text to match

        Returns:
            str | None: Matching type name or None
        """
        # Search through all translation sets
        for type_translations in self._type_translations.values():
            if text in type_translations:
                # Return the canonical (first) translation
                return type_translations[0]

        return None

    def _fuzzy_match_type(self, text: str) -> str | None:
        """Attempt fuzzy matching for common OCR errors in type names.

        Args:
            text (str): Text to fuzzy match

        Returns:
            str | None: Best fuzzy match or None
        """
        # Common OCR errors in stockpile type names
        text_variations = [
            text,
            text.replace("l", "I"),  # lowercase l -> uppercase I
            text.replace("I", "l"),  # uppercase I -> lowercase l
            text.replace("0", "O"),  # zero -> O
            text.replace("O", "0"),  # O -> zero
            text.replace("1", "I"),  # one -> I
            text.replace("5", "S"),  # five -> S
            text.replace("8", "B"),  # eight -> B
        ]

        # Try each variation
        for variation in text_variations:
            match = self._find_matching_type(variation)
            if match:
                self._logger.debug(
                    "Fuzzy match found: '%s' -> '%s' -> '%s'", text, variation, match
                )
                return match

        return None

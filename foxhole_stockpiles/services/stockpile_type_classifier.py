"""Stockpile Classifier Service."""

import logging

from foxhole_stockpiles.constants import STOCKPILE_TYPE_TEXTS
from foxhole_stockpiles.core.settings import get_settings
from foxhole_stockpiles.enums.stockpile_type import StockpileType


class StockpileTypeClassifier:
    """Service for classifying stockpile types given some text."""

    def __init__(self) -> None:
        """Initialize the classifier service."""
        self._logger = logging.getLogger(__name__)
        self._settings = get_settings()

        # Build translations combining hardcoded texts with user-configured aliases
        self._type_translations: dict[StockpileType, list[str]] = self._build_translations()

    def _build_translations(self) -> dict[StockpileType, list[str]]:
        """Build the complete translations dict from hardcoded texts and user aliases.

        Returns:
            dict[StockpileType, list[str]]: Combined translations for each type
        """
        # Start with a copy of the hardcoded texts
        translations: dict[StockpileType, list[str]] = {
            stockpile_type: list(texts) for stockpile_type, texts in STOCKPILE_TYPE_TEXTS.items()
        }

        # Map settings field names to StockpileType enum values
        field_to_type: dict[str, StockpileType] = {
            "encampment": StockpileType.ENCAMPMENT,
            "keep": StockpileType.KEEP,
            "safe_house": StockpileType.SAFE_HOUSE,
            "relic_base": StockpileType.RELIC_BASE,
            "bunker_base": StockpileType.BUNKER_BASE,
            "border_base": StockpileType.BORDER_BASE,
            "town_base": StockpileType.TOWN_BASE,
            "bms_longhook": StockpileType.BMS_LONGHOOK,
            "storage_depot": StockpileType.STORAGE_DEPOT,
            "seaport": StockpileType.SEAPORT,
            "aircraft_depot": StockpileType.AIRCRAFT_DEPOT,
            # Note: UNDEFINED has no user-configurable aliases
        }

        # Add user-configured additional aliases from each field
        user_settings = self._settings.stockpile_types
        for field_name, stockpile_type in field_to_type.items():
            aliases: list[str] = getattr(user_settings, field_name, [])
            for alias in aliases:
                if alias not in translations[stockpile_type]:
                    translations[stockpile_type].append(alias)

        return translations

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
            return matching_type

        # Try fuzzy matching for common OCR errors
        fuzzy_match = self._fuzzy_match_type(cleaned_text)
        if fuzzy_match:
            return fuzzy_match

        self._logger.warning("No matching stockpile type for text: '%s'", cleaned_text)
        return StockpileType.UNDEFINED

    def _find_matching_type(self, text: str) -> StockpileType | None:
        """Find exact matching stockpile type from text.

        Args:
            text (str): Text to match

        Returns:
            StockpileType | None: Matching type or None
        """
        # Search through all translation sets
        for stockpile_type, type_translations in self._type_translations.items():
            if text in type_translations:
                return stockpile_type

        return None

    def _fuzzy_match_type(self, text: str) -> StockpileType | None:
        """Attempt fuzzy matching for common OCR errors in type names.

        Args:
            text (str): Text to fuzzy match

        Returns:
            StockpileType | None: Best fuzzy match or None
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

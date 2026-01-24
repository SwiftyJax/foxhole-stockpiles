"""Tests for services.stockpile_type_classifier module.

This module contains comprehensive tests for the StockpileTypeClassifier class,
which classifies stockpile types from extracted OCR text using hardcoded
translations and user-configured additional aliases.
"""

from unittest.mock import MagicMock, patch

from foxhole_stockpiles.constants import STOCKPILE_TYPE_TEXTS
from foxhole_stockpiles.core.settings import AppSettings
from foxhole_stockpiles.core.settings.sections.stockpile_types import StockpileTypesSettings
from foxhole_stockpiles.enums.stockpile_type import StockpileType
from foxhole_stockpiles.services.stockpile_type_classifier import StockpileTypeClassifier


class TestStockpileTypeClassifierInitialization:
    """Test suite for StockpileTypeClassifier initialization."""

    def test_init_default(self) -> None:
        """Test initializing StockpileTypeClassifier with default settings."""
        with patch("foxhole_stockpiles.services.stockpile_type_classifier.get_settings"):
            classifier = StockpileTypeClassifier()

            assert classifier._type_translations is not None
            # Should have all hardcoded types
            assert StockpileType.SEAPORT in classifier._type_translations
            assert StockpileType.STORAGE_DEPOT in classifier._type_translations

    def test_init_includes_hardcoded_texts(self) -> None:
        """Test that initialization includes all hardcoded texts."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings()

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            # Verify hardcoded texts are included
            assert "Seaport" in classifier._type_translations[StockpileType.SEAPORT]
            assert "Port" in classifier._type_translations[StockpileType.SEAPORT]
            assert "Storage Depot" in classifier._type_translations[StockpileType.STORAGE_DEPOT]

    def test_init_merges_additional_aliases(self) -> None:
        """Test that user-configured additional aliases are merged."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings(
            seaport=["seapon", "Seapont"],
            storage_depot=["Storage Depo"],
        )

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            # Verify additional aliases are merged
            assert "seapon" in classifier._type_translations[StockpileType.SEAPORT]
            assert "Seapont" in classifier._type_translations[StockpileType.SEAPORT]
            assert "Storage Depo" in classifier._type_translations[StockpileType.STORAGE_DEPOT]
            # Original hardcoded texts should still be there
            assert "Seaport" in classifier._type_translations[StockpileType.SEAPORT]


class TestClassifyFromText:
    """Test suite for StockpileTypeClassifier.classify_from_text method."""

    def test_classify_empty_text(self) -> None:
        """Test classifying empty text returns UNDEFINED."""
        with patch("foxhole_stockpiles.services.stockpile_type_classifier.get_settings"):
            classifier = StockpileTypeClassifier()

            result = classifier.classify_from_text("")

            assert result == StockpileType.UNDEFINED

    def test_classify_exact_match_english(self) -> None:
        """Test classifying with exact English match."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings()

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            assert classifier.classify_from_text("Seaport") == StockpileType.SEAPORT
            assert classifier.classify_from_text("Storage Depot") == StockpileType.STORAGE_DEPOT
            assert classifier.classify_from_text("Encampment") == StockpileType.ENCAMPMENT

    def test_classify_translation_match(self) -> None:
        """Test classifying with translation match."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings()

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            # French
            assert classifier.classify_from_text("Dépôt") == StockpileType.STORAGE_DEPOT
            # German
            assert classifier.classify_from_text("Seehafen") == StockpileType.SEAPORT

    def test_classify_with_additional_alias(self) -> None:
        """Test classifying with user-configured additional alias."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings(seaport=["seapon"])

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            result = classifier.classify_from_text("seapon")

            assert result == StockpileType.SEAPORT

    def test_classify_with_whitespace(self) -> None:
        """Test that whitespace is stripped before matching."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings()

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            result = classifier.classify_from_text("  Seaport  ")

            assert result == StockpileType.SEAPORT

    def test_classify_no_match(self) -> None:
        """Test classifying unrecognized text returns UNDEFINED."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings()

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            result = classifier.classify_from_text("Unknown Type")

            assert result == StockpileType.UNDEFINED


class TestFindMatchingType:
    """Test suite for StockpileTypeClassifier._find_matching_type method."""

    def test_find_matching_type_found(self) -> None:
        """Test finding exact matching type."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings()

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            result = classifier._find_matching_type("Seaport")

            assert result == StockpileType.SEAPORT

    def test_find_matching_type_not_found(self) -> None:
        """Test finding non-existent type returns None."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings()

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            result = classifier._find_matching_type("Unknown")

            assert result is None

    def test_find_matching_type_returns_stockpile_type(self) -> None:
        """Test that matching returns a StockpileType enum value."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings()

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            # Match with alternative translation
            result = classifier._find_matching_type("Port")  # Alternative for Seaport

            assert result == StockpileType.SEAPORT
            assert isinstance(result, StockpileType)


class TestFuzzyMatchType:
    """Test suite for StockpileTypeClassifier._fuzzy_match_type method."""

    def test_fuzzy_match_I_to_l(self) -> None:
        """Test fuzzy matching corrects uppercase 'I' to lowercase 'l'."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings()

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            # OCR might read 'l' as 'I' in "Relic Base"
            result = classifier._fuzzy_match_type("ReIic Base")

            assert result == StockpileType.RELIC_BASE

    def test_fuzzy_match_tries_multiple_variations(self) -> None:
        """Test that fuzzy matching tries multiple character variations."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings()

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            with patch.object(classifier, "_find_matching_type") as mock_find:
                mock_find.return_value = None

                classifier._fuzzy_match_type("Test")

                # Should try at least the original + several variations
                assert mock_find.call_count >= 2

    def test_fuzzy_match_not_found(self) -> None:
        """Test fuzzy matching returns None when no match found."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings()

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            result = classifier._fuzzy_match_type("Completely Different")

            assert result is None


class TestHardcodedTexts:
    """Test suite for verifying hardcoded stockpile type texts."""

    def test_all_stockpile_types_have_texts(self) -> None:
        """Test that all StockpileType enum values have hardcoded texts."""
        for stockpile_type in StockpileType:
            assert stockpile_type in STOCKPILE_TYPE_TEXTS, (
                f"Missing hardcoded texts for {stockpile_type}"
            )

    def test_all_types_have_english_text(self) -> None:
        """Test that all types have at least one text (English)."""
        for stockpile_type, texts in STOCKPILE_TYPE_TEXTS.items():
            assert len(texts) >= 1, f"{stockpile_type} has no texts"
            # First text should be the English canonical name
            assert texts[0] == stockpile_type.value


class TestRealWorldScenarios:
    """Test suite for real-world stockpile type classification scenarios."""

    def test_classify_all_stockpile_types(self) -> None:
        """Test classification works for all stockpile types."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings()

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            for stockpile_type in StockpileType:
                # Use the canonical name
                result = classifier.classify_from_text(stockpile_type.value)
                assert result == stockpile_type

    def test_classify_with_ocr_error_and_alias(self) -> None:
        """Test classification with user-configured OCR error alias."""
        mock_settings = MagicMock(spec=AppSettings)
        mock_settings.stockpile_types = StockpileTypesSettings(
            seaport=["seapon", "Seapont", "5eaport"],
            storage_depot=["Storage Depo", "Slorage Depot"],
        )

        with patch(
            "foxhole_stockpiles.services.stockpile_type_classifier.get_settings",
            return_value=mock_settings,
        ):
            classifier = StockpileTypeClassifier()

            # Test OCR error aliases
            assert classifier.classify_from_text("seapon") == StockpileType.SEAPORT
            assert classifier.classify_from_text("Seapont") == StockpileType.SEAPORT
            assert classifier.classify_from_text("5eaport") == StockpileType.SEAPORT
            assert classifier.classify_from_text("Storage Depo") == StockpileType.STORAGE_DEPOT
            assert classifier.classify_from_text("Slorage Depot") == StockpileType.STORAGE_DEPOT

            # Original texts should still work
            assert classifier.classify_from_text("Seaport") == StockpileType.SEAPORT
            assert classifier.classify_from_text("Storage Depot") == StockpileType.STORAGE_DEPOT

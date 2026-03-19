"""Tests for services.stockpile_text_extractor module.

This module contains comprehensive tests for the StockpileTextExtractor class,
which extracts quantities from composite images using OCR with support for
'k' suffix and '+' suffix in numbers.
"""

from unittest.mock import AsyncMock, patch

import numpy as np

from foxhole_stockpiles.enums.supported_language import SupportedLanguage
from foxhole_stockpiles.services.stockpile_text_extractor import StockpileTextExtractor


class TestStockpileTextExtractorInitialization:
    """Test suite for StockpileTextExtractor initialization.

    This class contains tests for proper initialization of the StockpileTextExtractor
    including tesseract path setup and custom model configuration.
    """

    def test_init_default(self) -> None:
        """Test initializing StockpileTextExtractor with defaults."""
        extractor = StockpileTextExtractor()

        assert extractor.custom_model is None

    def test_init_with_custom_model(self) -> None:
        """Test initializing with custom OCR model."""
        extractor = StockpileTextExtractor(custom_model="custom")

        assert extractor.custom_model == "custom"

    def test_init_with_tessdata_path(self) -> None:
        """Test initializing with tessdata path."""
        extractor = StockpileTextExtractor(tessdata_path="/path/to/tessdata")
        assert extractor.tessdata_path == "/path/to/tessdata"

    def test_init_with_tessdata_path_converts_to_absolute(self) -> None:
        """Test that tessdata path is converted to absolute path."""
        extractor = StockpileTextExtractor(tessdata_path="./relative/path")
        assert extractor.tessdata_path is not None
        assert not extractor.tessdata_path.startswith(".")


class TestExtractRawText:
    """Test suite for StockpileTextExtractor.extract_raw_text method.

    This class contains tests for raw text extraction functionality.
    """

    async def test_extract_raw_text_numbers_only(self) -> None:
        """Test extracting raw text with numbers only mode."""
        extractor = StockpileTextExtractor(custom_model="custom")
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch("pytesseract.image_to_string", return_value="123 456") as mock_ocr:
            result = await extractor.extract_raw_text(test_image, numbers_only=True)

            assert result == "123 456"
            mock_ocr.assert_called_once()
            # Check that config includes numbers-only whitelist
            config = mock_ocr.call_args[1]["config"]
            assert "tessedit_char_whitelist=0123456789k+" in config

    async def test_extract_raw_text_all_chars(self) -> None:
        """Test extracting raw text with all characters mode."""
        extractor = StockpileTextExtractor(custom_model="custom")
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch("pytesseract.image_to_string", return_value="Hello World") as mock_ocr:
            result = await extractor.extract_raw_text(test_image, numbers_only=False)

            assert result == "Hello World"
            mock_ocr.assert_called_once()
            # Check that config does not include numbers-only whitelist
            config = mock_ocr.call_args[1]["config"]
            assert "tessedit_char_whitelist" not in config
            # Should use all languages by default for text
            assert "-l eng+por+fra+deu+rus+chi_sim" in config

    async def test_extract_raw_text_strips_whitespace(self) -> None:
        """Test that extracted text is stripped of trailing whitespace."""
        extractor = StockpileTextExtractor()
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch("pytesseract.image_to_string", return_value="123 456  \n"):
            result = await extractor.extract_raw_text(test_image)

            assert result == "123 456"

    async def test_extract_raw_text_handles_none_result(self) -> None:
        """Test handling of None result from OCR."""
        extractor = StockpileTextExtractor()
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch("pytesseract.image_to_string", return_value=None):
            result = await extractor.extract_raw_text(test_image)

            assert result == ""


class TestExtractQuantities:
    """Test suite for StockpileTextExtractor.extract_quantities method.

    This class contains tests for quantity extraction from composite images.
    """

    async def test_extract_quantities_simple(self) -> None:
        """Test extracting simple quantities."""
        extractor = StockpileTextExtractor()
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch.object(extractor, "extract_raw_text", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = "100 200"

            result = await extractor.extract_quantities(test_image)

            assert result == [[100, 200]]

    async def test_extract_quantities_multiple_rows(self) -> None:
        """Test extracting quantities from multiple rows."""
        extractor = StockpileTextExtractor()
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch.object(extractor, "extract_raw_text", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = "100 200\n300 400"

            result = await extractor.extract_quantities(test_image)

            assert result == [[100, 200], [300, 400]]

    async def test_extract_quantities_with_k_suffix(self) -> None:
        """Test extracting quantities with 'k+' suffix."""
        extractor = StockpileTextExtractor()
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch.object(extractor, "extract_raw_text", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = "5k+ 10k+"

            result = await extractor.extract_quantities(test_image)

            assert result == [[5000, 10000]]


class TestParseTextToLists:
    """Test suite for StockpileTextExtractor.parse_text_to_lists method.

    This class contains tests for text parsing functionality.
    """

    def test_parse_simple_numbers(self) -> None:
        """Test parsing simple space-separated numbers."""
        extractor = StockpileTextExtractor()
        text = "100 200 300"

        result = extractor.parse_text_to_lists(text)

        assert result == [[100, 200, 300]]

    def test_parse_multiple_lines(self) -> None:
        """Test parsing multiple lines of numbers."""
        extractor = StockpileTextExtractor()
        text = "100 200\n300 400\n500 600"

        result = extractor.parse_text_to_lists(text)

        assert result == [[100, 200], [300, 400], [500, 600]]

    def test_parse_k_suffix(self) -> None:
        """Test parsing numbers with 'k+' suffix."""
        extractor = StockpileTextExtractor()
        text = "1k+ 5k+ 10k+"

        result = extractor.parse_text_to_lists(text)

        assert result == [[1000, 5000, 10000]]

    def test_parse_mixed_formats(self) -> None:
        """Test parsing mixed number formats."""
        extractor = StockpileTextExtractor()
        text = "100 5k+ 200 10k+"

        result = extractor.parse_text_to_lists(text)

        assert result == [[100, 5000, 200, 10000]]

    def test_parse_empty_lines(self) -> None:
        """Test parsing text with empty lines."""
        extractor = StockpileTextExtractor()
        text = "100 200\n\n300 400"

        result = extractor.parse_text_to_lists(text)

        # Empty lines are skipped to avoid misalignment during OCR merge
        assert result == [[100, 200], [300, 400]]

    def test_parse_invalid_tokens(self) -> None:
        """Test parsing text with invalid tokens."""
        extractor = StockpileTextExtractor()
        text = "100 abc 200"

        result = extractor.parse_text_to_lists(text)

        # Invalid tokens should be skipped
        assert result == [[100, 200]]

    def test_parse_invalid_k_suffix(self) -> None:
        """Test parsing invalid 'k+' suffix numbers."""
        extractor = StockpileTextExtractor()
        text = "abck+ 100"

        result = extractor.parse_text_to_lists(text)

        # Invalid k+ should be replaced with -1
        assert result == [[-1000, 100]]

    def test_parse_whitespace_handling(self) -> None:
        """Test parsing with extra whitespace."""
        extractor = StockpileTextExtractor()
        text = "  100   200  \n  300   "

        result = extractor.parse_text_to_lists(text)

        assert result == [[100, 200], [300]]

    def test_parse_empty_string(self) -> None:
        """Test parsing empty string."""
        extractor = StockpileTextExtractor()
        text = ""

        result = extractor.parse_text_to_lists(text)

        # Empty string returns empty list (empty lines are skipped)
        assert result == []

    def test_parse_only_whitespace(self) -> None:
        """Test parsing string with only whitespace."""
        extractor = StockpileTextExtractor()
        text = "   \n   \n   "

        result = extractor.parse_text_to_lists(text)

        # Whitespace-only returns empty list (empty lines are skipped)
        assert result == []

    def test_parse_single_number(self) -> None:
        """Test parsing single number."""
        extractor = StockpileTextExtractor()
        text = "42"

        result = extractor.parse_text_to_lists(text)

        assert result == [[42]]

    def test_parse_large_numbers(self) -> None:
        """Test parsing large numbers."""
        extractor = StockpileTextExtractor()
        text = "999999 100k+"

        result = extractor.parse_text_to_lists(text)

        assert result == [[999999, 100000]]


class TestGetTesseractConfig:
    """Test suite for StockpileTextExtractor.get_tesseract_config method.

    This class contains tests for Tesseract configuration generation.
    """

    def test_get_config_numbers_only(self) -> None:
        """Test getting config for numbers-only mode."""
        extractor = StockpileTextExtractor(custom_model="custom")

        config = extractor.get_tesseract_config(numbers_only=True)

        assert "--psm 6" in config
        assert "-l custom" in config
        assert "tessedit_char_whitelist=0123456789k+" in config
        assert "--oem 3" in config

    def test_get_config_all_chars(self) -> None:
        """Test getting config for all characters mode."""
        extractor = StockpileTextExtractor(custom_model="custom")

        config = extractor.get_tesseract_config(numbers_only=False)

        assert "--psm 6" in config
        # When numbers_only=False, uses all languages by default (not custom model)
        assert "-l eng+por+fra+deu+rus+chi_sim" in config
        assert "tessedit_char_whitelist" not in config
        assert "--oem 3" in config

    def test_get_config_no_custom_model(self) -> None:
        """Test getting config without custom model."""
        extractor = StockpileTextExtractor()

        config = extractor.get_tesseract_config(numbers_only=True)

        assert "--psm 6" in config
        assert "tessedit_char_whitelist=0123456789k+" in config
        # Without custom model for numbers, uses all languages
        assert "-l eng+por+fra+deu+rus+chi_sim" in config

    def test_get_config_custom_model_none(self) -> None:
        """Test getting config when custom model is None."""
        extractor = StockpileTextExtractor(custom_model=None)

        config = extractor.get_tesseract_config()

        # Uses all languages when custom model is None
        assert "-l eng+por+fra+deu+rus+chi_sim" in config
        assert "tessedit_char_whitelist=0123456789k+" in config

    def test_get_config_with_specific_languages(self) -> None:
        """Test getting config with specific languages for text detection."""
        extractor = StockpileTextExtractor()

        config = extractor.get_tesseract_config(
            numbers_only=False, languages=[SupportedLanguage.FRENCH]
        )

        assert "--psm 6" in config
        assert "-l fra" in config
        assert "tessedit_char_whitelist" not in config
        assert "--oem 3" in config

    def test_get_config_with_multiple_languages(self) -> None:
        """Test getting config with multiple languages for text detection."""
        extractor = StockpileTextExtractor()

        config = extractor.get_tesseract_config(
            numbers_only=False,
            languages=[SupportedLanguage.ENGLISH, SupportedLanguage.RUSSIAN],
        )

        assert "-l eng+rus" in config

    def test_get_config_with_languages_but_numbers_only_uses_custom_model(self) -> None:
        """Test that numbers_only mode uses custom model even when languages is set."""
        extractor = StockpileTextExtractor(custom_model="renner_numbers")

        config = extractor.get_tesseract_config(
            numbers_only=True, languages=[SupportedLanguage.GERMAN]
        )

        # For numbers, custom model takes precedence
        assert "-l renner_numbers" in config
        assert "tessedit_char_whitelist=0123456789k+" in config

    def test_get_config_without_languages_uses_all_languages(self) -> None:
        """Test that not specifying languages defaults to all supported languages."""
        extractor = StockpileTextExtractor()

        config = extractor.get_tesseract_config(numbers_only=False)

        assert "-l eng+por+fra+deu+rus+chi_sim" in config

    def test_get_config_with_languages_for_text_only(self) -> None:
        """Test that languages is used for text but not for numbers."""
        extractor = StockpileTextExtractor(custom_model="renner_numbers")

        # Text mode should use the languages
        text_config = extractor.get_tesseract_config(
            numbers_only=False, languages=[SupportedLanguage.PORTUGUESE]
        )
        assert "-l por" in text_config

        # Numbers mode should use custom model
        numbers_config = extractor.get_tesseract_config(
            numbers_only=True, languages=[SupportedLanguage.PORTUGUESE]
        )
        assert "-l renner_numbers" in numbers_config

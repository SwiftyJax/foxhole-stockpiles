"""Tests for enums.supported_language module."""

from foxhole_stockpiles.enums.supported_language import SupportedLanguage


class TestSupportedLanguage:
    """Test suite for SupportedLanguage enum."""

    def test_enum_values(self) -> None:
        """Test that enum values match i18n (ISO 639-1) language codes."""
        assert SupportedLanguage.ENGLISH.value == "en"
        assert SupportedLanguage.PORTUGUESE.value == "pt"
        assert SupportedLanguage.FRENCH.value == "fr"
        assert SupportedLanguage.GERMAN.value == "de"
        assert SupportedLanguage.RUSSIAN.value == "ru"
        assert SupportedLanguage.CHINESE_SIMPLIFIED.value == "zh"

    def test_get_tesseract_code(self) -> None:
        """Test get_tesseract_code returns correct Tesseract language codes."""
        assert SupportedLanguage.ENGLISH.get_tesseract_code() == "eng"
        assert SupportedLanguage.PORTUGUESE.get_tesseract_code() == "por"
        assert SupportedLanguage.FRENCH.get_tesseract_code() == "fra"
        assert SupportedLanguage.GERMAN.get_tesseract_code() == "deu"
        assert SupportedLanguage.RUSSIAN.get_tesseract_code() == "rus"
        assert SupportedLanguage.CHINESE_SIMPLIFIED.get_tesseract_code() == "chi_sim"

    def test_get_all_languages_string(self) -> None:
        """Test get_all_languages_string returns all Tesseract codes joined with +."""
        result = SupportedLanguage.get_all_languages_string()
        assert result == "eng+por+fra+deu+rus+chi_sim"

    def test_enum_is_str(self) -> None:
        """Test that enum inherits from str."""
        assert isinstance(SupportedLanguage.ENGLISH, str)
        assert isinstance(SupportedLanguage.FRENCH, str)

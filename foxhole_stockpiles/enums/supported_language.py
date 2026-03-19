"""Supported language enumeration for OCR text detection."""

from enum import StrEnum


class SupportedLanguage(StrEnum):
    """Enumeration of supported languages for OCR text detection.

    Uses standard ISO 639-1 language codes (i18n format) as values.
    These are mapped to Tesseract language model codes internally.
    """

    ENGLISH = "en"
    PORTUGUESE = "pt"
    FRENCH = "fr"
    GERMAN = "de"
    RUSSIAN = "ru"
    CHINESE_SIMPLIFIED = "zh"

    def get_tesseract_code(self) -> str:
        """Get the corresponding Tesseract language model code.

        Returns:
            str: Tesseract language code (e.g., "eng", "por", "fra")
        """
        # Mapping from ISO 639-1 (i18n) to Tesseract codes
        tesseract_mapping = {
            "en": "eng",
            "pt": "por",
            "fr": "fra",
            "de": "deu",
            "ru": "rus",
            "zh": "chi_sim",
        }
        return tesseract_mapping[self.value]

    @classmethod
    def get_all_languages(cls) -> list["SupportedLanguage"]:
        """Get all supported languages as a list.

        Returns:
            list[SupportedLanguage]: List of all supported languages
        """
        return list(cls)

    @classmethod
    def get_name_detection_languages(cls) -> list["SupportedLanguage"]:
        """Get languages for stockpile name detection.

        Uses a subset of languages (eng+rus+chi_sim) that properly detect
        underscores in names. Portuguese and other Latin-based languages
        cause underscore characters to be misread as spaces.

        Returns:
            list[SupportedLanguage]: Languages for name detection
        """
        return [cls.ENGLISH, cls.RUSSIAN, cls.CHINESE_SIMPLIFIED]

    @classmethod
    def to_tesseract_string(cls, languages: list["SupportedLanguage"] | None) -> str:
        """Convert a list of languages to a Tesseract language string.

        Args:
            languages (list[SupportedLanguage] | None): List of languages or None for all

        Returns:
            str: Plus-separated list of Tesseract language codes (e.g., "eng+por+fra")
        """
        if languages is None:
            languages = list(cls)
        return "+".join([lang.get_tesseract_code() for lang in languages])

"""Supported language enumeration for OCR text detection."""

from enum import Enum


class SupportedLanguage(str, Enum):
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
    def get_all_languages_string(cls) -> str:
        """Get a string with all supported languages for Tesseract.

        Returns:
            str: Plus-separated list of Tesseract language codes (e.g., "eng+por+fra")
        """
        return "+".join([lang.get_tesseract_code() for lang in cls])

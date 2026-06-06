"""Tests for catalog_builder.localization_lookup module."""

import struct
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from fs_tools.services.catalog_builder.localization_lookup import (
    LOCRES_MAGIC,
    SUPPORTED_LANGUAGES,
    LocalizationLookup,
)


@pytest.fixture
def temp_localization_dir() -> Generator[Path, None, None]:
    """Create a temporary localization directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loc_dir = Path(tmpdir)
        yield loc_dir


def create_mock_locres(filepath: Path, strings: dict[str, str]) -> None:
    """Create a mock .locres file with the given strings.

    This creates a simplified version of the UE4 .locres format.

    Args:
        filepath: Path to write the file.
        strings: Dict mapping GUIDs to localized strings.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "wb") as f:
        # Write magic (16 bytes)
        f.write(LOCRES_MAGIC)

        # Version (1 byte) - use version 2 (Optimized_CRC32)
        f.write(struct.pack("<B", 2))

        # String array offset (8 bytes) - write -1 for now, update later
        str_array_offset_pos = f.tell()
        f.write(struct.pack("<q", -1))

        # Entries count (for version >= 2)
        f.write(struct.pack("<I", len(strings)))

        # Namespace count (1 namespace containing all strings)
        f.write(struct.pack("<I", 1))

        # Namespace key (hash + string)
        # Hash (4 bytes)
        f.write(struct.pack("<I", 0))
        # Empty namespace string (length=0)
        f.write(struct.pack("<i", 0))

        # Key count
        f.write(struct.pack("<I", len(strings)))

        # Build string array first (for indexing)
        string_list = list(strings.values())

        # Write keys with string indices
        for guid, text in strings.items():
            # Key hash (4 bytes)
            f.write(struct.pack("<I", 0))

            # Key string (GUID) - ANSI format
            guid_bytes = guid.encode("latin-1") + b"\x00"
            f.write(struct.pack("<i", len(guid_bytes)))
            f.write(guid_bytes)

            # Source string hash (4 bytes)
            f.write(struct.pack("<I", 0))

            # String index (for version >= 1)
            str_index = string_list.index(text)
            f.write(struct.pack("<i", str_index))

        # Remember where string array starts
        str_array_offset = f.tell()

        # Write string array
        f.write(struct.pack("<i", len(string_list)))
        for text in string_list:
            # Write string as ANSI
            text_bytes = text.encode("latin-1") + b"\x00"
            f.write(struct.pack("<i", len(text_bytes)))
            f.write(text_bytes)

            # Source string hash (4 bytes)
            f.write(struct.pack("<I", 0))

        # Go back and write string array offset
        f.seek(str_array_offset_pos)
        f.write(struct.pack("<q", str_array_offset))


class TestLocalizationLookupInit:
    """Tests for LocalizationLookup initialization."""

    def test_init_sets_localization_dir(self, temp_localization_dir: Path) -> None:
        """Test that localization_dir is set correctly."""
        lookup = LocalizationLookup(temp_localization_dir)
        assert lookup.localization_dir == temp_localization_dir.resolve()

    def test_init_sets_default_language(self, temp_localization_dir: Path) -> None:
        """Test that default_language defaults to 'en'."""
        lookup = LocalizationLookup(temp_localization_dir)
        assert lookup.default_language == "en"

    def test_init_sets_custom_default_language(self, temp_localization_dir: Path) -> None:
        """Test that default_language can be customized."""
        lookup = LocalizationLookup(temp_localization_dir, default_language="de")
        assert lookup.default_language == "de"

    def test_init_creates_empty_cache(self, temp_localization_dir: Path) -> None:
        """Test that cache is initialized as empty."""
        lookup = LocalizationLookup(temp_localization_dir)
        assert lookup._cache == {}


class TestLocalizationLookupGet:
    """Tests for LocalizationLookup.get method."""

    def test_get_returns_none_for_missing_dir(self, temp_localization_dir: Path) -> None:
        """Test that get returns None when directory doesn't exist."""
        lookup = LocalizationLookup(temp_localization_dir / "nonexistent")
        result = lookup.get("SOMEGUID")
        assert result is None

    def test_get_returns_none_for_missing_guid(self, temp_localization_dir: Path) -> None:
        """Test that get returns None for missing GUIDs."""
        # Create a locres file
        locres_path = temp_localization_dir / "Foxhole-Content" / "en" / "test.locres"
        create_mock_locres(locres_path, {"ABC123": "Hello"})

        lookup = LocalizationLookup(temp_localization_dir)
        result = lookup.get("NONEXISTENT")
        assert result is None

    def test_get_returns_string_for_existing_guid(self, temp_localization_dir: Path) -> None:
        """Test that get returns the localized string for existing GUIDs."""
        locres_path = temp_localization_dir / "Foxhole-Content" / "en" / "test.locres"
        create_mock_locres(locres_path, {"ABC123": "Hello World"})

        lookup = LocalizationLookup(temp_localization_dir)
        result = lookup.get("ABC123")
        assert result == "Hello World"

    def test_get_uses_specified_language(self, temp_localization_dir: Path) -> None:
        """Test that get uses the specified language."""
        # Create English and German locres files
        en_path = temp_localization_dir / "Foxhole-Content" / "en" / "test.locres"
        de_path = temp_localization_dir / "Foxhole-Content" / "de" / "test.locres"
        create_mock_locres(en_path, {"GREETING": "Hello"})
        create_mock_locres(de_path, {"GREETING": "Hallo"})

        lookup = LocalizationLookup(temp_localization_dir)

        assert lookup.get("GREETING", "en") == "Hello"
        assert lookup.get("GREETING", "de") == "Hallo"

    def test_get_caches_loaded_language(self, temp_localization_dir: Path) -> None:
        """Test that get caches loaded language data."""
        locres_path = temp_localization_dir / "Foxhole-Content" / "en" / "test.locres"
        create_mock_locres(locres_path, {"ABC123": "Hello"})

        lookup = LocalizationLookup(temp_localization_dir)

        # First call
        lookup.get("ABC123")

        # Check cache was populated
        assert "en" in lookup._cache

        # Verify cached data
        assert lookup._cache["en"]["ABC123"] == "Hello"


class TestLocalizationLookupGetWithFallback:
    """Tests for LocalizationLookup.get_with_fallback method."""

    def test_fallback_returns_string_for_existing_guid(self, temp_localization_dir: Path) -> None:
        """Test that fallback returns string when it exists."""
        locres_path = temp_localization_dir / "Foxhole-Content" / "en" / "test.locres"
        create_mock_locres(locres_path, {"ABC123": "Hello"})

        lookup = LocalizationLookup(temp_localization_dir)
        result = lookup.get_with_fallback("ABC123")
        assert result == "Hello"

    def test_fallback_returns_english_when_language_missing(
        self, temp_localization_dir: Path
    ) -> None:
        """Test that fallback returns English when requested language missing."""
        # Only create English locres
        en_path = temp_localization_dir / "Foxhole-Content" / "en" / "test.locres"
        create_mock_locres(en_path, {"GREETING": "Hello"})

        lookup = LocalizationLookup(temp_localization_dir)
        result = lookup.get_with_fallback("GREETING", "de")
        assert result == "Hello"

    def test_fallback_returns_guid_when_not_found(self, temp_localization_dir: Path) -> None:
        """Test that fallback returns the GUID when string not found."""
        lookup = LocalizationLookup(temp_localization_dir)
        result = lookup.get_with_fallback("NONEXISTENT123")
        assert result == "NONEXISTENT123"


class TestLocalizationLookupGetAllLanguages:
    """Tests for LocalizationLookup.get_all_languages method."""

    def test_get_all_returns_all_available_translations(self, temp_localization_dir: Path) -> None:
        """Test that get_all_languages returns all available translations."""
        # Create locres files for multiple languages
        for lang in ["en", "de", "fr"]:
            path = temp_localization_dir / "Foxhole-Content" / lang / "test.locres"
            create_mock_locres(path, {"GREETING": f"Hello-{lang}"})

        lookup = LocalizationLookup(temp_localization_dir)
        result = lookup.get_all_languages("GREETING")

        assert result.get("en") == "Hello-en"
        assert result.get("de") == "Hello-de"
        assert result.get("fr") == "Hello-fr"

    def test_get_all_returns_empty_for_missing_guid(self, temp_localization_dir: Path) -> None:
        """Test that get_all_languages returns empty dict for missing GUID."""
        lookup = LocalizationLookup(temp_localization_dir)
        result = lookup.get_all_languages("NONEXISTENT")
        assert result == {}


class TestLocalizationLookupIsGuid:
    """Tests for LocalizationLookup.is_guid method."""

    def test_is_guid_returns_true_for_valid_guid(self, temp_localization_dir: Path) -> None:
        """Test that is_guid returns True for valid GUIDs."""
        lookup = LocalizationLookup(temp_localization_dir)

        # 32-character hex string
        assert lookup.is_guid("8BB336F4459740A6ADA7B28B2D91748B") is True
        assert lookup.is_guid("abc123def456abc123def456abc12345") is True

    def test_is_guid_returns_false_for_non_guid(self, temp_localization_dir: Path) -> None:
        """Test that is_guid returns False for non-GUIDs."""
        lookup = LocalizationLookup(temp_localization_dir)

        # Too short
        assert lookup.is_guid("ABC123") is False

        # Too long
        assert lookup.is_guid("8BB336F4459740A6ADA7B28B2D91748B1") is False

        # Non-hex characters
        assert lookup.is_guid("8BB336F4459740A6ADA7B28B2D91748G") is False

        # Regular text
        assert lookup.is_guid("Hello World") is False

        # Non-string
        assert lookup.is_guid(12345) is False
        assert lookup.is_guid(None) is False


class TestLocalizationLookupGetStats:
    """Tests for LocalizationLookup.get_stats method."""

    def test_get_stats_returns_counts(self, temp_localization_dir: Path) -> None:
        """Test that get_stats returns string counts per language."""
        # Create locres files
        en_path = temp_localization_dir / "Foxhole-Content" / "en" / "test.locres"
        de_path = temp_localization_dir / "Foxhole-Content" / "de" / "test.locres"
        create_mock_locres(en_path, {"A": "Hello", "B": "World"})
        create_mock_locres(de_path, {"A": "Hallo"})

        lookup = LocalizationLookup(temp_localization_dir)

        # Load both languages
        lookup.get("A", "en")
        lookup.get("A", "de")

        stats = lookup.get_stats()

        assert stats.get("en") == 2
        assert stats.get("de") == 1

    def test_get_stats_returns_empty_for_no_loaded(self, temp_localization_dir: Path) -> None:
        """Test that get_stats returns empty dict when nothing loaded."""
        lookup = LocalizationLookup(temp_localization_dir)
        stats = lookup.get_stats()
        assert stats == {}


class TestSupportedLanguages:
    """Tests for supported languages constant."""

    def test_supported_languages_has_expected_entries(self) -> None:
        """Test that SUPPORTED_LANGUAGES has expected entries."""
        assert "en" in SUPPORTED_LANGUAGES
        assert "de" in SUPPORTED_LANGUAGES
        assert "fr" in SUPPORTED_LANGUAGES

    def test_supported_languages_maps_to_folder_names(self) -> None:
        """Test that SUPPORTED_LANGUAGES maps to folder names."""
        assert SUPPORTED_LANGUAGES["en"] == "English"
        assert SUPPORTED_LANGUAGES["de"] == "German"
        assert SUPPORTED_LANGUAGES["fr"] == "French"


class TestLocalizationLookupEdgeCases:
    """Edge case tests for LocalizationLookup."""

    def test_handles_legacy_locres_format(self, temp_localization_dir: Path) -> None:
        """Test that legacy locres format is handled gracefully."""
        # Create a file with wrong magic bytes
        locres_path = temp_localization_dir / "Foxhole-Content" / "en" / "legacy.locres"
        locres_path.parent.mkdir(parents=True, exist_ok=True)
        with open(locres_path, "wb") as f:
            f.write(b"WRONG_MAGIC_BYTES")

        lookup = LocalizationLookup(temp_localization_dir)
        result = lookup.get("SOMEGUID", "en")
        assert result is None

    def test_handles_missing_language_dir(self, temp_localization_dir: Path) -> None:
        """Test that missing language directories are skipped."""
        # Create only English, not German
        en_path = temp_localization_dir / "Foxhole-Content" / "en" / "test.locres"
        create_mock_locres(en_path, {"GUID": "Hello"})

        lookup = LocalizationLookup(temp_localization_dir)
        # Load German which doesn't exist
        result = lookup.get("GUID", "de")
        assert result is None

    def test_handles_non_directory_in_localization_dir(self, temp_localization_dir: Path) -> None:
        """Test that non-directory entries in localization dir are skipped."""
        # Create a file in localization dir (not a subdir)
        (temp_localization_dir / "not_a_dir.txt").touch()

        # Also create valid locres
        en_path = temp_localization_dir / "Foxhole-Content" / "en" / "test.locres"
        create_mock_locres(en_path, {"GUID": "Hello"})

        lookup = LocalizationLookup(temp_localization_dir)
        result = lookup.get("GUID", "en")
        assert result == "Hello"

    def test_skips_already_loaded_files(self, temp_localization_dir: Path) -> None:
        """Test that already loaded files are skipped on reload."""
        en_path = temp_localization_dir / "Foxhole-Content" / "en" / "test.locres"
        create_mock_locres(en_path, {"GUID": "Hello"})

        lookup = LocalizationLookup(temp_localization_dir)

        # First load
        result1 = lookup.get("GUID", "en")
        assert result1 == "Hello"

        # Clear cache but keep loaded_files tracker
        lookup._cache.clear()

        # Second load should skip the file
        result2 = lookup.get("GUID", "en")
        # Cache was cleared, but file won't be reloaded, so result should be None
        assert result2 is None

    def test_handles_error_parsing_locres(self, temp_localization_dir: Path) -> None:
        """Test that errors during parsing are handled gracefully."""
        # Create a truncated/corrupt locres file
        locres_path = temp_localization_dir / "Foxhole-Content" / "en" / "corrupt.locres"
        locres_path.parent.mkdir(parents=True, exist_ok=True)
        with open(locres_path, "wb") as f:
            # Write valid magic but truncate after
            f.write(LOCRES_MAGIC)
            # Don't write anything else - will cause struct.unpack to fail

        lookup = LocalizationLookup(temp_localization_dir)
        result = lookup.get("SOMEGUID", "en")
        assert result is None


class TestLocalizationLookupUnicodeStrings:
    """Tests for Unicode string handling in LocalizationLookup."""

    def test_handles_unicode_strings(self, temp_localization_dir: Path) -> None:
        """Test that Unicode strings (UTF-16) are handled correctly."""
        # Create locres with Unicode content
        locres_path = temp_localization_dir / "Foxhole-Content" / "zh" / "test.locres"
        locres_path.parent.mkdir(parents=True, exist_ok=True)

        with open(locres_path, "wb") as f:
            # Write magic
            f.write(LOCRES_MAGIC)
            # Version 2
            f.write(struct.pack("<B", 2))
            # String array offset (will write at end)
            str_array_offset_pos = f.tell()
            f.write(struct.pack("<q", -1))

            # Entries count
            f.write(struct.pack("<I", 1))
            # Namespace count
            f.write(struct.pack("<I", 1))

            # Namespace key (hash + empty string)
            f.write(struct.pack("<I", 0))
            f.write(struct.pack("<i", 0))

            # Key count
            f.write(struct.pack("<I", 1))

            # Key (hash + GUID string)
            f.write(struct.pack("<I", 0))
            guid = "UNICODEGUID12345678901234567890"
            guid_bytes = guid.encode("latin-1") + b"\x00"
            f.write(struct.pack("<i", len(guid_bytes)))
            f.write(guid_bytes)

            # Source string hash
            f.write(struct.pack("<I", 0))
            # String index
            f.write(struct.pack("<i", 0))

            # String array
            str_array_offset = f.tell()
            f.write(struct.pack("<i", 1))

            # Unicode string - negative length indicates UTF-16
            chinese_text = "你好世界"
            text_bytes = chinese_text.encode("utf-16-le")
            f.write(struct.pack("<i", -(len(chinese_text) + 1)))  # Negative for Unicode
            f.write(text_bytes + b"\x00\x00")  # Null terminated UTF-16

            # Source string hash
            f.write(struct.pack("<I", 0))

            # Update string array offset
            f.seek(str_array_offset_pos)
            f.write(struct.pack("<q", str_array_offset))

        lookup = LocalizationLookup(temp_localization_dir)
        result = lookup.get("UNICODEGUID12345678901234567890", "zh")
        assert result == "你好世界"


class TestLocalizationLookupMultipleFiles:
    """Tests for multiple locres files handling."""

    def test_merges_multiple_locres_files(self, temp_localization_dir: Path) -> None:
        """Test that multiple locres files are merged."""
        # Create two locres files
        path1 = temp_localization_dir / "Foxhole-Content" / "en" / "file1.locres"
        path2 = temp_localization_dir / "Foxhole-CodeStrings" / "en" / "file2.locres"
        create_mock_locres(path1, {"GUID1": "Text1"})
        create_mock_locres(path2, {"GUID2": "Text2"})

        lookup = LocalizationLookup(temp_localization_dir)

        assert lookup.get("GUID1", "en") == "Text1"
        assert lookup.get("GUID2", "en") == "Text2"

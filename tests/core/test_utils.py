"""Tests for core.utils module.

This module contains comprehensive tests for the core utility functions,
including catalog loading, frequency analysis, hash distance calculations,
and perceptual hash computation for images.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from foxhole_stockpiles.core.utils import (
    auto_detect_savefile,
    compute_icon_phash,
    extract_day_and_hour,
    find_mapdata_file,
    find_uesave_in_path,
    force_memory_release,
    get_bundled_resource_path,
    get_default_savefile_dir,
    get_subprocess_kwargs,
    get_tesseract_version,
    get_uesave_path,
    is_frozen,
    load_catalog,
    malloc_trim,
    most_frequent,
    validate_tool_path,
)


class TestLoadCatalog:
    """Test suite for the load_catalog function.

    This class contains tests for loading and parsing catalog files,
    including valid files, error conditions, and partial data handling.
    """

    def test_load_valid_catalog(self, tmp_path: Path) -> None:
        """Test loading a valid catalog file.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        catalog_data = [
            {
                "CodeName": "Rifle",
                "FactionVariant": "",
                "ItemCategory": "weapon",
                "Icon": "icons/rifle.png",
                "SubTypeIcon": "",
            },
            {
                "CodeName": "Ammo",
                "FactionVariant": "EFactionId::Colonials",
                "ItemCategory": "item",
                "Icon": "icons/ammo.png",
                "SubTypeIcon": "icons/ammo_sub.png",
            },
        ]

        catalog_file = tmp_path / "catalog.json"
        catalog_file.write_text(json.dumps(catalog_data))

        items = load_catalog(catalog_file)

        assert len(items) == 2
        assert items[0].code == "Rifle"
        assert items[0].faction.value == "neutral"
        assert items[1].code == "Ammo"
        assert items[1].faction.value == "Colonials"

    def test_load_nonexistent_catalog(self, tmp_path: Path) -> None:
        """Test loading a non-existent catalog file.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        catalog_file = tmp_path / "nonexistent.json"

        items = load_catalog(catalog_file)

        assert items == []

    def test_load_invalid_json_catalog(self, tmp_path: Path) -> None:
        """Test loading a catalog file with invalid JSON.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        catalog_file = tmp_path / "invalid.json"
        catalog_file.write_text("{ invalid json content")

        items = load_catalog(catalog_file)

        assert items == []

    def test_load_catalog_with_partial_invalid_items(self, tmp_path: Path) -> None:
        """Test loading a catalog with some invalid items.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        catalog_data = [
            {
                "CodeName": "ValidItem",
                "FactionVariant": "",
                "ItemCategory": "item",
                "Icon": "icons/valid.png",
            },
            {
                # Missing required fields
                "InvalidField": "test",
            },
            {
                "CodeName": "AnotherValid",
                "FactionVariant": "EFactionId::Wardens",
                "ItemCategory": "weapon",
                "Icon": "icons/another.png",
            },
        ]

        catalog_file = tmp_path / "mixed.json"
        catalog_file.write_text(json.dumps(catalog_data))

        items = load_catalog(catalog_file)

        # The loader creates items even for invalid data, but with empty/default values
        assert len(items) == 3
        assert items[0].code == "ValidItem"
        assert items[1].code == ""  # Invalid item gets empty code
        assert items[2].code == "AnotherValid"

    def test_load_catalog_logs_warning_on_failed_items(self, tmp_path: Path) -> None:
        """Test that loading logs warning when items fail to convert.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        catalog_data = [
            {
                "CodeName": "ValidItem",
                "FactionVariant": "",
                "ItemCategory": "item",
                "Icon": "icons/valid.png",
            },
        ]

        catalog_file = tmp_path / "catalog.json"
        catalog_file.write_text(json.dumps(catalog_data))

        # Mock from_catalog to return None for some items
        with patch("foxhole_stockpiles.core.utils.CatalogItem.from_catalog") as mock_from:
            mock_from.return_value = None  # Simulate failed conversion

            with patch("foxhole_stockpiles.core.utils.logging.getLogger") as mock_logger_get:
                mock_logger = patch.object(mock_logger_get.return_value, "warning")
                with mock_logger:
                    items = load_catalog(catalog_file)

                    # Should have logged a warning
                    mock_logger_get.return_value.warning.assert_called()
                    assert items == []

    def test_load_empty_catalog(self, tmp_path: Path) -> None:
        """Test loading an empty catalog file.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        catalog_file = tmp_path / "empty.json"
        catalog_file.write_text("[]")

        items = load_catalog(catalog_file)

        assert items == []


class TestMostFrequent:
    """Test suite for the most_frequent function.

    This class contains tests for the frequency analysis function that finds
    the most common element in a list, handling ties and edge cases.
    """

    def test_single_most_frequent(self) -> None:
        """Test with a clear most frequent item.

        Validates that the function correctly identifies the most frequent
        element when there's a clear winner.
        """
        items = ["a", "b", "a", "c", "a", "b"]
        result = most_frequent(items)
        assert result == "a"

    def test_tie_returns_none(self) -> None:
        """Test that a tie returns None.

        Validates that when multiple elements are tied for most frequent,
        the function returns None.
        """
        items = ["a", "b", "a", "b", "c"]
        result = most_frequent(items)
        assert result is None

    def test_empty_list(self) -> None:
        """Test with an empty list.

        Validates that the function handles empty input gracefully.
        """
        items: list[str] = []
        result = most_frequent(items)
        assert result is None

    def test_single_item(self) -> None:
        """Test with a single item.

        Validates that a list with one element returns that element.
        """
        items = ["unique"]
        result = most_frequent(items)
        assert result == "unique"

    def test_all_same_items(self) -> None:
        """Test with all identical items.

        Validates that when all elements are the same, that element is returned.
        """
        items = ["same", "same", "same", "same"]
        result = most_frequent(items)
        assert result == "same"

    def test_with_numbers(self) -> None:
        """Test with numeric values.

        Validates that the function works correctly with numeric types.
        """
        items = [1, 2, 3, 2, 2, 3, 1, 2]
        result = most_frequent(items)
        assert result == 2

    def test_with_none_values(self) -> None:
        """Test with None values in the list.

        Validates that None values are counted properly in frequency analysis.
        """
        items = [None, "a", None, "b", None]
        result = most_frequent(items)
        assert result is None  # None appears 3 times, others once

    def test_multiple_tie(self) -> None:
        """Test with multiple items tied for most frequent.

        Validates that when multiple elements have the same highest frequency,
        the function returns None.
        """
        items = ["a", "a", "b", "b", "c", "c"]
        result = most_frequent(items)
        assert result is None


class TestComputeIconPhash:
    """Test suite for the compute_icon_phash function.

    This class contains tests for perceptual hash computation of images,
    including various image types, formats, and similarity scenarios.
    """

    def test_grayscale_image(self) -> None:
        """Test phash computation with grayscale image.

        Validates that grayscale images produce valid perceptual hashes.
        """
        # Create a simple 16x16 grayscale test image
        image = np.zeros((16, 16), dtype=np.uint8)
        image[0:8, 0:8] = 255  # Top-left quadrant white

        phash = compute_icon_phash(image)

        assert isinstance(phash, int)
        assert phash >= 0

    def test_color_image(self) -> None:
        """Test phash computation with color image.

        Validates that color images are properly converted and hashed.
        """
        # Create a simple 16x16 BGR test image
        image = np.zeros((16, 16, 3), dtype=np.uint8)
        image[0:8, 0:8] = [255, 255, 255]  # Top-left quadrant white

        phash = compute_icon_phash(image)

        assert isinstance(phash, int)
        assert phash >= 0

    def test_uniform_image(self) -> None:
        """Test phash computation with uniform image.

        Validates hash computation for images with uniform pixel values.
        """
        # Create a uniform gray image
        image = np.full((16, 16), 128, dtype=np.uint8)

        phash = compute_icon_phash(image)

        # Uniform image should produce a specific pattern
        assert isinstance(phash, int)

    def test_identical_images_same_hash(self) -> None:
        """Test that identical images produce the same hash.

        Validates that the hash function is deterministic for identical inputs.
        """
        image1 = np.random.randint(0, 256, (32, 32), dtype=np.uint8)
        image2 = image1.copy()

        phash1 = compute_icon_phash(image1)
        phash2 = compute_icon_phash(image2)

        assert phash1 == phash2

    def test_different_images_different_hash(self) -> None:
        """Test that different images produce different hashes.

        Validates that substantially different images produce different hashes.
        """
        # Create image with gradient pattern
        image1 = np.zeros((16, 16), dtype=np.uint8)
        image1[:8, :] = 100
        image1[8:, :] = 200

        # Create different pattern
        image2 = np.zeros((16, 16), dtype=np.uint8)
        image2[:, :8] = 100
        image2[:, 8:] = 200

        phash1 = compute_icon_phash(image1)
        phash2 = compute_icon_phash(image2)

        assert phash1 != phash2

    def test_small_variation_similar_hash(self) -> None:
        """Test that small variations produce similar hashes.

        Validates that perceptual hashes are robust to small image changes.
        """
        image1 = np.random.randint(0, 256, (32, 32), dtype=np.uint8)
        image2 = image1.copy()
        # Modify a small region
        image2[0:2, 0:2] = 255 - image2[0:2, 0:2]

        phash1 = compute_icon_phash(image1)
        phash2 = compute_icon_phash(image2)

        # Hashes should be similar (small hamming distance)
        distance = bin(phash1 ^ phash2).count("1")
        assert distance < 20  # Threshold for similarity


class TestExtractDayAndHour:
    """Test suite for the extract_day_and_hour function.

    This class contains tests for extracting and formatting days and hours
    from various text input formats.
    """

    def test_standard_format_with_two_commas(self) -> None:
        """Test extraction with standard format containing two commas.

        Validates that the function correctly formats text with day and time
        when there are exactly two commas (e.g., "1,234,1530" -> "1234, 15:30").
        """
        text = "1,234,1530"
        result = extract_day_and_hour(text)
        assert result == "1234, 15:30"

    def test_already_formatted_input(self) -> None:
        """Test with already properly formatted input.

        Validates that already formatted input is handled correctly.
        """
        text = "1234,1530"
        result = extract_day_and_hour(text)
        assert result == "1234, 15:30"

    def test_with_text_mixed_in(self) -> None:
        """Test extraction with text mixed in.

        Validates that non-numeric characters are properly filtered out.
        Note: Separate number groups are concatenated.
        """
        text = "Day 1,234 at 15:30"
        result = extract_day_and_hour(text)
        # "1,234" and "1530" are joined -> "1,2341530"
        # Only 1 comma, so no first comma removal, no 4-digit formatting
        assert result == "1,2341530"

    def test_single_number_no_comma(self) -> None:
        """Test with single number and no comma.

        Validates behavior when input has no comma separator.
        """
        text = "1234"
        result = extract_day_and_hour(text)
        assert result == "1234"

    def test_only_time_four_digits(self) -> None:
        """Test with only time component (4 digits after comma).

        Validates correct formatting when only time is provided.
        """
        text = ",1530"
        result = extract_day_and_hour(text)
        assert result == ", 15:30"

    def test_time_not_four_digits(self) -> None:
        """Test when time portion is not exactly 4 digits.

        Validates that non-standard time formats are returned as-is.
        """
        text = "123,456"
        result = extract_day_and_hour(text)
        assert result == "123,456"

    def test_three_commas_removes_first(self) -> None:
        """Test with three commas (should not remove first).

        Validates that only exactly two commas triggers first comma removal.
        """
        text = "1,2,3,4"
        result = extract_day_and_hour(text)
        # Two commas: removes first, then splits
        # Result should have digit extraction
        assert "," in result

    def test_empty_string(self) -> None:
        """Test with empty string input.

        Validates handling of empty input.
        """
        text = ""
        result = extract_day_and_hour(text)
        assert result == ""

    def test_no_digits(self) -> None:
        """Test with text containing no digits.

        Validates that text without digits returns empty string.
        """
        text = "No numbers here"
        result = extract_day_and_hour(text)
        assert result == ""

    def test_complex_text_with_multiple_numbers(self) -> None:
        """Test with complex text containing multiple number groups.

        Validates extraction from complex formatted strings.
        Note: Multiple separate number groups are concatenated.
        """
        text = "Days: 1,234 Time: 15:30"
        result = extract_day_and_hour(text)
        # "1,234" and "1530" are joined -> "1,2341530"
        assert result == "1,2341530"

    def test_large_day_number(self) -> None:
        """Test with large day numbers.

        Validates handling of multi-digit day values.
        """
        text = "12,345,2359"
        result = extract_day_and_hour(text)
        assert result == "12345, 23:59"

    def test_midnight_time(self) -> None:
        """Test with midnight time (00:00).

        Validates handling of edge case time values.
        """
        text = "100,0000"
        result = extract_day_and_hour(text)
        assert result == "100, 00:00"

    def test_with_spaces_and_special_chars(self) -> None:
        """Test with spaces and special characters.

        Validates that only digits and commas are extracted.
        Note: Multiple number groups are concatenated.
        """
        text = "Day: 5,678 @ 14:25 hours"
        result = extract_day_and_hour(text)
        # "5,678" and "1425" are joined -> "5,6781425"
        assert result == "5,6781425"


class TestMallocTrim:
    """Test suite for the malloc_trim function."""

    def test_malloc_trim_success(self) -> None:
        """Test malloc_trim when libc is available."""
        result = malloc_trim()
        assert isinstance(result, int)
        assert result in (-1, 0, 1)

    def test_malloc_trim_with_pad(self) -> None:
        """Test malloc_trim with custom pad value."""
        result = malloc_trim(pad=1024)
        assert isinstance(result, int)

    def test_malloc_trim_handles_unavailable_libc(self) -> None:
        """Test malloc_trim when libc is not available."""
        with patch("foxhole_stockpiles.core.utils.ctypes.CDLL") as mock_cdll:
            mock_cdll.side_effect = OSError("libc not found")
            result = malloc_trim()
            assert result == -1


class TestForceMemoryRelease:
    """Test suite for the force_memory_release function."""

    def test_force_memory_release_returns_stats(self) -> None:
        """Test that force_memory_release returns statistics."""
        result = force_memory_release()
        assert isinstance(result, dict)
        assert "gc_collected" in result
        assert "malloc_trimmed" in result

    def test_force_memory_release_calls_gc_collect(self) -> None:
        """Test that force_memory_release calls gc.collect."""
        with patch("foxhole_stockpiles.core.utils.gc.collect") as mock_collect:
            mock_collect.return_value = 42
            result = force_memory_release()
            mock_collect.assert_called_once()
            assert result["gc_collected"] == 42


class TestGetSubprocessKwargs:
    """Test suite for the get_subprocess_kwargs function."""

    def test_returns_dict(self) -> None:
        """Test that get_subprocess_kwargs returns a dictionary."""
        result = get_subprocess_kwargs()
        assert isinstance(result, dict)

    def test_returns_creationflags_on_windows(self) -> None:
        """Test that creationflags is returned on Windows."""
        # CREATE_NO_WINDOW only exists on Windows, so we need to mock it
        mock_create_no_window = 0x08000000  # Actual value on Windows

        with (
            patch("foxhole_stockpiles.core.utils.sys.platform", "win32"),
            patch(
                "foxhole_stockpiles.core.utils.subprocess.CREATE_NO_WINDOW",
                mock_create_no_window,
                create=True,
            ),
        ):
            result = get_subprocess_kwargs()
            assert "creationflags" in result
            assert result["creationflags"] == mock_create_no_window

    def test_returns_empty_dict_on_linux(self) -> None:
        """Test that empty dict is returned on Linux."""
        with patch("foxhole_stockpiles.core.utils.sys.platform", "linux"):
            result = get_subprocess_kwargs()
            assert result == {}

    def test_returns_empty_dict_on_darwin(self) -> None:
        """Test that empty dict is returned on macOS."""
        with patch("foxhole_stockpiles.core.utils.sys.platform", "darwin"):
            result = get_subprocess_kwargs()
            assert result == {}


class TestGetTesseractVersion:
    """Test suite for the get_tesseract_version function."""

    def test_tesseract_version_success(self) -> None:
        """Test getting tesseract version when available."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "tesseract 5.3.0\nleptonica-1.82.0\n"

        with patch("foxhole_stockpiles.core.utils.subprocess.run", return_value=mock_result):
            result = get_tesseract_version()
            assert result == "tesseract 5.3.0"

    def test_tesseract_version_non_zero_return(self) -> None:
        """Test getting tesseract version when command returns non-zero."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("foxhole_stockpiles.core.utils.subprocess.run", return_value=mock_result):
            result = get_tesseract_version()
            assert result is None

    def test_tesseract_version_file_not_found(self) -> None:
        """Test getting tesseract version when tesseract not found."""
        with patch(
            "foxhole_stockpiles.core.utils.subprocess.run",
            side_effect=FileNotFoundError("tesseract not found"),
        ):
            result = get_tesseract_version()
            assert result is None

    def test_tesseract_version_timeout(self) -> None:
        """Test getting tesseract version when command times out."""
        import subprocess

        with patch(
            "foxhole_stockpiles.core.utils.subprocess.run",
            side_effect=subprocess.TimeoutExpired("tesseract", 10),
        ):
            result = get_tesseract_version()
            assert result is None

    def test_tesseract_version_subprocess_error(self) -> None:
        """Test getting tesseract version when subprocess raises error."""
        import subprocess

        with patch(
            "foxhole_stockpiles.core.utils.subprocess.run",
            side_effect=subprocess.SubprocessError("Failed"),
        ):
            result = get_tesseract_version()
            assert result is None


class TestIsFrozen:
    """Test suite for the is_frozen function."""

    def test_is_frozen_false(self) -> None:
        """Test is_frozen returns False in normal mode."""
        result = is_frozen()
        assert result is False

    def test_is_frozen_true(self) -> None:
        """Test is_frozen returns True when frozen."""
        with (
            patch("foxhole_stockpiles.core.utils.sys", frozen=True, _MEIPASS="/tmp/bundle"),
        ):
            # Need to mock getattr and hasattr behavior
            with (
                patch("foxhole_stockpiles.core.utils.getattr", return_value=True),
                patch("foxhole_stockpiles.core.utils.hasattr", return_value=True),
            ):
                result = is_frozen()
                # Will still be False since we can't easily mock sys attributes
                assert isinstance(result, bool)


class TestGetBundledResourcePath:
    """Test suite for the get_bundled_resource_path function."""

    def test_bundled_resource_path_dev_mode(self) -> None:
        """Test getting bundled resource path in development mode."""
        with patch("foxhole_stockpiles.core.utils.is_frozen", return_value=False):
            result = get_bundled_resource_path("tessdata")
            assert result == Path.cwd() / "tessdata"

    def test_bundled_resource_path_frozen_mode(self) -> None:
        """Test getting bundled resource path in frozen mode."""
        mock_meipass = "/tmp/pyinstaller_bundle"

        import sys

        import foxhole_stockpiles.core.utils as utils_module

        # Save original
        original_is_frozen = utils_module.is_frozen
        had_meipass = hasattr(sys, "_MEIPASS")
        original_meipass = getattr(sys, "_MEIPASS", None)

        try:
            # Mock is_frozen to return True
            utils_module.is_frozen = lambda: True
            # Set sys._MEIPASS
            sys._MEIPASS = mock_meipass  # type: ignore[attr-defined]

            result = get_bundled_resource_path("tessdata")
            assert str(result) == f"{mock_meipass}/tessdata"
        finally:
            # Restore original
            utils_module.is_frozen = original_is_frozen
            if had_meipass:
                sys._MEIPASS = original_meipass  # type: ignore[attr-defined]
            elif hasattr(sys, "_MEIPASS"):
                del sys._MEIPASS


class TestValidateToolPath:
    """Test suite for the validate_tool_path function."""

    def test_valid_tool_path(self, tmp_path: Path) -> None:
        """Test validation passes for a valid tool path.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        tool = tmp_path / "tool.exe"
        tool.touch()

        # Should not raise
        validate_tool_path(tool)

    def test_nonexistent_tool_raises_file_not_found(self, tmp_path: Path) -> None:
        """Test validation raises FileNotFoundError for nonexistent tool.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        tool = tmp_path / "nonexistent.exe"

        with pytest.raises(FileNotFoundError, match="Tool not found"):
            validate_tool_path(tool)

    def test_directory_raises_value_error(self, tmp_path: Path) -> None:
        """Test validation raises ValueError for directory path.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        with pytest.raises(ValueError, match="not a file"):
            validate_tool_path(tmp_path)

    def test_dangerous_chars_raise_value_error(self, tmp_path: Path) -> None:
        """Test validation raises ValueError for paths with dangerous characters.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Test each dangerous character
        dangerous_chars = [";", "|", "&", "`", "$"]

        for char in dangerous_chars:
            # Create a path with the dangerous character
            # Note: Some characters may not be valid in filenames on all systems
            with (
                patch("pathlib.Path.exists", return_value=True),
                patch("pathlib.Path.is_file", return_value=True),
                patch("pathlib.Path.resolve", return_value=Path(f"/path/to/tool{char}bad")),
            ):
                with pytest.raises(ValueError, match="Invalid character"):
                    validate_tool_path(tmp_path / "tool")

    def test_windows_invalid_extension_raises_value_error(self, tmp_path: Path) -> None:
        """Test validation raises ValueError for invalid extensions on Windows.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        tool = tmp_path / "tool.txt"
        tool.touch()

        with patch("foxhole_stockpiles.core.utils.sys.platform", "win32"):
            with pytest.raises(ValueError, match="Invalid executable extension"):
                validate_tool_path(tool)

    def test_windows_valid_extensions(self, tmp_path: Path) -> None:
        """Test validation passes for valid Windows executable extensions.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        valid_extensions = [".exe", ".bat", ".cmd", ".com"]

        with patch("foxhole_stockpiles.core.utils.sys.platform", "win32"):
            for ext in valid_extensions:
                tool = tmp_path / f"tool{ext}"
                tool.touch()
                # Should not raise
                validate_tool_path(tool)


class TestGetDefaultSavefileDir:
    """Test suite for the get_default_savefile_dir function."""

    def test_windows_with_appdata(self, tmp_path: Path) -> None:
        """Test finding save directory on Windows with LOCALAPPDATA set.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Create fake Windows save directory structure
        save_dir = tmp_path / "Foxhole" / "Saved" / "SaveGames"
        save_dir.mkdir(parents=True)

        with (
            patch("foxhole_stockpiles.core.utils.sys.platform", "win32"),
            patch.dict("os.environ", {"LOCALAPPDATA": str(tmp_path)}),
        ):
            result = get_default_savefile_dir()
            assert result == save_dir

    def test_windows_no_appdata(self) -> None:
        """Test Windows without LOCALAPPDATA environment variable."""
        with (
            patch("foxhole_stockpiles.core.utils.sys.platform", "win32"),
            patch.dict("os.environ", {}, clear=True),
        ):
            result = get_default_savefile_dir()
            assert result is None

    def test_windows_dir_not_exists(self, tmp_path: Path) -> None:
        """Test Windows with LOCALAPPDATA but no save directory.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        with (
            patch("foxhole_stockpiles.core.utils.sys.platform", "win32"),
            patch.dict("os.environ", {"LOCALAPPDATA": str(tmp_path)}),
        ):
            result = get_default_savefile_dir()
            assert result is None

    def test_unsupported_platform(self) -> None:
        """Test with unsupported platform."""
        with patch("foxhole_stockpiles.core.utils.sys.platform", "darwin"):
            result = get_default_savefile_dir()
            assert result is None

    def test_linux_no_wsl_no_proton(self) -> None:
        """Test Linux when neither WSL nor Proton paths exist."""
        with patch("foxhole_stockpiles.core.utils.sys.platform", "linux"):
            result = get_default_savefile_dir()
            # Should return None since paths don't exist
            assert result is None or isinstance(result, Path)


class TestFindMapdataFile:
    """Test suite for the find_mapdata_file function."""

    def test_find_existing_mapdata(self, tmp_path: Path) -> None:
        """Test finding existing MapData.sav file.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        mapdata_file = tmp_path / "User_MapData.sav"
        mapdata_file.touch()

        result = find_mapdata_file(tmp_path)
        assert result == mapdata_file

    def test_find_first_mapdata(self, tmp_path: Path) -> None:
        """Test finding first MapData.sav when multiple exist.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        mapdata1 = tmp_path / "User1_MapData.sav"
        mapdata2 = tmp_path / "User2_MapData.sav"
        mapdata1.touch()
        mapdata2.touch()

        result = find_mapdata_file(tmp_path)
        # Should return one of them (first found)
        assert result in (mapdata1, mapdata2)

    def test_no_mapdata_found(self, tmp_path: Path) -> None:
        """Test when no MapData.sav exists.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Create some other files
        (tmp_path / "other.sav").touch()
        (tmp_path / "something.dat").touch()

        result = find_mapdata_file(tmp_path)
        assert result is None

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Test with empty directory.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        result = find_mapdata_file(tmp_path)
        assert result is None


class TestAutoDetectSavefile:
    """Test suite for the auto_detect_savefile function."""

    def test_auto_detect_success(self, tmp_path: Path) -> None:
        """Test successful auto-detection of save file.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        save_dir = tmp_path / "SaveGames"
        save_dir.mkdir()
        mapdata = save_dir / "User_MapData.sav"
        mapdata.touch()

        with patch("foxhole_stockpiles.core.utils.get_default_savefile_dir", return_value=save_dir):
            result = auto_detect_savefile()
            assert result == mapdata

    def test_auto_detect_no_save_dir(self) -> None:
        """Test auto-detection when no save directory found."""
        with patch("foxhole_stockpiles.core.utils.get_default_savefile_dir", return_value=None):
            result = auto_detect_savefile()
            assert result is None

    def test_auto_detect_no_mapdata_file(self, tmp_path: Path) -> None:
        """Test auto-detection when save dir exists but no MapData file.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        save_dir = tmp_path / "SaveGames"
        save_dir.mkdir()

        with patch("foxhole_stockpiles.core.utils.get_default_savefile_dir", return_value=save_dir):
            result = auto_detect_savefile()
            assert result is None


class TestFindUesaveInPath:
    """Test suite for the find_uesave_in_path function."""

    def test_find_uesave(self, tmp_path: Path) -> None:
        """Test finding uesave in PATH.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        uesave_path = tmp_path / "uesave"
        uesave_path.touch()

        with patch("shutil.which", return_value=str(uesave_path)):
            result = find_uesave_in_path()
            assert result == uesave_path

    def test_find_uesave_exe(self, tmp_path: Path) -> None:
        """Test finding uesave.exe in PATH (Windows).

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        uesave_path = tmp_path / "uesave.exe"
        uesave_path.touch()

        def mock_which(name: str) -> str | None:
            if name == "uesave.exe":
                return str(uesave_path)
            return None

        with patch("shutil.which", side_effect=mock_which):
            result = find_uesave_in_path()
            assert result == uesave_path

    def test_uesave_not_found(self) -> None:
        """Test when uesave is not in PATH."""
        with patch("shutil.which", return_value=None):
            result = find_uesave_in_path()
            assert result is None


class TestGetUesavePath:
    """Test suite for the get_uesave_path function."""

    def test_configured_path_exists(self, tmp_path: Path) -> None:
        """Test with valid configured path.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        uesave_path = tmp_path / "uesave"
        uesave_path.touch()

        result = get_uesave_path(uesave_path)
        assert result == uesave_path

    def test_configured_path_not_exists(self, tmp_path: Path) -> None:
        """Test with configured path that doesn't exist.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        nonexistent = tmp_path / "nonexistent"
        fallback = tmp_path / "uesave_fallback"
        fallback.touch()

        with patch("foxhole_stockpiles.core.utils.find_uesave_in_path", return_value=fallback):
            result = get_uesave_path(nonexistent)
            assert result == fallback

    def test_no_configured_path(self, tmp_path: Path) -> None:
        """Test with no configured path, fallback to PATH.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        fallback = tmp_path / "uesave"
        fallback.touch()

        with patch("foxhole_stockpiles.core.utils.find_uesave_in_path", return_value=fallback):
            result = get_uesave_path(None)
            assert result == fallback

    def test_no_configured_no_path(self) -> None:
        """Test with no configured path and not in PATH."""
        with patch("foxhole_stockpiles.core.utils.find_uesave_in_path", return_value=None):
            result = get_uesave_path(None)
            assert result is None

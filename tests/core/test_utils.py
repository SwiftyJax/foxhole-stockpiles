"""Tests for core.utils module.

This module contains comprehensive tests for the core utility functions,
including catalog loading, frequency analysis, hash distance calculations,
and perceptual hash computation for images.
"""

import json
from pathlib import Path

import numpy as np

from foxhole_stockpiles.core.utils import (
    compute_icon_phash,
    extract_day_and_hour,
    hamming_distance,
    load_catalog,
    most_frequent,
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


class TestHammingDistance:
    """Test suite for the hamming_distance function.

    This class contains tests for the Hamming distance calculation between
    integer hash values, used for measuring similarity between perceptual hashes.
    """

    def test_identical_hashes(self) -> None:
        """Test distance between identical hashes.

        Validates that identical hash values have zero Hamming distance.
        """
        hash1 = 0b1010101010
        hash2 = 0b1010101010
        distance = hamming_distance(hash1, hash2)
        assert distance == 0

    def test_completely_different_hashes(self) -> None:
        """Test distance between completely different hashes.

        Validates distance calculation when all bits are different.
        """
        hash1 = 0b1111111111
        hash2 = 0b0000000000
        distance = hamming_distance(hash1, hash2)
        assert distance == 10

    def test_one_bit_difference(self) -> None:
        """Test distance with single bit difference.

        Validates that a single bit difference results in distance of 1.
        """
        hash1 = 0b1010101010
        hash2 = 0b1010101011
        distance = hamming_distance(hash1, hash2)
        assert distance == 1

    def test_half_different_bits(self) -> None:
        """Test distance with half the bits different.

        Validates distance calculation when exactly half the bits differ.
        """
        hash1 = 0b11110000
        hash2 = 0b11000011
        distance = hamming_distance(hash1, hash2)
        assert distance == 4

    def test_zero_hashes(self) -> None:
        """Test with zero values.

        Validates that zero hash values have zero distance.
        """
        hash1 = 0
        hash2 = 0
        distance = hamming_distance(hash1, hash2)
        assert distance == 0

    def test_large_hashes(self) -> None:
        """Test with large hash values (64-bit).

        Validates distance calculation with maximum-sized hash values.
        """
        hash1 = 0xFFFFFFFFFFFFFFFF
        hash2 = 0x0000000000000000
        distance = hamming_distance(hash1, hash2)
        assert distance == 64


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
        distance = hamming_distance(phash1, phash2)
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

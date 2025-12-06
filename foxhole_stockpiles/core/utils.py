"""Utility functions for the stockpile system."""

import ctypes
import gc
import json
import logging
import re
from pathlib import Path
from typing import Any, TypeVar

import cv2
import numpy as np
from numpy.typing import NDArray

from foxhole_stockpiles.models.catalog_item import CatalogItem


def load_catalog(path: Path) -> list[CatalogItem]:
    """Load catalog.json file with item definitions.

    Args:
        path (Path): Path to the catalog.json file.

    Returns:
        list[CatalogItem]: List of CatalogItem instances loaded from the file.
    """
    logger = logging.getLogger(__name__)
    if not path.exists():
        logger.warning("Catalog file not found at %s", path)
        return []

    catalog_data = []
    try:
        with path.open(encoding="utf-8") as f:
            catalog_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse catalog file %s: %s", path, e)
        return []

    items = [CatalogItem.from_catalog(item=item) for item in catalog_data]
    valid_items = [item for item in items if item is not None]

    if len(valid_items) != len(catalog_data):
        failed_count = len(catalog_data) - len(valid_items)
        logger.warning(
            "Failed to convert %d out of %d catalog items", failed_count, len(catalog_data)
        )

    return valid_items


T = TypeVar("T")


def most_frequent[T](items: list[T]) -> T | None:
    """Return the most frequently occurring item, or None if there's a tie.

    Args:
        items (list[T]): List of items to analyze.

    Returns:
        T | None: The most frequently occurring item, or None if multiple items tie for most
            frequent.
    """
    if not items:
        return None

    unique_items = set(items)
    max_count = max(items.count(item) for item in unique_items)

    # Count how many items have the maximum frequency
    items_with_max_count = sum(1 for item in unique_items if items.count(item) == max_count)

    return None if items_with_max_count > 1 else max(unique_items, key=items.count)


def hamming_distance(hash1: int, hash2: int) -> int:
    """Calculate Hamming distance between two perceptual hashes.

    Args:
        hash1 (int): First hash as integer
        hash2 (int): Second hash as integer

    Returns:
        int: Number of differing bits
    """
    xor = hash1 ^ hash2
    return bin(xor).count("1")


def compute_icon_phash(icon_image: NDArray[np.uint8]) -> int:
    """Compute perceptual hash for an icon image.

    Args:
        icon_image (NDArray[np.uint8]): Input icon image (BGR or grayscale)

    Returns:
        int: Perceptual hash as integer
    """
    # Convert to grayscale if needed
    if len(icon_image.shape) == 3:
        icon_gray = cv2.cvtColor(icon_image, cv2.COLOR_BGR2GRAY)
    else:
        icon_gray = icon_image

    # Resize to 8x8 for standard pHash
    img_resized = cv2.resize(icon_gray, (8, 8), interpolation=cv2.INTER_AREA)
    avg = img_resized.mean()

    # Create binary hash based on pixel values above/below average
    bits = (img_resized > avg).astype(np.uint8)
    return int("".join(str(b) for b in bits.flatten()), 2)


def extract_day_and_hour(text: str) -> str:
    """Extracts Days and Hours from a formatted string.

    Args:
        text (str): Input text containing numbers and commas.

    Returns:
        str: Formatted string with days and hours, e.g. "1234, 15:30".
    """
    # Find all digit/comma groups and join
    result = "".join(re.findall(r"[\d,]+", text))
    # Remove first comma if exactly two commas
    if result.count(",") == 2:
        result = result.replace(",", "", 1)
    # Try to split into left/right by first comma
    parts = result.split(",", 1)
    if len(parts) == 2:
        left, right = parts
        digits = re.sub(r"\D", "", right)
        if len(digits) == 4:
            return f"{left}, {digits[:2]}:{digits[2:]}"
    return result


def malloc_trim(pad: int = 0) -> int:
    """Force glibc to return free memory to the operating system.

    This calls the glibc malloc_trim() function which releases free memory from the heap
    back to the system. This is useful after processing large data structures to prevent
    memory fragmentation from keeping process RSS high.

    On Linux with glibc, this can significantly reduce memory usage after freeing large
    allocations (numpy arrays, images, etc.) that would otherwise stay in malloc's
    internal pools.

    Args:
        pad (int): Amount of free space to leave untrimmed in bytes (default: 0)

    Returns:
        int: 1 if memory was released, 0 if not, -1 if malloc_trim is unavailable

    Note:
        - Only works on Linux with glibc
        - Has no effect on other platforms (returns -1)
        - Should be called after gc.collect() for best results
    """
    logger = logging.getLogger(__name__)
    try:
        libc = ctypes.CDLL("libc.so.6")
        result = libc.malloc_trim(pad)
        logger.debug("malloc_trim() returned: %d", result)
        return int(result)
    except (OSError, AttributeError) as e:
        logger.debug("malloc_trim() not available: %s", e)
        return -1


def force_memory_release() -> dict[str, Any]:
    """Force Python garbage collection and system memory release.

    This performs a full garbage collection cycle and then attempts to release
    freed memory back to the operating system via malloc_trim().

    Returns:
        dict[str, Any]: Statistics about the memory release operation
            - gc_collected: Number of objects collected by garbage collector
            - malloc_trimmed: 1 if memory was released, 0 if not, -1 if unavailable
    """
    logger = logging.getLogger(__name__)

    # Force full garbage collection
    collected = gc.collect()
    logger.debug("Garbage collector freed %d objects", collected)

    # Attempt to release memory to OS
    trimmed = malloc_trim()

    return {
        "gc_collected": collected,
        "malloc_trimmed": trimmed,
    }

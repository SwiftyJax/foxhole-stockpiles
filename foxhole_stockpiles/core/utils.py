"""Utility functions for the stockpile system."""

import json
import logging
from pathlib import Path

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

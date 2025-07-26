"""Category for items."""

from enum import StrEnum


class ItemCategory(StrEnum):
    """Item Category."""

    Item = "item"
    Vehicle = "vehicle"
    Shippable = "shippable"
    Invalid = "invalid"

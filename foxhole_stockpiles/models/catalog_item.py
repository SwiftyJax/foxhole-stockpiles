"""Catalog item model for the stockpile system."""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction


class CatalogItem(BaseModel):
    """Base model for items in the stockpile system."""

    code: str = Field(description="Unique identifier for the item")
    faction: ItemFaction = Field(
        description="Faction that uses this item", default=ItemFaction.NEUTRAL
    )
    category: ItemCategory = Field(
        description="Category of the item (e.g., Weapon, Ammo, Equipment)"
    )
    icon_path: str = Field(description="Path to the icon image file", default="")
    subicon_path: str = Field(description="Path to the subicon image file", default="")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "code": "MaintenanceSupplies",
                "faction": "neutral",
                "category": "item",
                "icon_path": "icons/maintenance_supplies.png",
                "subicon_path": "icons/maintenance_supplies_sub.png",
            }
        },
    )

    @classmethod
    def from_catalog(cls, item: dict[str, Any]) -> "CatalogItem | None":
        """Create a CatalogItem instance from a dictionary.

        Args:
            item (dict[str, Any]): Dictionary containing item data.

        Returns:
            CatalogItem | None: Instance of CatalogItem or None if creation fails.
        """
        try:
            return cls(
                code=item.get("CodeName", ""),
                faction=ItemFaction.from_string(item.get("FactionVariant")),
                category=cls._determine_item_type(item),
                icon_path=item.get("Icon", ""),
                subicon_path=item.get("SubTypeIcon", ""),
            )
        except (ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def _determine_item_type(item: dict[str, Any]) -> ItemCategory:
        """Determine item type based on available fields.

        Args:
            item (dict[str, Any]): Item definition from catalog

        Returns:
            ItemCategory: The category of the item based on its properties.
        """
        if item.get("VehicleProfileType"):
            return ItemCategory.Vehicle

        if item.get("ShippableInfo"):
            return ItemCategory.Shippable

        if item.get("ItemCategory"):
            return ItemCategory.Item

        # Default fallback
        return ItemCategory.Invalid

    def model_post_init(self, context: Any) -> None:
        """Post-initialization hook for additional processing."""
        super().model_post_init(context)

        # Remove the version suffix from icon paths
        self.subicon_path = re.sub(r"\.\d+$", "", self.subicon_path)
        self.icon_path = re.sub(r"\.\d+$", "", self.icon_path)

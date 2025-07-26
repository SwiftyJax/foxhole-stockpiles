"""Catalog item model for the stockpile system."""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction


class CatalogItem(BaseModel):
    """Base model for items in the stockpile system."""

    code: str = Field(description="Unique identifier for the item")
    crated: bool = Field(description="Indicates if the item is crated", default=False)
    faction: ItemFaction = Field(
        description="Faction that uses this item", default=ItemFaction.NEUTRAL
    )
    category: ItemCategory = Field(
        description="Category of the item (e.g., Weapon, Ammo, Equipment)"
    )

    mod: str = Field(description="Mod name extracted from the filename", default="vanilla")
    size: int = Field(description="Icon size in pixels", default=64)

    icon_path: str = Field(description="Path to the icon image file", default="")
    subicon_path: str = Field(description="Path to the subicon image file", default="")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "code": "MaintenanceSupplies",
                "crated": True,
                "faction": "neutral",
                "category": "item",
                "mod": "vanilla",
                "size": 64,
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
                crated=False,
                faction=ItemFaction.from_string(item.get("FactionVariant")),
                category=cls._determine_item_type(item),
                mod="",
                size=0,
                icon_path=item.get("Icon", ""),
                subicon_path=item.get("SubTypeIcon", ""),
            )
        except (ValueError, KeyError, TypeError):
            raise
            return None

    @staticmethod
    def _determine_item_type(item: dict[str, Any]) -> ItemCategory:
        """Determine item type based on available fields.

        Args:
            item (dict[str, Any]): Item definition from catalog

        Returns:
            ItemCategory: The category of the item based on its properties.
        """
        if item.get("ShippableInfo"):
            return ItemCategory.Shippable

        if item.get("VehicleProfileType"):
            return ItemCategory.Vehicle

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

"""Stockpile type enum."""

from __future__ import annotations

from enum import StrEnum


class StockpileType(StrEnum):
    """Stockpile type enum."""

    # Bases (order from the game).
    # Bunker and town bases can have different level but the name is the same
    ENCAMPMENT = "Encampment"
    KEEP = "Keep"
    SAFE_HOUSE = "Safe House"
    RELIC_BASE = "Relic Base"
    BUNKER_BASE = "Bunker Base"
    BORDER_BASE = "Border Base"
    TOWN_BASE = "Town Base"
    UNDERGROUND_FORTRESS = "Underground Fortress"
    BMS_LONGHOOK = "BMS - Longhook"
    BMS_BLUEFIN = "BMS - Bluefin"

    # Structures (order from the game)
    STORAGE_DEPOT = "Storage Depot"
    SEAPORT = "Seaport"
    AIRCRAFT_DEPOT = "Aircraft Depot"

    UNDEFINED = "Undefined"

    def has_custom_name(self) -> bool:
        """Check if this stockpile type supports custom player-given names.

        Only player-built structures (Storage Depot, Seaport, Aircraft Depot)
        can have custom names. Base types use their type as the display name.

        Returns:
            bool: True if this stockpile type can have a custom name.
        """
        return self in (
            StockpileType.STORAGE_DEPOT,
            StockpileType.SEAPORT,
            StockpileType.AIRCRAFT_DEPOT,
        )

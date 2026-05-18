"""Stockpile types settings."""

from pydantic import BaseModel, ConfigDict, Field


class StockpileTypesSettings(BaseModel):
    """Settings for additional stockpile type aliases.

    The valid stockpile type texts (including translations) are hardcoded in the
    classifier. This settings class stores additional aliases per stockpile type
    that users can add to handle OCR errors or other variations.

    Field names match StockpileType enum names in lowercase (e.g., bunker_base_1).

    Example: If OCR sometimes detects "Seaport" as "seapon", add "seapon" to the
    seaport list.

    Note: UNDEFINED type has no additional aliases as it's a fallback type.
    Note: Some languages have different translations per tier (e.g., Portuguese
          Bunker Base T1 vs T2/T3), so each tier has its own field.
    """

    # Bases
    encampment: list[str] = Field(
        description="Additional aliases for Encampment",
        default_factory=list,
    )
    keep: list[str] = Field(
        description="Additional aliases for Keep",
        default_factory=list,
    )
    safe_house: list[str] = Field(
        description="Additional aliases for Safe House",
        default_factory=list,
    )
    relic_base: list[str] = Field(
        description="Additional aliases for Relic Base",
        default_factory=list,
    )
    bunker_base_1: list[str] = Field(
        description="Additional aliases for Bunker Base T1",
        default_factory=list,
    )
    bunker_base_2: list[str] = Field(
        description="Additional aliases for Bunker Base T2",
        default_factory=list,
    )
    bunker_base_3: list[str] = Field(
        description="Additional aliases for Bunker Base T3",
        default_factory=list,
    )
    border_base: list[str] = Field(
        description="Additional aliases for Border Base",
        default_factory=list,
    )
    town_base_1: list[str] = Field(
        description="Additional aliases for Town Base T1",
        default_factory=list,
    )
    town_base_2: list[str] = Field(
        description="Additional aliases for Town Base T2",
        default_factory=list,
    )
    town_base_3: list[str] = Field(
        description="Additional aliases for Town Base T3",
        default_factory=list,
    )
    underground_fortress: list[str] = Field(
        description="Additional aliases for Underground Fortress",
        default_factory=list,
    )
    bms_longhook: list[str] = Field(
        description="Additional aliases for BMS - Longhook",
        default_factory=list,
    )
    bms_bluefin: list[str] = Field(
        description="Additional aliases for BMS - Bluefin",
        default_factory=list,
    )

    # Structures
    storage_depot: list[str] = Field(
        description="Additional aliases for Storage Depot",
        default_factory=list,
    )
    seaport: list[str] = Field(
        description="Additional aliases for Seaport",
        default_factory=list,
    )
    aircraft_depot: list[str] = Field(
        description="Additional aliases for Aircraft Depot",
        default_factory=list,
    )

    # Facilities
    hospital: list[str] = Field(
        description="Additional aliases for Hospital",
        default_factory=list,
    )
    refinery: list[str] = Field(
        description="Additional aliases for Refinery",
        default_factory=list,
    )
    maintenance_tunnel: list[str] = Field(
        description="Additional aliases for Maintenance Tunnel",
        default_factory=list,
    )
    small_arms_factory: list[str] = Field(
        description="Additional aliases for Small Arms Factory",
        default_factory=list,
    )
    modification_center: list[str] = Field(
        description="Additional aliases for Modification Center",
        default_factory=list,
    )
    transfer_liquid: list[str] = Field(
        description="Additional aliases for Transfer Station (Liquid)",
        default_factory=list,
    )
    transfer_material: list[str] = Field(
        description="Additional aliases for Transfer Station (Material)",
        default_factory=list,
    )
    transfer_resource: list[str] = Field(
        description="Additional aliases for Transfer Station (Resource)",
        default_factory=list,
    )
    vehicle_factory_1: list[str] = Field(
        description="Additional aliases for Vehicle Factory T1",
        default_factory=list,
    )
    vehicle_factory_2: list[str] = Field(
        description="Additional aliases for Vehicle Factory T2",
        default_factory=list,
    )
    vehicle_factory_3: list[str] = Field(
        description="Additional aliases for Vehicle Factory T3",
        default_factory=list,
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "Seaport": ["seapon", "Seapont"],
                "StorageFacility": ["Storage Depo", "Slorage Depot"],
            }
        },
    )

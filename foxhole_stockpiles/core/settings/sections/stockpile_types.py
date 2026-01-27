"""Stockpile types settings."""

from pydantic import BaseModel, ConfigDict, Field


class StockpileTypesSettings(BaseModel):
    """Settings for additional stockpile type aliases.

    The valid stockpile type texts (including translations) are hardcoded in the
    classifier. This settings class stores additional aliases per stockpile type
    that users can add to handle OCR errors or other variations.

    Example: If OCR sometimes detects "Seaport" as "seapon", add "seapon" to the
    seaport list.

    Note: UNDEFINED type has no additional aliases as it's a fallback type.
    """

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
    bunker_base: list[str] = Field(
        description="Additional aliases for Bunker Base",
        default_factory=list,
    )
    border_base: list[str] = Field(
        description="Additional aliases for Border Base",
        default_factory=list,
    )
    town_base: list[str] = Field(
        description="Additional aliases for Town Base",
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

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "seaport": ["seapon", "Seapont"],
                "storage_depot": ["Storage Depo", "Slorage Depot"],
            }
        },
    )

"""Settings needed for the OCR coordinator."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from foxhole_stockpiles.enums.item_faction import ItemFaction


class OCRCoordinatorConfig(BaseModel):
    """Configuration for stockpile analysis."""

    database_path: Path = Field(description="Path to the template database file")
    confidence_threshold: float = Field(
        description="Minimum confidence threshold for icon matching", default=0.8, ge=0.0, le=1.0
    )
    faction_filter: ItemFaction | None = Field(
        description="Optional faction filter for icon matching", default=None
    )
    custom_model: str = Field(description="Custom OCR model name", default="custom")
    tessdata_path: str = Field(description="Path to tessdata directory", default="./tessdata")
    debug_mode: bool = Field(description="Enable debug mode to save debug images", default=False)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "database_path": "/path/to/templates.db",
                "confidence_threshold": 0.8,
                "faction_filter": "colonial",
                "custom_model": "custom",
                "tessdata_path": "./tessdata",
                "debug_mode": False,
            }
        },
    )

    @field_validator("database_path")
    @classmethod
    def validate_database_path(cls, v: Path) -> Path:
        """Validate that the database path exists and is a file."""
        if not v.exists():
            raise ValueError(f"Database path does not exist: {v}")
        if not v.is_file():
            raise ValueError(f"Database path is not a file: {v}")
        return v

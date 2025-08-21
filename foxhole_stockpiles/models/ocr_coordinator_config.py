"""Settings needed for the OCR coordinator."""

from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from foxhole_stockpiles.enums.item_faction import ItemFaction


class OCRCoordinatorConfig(BaseModel):
    """Configuration for stockpile analysis."""

    database_path: Path = Field(description="Path to the template database file")
    confidence_threshold: float = Field(
        description="Minimum confidence threshold for icon matching", default=0.85, ge=0.0, le=1.0
    )
    early_exit_threshold: float = Field(
        description="Early exit threshold for icon matching",
        default=0.95,
        ge=0.0,
        le=1.0,
    )
    faction_filter: ItemFaction | None = Field(
        description="Optional faction filter for icon matching", default=None
    )
    custom_model: str = Field(description="Custom OCR model name", default="custom")
    tessdata_path: str = Field(description="Path to tessdata directory", default="./tessdata")
    debug_mode: bool = Field(description="Enable debug mode to save debug images", default=False)

    max_ncc_candidates: int = Field(
        description="Maximum number of NCC candidates to consider for matching",
        default=25,
        ge=1,
    )
    phash_threshold: int = Field(
        description="Maximum Hamming distance for pHash filtering",
        default=12,
        ge=0,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "database_path": "/path/to/templates.db",
                "confidence_threshold": 0.85,
                "early_exit_threshold": 0.95,
                "faction_filter": "colonial",
                "custom_model": "custom",
                "tessdata_path": "./tessdata",
                "debug_mode": False,
                "max_ncc_candidates": 25,
                "phash_threshold": 12,
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

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        """Validate the options are valid.

        Returns:
            Self: Returns the instance itself for method chaining.

        Raises:
            ValueError: if early_exit_threshold is not greater than confidence_threshold
        """
        if self.early_exit_threshold <= self.confidence_threshold:
            raise ValueError("Early exit threshold must be greater than confidence threshold")

        return self

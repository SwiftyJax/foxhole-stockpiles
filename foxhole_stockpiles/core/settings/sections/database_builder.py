"""Database builder settings."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class DatabaseBuilderSettings(BaseModel):
    """Settings for the database builder (icon import).

    Note: External tools (repak, umodel) are configured in ExternalToolsSettings.
    """

    catalog_file: Path | None = Field(
        description="Path to catalog.json file for building the database",
        default=None,
    )
    target_resolutions: list[str] | None = Field(
        description=(
            "List of resolutions to generate when importing icons. "
            "Set to None or empty list to generate all supported resolutions. "
            "Example: ['1080', '1440', '2160']"
        ),
        default=None,
    )
    workers: int | None = Field(
        description=(
            "Number of worker processes for database building. "
            "Set to None to auto-detect (uses CPU count). "
            "Set to 1 to disable multiprocessing."
        ),
        default=None,
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "catalog_file": "C:/foxhole/catalog.json",
                "target_resolutions": None,  # None = all resolutions
                "workers": None,  # None = auto-detect (CPU count)
            }
        },
    )

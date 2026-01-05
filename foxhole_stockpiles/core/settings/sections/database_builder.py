"""Database builder settings."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class DatabaseBuilderSettings(BaseModel):
    """Settings for the database builder (icon import)."""

    extractor_tool: Path | None = Field(
        description="Path to repak.exe for extracting PAK files",
        default=None,
    )
    converter_tool: Path | None = Field(
        description="Path to umodel.exe for converting UAsset files to PNG",
        default=None,
    )
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

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "extractor_tool": "C:/repak/repak.exe",
                "converter_tool": "C:/UModel/umodel.exe",
                "catalog_file": "C:/foxhole/catalog.json",
                "target_resolutions": None,  # None = all resolutions
            }
        },
    )

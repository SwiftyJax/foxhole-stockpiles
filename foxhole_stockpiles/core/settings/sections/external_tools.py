"""External tools settings."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ExternalToolsSettings(BaseModel):
    """Settings for external tools shared across features.

    These tools are used by multiple features:
    - repak: Used by Database Builder and Catalog Builder for PAK extraction
    - umodel: Used by Database Builder for converting UAsset to PNG
    - uassetgui: Used by Catalog Builder for converting UAsset to JSON
    - uesave: Used by SAV Processing for converting save files to JSON
    """

    repak: Path | None = Field(
        description="Path to repak executable for extracting PAK files",
        default=None,
    )
    umodel: Path | None = Field(
        description="Path to umodel executable for converting UAsset files to PNG",
        default=None,
    )
    uassetgui: Path | None = Field(
        description="Path to UAssetGUI executable for converting UAsset files to JSON",
        default=None,
    )
    uesave: Path | None = Field(
        description="Path to uesave executable for converting save files to JSON",
        default=None,
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "repak": "C:/repak/repak.exe",
                "umodel": "C:/UModel/umodel.exe",
                "uassetgui": "C:/UAssetGUI/UAssetGUI.exe",
                "uesave": "C:/uesave/uesave.exe",
            }
        },
    )

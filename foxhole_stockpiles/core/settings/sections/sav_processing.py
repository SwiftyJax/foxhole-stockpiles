"""SAV processing settings."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class SavProcessingSettings(BaseModel):
    """Settings for SAV file processing.

    These settings configure how the application handles Foxhole save files
    for stockpile data extraction.
    """

    sav_file_path: Path | None = Field(
        description="Path to the Foxhole save file (.sav) to process",
        default=None,
    )
    poll_interval: float = Field(
        description="Polling interval in seconds for monitoring mode",
        default=1.0,
        ge=0.1,
        le=60.0,
    )
    emit_all_on_start: bool = Field(
        description="Emit all stockpiles on first read (for single scan mode)",
        default=True,
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "sav_file_path": (
                    "C:/Users/User/AppData/Local/Foxhole/Saved/SaveGames/User_MapData.sav"
                ),
                "poll_interval": 1.0,
                "emit_all_on_start": True,
            }
        },
    )

"""GUI settings."""

from pydantic import BaseModel, ConfigDict, Field

from foxhole_stockpiles.enums.config_level import ConfigLevel


class GUISettings(BaseModel):
    """Settings for the GUI."""

    config_level: ConfigLevel = Field(
        description=(
            "Configuration level controlling which options are visible in the GUI.\n"
            "basic: Essential settings only (recommended for most users)\n"
            "advanced: Additional tuning options for power users\n"
            "developer: Full access including OCR/Template settings (may break scanning)"
        ),
        default=ConfigLevel.BASIC,
    )
    minimize_to_tray: bool = Field(
        description="Minimize to system tray instead of quitting when closing the window",
        default=False,
    )
    language: str = Field(
        description="Language code for the GUI (e.g., 'en', 'es', 'de')",
        default="en",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "config_level": ConfigLevel.BASIC,
                "minimize_to_tray": False,
                "language": "en",
            }
        },
    )

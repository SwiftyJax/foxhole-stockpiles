"""Settings needed for the OCR coordinator."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_language import SupportedLanguage


class OCRCoordinatorConfig(BaseModel):
    """Configuration for stockpile analysis."""

    database_path: Path | None = Field(
        description=(
            "Path to the template database file. Optional for commands that don't use templates."
        ),
        default=None,
    )
    early_exit_threshold: float = Field(
        description=(
            "Early exit threshold for icon matching. "
            "If a match with confidence >= this threshold is found, stop testing other candidates. "
            "Set to 0.0 to disable early exit and test all candidates."
        ),
        default=0.0,
        ge=0.0,
        le=1.0,
    )
    confidence_gap: float = Field(
        description=(
            "Confidence gap for returning alternative candidates. "
            "If set > 0.0, returns candidates within (best_confidence - confidence_gap) range. "
            "These candidates must have the same category, crated status, and mod as the "
            "best match. Set to 0.0 to disable candidate reporting."
        ),
        default=0.0,
        ge=0.0,
        le=1.0,
    )
    faction_filter: ItemFaction | None = Field(
        description="Optional faction filter for icon matching", default=None
    )
    mod_name: str | None = Field(
        description="Optional mod name filter for icon matching (max 50 chars)",
        default=None,
        max_length=50,
    )
    language: SupportedLanguage | None = Field(
        description="Optional language for text detection (stockpile name, type, hex_name). "
        "If None, uses all supported languages. Number detection always uses the custom model.",
        default=None,
    )
    custom_model: str = Field(description="Custom OCR model name", default="renner_numbers")
    tessdata_path: str = Field(description="Path to tessdata directory", default="./tessdata")
    debug_mode: bool = Field(description="Enable debug mode to save debug images", default=False)
    extract_icons: bool = Field(
        description="Extract detected icons to 'icons' folder for debugging (<index>_<code>.png)",
        default=False,
    )
    screenshots_folder: str = Field(
        description="Folder to save screenshots before processing. Empty string disables saving.",
        default="",
    )

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
                "database_path": "database.pkl",
                "early_exit_threshold": 0.0,
                "confidence_gap": 0.0,
                "faction_filter": "colonial",
                "mod_name": "my_mod",
                "language": "eng",
                "custom_model": "custom",
                "tessdata_path": "./tessdata",
                "debug_mode": False,
                "extract_icons": False,
                "screenshots_folder": "screenshots",
                "max_ncc_candidates": 25,
                "phash_threshold": 12,
            }
        },
    )

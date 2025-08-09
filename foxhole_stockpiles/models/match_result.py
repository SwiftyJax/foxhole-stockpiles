"""Match result models for template matching operations."""

from pydantic import BaseModel, ConfigDict, Field

from foxhole_stockpiles.models.icon_template import IconTemplate


class MatchResult(BaseModel):
    """Complete result of candidate filtering and optional icon matching."""

    candidates: list[int] = Field(description="List of candidate template indices")
    icon: IconTemplate | None = Field(
        description=(
            "Matched IconTemplate if icon_image was provided and match found, None otherwise"
        ),
        default=None,
    )
    confidence: float | None = Field(
        description="Confidence score of the icon match, None if no icon matching performed",
        default=None,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "candidates": [0, 15, 42],
                "icon": {
                    "code": "Rifle",
                    "crated": False,
                    "faction": "neutral",
                    "category": "item",
                    "mod": "vanilla",
                    "resolution": "1080",
                },
                "confidence": 0.8756,
            }
        },
    )

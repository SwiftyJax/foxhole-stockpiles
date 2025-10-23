"""Item candidate model for alternative matches."""

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ItemCandidate(BaseModel):
    """Alternative candidate for an item match."""

    code: str = Field(description="Code of the alternative candidate item")
    confidence: float = Field(
        description="Confidence score of the alternative candidate",
        ge=0.0,
        le=1.0,
    )

    @field_serializer("confidence")
    def serialize_confidence(self, value: float) -> float:
        """Serialize confidence to 3 decimal places.

        Args:
            value (float): Confidence value

        Returns:
            float: Rounded confidence value
        """
        return round(value, 3)

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "code": "RifleAlternative",
                "confidence": 0.92,
            }
        },
    )

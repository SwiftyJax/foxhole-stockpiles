"""Stockpile item model."""

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class StockpileItem(BaseModel):
    """Stockpile item model."""

    code: str = Field(description="Code of item detected from the icon")
    quantity: int = Field(description="Quantity of the item", ge=-1, default=-1)
    crated: bool = Field(description="Is the item crated?", default=False)
    confidence: float | None = Field(
        description="Confidence of the item detection",
        ge=0.0,
        le=1.0,
        default=None,
    )

    @field_serializer("confidence")
    def serialize_confidence(self, value: float | None) -> float | None:
        """Serialize confidence to 3 decimal places.

        Args:
            value (float | None): Confidence value

        Returns:
            float | None: Rounded confidence value
        """
        if value is None:
            return None
        return round(value, 3)

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "code": "GrenadeLauncherC",
                "quantity": 3,
                "crated": False,
                "confidence": 0.95,
            }
        },
    )

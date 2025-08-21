"""Stockpile item model."""

from pydantic import BaseModel, ConfigDict, Field


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

"""Stockpile coordinates model."""

from pydantic import BaseModel, ConfigDict, Field


class StockpileCoords(BaseModel):
    """Normalized map coordinates for a stockpile location."""

    x: float = Field(description="Normalized X coordinate on the map (0.0 to 1.0)")
    y: float = Field(description="Normalized Y coordinate on the map (0.0 to 1.0)")

    def to_key(self) -> str:
        """Convert coordinates to a string key for comparison.

        Rounds to 6 decimal places to avoid floating point comparison issues.

        Returns:
            str: Coordinate string in format "x,y".
        """
        return f"{self.x:.6f},{self.y:.6f}"

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "x": 0.457745,
                "y": 0.664469,
            }
        },
    )

"""Stockpile model."""

from datetime import datetime
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from foxhole_stockpiles.enums.stockpile_type import StockpileType
from foxhole_stockpiles.models.stockpile_item import StockpileItem


class Stockpile(BaseModel):
    """Stockpile model."""

    name: str = Field(description="Name of the stockpile", default="")
    type: StockpileType = Field(description="Type of stockpile", default=StockpileType.UNDEFINED)
    items: list[StockpileItem] = Field(description="List of items", default_factory=list)
    timestamp: datetime = Field(description="last update datetime", default_factory=datetime.now)
    shard: str = Field(description="Shard name", default="")
    ingame_timestamp: str = Field(description="In game timestamp", default="")
    resolution: str | None = Field(description="Resolution of the screenshot", default=None)
    errors: list[str] = Field(
        description="List of errors encountered during processing", default_factory=list
    )

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize the timestamp."""
        return value.isoformat()

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "name": "Logi",
                "type": StockpileType.SEAPORT,
                "items": [
                    cast(dict[str, Any], StockpileItem.model_config)
                    .get("json_schema_extra", {})
                    .get("example", {})
                ],
                "timestamp": "2024-01-04T09:00:00Z",
                "resolution": "1920x1080",
                "shard": "ABLE",
                "ingame_timestamp": "Day 1,293, 1906 Hours",
                "errors": ["No icon detected in group 1, index 67 with confidence 0.75"],
            }
        },
    )

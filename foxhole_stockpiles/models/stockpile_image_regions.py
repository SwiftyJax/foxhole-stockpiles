"""Stockpile Image module for returning detected stockpile regions."""

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field


class StockpileImageRegions(BaseModel):
    """Model representing detected stockpile regions in a screenshot."""

    quantities: list[NDArray[np.uint8]] = Field(description="List of detected quantity boxes")
    composite_quantities_image: NDArray[np.uint8] = Field(description="Composited quantities image")
    icons: list[NDArray[np.uint8]] = Field(description="List of detected stockpile icons")
    stockpile_type: NDArray[np.uint8] | None = Field(
        description="Detected stockpile type region", default=None
    )
    stockpile_name: NDArray[np.uint8] | None = Field(
        description="Detected stockpile name region", default=None
    )
    hex_name: NDArray[np.uint8] | None = Field(description="Detected hex name region", default=None)
    vertical_resolution: int = Field(description="Vertical resolution of the screenshot", ge=0)
    groups: list[tuple[int, int]] = Field(
        description="List of detected icon groups, each represented as (size, start_index)"
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "quantities": [[10, 20, 30]],
                "composite_quantities_image": [[5, 6, 7]],
                "icons": [[1, 2, 3]],
                "stockpile_type": [1],
                "stockpile_name": [1],
                "hex_name": [1],
                "vertical_resolution": 1080,
                "groups": [[3, 0], [2, 3]],
            }
        },
    )

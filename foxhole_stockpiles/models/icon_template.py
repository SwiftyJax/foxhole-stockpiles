"""Icon template model for template matching."""

from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field, field_validator

from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution


class IconTemplate(BaseModel):
    """Template data for basic icon matching."""

    image: NDArray[np.uint8] = Field(description="Template image as numpy array")
    code: str = Field(description="Item code name", min_length=1)
    crated: bool = Field(description="Whether this is a crated variant", default=False)
    resolution: SupportedResolution = Field(description="Target resolution for this template")
    faction: ItemFaction = Field(description="Faction this template belongs to")
    category: ItemCategory = Field(description="Category this template belongs to")
    mod: str = Field(description="Mod this template comes from", min_length=1)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "code": "Rifle",
                "crated": False,
                "resolution": "1080",
                "faction": "neutral",
                "category": "item",
                "mod": "vanilla",
            }
        },
    )

    @field_validator("image")
    @classmethod
    def validate_image(cls, v: Any) -> NDArray[np.uint8]:
        """Validate that image is a numpy array."""
        if not isinstance(v, np.ndarray):
            raise ValueError("Image must be a numpy array")
        if v.dtype != np.uint8:
            raise ValueError("Image must be uint8 type")
        if len(v.shape) != 3 or v.shape[2] not in [3, 4]:
            raise ValueError("Image must be 3D array with 3 or 4 channels (BGR or BGRA)")
        return v

    def __str__(self) -> str:
        """String representation of the template."""
        return (
            f"IconTemplate(code={self.code}, faction={self.faction.value}, "
            f"mod={self.mod}, crated={self.crated})"
        )

    def __repr__(self) -> str:
        """Detailed representation of the template."""
        image_shape = self.image.shape if hasattr(self.image, "shape") else "unknown"
        return (
            f"IconTemplate(code='{self.code}', faction='{self.faction.value}', "
            f"mod='{self.mod}', crated={self.crated}, resolution='{self.resolution.value}', "
            f"image_shape={image_shape})"
        )

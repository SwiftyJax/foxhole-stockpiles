"""OCR settings."""

from pydantic import BaseModel, ConfigDict, Field


class OCRSettings(BaseModel):
    """Settings for the OCR."""

    height: int = Field(description="Base Height for the scaling", gt=0, default=2160)
    box_width: int = Field(description="Width of the quantity square", gt=0, default=84)
    box_height: int = Field(description="Height of the quantity square", gt=0, default=64)
    column_offset: int = Field(description="Horizontal separation between icons", gt=0, default=112)
    row_offset: int = Field(description="Vertical separation between icons", gt=0, default=78)
    group_offset: int = Field(description="Vertical separation for a new group", gt=0, default=98)
    title_margin: int = Field(
        description="Gap from top-left icon to title top-left point", gt=0, default=24
    )
    title_min_width: int = Field(description="Mimimum width for title", gt=0, default=600)
    title_height: int = Field(description="Title height", gt=0, default=64)
    icon_to_quantity_offset: int = Field(
        description="Gap between icon and quantity", gt=0, default=88
    )
    gray_lower: int = Field(
        description="Value for quantity boxes with darkest gamma", gt=0, default=15
    )
    gray_upper: int = Field(
        description="Value for quantity boxes with brighest gamma", gt=0, default=98
    )
    pixel_diff_tolerance: int = Field(description="pixel error tolerance", gt=0, default=2)

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "height": 2160,
                "box_width": 84,
                "box_height": 64,
                "column_offset": 112,
                "row_offset": 78,
                "group_offset": 98,
                "title_margin": 24,
                "title_min_width": 600,
                "title_height": 64,
                "icon_to_quantity_offset": 88,
                "gray_lower": 15,
                "gray_upper": 98,
                "pixel_diff_tolerance": 2,
            }
        },
    )

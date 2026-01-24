"""JSON format settings."""

from pydantic import BaseModel, ConfigDict, Field

from foxhole_stockpiles.enums.output_format import OutputFormat


class JsonFormatSettings(BaseModel):
    """Settings for JSON output format."""

    type: OutputFormat = Field(default=OutputFormat.JSON, description="Output format type")

    model_config = ConfigDict(extra="forbid")

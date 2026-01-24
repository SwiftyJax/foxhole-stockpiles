"""CSV/TSV format settings."""

from pydantic import BaseModel, ConfigDict, Field

from foxhole_stockpiles.enums.output_format import OutputFormat

# Available fields for CSV/TSV export
AVAILABLE_FIELDS = [
    "code",
    "quantity",
    "crated",
    "confidence",
    "stockpile_name",
    "stockpile_type",
    "shard",
    "timestamp",
    "resolution",
]

# Default fields for minimal export
DEFAULT_FIELDS = ["code", "quantity", "crated"]


class CsvFormatSettings(BaseModel):
    """Settings for CSV/TSV output format."""

    type: OutputFormat = Field(
        default=OutputFormat.CSV, description="Output format type (csv or tsv)"
    )
    separator: str = Field(
        default=",",
        description="Field separator character. Use ',' for CSV, '\\t' for TSV.",
    )
    fields: list[str] = Field(
        default_factory=lambda: DEFAULT_FIELDS.copy(),
        description=f"Fields to include in output. Available: {', '.join(AVAILABLE_FIELDS)}",
    )
    include_header: bool = Field(
        default=True,
        description="Include header row with field names",
    )

    model_config = ConfigDict(extra="forbid")

"""CSV/TSV format settings."""

from pydantic import BaseModel, ConfigDict, Field

from foxhole_stockpiles.enums.output_format import OutputFormat

# Fixed fields for CSV/TSV export (order matters)
CSV_FIELDS = [
    "stockpile_name",
    "stockpile_type",
    "code",
    "crated",
    "quantity",
    "confidence",
    "shard",
    "ingame_timestamp",
]

# Header names for CSV/TSV export
CSV_HEADERS = [
    "Stockpile Name",
    "Stockpile Type",
    "Code",
    "Crated",
    "Quantity",
    "Confidence",
    "Shard",
    "Ingame Time",
]


class CsvFormatSettings(BaseModel):
    """Settings for CSV/TSV output format."""

    type: OutputFormat = Field(
        default=OutputFormat.CSV, description="Output format type (csv or tsv)"
    )
    include_header: bool = Field(
        default=True,
        description="Include header row with field names",
    )

    model_config = ConfigDict(extra="forbid")

"""File output handler - writes data to filesystem."""

import asyncio
import datetime
import logging
from pathlib import Path
from typing import Any

from foxhole_stockpiles.core.settings.sections.output.csv_format import (
    CSV_FIELDS,
    CSV_HEADERS,
    CsvFormatSettings,
)
from foxhole_stockpiles.core.settings.sections.output.json_format import JsonFormatSettings
from foxhole_stockpiles.enums.output_format import OutputFormat
from foxhole_stockpiles.handlers.base_handler import BaseOutputDestinationHandler
from foxhole_stockpiles.models.stockpile import Stockpile

FormatSettings = JsonFormatSettings | CsvFormatSettings


class FileOutputHandler(BaseOutputDestinationHandler):
    """Handles writing stockpile data to files."""

    def __init__(
        self,
        default_file_path: str | None = None,
        format_settings: FormatSettings | None = None,
    ) -> None:
        """Initialize file output handler.

        Args:
            default_file_path (str | None): Default file path if not provided in handle()
            format_settings (FormatSettings | None): Format settings for output
        """
        self.logger = logging.getLogger(__name__)
        self.default_file_path = default_file_path
        self.format_settings = format_settings or JsonFormatSettings()

    async def handle(self, stockpile: Stockpile, **kwargs: Any) -> None:
        """Write stockpile data to file.

        Args:
            stockpile (Stockpile): The stockpile data to write
            **kwargs: Additional parameters:
                - file_path (str | Path): Path where to write the file

        Raises:
            ValueError: If no file path is provided
        """
        file_path_arg = kwargs.get("file_path")

        if not file_path_arg and not self.default_file_path:
            raise ValueError("File path must be provided via file_path argument or default")

        file = str(file_path_arg) if file_path_arg else self.default_file_path or "output.json"

        # Support placeholders in filename/path
        now = datetime.datetime.now()
        placeholders = {
            "{timestamp}": now.strftime("%Y-%m-%d_%H-%M-%S"),
            "{year}": now.strftime("%Y"),
            "{month}": now.strftime("%m"),
            "{day}": now.strftime("%d"),
            "{hour}": now.strftime("%H"),
            "{minute}": now.strftime("%M"),
            "{second}": now.strftime("%S"),
            "{stockpile_type}": (
                stockpile.type.title()
                if isinstance(stockpile.type, str)
                else stockpile.type.value.title()
            )
            if stockpile.type
            else "Unknown",
            "{stockpile_name}": stockpile.name or "Unknown",
            "{resolution}": stockpile.resolution or "Unknown",
        }
        for placeholder, value in placeholders.items():
            file = file.replace(placeholder, value)

        # Ensure correct file extension based on format
        file = self._fix_extension(file)

        output_path = Path(file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Format the output based on settings
        content = self._format_output(stockpile)

        def write_file() -> None:
            """Write stockpile data to file synchronously."""
            with output_path.open("w", encoding="utf-8") as f:
                f.write(content)

        await asyncio.to_thread(write_file)

        self.logger.info("Output saved to: %s", output_path)

    def _format_output(self, stockpile: Stockpile) -> str:
        """Format stockpile data based on format settings.

        Args:
            stockpile (Stockpile): The stockpile data to format

        Returns:
            str: Formatted output string
        """
        if isinstance(self.format_settings, CsvFormatSettings):
            return self._format_csv(stockpile)
        return stockpile.model_dump_json()

    def _format_csv(self, stockpile: Stockpile) -> str:
        """Format stockpile data as CSV/TSV.

        Args:
            stockpile (Stockpile): The stockpile data to format

        Returns:
            str: CSV/TSV formatted string
        """
        separator = "\t" if self.format_settings.type == OutputFormat.TSV else ","
        lines: list[str] = []

        # Add header if enabled
        if (
            isinstance(self.format_settings, CsvFormatSettings)
            and self.format_settings.include_header
        ):
            lines.append(separator.join(CSV_HEADERS))

        # Get stockpile-level values
        stockpile_name = stockpile.name or ""
        stockpile_type = (
            (
                stockpile.type.title()
                if isinstance(stockpile.type, str)
                else stockpile.type.value.title()
            )
            if stockpile.type
            else ""
        )
        shard = stockpile.shard or ""
        ingame_timestamp = stockpile.ingame_timestamp or ""

        # Add a row for each item
        for item in stockpile.items:
            row_values: list[str] = []
            for field in CSV_FIELDS:
                if field == "code":
                    row_values.append(self._escape_csv_value(item.code, separator))
                elif field == "crated":
                    row_values.append("1" if item.crated else "0")
                elif field == "quantity":
                    row_values.append(str(item.quantity))
                elif field == "confidence":
                    confidence = round(item.confidence, 3) if item.confidence is not None else ""
                    row_values.append(str(confidence) if confidence != "" else "")
                elif field == "stockpile_name":
                    row_values.append(self._escape_csv_value(stockpile_name, separator))
                elif field == "stockpile_type":
                    row_values.append(self._escape_csv_value(stockpile_type, separator))
                elif field == "shard":
                    row_values.append(self._escape_csv_value(shard, separator))
                elif field == "ingame_timestamp":
                    row_values.append(self._escape_csv_value(ingame_timestamp, separator))
            lines.append(separator.join(row_values))

        return "\n".join(lines)

    def _escape_csv_value(self, value: str, separator: str) -> str:
        """Escape a value for CSV/TSV output.

        Args:
            value (str): The value to escape
            separator (str): The field separator

        Returns:
            str: Escaped value
        """
        # Quote if value contains separator, quotes, or newlines
        if separator in value or '"' in value or "\n" in value:
            return '"' + value.replace('"', '""') + '"'
        return value

    def _fix_extension(self, file_path: str) -> str:
        """Fix the file extension based on format settings.

        Args:
            file_path (str): The file path to fix

        Returns:
            str: File path with correct extension
        """
        # Determine the correct extension based on format
        if self.format_settings.type == OutputFormat.TSV:
            correct_ext = ".tsv"
        elif self.format_settings.type == OutputFormat.CSV:
            correct_ext = ".csv"
        else:
            correct_ext = ".json"

        path = Path(file_path)
        current_ext = path.suffix.lower()

        # Known extensions to replace
        known_extensions = {".json", ".csv", ".tsv"}

        if current_ext in known_extensions:
            # Replace the existing extension
            return str(path.with_suffix(correct_ext))
        elif current_ext:
            # Has some other extension, replace it
            return str(path.with_suffix(correct_ext))
        else:
            # No extension, add the correct one
            return file_path + correct_ext

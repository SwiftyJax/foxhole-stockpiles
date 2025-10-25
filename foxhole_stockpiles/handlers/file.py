"""File output handler - writes data to filesystem."""

import asyncio
import datetime
import logging
from pathlib import Path
from typing import Any

from foxhole_stockpiles.handlers.base_handler import BaseOutputDestinationHandler
from foxhole_stockpiles.models.stockpile import Stockpile


class FileOutputHandler(BaseOutputDestinationHandler):
    """Handles writing stockpile data to files."""

    def __init__(self, default_file_path: str | None = None) -> None:
        """Initialize file output handler.

        Args:
            default_file_path (str | None): Default file path if not provided in handle()
        """
        self.logger = logging.getLogger(__name__)
        self.default_file_path = default_file_path

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

        # Support {timestamp} placeholder in filename
        if "{timestamp}" in file:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file = file.replace("{timestamp}", timestamp)

        output_path = Path(file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def write_file() -> None:
            """Write stockpile data to file synchronously."""
            with output_path.open("w", encoding="utf-8") as f:
                f.write(stockpile.model_dump_json())

        await asyncio.to_thread(write_file)

        self.logger.info("Output saved to: %s", output_path)

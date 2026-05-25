"""Webhook output handler - sends data to webhook endpoint."""

import logging
from typing import Any

from foxhole_stockpiles.core.settings.sections.output import SheetsHandlerSettings
from foxhole_stockpiles.handlers.base_handler import BaseOutputDestinationHandler
from foxhole_stockpiles.models.stockpile import Stockpile


class SheetsOutputHandler(BaseOutputDestinationHandler):
    """Handles sending stockpile data to webhook endpoints."""

    def __init__(self, sheets_settings: SheetsHandlerSettings) -> None:
        """Initialize sheets output handler.

        Args:
            sheets_settings(SheetsHandlerSettings): Sheets configuration settings
        """
        self.logger = logging.getLogger(__name__)
        self._creds_path = sheets_settings.creds_path
        self._spreadsheet_url = sheets_settings.spreadsheet_url
        self._spreadsheet_sheet_id = sheets_settings.spreadsheet_sheet_id

    async def handle(self, stockpiles: list[Stockpile], **kwargs: Any) -> None:
        """Append stockpile data to sheets spreadsheet.

        Args:
            TODO: REWRITE
            stockpiles (list[Stockpile]): The stockpile data to send
            **kwargs: Additional parameters:
                - token (str | None): Optional auth token to override configured token

        Returns:
            dict[str, Any]: Webhook response data
        """
        print("NYI")

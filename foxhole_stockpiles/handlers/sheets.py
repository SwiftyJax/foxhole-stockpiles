"""Sheets output handler - appends data to Google Sheets spreadsheet."""

import logging
import os
from pathlib import Path
from re import Match, search
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from foxhole_stockpiles.core.settings.sections.output.sheets_handler import SheetsHandlerSettings
from foxhole_stockpiles.handlers.base_handler import BaseOutputDestinationHandler
from foxhole_stockpiles.models.stockpile import Stockpile
from foxhole_stockpiles.services.catalog_service import CatalogService


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

    async def handle(self, stockpiles: list[Stockpile], **kwargs: Any) -> dict[str, Any]:
        """Append stockpile data to sheets spreadsheet in FIR format.

        Args:
            stockpiles (list[Stockpile]): The stockpile data to send
            **kwargs: Additional parameters:
                - None

        Returns:
            dict[str, Any]: Append response data
        """
        auth_scopes = ["https://www.googleapis.com/auth/spreadsheets"]  # Needed scopes to append

        creds = None
        # Try to find saved token, if it doesn't exist or is invalid, prompt reauth using creds json
        # Unsure if it should be saved in home directory
        # might probably move it to temp dir or delete after appending
        if os.path.exists(Path("~/.fs_token").expanduser()):
            # ignoring mypy error since it's a import issue
            creds = Credentials.from_authorized_user_file(  # type: ignore [no-untyped-call]
                str(Path("~/.fs_token").expanduser()), auth_scopes
            )
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self._creds_path, auth_scopes)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(Path("~/.fs_token").expanduser(), "w") as token:
                token.write(creds.to_json())

        if creds is None:
            return {"message": "Credentials invalid or authorization failed"}
            raise ConnectionError()

        if self._spreadsheet_url is None:
            return {"message": "Spreadsheet URL missing"}

        spreadsheet_id_match: Match[str] | None = search(
            pattern=r"(?<=https://docs.google.com/spreadsheets/d/).*(?=/)",
            string=self._spreadsheet_url,
        )  # Get spreadsheet ID from URL (needs tidying up)

        if spreadsheet_id_match is None:
            return {"message": "Spreadsheet URL invalid"}

        spreadsheet_id = spreadsheet_id_match.group()

        if self._spreadsheet_sheet_id is None or self._spreadsheet_sheet_id.strip() == "":
            return {"message": "Sheet ID missing"}

        self.logger.debug(
            "Appending to spreadsheet (Spreadsheet ID: %s, Sheet: %s)",
            spreadsheet_id,
            self._spreadsheet_sheet_id,
        )

        catalog_service = CatalogService()  # temp hack to get display names working
        catalog_service._catalog_path = Path("./data/catalog.json")

        # TODO: check is_reserve flag being not set with .sav export
        rows = []
        for stockpile in stockpiles:
            for item in stockpile.items:
                rows.append(
                    [
                        str(stockpile.timestamp),
                        stockpile.type,
                        stockpile.name if stockpile.is_reserve else "Public",
                        "NONE",  # no image info provided, value ignored anyway
                        item.code,
                        catalog_service.get_display_name(item.code),
                        item.quantity,
                        item.crated,
                    ]
                )
        try:
            service = build("sheets", "v4", credentials=creds)

            # Call the Sheets API
            body = {"values": rows}
            result = await (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=self._spreadsheet_sheet_id + "!A1",
                    valueInputOption="USER_ENTERED",
                    body=body,
                )
                .execute()
            )
            self.logger.debug("Append result: %s", result)
            return {"status": "ok"}
        except HttpError:
            return {"message": "Appending failed"}

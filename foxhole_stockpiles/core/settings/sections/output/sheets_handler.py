"""Sheets handler settings."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from foxhole_stockpiles.enums.output_handler_type import OutputHandlerType


class SheetsHandlerSettings(BaseModel):
    """Settings for sheets output handler."""

    type: OutputHandlerType = Field(default=OutputHandlerType.SHEETS, description="Handler type")
    creds_path: str | None = Field(
        description="Path to the Google OAuth Credentials JSON file", default=None
    )

    spreadsheet_url: str | None = Field(description="Spreadsheet to append data to", default=None)
    spreadsheet_sheet_id: str | None = Field(
        description="Target sheet id for appending data", default=None
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_auth_consistency(self) -> Self:
        """Validate that the OAuth credentials, spreadsheet URL and sheet ID are valid.

        Returns:
            Self: The validated instance.

        Raises:
            TBD
        """
        # TODO: Implement validation
        return self

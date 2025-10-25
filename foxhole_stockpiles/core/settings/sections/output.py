"""Output settings."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from foxhole_stockpiles.enums.auth_type import AuthType
from foxhole_stockpiles.enums.output_destination import OutputDestination
from foxhole_stockpiles.enums.output_format import OutputFormat


class FileOutputSettings(BaseModel):
    """Settings for file output destination."""

    path: str = Field(
        description="Path to the output file (supports {timestamp} placeholder)",
        default="output.json",
    )

    model_config = ConfigDict(extra="forbid")


class WebhookOutputSettings(BaseModel):
    """Settings for webhook output destination."""

    url: str | None = Field(description="Webhook URL for sending output", default=None)
    auth_type: AuthType | None = Field(
        description=(
            "Authentication type to use when sending to webhook. "
            "Supported types: 'basic', 'bearer', or 'forward'."
        ),
        default=None,
    )
    token: str | None = Field(
        description=(
            "Token to use for authentication when sending to webhook. "
            "For 'basic' auth_type, this should be base64 encoded 'username:password'. "
            "Required when auth_type is 'basic' or 'bearer'."
        ),
        default=None,
    )
    client_auth_header: str | None = Field(
        description=(
            "Client header name to pass through from API client to webhook. "
            "Required when auth_type is 'forward'."
        ),
        default=None,
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_auth_consistency(self) -> Self:
        """Validate that webhook auth type and token are consistent.

        Returns:
            Self: The validated instance.

        Raises:
            ValueError: If webhook auth configuration is invalid.
        """
        auth = self.auth_type
        if auth in (AuthType.BASIC, AuthType.BEARER):
            if not self.token:
                raise ValueError(f"token must be set when auth_type is '{auth}'")
        elif auth == AuthType.FORWARD:
            if not self.client_auth_header:
                raise ValueError("client_auth_header must be set when auth_type is 'forward'")
        return self


class ConsoleOutputSettings(BaseModel):
    """Settings for console output destination."""

    model_config = ConfigDict(extra="forbid")


class OutputSettings(BaseModel):
    """Settings for output formats and destinations."""

    format: OutputFormat = Field(description="Data serialization format", default=OutputFormat.JSON)
    destination: OutputDestination = Field(
        description="Output destination (return, file, webhook, console)",
        default=OutputDestination.RETURN,
    )
    file: FileOutputSettings = Field(
        description="File output settings",
        default_factory=FileOutputSettings,
    )
    webhook: WebhookOutputSettings = Field(
        description="Webhook output settings",
        default_factory=WebhookOutputSettings,
    )
    console: ConsoleOutputSettings = Field(
        description="Console output settings",
        default_factory=ConsoleOutputSettings,
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "format": "json",
                "destination": "webhook",
                "webhook": {
                    "url": "https://api.example.com/stockpiles",
                    "auth_type": "bearer",
                    "token": "your-token",
                },
                "file": {
                    "path": "output.json",
                },
            }
        },
    )

    @model_validator(mode="after")
    def validate_active_destination(self) -> Self:
        """Validate only the active destination configuration.

        Returns:
            Self: The validated instance.

        Raises:
            ValueError: If the active destination configuration is invalid.
        """
        if self.destination == OutputDestination.WEBHOOK:
            if not self.webhook.url:
                raise ValueError("webhook.url must be provided when destination is 'webhook'")
        elif self.destination == OutputDestination.FILE:
            if not self.file.path:
                raise ValueError("file.path must be provided when destination is 'file'")

        return self

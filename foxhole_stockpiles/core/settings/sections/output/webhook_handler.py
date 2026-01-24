"""Webhook handler settings."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from foxhole_stockpiles.enums.auth_type import AuthType
from foxhole_stockpiles.enums.output_handler_type import OutputHandlerType


class WebhookHandlerSettings(BaseModel):
    """Settings for webhook output handler."""

    type: OutputHandlerType = Field(default=OutputHandlerType.WEBHOOK, description="Handler type")
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

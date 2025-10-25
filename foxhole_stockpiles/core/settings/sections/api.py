"""API settings."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from foxhole_stockpiles.enums.auth_type import AuthType


class APIServerSettings(BaseModel):
    """Settings for API server."""

    cors_allow_origins: list[str] = Field(
        description="List of allowed CORS origins. Use ['*'] to allow all origins.",
        default=["*"],
    )
    host: str = Field(
        description="Server bind host",
        default="127.0.0.1",
    )
    port: int = Field(
        description="Server bind port",
        default=8000,
        gt=0,
        le=65535,
    )
    workers: int = Field(
        description="Number of worker processes",
        default=1,
        gt=0,
    )
    reload: bool = Field(
        description="Enable auto-reload on code changes (development only)",
        default=False,
    )
    log_level: str = Field(
        description="Server log level",
        default="info",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "cors_allow_origins": ["https://yourdomain.com", "https://app.yourdomain.com"],
                "host": "0.0.0.0",
                "port": 8000,
                "workers": 4,
                "reload": False,
                "log_level": "info",
            }
        },
    )


class APIAuthSettings(BaseModel):
    """Settings for API authentication."""

    auth_type: AuthType | None = Field(
        description=(
            "Authentication type to protect API endpoints. "
            "Supported types: 'basic' or 'bearer'. "
            "If None, authentication is disabled."
        ),
        default=None,
    )
    auth_token: str | None = Field(
        description=(
            "Token to use for API authentication. "
            "For 'basic' auth_type, this should be base64 encoded 'username:password'. "
            "Required when auth_type is set."
        ),
        default=None,
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "auth_type": "bearer",
                "auth_token": "your-secret-token",
            }
        },
    )

    def _validate_auth_consistency(self) -> None:
        """Validate that auth type and token are consistent.

        Raises:
            ValueError: If only one of auth_type or auth_token is provided.
        """
        if bool(self.auth_type) != bool(self.auth_token):
            raise ValueError("auth_type and auth_token must both be set or both be None")
        if self.auth_type == AuthType.FORWARD:
            raise ValueError("auth_type 'forward' is not supported for API authentication")

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        """Validate the model.

        Returns:
            Self: The validated instance.

        Raises:
            ValueError: If any of the fields is invalid
        """
        self._validate_auth_consistency()

        return self

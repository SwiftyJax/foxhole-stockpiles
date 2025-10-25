"""Configuration module for the app."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from foxhole_stockpiles.enums.auth_type import AuthType
from foxhole_stockpiles.enums.output_destination import OutputDestination
from foxhole_stockpiles.enums.output_format import OutputFormat
from foxhole_stockpiles.models.ocr_coordinator_config import OCRCoordinatorConfig


class Utf8JsonConfigSettingsSource(JsonConfigSettingsSource):
    """JSON config settings source that reads files with UTF-8 encoding."""

    def _read_file(self, file_path: Path) -> dict[str, Any]:
        """Read and parse a JSON file with UTF-8 encoding.

        Args:
            file_path: Path to the JSON file

        Returns:
            dict[str, Any]: The parsed JSON data
        """
        with file_path.open("r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data


class LoggingSettings(BaseModel):
    """Settings for logging."""

    loggers: dict[str, str] = Field(description="Loggers and their levels", default={})
    log_level: str = Field(description="Logging level", default="INFO")
    log_format: str = Field(
        description="Logging format",
        default="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    )
    date_format: str = Field(description="Logging date format", default="%Y-%m-%d %H:%M:%S")
    rotate_logs: bool = Field(description="Rotate logs daily", default=False)
    log_file: str | None = Field(description="Log file to write to", default=None)

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "loggers": {"foxhole_stockpiles": "DEBUG", "uvicorn": "INFO"},
                "log_level": "INFO",
                "log_format": "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
                "rotate_logs": False,
                "log_file": None,
            }
        },
    )


class OCRSettings(BaseModel):
    """Settings for the OCR."""

    height: int = Field(description="Base Height for the scaling", gt=0, default=2160)
    box_width: int = Field(description="Width of the quantity square", gt=0, default=84)
    box_height: int = Field(description="Height of the quantity square", gt=0, default=64)
    column_offset: int = Field(description="Horizontal separation between icons", gt=0, default=112)
    row_offset: int = Field(description="Vertical separation between icons", gt=0, default=78)
    group_offset: int = Field(description="Vertical separation for a new group", gt=0, default=98)
    title_margin: int = Field(
        description="Gap from top-left icon to title top-left point", gt=0, default=24
    )
    title_min_width: int = Field(description="Mimimum width for title", gt=0, default=600)
    title_height: int = Field(description="Title height", gt=0, default=64)
    icon_to_quantity_offset: int = Field(
        description="Gap between icon and quantity", gt=0, default=88
    )
    gray_lower: int = Field(
        description="Value for quantity boxes with darkest gamma", gt=0, default=15
    )
    gray_upper: int = Field(
        description="Value for quantity boxes with brighest gamma", gt=0, default=98
    )
    pixel_diff_tolerance: int = Field(description="pixel error tolerance", gt=0, default=2)

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "height": 2160,
                "box_width": 84,
                "box_height": 64,
                "column_offset": 112,
                "row_offset": 78,
                "group_offset": 98,
                "title_margin": 24,
                "title_min_width": 600,
                "title_height": 64,
                "icon_to_quantity_offset": 88,
                "gray_lower": 15,
                "gray_upper": 98,
                "pixel_diff_tolerance": 2,
            }
        },
    )


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
        extra="ignore",
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
        extra="ignore",
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


class FileOutputSettings(BaseModel):
    """Settings for file output destination."""

    path: str = Field(
        description="Path to the output file (supports {timestamp} placeholder)",
        default="output.json",
    )

    model_config = ConfigDict(extra="ignore")


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

    model_config = ConfigDict(extra="ignore")

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

    model_config = ConfigDict(extra="ignore")


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
        extra="ignore",
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


class StockpileTypesSettings(BaseModel):
    """Settings for the stockpile types."""

    encampment: list[str] = Field(
        description="Encampment values",
        default=[
            "Encampment",
            "Campement",
            "Feldlager",
            "Acampamento",
            "Лагерь",
            "营地",
        ],
    )
    keep: list[str] = Field(
        description="Keep values",
        default=[
            "Keep",
            "Place Forte",
            "Wehrturm",
            "Torreão",
            "Крепость",
            "要塞",
        ],
    )
    safe_house: list[str] = Field(
        description="Safe House values",
        default=[
            "Safe House",
            "Planque",
            "Unterschlupf",
            "Casa Fortificada",
            "Yбeжищe",
            "安全屋",
        ],
    )
    relic_base: list[str] = Field(
        description="Relic Base values",
        default=[
            "Relic Base",
            "Base Relique",
            "Reliktbasis",
            "Base Relíquia",
            "Peликтoвая база",
            "遗迹基地",
        ],
    )
    bunker_base: list[str] = Field(
        description="Bunker Base values",
        default=[
            "Bunker Base",
            "Base Bunker",
            "Bunkerbasis",
            "Centro do Bunker",
            "Base de Bunker",
            "Base de Casamata",
            "Бункерная база",
            "Бункерная База",
            "地堡基地",
        ],
    )
    border_base: list[str] = Field(
        description="Border Base values",
        default=[
            "Border Base",
            "Base Frontalière",
            "Grenzbasis",
            "Base Fronteiriça",
            "Пограничная База",
            "边境基地",
        ],
    )
    town_base: list[str] = Field(
        description="Town Base values",
        default=[
            "Town Base",
            "Quartier Général",
            "Stadtkernbasis",
            "Base de Cidade",
            "Ратуша",
            "城镇基地",
        ],
    )
    bms_longhook: list[str] = Field(
        description="BMS - Longhook values",
        default=["BMS - Longhook"],
    )
    storage_depot: list[str] = Field(
        description="Storage Depot values",
        default=[
            "Storage Depot",
            "Dépôt",
            "Lagerdepot",
            "Depósito",
            "Складское Помещение",
            "仓库",
        ],
    )
    seaport: list[str] = Field(
        description="Seaport values",
        default=[
            "Seaport",
            "Port",
            "Seehafen",
            "Porto",
            "Морской порт",
            "海港",
        ],
    )
    undefined: list[str] = Field(
        description="Undefined values",
        default=["Undefined"],
    )

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "encampment": [
                    "Encampment",
                    "Campement",
                    "Feldlager",
                    "Acampamento",
                    "Лагерь",
                    "营地",
                ],
                "keep": [
                    "Keep",
                    "Place Forte",
                    "Wehrturm",
                    "Torreão",
                    "Крепость",
                    "要塞",
                ],
                "safe_house": [
                    "Safe House",
                    "Planque",
                    "Unterschlupf",
                    "Casa Fortificada",
                    "Yбeжищe",
                    "安全屋",
                ],
                "relic_base": [
                    "Relic Base",
                    "Base Relique",
                    "Reliktbasis",
                    "Base Relíquia",
                    "Peликтoвая база",
                    "遗迹基地",
                ],
                "bunker_base": [
                    "Bunker Base",
                    "Base Bunker",
                    "Bunkerbasis",
                    "Centro do Bunker",
                    "Base de Bunker",
                    "Base de Casamata",
                    "Бункерная база",
                    "Бункерная База",
                    "地堡基地",
                ],
                "border_base": [
                    "Border Base",
                    "Base Frontalière",
                    "Grenzbasis",
                    "Base Fronteiriça",
                    "Пограничная База",
                    "边境基地",
                ],
                "town_base": [
                    "Town Base",
                    "Quartier Général",
                    "Stadtkernbasis",
                    "Base de Cidade",
                    "Ратуша",
                    "城镇基地",
                ],
                "bms_longhook": ["BMS - Longhook"],
                "storage_depot": [
                    "Storage Depot",
                    "Dépôt",
                    "Lagerdepot",
                    "Depósito",
                    "Складское Помещение",
                    "仓库",
                ],
                "seaport": [
                    "Seaport",
                    "Port",
                    "Seehafen",
                    "Porto",
                    "Морской порт",
                    "海港",
                ],
                "undefined": ["Undefined"],
            }
        },
    )


class TemplateSettings(BaseModel):
    """Settings for the template generation."""

    crate_blue_multiplier: int = Field(
        description=(
            "Multiplier for blue channel when applying crate color tint "
            "(0-255, will be divided by 255)"
        ),
        ge=0,
        le=255,
        default=145,
    )
    crate_blue_offset: int = Field(
        description="Offset for blue channel when applying crate color tint",
        ge=0,
        le=255,
        default=82,
    )
    crate_green_multiplier: int = Field(
        description=(
            "Multiplier for green channel when applying crate color tint "
            "(0-255, will be divided by 255)"
        ),
        ge=0,
        le=255,
        default=152,
    )
    crate_green_offset: int = Field(
        description="Offset for green channel when applying crate color tint",
        ge=0,
        le=255,
        default=87,
    )
    crate_red_multiplier: int = Field(
        description=(
            "Multiplier for red channel when applying crate color tint "
            "(0-255, will be divided by 255)"
        ),
        ge=0,
        le=255,
        default=154,
    )
    crate_red_offset: int = Field(
        description="Offset for red channel when applying crate color tint",
        ge=0,
        le=255,
        default=89,
    )

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "crate_blue_multiplier": 145,
                "crate_blue_offset": 82,
                "crate_green_multiplier": 152,
                "crate_green_offset": 87,
                "crate_red_multiplier": 154,
                "crate_red_offset": 89,
            }
        },
    )


class AppSettings(BaseSettings):
    """Application Settings."""

    config_version: int = Field(
        default=2,
        description="Configuration format version for migration purposes",
    )
    api_server: APIServerSettings = Field(
        description="API server settings", default_factory=APIServerSettings
    )
    api_auth: APIAuthSettings = Field(
        description="API authentication settings", default_factory=APIAuthSettings
    )
    logging: LoggingSettings = Field(
        description="Logging settings", default_factory=LoggingSettings
    )
    ocr: OCRSettings = Field(description="OCR settings", default_factory=OCRSettings)
    output: OutputSettings = Field(description="Output settings", default_factory=OutputSettings)
    scanner: OCRCoordinatorConfig = Field(
        description="Stockpile scanner settings", default_factory=OCRCoordinatorConfig
    )
    stockpile_types: StockpileTypesSettings = Field(
        description="Stockpile types settings", default_factory=StockpileTypesSettings
    )
    templates: TemplateSettings = Field(
        description="Template generation settings", default_factory=TemplateSettings
    )
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_prefix="FS_",
        json_file=str(Path("~/.fs_config").expanduser()),
    )

    @model_validator(mode="before")
    @classmethod
    def migrate_config(cls, data: Any) -> Any:
        """Migrate configuration from older versions to current version.

        Args:
            data: Raw configuration data

        Returns:
            Migrated configuration data
        """
        if not isinstance(data, dict):
            return data

        # Determine config version (default to 1 for old configs without version field)
        version = data.get("config_version", 1)

        # Apply migrations sequentially
        if version == 1:
            data = cls._migrate_v1_to_v2(data)
            data["config_version"] = 2

        # Future migrations would go here:
        # if version == 2:
        #     data = cls._migrate_v2_to_v3(data)
        #     data["config_version"] = 3

        return data

    @staticmethod
    def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
        """Migrate from v1 (flat output structure) to v2 (nested output structure).

        V1 had: output_format.{output_format, output_destination, file_path, webhook_url, ...}
        V2 has: output.{format, destination, file.{path}, webhook.{url, auth_type, token, ...}}

        Args:
            data: V1 configuration data

        Returns:
            V2 configuration data
        """
        # Check if we have old output_format structure
        if "output_format" in data and isinstance(data["output_format"], dict):
            old_output = data["output_format"]

            # Build new nested structure
            new_output: dict[str, Any] = {
                "format": old_output.get("output_format", "json"),
                "destination": old_output.get("output_destination", "return"),
                "file": {
                    "path": old_output.get("file_path", "output.json"),
                },
                "webhook": {
                    "url": old_output.get("webhook_url"),
                    "auth_type": old_output.get("webhook_auth_type"),
                    "token": old_output.get("webhook_token"),
                    "client_auth_header": old_output.get("webhook_client_auth_header"),
                },
                "console": {},
            }

            # Replace with new structure
            data["output"] = new_output
            del data["output_format"]

        return data

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customise settings sources to include JSON config file.

        Args:
            settings_cls: The settings class
            init_settings: Init settings source
            env_settings: Environment settings source
            dotenv_settings: Dotenv settings source
            file_secret_settings: File secret settings source

        Returns:
            tuple: Settings sources in priority order (highest to lowest)
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            Utf8JsonConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


@lru_cache
def get_settings() -> AppSettings:
    """Get the settings.

    Returns:
        AppSettings: The settings
    """
    return AppSettings()

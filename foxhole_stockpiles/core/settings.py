"""Configuration module for the app."""

from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from foxhole_stockpiles.enums.output_format import OutputFormat
from foxhole_stockpiles.models.ocr_coordinator_config import OCRCoordinatorConfig


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

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "cors_allow_origins": ["https://yourdomain.com", "https://app.yourdomain.com"],
            }
        },
    )


class APIAuthSettings(BaseModel):
    """Settings for API authentication."""

    auth_type: str | None = Field(
        description=(
            "Authentication type to protect API endpoints. "
            "Supported types: 'basic', 'bearer', or custom header name. "
            "If None, authentication is disabled."
        ),
        default=None,
    )
    auth_token: str | None = Field(
        description=(
            "Token to use for API authentication. "
            "For 'basic' auth_type, this should be base64 encoded 'username:password'."
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


class OutputFormatSettings(BaseModel):
    """Settings for output formats."""

    output_format: OutputFormat = Field(
        description="Output format to use", default=OutputFormat.JSON
    )
    file_path: str = Field(
        description="Path to the output file when using file output format", default="output.json"
    )
    webhook_auth_type: str | None = Field(
        description=(
            "Authentication type to use when sending to webhook. "
            "Supported types: 'basic', 'bearer', or custom header name."
        ),
        default=None,
    )
    webhook_token: str | None = Field(
        description=(
            "Token to use for authentication when sending to webhook. "
            "For 'basic' auth_type, this should be base64 encoded 'username:password'."
        ),
        default=None,
    )
    webhook_url: str | None = Field(
        description="Webhook URL for sending output when using webhook output format", default=None
    )
    webhook_client_auth_header: str | None = Field(
        description=("Client header used from client to pass through to the webhook."),
        default=None,
    )

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "file_path": "output.txt",
                "output_format": "file",
            }
        },
    )

    def _validate_webhook_fields(self) -> None:
        """Validate the webhook settings.

        Raises:
            ValueError: If webhook configuration is invalid.
        """
        if self.output_format == OutputFormat.WEBHOOK and not self.webhook_url:
            raise ValueError("webhook_url must be provided when output_format is 'webhook'")

    def _validate_auth_consistency(self) -> None:
        """Validate that webhook auth type and token are consistent.

        Raises:
            ValueError: If only one of webhook_auth_type or webhook_token is provided.
        """
        if bool(self.webhook_auth_type) != bool(self.webhook_token):
            raise ValueError("webhook_auth_type and webhook_token must both be set or both be None")

    def _validate_file_fields(self) -> None:
        """Validate the file output settings.

        Raises:
            ValueError: If file_path is not provided when output_format is file.
        """
        if self.output_format == OutputFormat.FILE and not self.file_path:
            raise ValueError("file_path must be provided when output_format is 'file'")

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        """Validate the model.

        Returns:
            Self: The validated instance.

        Raises:
            ValueError: If any of the fields is invalid
        """
        self._validate_webhook_fields()
        self._validate_file_fields()
        self._validate_auth_consistency()

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
    output_format: OutputFormatSettings = Field(
        description="Output format settings", default_factory=OutputFormatSettings
    )
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
        env_file=str(Path("~/.fs_config").expanduser()),
    )


@lru_cache
def get_settings() -> AppSettings:
    """Get the settings.

    Returns:
        AppSettings: The settings
    """
    return AppSettings()

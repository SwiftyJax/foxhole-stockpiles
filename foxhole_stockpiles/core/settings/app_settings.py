"""Application settings."""

from pathlib import Path
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from foxhole_stockpiles.core.settings.sections import (
    APIAuthSettings,
    APIServerSettings,
    DatabaseBuilderSettings,
    ExternalToolsSettings,
    GUISettings,
    LoggingSettings,
    NotificationsSettings,
    OCRSettings,
    OutputSettings,
    ScannerSettings,
    StockpileTypesSettings,
    TemplateSettings,
)


class AppSettings(BaseSettings):
    """Application Settings."""

    config_version: int = Field(
        default=5,
        description="Configuration format version for migration purposes",
    )
    api_server: APIServerSettings = Field(
        description="API server settings", default_factory=APIServerSettings
    )
    api_auth: APIAuthSettings = Field(
        description="API authentication settings", default_factory=APIAuthSettings
    )
    external_tools: ExternalToolsSettings = Field(
        description="External tools settings", default_factory=ExternalToolsSettings
    )
    logging: LoggingSettings = Field(
        description="Logging settings", default_factory=LoggingSettings
    )
    ocr: OCRSettings = Field(description="OCR settings", default_factory=OCRSettings)
    output: OutputSettings = Field(description="Output settings", default_factory=OutputSettings)
    scanner: ScannerSettings = Field(
        description="Stockpile scanner settings", default_factory=ScannerSettings
    )
    stockpile_types: StockpileTypesSettings = Field(
        description="Stockpile types settings", default_factory=StockpileTypesSettings
    )
    templates: TemplateSettings = Field(
        description="Template generation settings", default_factory=TemplateSettings
    )
    database_builder: DatabaseBuilderSettings = Field(
        description="Database builder settings", default_factory=DatabaseBuilderSettings
    )
    notifications: NotificationsSettings = Field(
        description="Notifications settings", default_factory=NotificationsSettings
    )
    gui: GUISettings = Field(description="GUI settings", default_factory=GUISettings)
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_prefix="FS_",
        json_file=str(Path("~/.fs_config").expanduser()),
    )

    @classmethod
    def _apply_migrations(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Apply configuration migrations.

        Args:
            data: Raw configuration data

        Returns:
            Migrated configuration data
        """
        if not isinstance(data, dict):
            return data

        # Make a copy to avoid modifying the original
        data = dict(data)

        # Determine config version (default to 1 for old configs without version field)
        version = data.get("config_version", 1)

        # Apply migrations sequentially
        if version == 1:
            data = cls._migrate_v1_to_v2(data)
            data["config_version"] = 2
            version = 2

        if version == 2:
            data = cls._migrate_v2_to_v3(data)
            data["config_version"] = 3
            version = 3

        if version == 3:
            data = cls._migrate_v3_to_v4(data)
            data["config_version"] = 4
            version = 4

        if version == 4:
            data = cls._migrate_v4_to_v5(data)
            data["config_version"] = 5

        return data

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

        return cls._apply_migrations(data)

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

        if "scanner" in data and isinstance(data["scanner"], dict):
            data["scanner"].pop("confidence_threshold", None)
            data["scanner"].pop("confidence_by_resolution", None)

        return data

    @staticmethod
    def _migrate_v2_to_v3(data: dict[str, Any]) -> dict[str, Any]:
        """Migrate from v2 to v3 (move tools from database_builder to external_tools).

        V2 had: database_builder.{extractor_tool, converter_tool, catalog_file, ...}
        V3 has: external_tools.{repak, umodel, uassetgui} + database_builder.{catalog_file, ...}

        Args:
            data: V2 configuration data

        Returns:
            V3 configuration data
        """
        # Initialize external_tools if not present
        if "external_tools" not in data:
            data["external_tools"] = {}

        # Move tools from database_builder to external_tools
        if "database_builder" in data and isinstance(data["database_builder"], dict):
            db_builder = data["database_builder"]

            # Move extractor_tool -> repak
            if "extractor_tool" in db_builder:
                data["external_tools"]["repak"] = db_builder.pop("extractor_tool")

            # Move converter_tool -> umodel
            if "converter_tool" in db_builder:
                data["external_tools"]["umodel"] = db_builder.pop("converter_tool")

        return data

    @staticmethod
    def _migrate_v3_to_v4(data: dict[str, Any]) -> dict[str, Any]:
        """Migrate from v3 to v4 (stockpile_types now only stores additional aliases).

        V3 had: stockpile_types with all translations as defaults (including undefined)
        V4 has: stockpile_types with only user-added aliases (no undefined field)

        The valid translations are now in the constants module, so we filter
        out any default translations from the config, keeping only user-added aliases.

        Args:
            data: V3 configuration data

        Returns:
            V4 configuration data
        """
        if "stockpile_types" not in data or not isinstance(data["stockpile_types"], dict):
            return data

        # Lazy import to avoid circular dependencies at module load time
        from foxhole_stockpiles.constants import STOCKPILE_TYPE_TEXTS

        stockpile_types = data["stockpile_types"]

        # Remove the undefined field (no longer valid)
        stockpile_types.pop("undefined", None)

        # Build mapping from settings field names to default texts
        # The field names use snake_case, enum values use Title Case
        field_to_defaults: dict[str, set[str]] = {
            stockpile_type.name.lower(): set(texts)
            for stockpile_type, texts in STOCKPILE_TYPE_TEXTS.items()
            if stockpile_type.name != "UNDEFINED"  # Skip UNDEFINED
        }

        # Filter out default translations, keeping only user-added aliases
        for field_name, defaults in field_to_defaults.items():
            if field_name in stockpile_types and isinstance(stockpile_types[field_name], list):
                stockpile_types[field_name] = [
                    alias for alias in stockpile_types[field_name] if alias not in defaults
                ]

        return data

    @staticmethod
    def _migrate_v4_to_v5(data: dict[str, Any]) -> dict[str, Any]:
        """Migrate from v4 to v5 (output now supports multiple handlers).

        V4 had: output.{format, destination, file.{path}, webhook.{...}, console.{}}
        V5 has: output.{handlers: [{name, format: {type, ...}, handler: {type, ...}}, ...]}

        Args:
            data: V4 configuration data

        Returns:
            V5 configuration data
        """
        if "output" not in data or not isinstance(data["output"], dict):
            return data

        old_output = data["output"]

        # Get old values with defaults
        old_format = old_output.get("format", "json")
        old_destination = old_output.get("destination", "return")
        old_file = old_output.get("file", {})
        old_webhook = old_output.get("webhook", {})

        # Build format settings
        format_settings: dict[str, Any] = {"type": old_format}

        # Build handler settings based on destination
        handler_settings: dict[str, Any] = {"type": old_destination}

        if old_destination == "file":
            handler_settings["path"] = old_file.get("path", "output.json")
        elif old_destination == "webhook":
            if old_webhook.get("url"):
                handler_settings["url"] = old_webhook["url"]
            if old_webhook.get("auth_type"):
                handler_settings["auth_type"] = old_webhook["auth_type"]
            if old_webhook.get("token"):
                handler_settings["token"] = old_webhook["token"]
            if old_webhook.get("client_auth_header"):
                handler_settings["client_auth_header"] = old_webhook["client_auth_header"]

        # Determine handler name based on destination
        destination_names = {
            "return": "API Response",
            "file": "File Output",
            "webhook": "Webhook",
            "console": "Console",
        }
        handler_name = destination_names.get(old_destination, "Output")

        # Build new structure with single handler
        data["output"] = {
            "handlers": [
                {
                    "name": handler_name,
                    "format": format_settings,
                    "handler": handler_settings,
                }
            ]
        }

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
        # Import here to avoid circular imports
        from pydantic_settings import InitSettingsSource

        from foxhole_stockpiles.core.settings import (
            MigratingInitSettingsSource,
            Utf8JsonConfigSettingsSource,
        )

        # Replace init_settings with migrating version
        # Get init_kwargs from the init_settings instance
        migrating_init: PydanticBaseSettingsSource
        if isinstance(init_settings, InitSettingsSource):
            migrating_init = MigratingInitSettingsSource(settings_cls, init_settings.init_kwargs)
        else:
            # Fallback to original if not InitSettingsSource
            migrating_init = init_settings

        return (
            migrating_init,
            env_settings,
            dotenv_settings,
            Utf8JsonConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

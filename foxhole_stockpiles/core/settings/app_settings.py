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

        # Future migrations would go here:
        # if version == 2:
        #     data = cls._migrate_v2_to_v3(data)
        #     data["config_version"] = 3

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

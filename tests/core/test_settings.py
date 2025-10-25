"""Tests for configuration settings module.

This module contains comprehensive tests for the settings system,
including validation, defaults, custom values, environment variable
handling, and file-based configuration loading.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from pydantic_settings import BaseSettings
from pydantic_settings.sources import PydanticBaseSettingsSource

from foxhole_stockpiles.core.settings import AppSettings, get_settings
from foxhole_stockpiles.core.settings.sections.logging import LoggingSettings
from foxhole_stockpiles.core.settings.sections.ocr import OCRSettings
from foxhole_stockpiles.core.settings.sections.output import (
    FileOutputSettings,
    OutputSettings,
    WebhookOutputSettings,
)
from foxhole_stockpiles.core.settings.sections.stockpile_types import StockpileTypesSettings
from foxhole_stockpiles.enums.auth_type import AuthType
from foxhole_stockpiles.enums.output_destination import OutputDestination
from foxhole_stockpiles.enums.output_format import OutputFormat


class TestLoggingSettings:
    """Test cases for LoggingSettings.

    This class contains tests for the LoggingSettings configuration model,
    including default values, custom configurations, and validation.
    """

    def test_logging_settings_defaults(self) -> None:
        """Test default logging settings.

        Verifies that LoggingSettings initializes with the correct default values
        for all configuration parameters.
        """
        settings = LoggingSettings()

        assert settings.loggers == {}
        assert settings.log_level == "INFO"
        assert settings.log_format == "[%(asctime)s] %(levelname)s [%(name)s] %(message)s"
        assert settings.date_format == "%Y-%m-%d %H:%M:%S"
        assert settings.rotate_logs is False
        assert settings.log_file is None

    def test_logging_settings_custom_values(self) -> None:
        """Test logging settings with custom values.

        Verifies that LoggingSettings properly accepts and stores custom
        configuration values for all parameters.
        """
        custom_loggers = {"foxhole_stockpiles": "DEBUG", "uvicorn": "WARNING"}

        settings = LoggingSettings(
            loggers=custom_loggers,
            log_level="DEBUG",
            log_format="%(levelname)s: %(message)s",
            date_format="%Y-%m-%d",
            rotate_logs=True,
            log_file="app.log",
        )

        assert settings.loggers == custom_loggers
        assert settings.log_level == "DEBUG"
        assert settings.log_format == "%(levelname)s: %(message)s"
        assert settings.date_format == "%Y-%m-%d"
        assert settings.rotate_logs is True
        assert settings.log_file == "app.log"

    def test_logging_settings_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden in logging settings.

        Verifies that LoggingSettings rejects unknown fields according to
        Pydantic's extra='forbid' configuration.
        """
        with pytest.raises(ValidationError) as exc_info:
            LoggingSettings(log_level="DEBUG", unknown_field="ignored")  # type: ignore[call-arg]

        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestOCRSettings:
    """Test cases for OCRSettings.

    This class contains tests for the OCRSettings configuration model,
    including default values, custom configurations, and validation.
    """

    def test_ocr_settings_defaults(self) -> None:
        """Test default OCR settings.

        Verifies that OCRSettings initializes with the correct default values
        for all OCR-related configuration parameters.
        """
        settings = OCRSettings()

        assert settings.height == 2160
        assert settings.box_width == 84
        assert settings.box_height == 64
        assert settings.column_offset == 112
        assert settings.row_offset == 78
        assert settings.group_offset == 98

    def test_ocr_settings_custom_values(self) -> None:
        """Test OCR settings with custom values.

        Verifies that OCRSettings properly accepts and stores custom
        configuration values for all OCR parameters.
        """
        settings = OCRSettings(
            height=1080,
            box_width=100,
            box_height=80,
            column_offset=120,
            row_offset=85,
            group_offset=105,
        )

        assert settings.height == 1080
        assert settings.box_width == 100
        assert settings.box_height == 80
        assert settings.column_offset == 120
        assert settings.row_offset == 85
        assert settings.group_offset == 105

    def test_ocr_settings_validation_positive_values(self) -> None:
        """Test that OCR settings validate positive values."""
        with pytest.raises(ValidationError) as exc_info:
            OCRSettings(height=0)

        assert "greater than 0" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            OCRSettings(box_width=-1)

        assert "greater than 0" in str(exc_info.value)


class TestFileOutputSettings:
    """Test cases for FileOutputSettings."""

    def test_file_output_defaults(self) -> None:
        """Test default file output settings."""
        settings = FileOutputSettings()
        assert settings.path == "output.json"

    def test_file_output_custom_path(self) -> None:
        """Test file output with custom path."""
        settings = FileOutputSettings(path="custom.txt")
        assert settings.path == "custom.txt"


class TestWebhookOutputSettings:
    """Test cases for WebhookOutputSettings."""

    def test_webhook_output_defaults(self) -> None:
        """Test default webhook output settings."""
        settings = WebhookOutputSettings()
        assert settings.url is None
        assert settings.auth_type is None
        assert settings.token is None
        assert settings.client_auth_header is None

    def test_webhook_output_custom_values(self) -> None:
        """Test webhook output with custom values."""
        settings = WebhookOutputSettings(
            url="https://example.com/webhook",
            auth_type=AuthType.BEARER,
            token="secret_token",
        )
        assert settings.url == "https://example.com/webhook"
        assert settings.auth_type == AuthType.BEARER
        assert settings.token == "secret_token"

    def test_webhook_auth_bearer_validation(self) -> None:
        """Test bearer auth validation."""
        # Should fail when bearer auth_type is provided without token
        with pytest.raises(ValidationError) as exc_info:
            WebhookOutputSettings(auth_type=AuthType.BEARER)
        assert "token must be set when auth_type is 'bearer'" in str(exc_info.value)

        # Should pass when bearer and token are provided
        settings = WebhookOutputSettings(auth_type=AuthType.BEARER, token="token")
        assert settings.auth_type == AuthType.BEARER
        assert settings.token == "token"

    def test_webhook_auth_forward_validation(self) -> None:
        """Test forward auth validation."""
        # Should fail when forward auth_type is provided without client header
        with pytest.raises(ValidationError) as exc_info:
            WebhookOutputSettings(auth_type=AuthType.FORWARD)
        assert "client_auth_header must be set when auth_type is 'forward'" in str(exc_info.value)

        # Should pass when forward and client_auth_header are provided
        settings = WebhookOutputSettings(auth_type=AuthType.FORWARD, client_auth_header="X-Auth")
        assert settings.auth_type == AuthType.FORWARD
        assert settings.client_auth_header == "X-Auth"


class TestOutputSettings:
    """Test cases for OutputSettings."""

    def test_output_settings_defaults(self) -> None:
        """Test default output settings."""
        settings = OutputSettings()
        assert settings.format == OutputFormat.JSON
        assert settings.destination == OutputDestination.RETURN
        assert settings.file.path == "output.json"
        assert settings.webhook.url is None
        assert settings.webhook.auth_type is None
        assert settings.webhook.token is None
        assert settings.webhook.client_auth_header is None

    def test_output_settings_webhook_destination(self) -> None:
        """Test webhook destination validation."""
        # Should fail when webhook destination is used without URL
        with pytest.raises(ValidationError) as exc_info:
            OutputSettings(destination=OutputDestination.WEBHOOK)
        assert "webhook.url must be provided when destination is 'webhook'" in str(exc_info.value)

        # Should pass when URL is provided
        settings = OutputSettings(
            destination=OutputDestination.WEBHOOK,
            webhook=WebhookOutputSettings(url="https://example.com/webhook"),
        )
        assert settings.webhook.url == "https://example.com/webhook"

    def test_output_settings_file_destination(self) -> None:
        """Test file destination validation."""
        # Should fail when file destination is used without path
        with pytest.raises(ValidationError) as exc_info:
            OutputSettings(
                destination=OutputDestination.FILE,
                file=FileOutputSettings(path=""),
            )
        assert "file.path must be provided when destination is 'file'" in str(exc_info.value)

        # Should pass when path is provided
        settings = OutputSettings(
            destination=OutputDestination.FILE,
            file=FileOutputSettings(path="output.json"),
        )
        assert settings.file.path == "output.json"

    def test_output_settings_preconfigure_all_destinations(self) -> None:
        """Test that all destinations can be pre-configured."""
        # All destinations configured, only webhook is active and validated
        settings = OutputSettings(
            destination=OutputDestination.WEBHOOK,
            file=FileOutputSettings(path="/backup/output.json"),
            webhook=WebhookOutputSettings(
                url="https://example.com/webhook",
                auth_type=AuthType.BEARER,
                token="token123",
            ),
        )
        assert settings.destination == OutputDestination.WEBHOOK
        assert settings.file.path == "/backup/output.json"  # Pre-configured but not active
        assert settings.webhook.url == "https://example.com/webhook"  # Active and validated


class TestStockpileTypesSettings:
    """Test cases for StockpileTypesSettings."""

    def test_stockpile_types_defaults(self) -> None:
        """Test default stockpile types settings."""
        settings = StockpileTypesSettings()

        # Test some default values
        assert "Encampment" in settings.encampment
        assert "Campement" in settings.encampment
        assert "Keep" in settings.keep
        assert "Place Forte" in settings.keep
        assert "Safe House" in settings.safe_house
        assert "Seaport" in settings.seaport
        assert "Relic Base" in settings.relic_base
        assert "Undefined" in settings.undefined

    def test_stockpile_types_custom_values(self) -> None:
        """Test stockpile types with custom values."""
        settings = StockpileTypesSettings(
            encampment=["Custom Encampment"],
            keep=["Custom Keep"],
            safe_house=["Custom Safe House"],
            seaport=["Custom Seaport"],
            relic_base=["Custom Relic Base"],
            undefined=["Custom Undefined"],
        )

        assert settings.encampment == ["Custom Encampment"]
        assert settings.keep == ["Custom Keep"]
        assert settings.safe_house == ["Custom Safe House"]
        assert settings.seaport == ["Custom Seaport"]
        assert settings.relic_base == ["Custom Relic Base"]
        assert settings.undefined == ["Custom Undefined"]


class TestConfigMigration:
    """Test cases for config version migration."""

    def test_migrate_v1_to_v2_with_output_format(self) -> None:
        """Test migration from v1 (flat output) to v2 (nested output)."""
        # V1 config with old flat structure
        v1_config = {
            "output_format": {
                "output_format": "json",
                "output_destination": "webhook",
                "file_path": "/tmp/output.json",
                "webhook_url": "https://example.com/webhook",
                "webhook_auth_type": "bearer",
                "webhook_token": "secret123",
                "webhook_client_auth_header": "X-API-TOKEN",
            }
        }

        # Should auto-migrate to v2
        settings = AppSettings(**v1_config)  # type: ignore[arg-type]

        # Verify migration occurred
        assert settings.config_version == 2
        assert settings.output.destination == OutputDestination.WEBHOOK
        assert settings.output.file.path == "/tmp/output.json"
        assert settings.output.webhook.url == "https://example.com/webhook"
        assert settings.output.webhook.auth_type == AuthType.BEARER
        assert settings.output.webhook.token == "secret123"
        assert settings.output.webhook.client_auth_header == "X-API-TOKEN"

    def test_v2_config_no_migration_needed(self) -> None:
        """Test that v2 configs load without migration."""
        import warnings

        # V2 config with nested structure
        v2_config = {
            "config_version": 2,
            "output": {
                "format": "json",
                "destination": "file",
                "file": {"path": "/custom/output.json"},
                "webhook": {"url": None},
            },
        }

        # Mock the settings sources to avoid loading from ~/.fs_config

        def mock_settings_customise_sources(
            cls: type[BaseSettings],
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
        ) -> tuple[PydanticBaseSettingsSource, ...]:
            # Only use init_settings (passed kwargs), ignore config file
            return (init_settings,)

        # Suppress the expected warning about json_file not being used
        # (we're intentionally not loading from file in this test)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Config key.*json_file.*will be ignored")
            with patch.object(
                AppSettings, "settings_customise_sources", mock_settings_customise_sources
            ):
                settings = AppSettings(**v2_config)  # type: ignore[arg-type]

        # Should remain v2
        assert settings.config_version == 2
        assert settings.output.destination == OutputDestination.FILE
        assert settings.output.file.path == "/custom/output.json"

    def test_default_config_is_v2(self) -> None:
        """Test that default config is version 2."""
        settings = AppSettings()
        assert settings.config_version == 2

    def test_migrate_v1_to_v2_with_scanner_fields_cleanup(self) -> None:
        """Test migration removes deprecated scanner fields."""
        # V1 config with old scanner fields that should be removed
        v1_config = {
            "output_format": {
                "output_format": "json",
                "output_destination": "return",
            },
            "scanner": {
                "database_path": None,
                "confidence_threshold": 0.8,  # Should be removed
                "confidence_by_resolution": {"1080p": 0.85, "720p": 0.75},  # Should be removed
                "early_exit_threshold": 0.95,
            },
        }

        # Should auto-migrate to v2 and remove deprecated fields
        settings = AppSettings(**v1_config)  # type: ignore[arg-type]

        # Verify migration occurred
        assert settings.config_version == 2
        # Verify deprecated fields are not in scanner settings
        assert not hasattr(settings.scanner, "confidence_threshold")
        assert not hasattr(settings.scanner, "confidence_by_resolution")
        # Verify valid fields remain
        assert settings.scanner.early_exit_threshold == 0.95

    def test_migrate_config_with_non_dict_data(self) -> None:
        """Test that migration guard clause returns non-dict data unchanged."""
        # The method has a guard clause for non-dict data (defensive programming)
        # In practice, this should never happen since validators check before calling
        result = AppSettings._apply_migrations(None)  # type: ignore[arg-type]
        assert result is None


class TestAppSettings:
    """Test cases for main AppSettings class."""

    def test_app_settings_defaults(self) -> None:
        """Test default app settings."""
        settings = AppSettings()

        assert isinstance(settings.logging, LoggingSettings)
        assert isinstance(settings.ocr, OCRSettings)
        assert isinstance(settings.output, OutputSettings)
        assert isinstance(settings.stockpile_types, StockpileTypesSettings)
        # scanner field should exist
        assert hasattr(settings, "scanner")

    def test_app_settings_custom_values(self) -> None:
        """Test app settings with custom values."""
        import warnings

        # Mock settings sources to avoid loading from ~/.fs_config
        def mock_settings_customise_sources(
            cls: type[BaseSettings],
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
        ) -> tuple[PydanticBaseSettingsSource, ...]:
            # Only use init_settings (passed kwargs), ignore file and env
            return (init_settings,)

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Config key.*json_file.*will be ignored")
            with patch.object(
                AppSettings, "settings_customise_sources", mock_settings_customise_sources
            ):
                settings = AppSettings(
                    logging=LoggingSettings(log_level="DEBUG", rotate_logs=True),
                    ocr=OCRSettings(height=1080, box_width=100),
                    output=OutputSettings(
                        destination=OutputDestination.FILE,
                        file=FileOutputSettings(path="custom.txt"),
                    ),
                )

        assert settings.logging.log_level == "DEBUG"
        assert settings.logging.rotate_logs is True
        assert settings.ocr.height == 1080
        assert settings.ocr.box_width == 100
        assert settings.output.destination == OutputDestination.FILE
        assert settings.output.file.path == "custom.txt"

    def test_app_settings_nested_configuration(self) -> None:
        """Test app settings with nested configuration."""
        settings = AppSettings(
            logging=LoggingSettings(log_level="DEBUG", rotate_logs=True),
            ocr=OCRSettings(height=1080, box_width=100),
            stockpile_types=StockpileTypesSettings(encampment=["Custom Encampment"]),
        )

        assert settings.logging.log_level == "DEBUG"
        assert settings.logging.rotate_logs is True
        assert settings.ocr.height == 1080
        assert settings.ocr.box_width == 100
        assert settings.stockpile_types.encampment == ["Custom Encampment"]

    def test_app_settings_from_environment_variables(self) -> None:
        """Test loading app settings from environment variables."""
        import warnings

        env_vars = {
            "FS_OUTPUT__DESTINATION": "file",
            "FS_OUTPUT__FILE__PATH": "env.txt",
            "FS_OCR__BOX_WIDTH": "100",
            "FS_LOGGING__LOG_LEVEL": "WARNING",
        }

        # Mock settings sources to use env but not file
        def mock_settings_customise_sources(
            cls: type[BaseSettings],
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
        ) -> tuple[PydanticBaseSettingsSource, ...]:
            # Use env_settings and init_settings, but not file
            return (init_settings, env_settings)

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Config key.*json_file.*will be ignored")
            with patch.dict(os.environ, env_vars, clear=True):
                with patch.object(
                    AppSettings, "settings_customise_sources", mock_settings_customise_sources
                ):
                    settings = AppSettings()

                    assert settings.output.destination == OutputDestination.FILE
                    assert settings.output.file.path == "env.txt"
                    assert settings.ocr.box_width == 100
                    assert settings.logging.log_level == "WARNING"


class TestGetSettings:
    """Test cases for get_settings function."""

    def test_get_settings_singleton(self) -> None:
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_get_settings_caching(self) -> None:
        """Test that get_settings uses LRU cache."""
        # Clear the cache first
        get_settings.cache_clear()

        # Call multiple times and verify same instance
        settings1 = get_settings()
        settings2 = get_settings()
        settings3 = get_settings()

        assert settings1 is settings2 is settings3

        # Check cache info
        cache_info = get_settings.cache_info()
        assert cache_info.hits >= 2
        assert cache_info.misses == 1

    def test_get_settings_cache_clear(self) -> None:
        """Test clearing the settings cache."""
        settings1 = get_settings()
        get_settings.cache_clear()
        settings2 = get_settings()

        # After clearing cache, we should get a new instance
        assert settings1 is not settings2
        assert isinstance(settings1, type(settings2))

    def test_get_settings_returns_app_settings(self) -> None:
        """Test that get_settings returns AppSettings instance."""
        settings = get_settings()
        assert isinstance(settings, AppSettings)
        assert hasattr(settings, "logging")
        assert hasattr(settings, "ocr")
        assert hasattr(settings, "output")
        assert hasattr(settings, "stockpile_types")

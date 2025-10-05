"""Tests for configuration settings module.

This module contains comprehensive tests for the settings system,
including validation, defaults, custom values, environment variable
handling, and file-based configuration loading.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from foxhole_stockpiles.core.settings import (
    AppSettings,
    LoggingSettings,
    OCRSettings,
    OutputFormatSettings,
    StockpileTypesSettings,
    get_settings,
)
from foxhole_stockpiles.enums.auth_type import AuthType
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

    def test_logging_settings_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored in logging settings.

        Verifies that LoggingSettings ignores unknown fields according to
        Pydantic's extra='ignore' configuration.
        """
        settings = LoggingSettings(log_level="DEBUG", unknown_field="ignored")  # type: ignore[call-arg]

        assert settings.log_level == "DEBUG"
        assert not hasattr(settings, "unknown_field")


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


class TestOutputFormatSettings:
    """Test cases for OutputFormatSettings."""

    def test_output_format_settings_defaults(self) -> None:
        """Test default output format settings."""
        settings = OutputFormatSettings()

        assert settings.output_format == OutputFormat.JSON
        assert settings.file_path == "output.json"
        assert settings.webhook_auth_type is None
        assert settings.webhook_token is None
        assert settings.webhook_url is None
        assert settings.webhook_client_auth_header is None

    def test_output_format_settings_custom_values(self) -> None:
        """Test output format settings with custom values."""
        settings = OutputFormatSettings(
            output_format=OutputFormat.FILE,
            file_path="custom.txt",
            webhook_url="https://example.com/webhook",
            webhook_auth_type=AuthType.BEARER,
            webhook_token="secret_token",
        )

        assert settings.output_format == OutputFormat.FILE
        assert settings.file_path == "custom.txt"
        assert settings.webhook_url == "https://example.com/webhook"
        assert settings.webhook_auth_type == AuthType.BEARER
        assert settings.webhook_token == "secret_token"

    def test_output_format_webhook_validation(self) -> None:
        """Test webhook validation."""
        # Should fail when webhook format is used without URL
        with pytest.raises(ValidationError) as exc_info:
            OutputFormatSettings(output_format=OutputFormat.WEBHOOK)

        assert "webhook_url must be provided" in str(exc_info.value)

        # Should pass when URL is provided
        settings = OutputFormatSettings(
            output_format=OutputFormat.WEBHOOK, webhook_url="https://example.com/webhook"
        )
        assert settings.webhook_url == "https://example.com/webhook"

    def test_output_format_file_validation(self) -> None:
        """Test file output validation."""
        # Should fail when file format is used without file_path
        with pytest.raises(ValidationError) as exc_info:
            OutputFormatSettings(output_format=OutputFormat.FILE, file_path="")

        assert "file_path must be provided" in str(exc_info.value)

    def test_auth_consistency_validation(self) -> None:
        """Test webhook auth consistency validation."""
        # Should fail when bearer/basic auth_type is provided without token
        with pytest.raises(ValidationError) as exc_info:
            OutputFormatSettings(webhook_auth_type=AuthType.BEARER)

        assert "webhook_token must be set when webhook_auth_type is 'bearer'" in str(exc_info.value)

        # Should fail when forward auth_type is provided without client header
        with pytest.raises(ValidationError) as exc_info:
            OutputFormatSettings(webhook_auth_type=AuthType.FORWARD)

        assert "webhook_client_auth_header must be set when webhook_auth_type is 'forward'" in str(
            exc_info.value
        )

        # Should pass when bearer and token are provided
        settings = OutputFormatSettings(webhook_auth_type=AuthType.BEARER, webhook_token="token")
        assert settings.webhook_auth_type == AuthType.BEARER
        assert settings.webhook_token == "token"

        # Should pass when forward and client_auth_header are provided
        settings = OutputFormatSettings(
            webhook_auth_type=AuthType.FORWARD, webhook_client_auth_header="X-Auth"
        )
        assert settings.webhook_auth_type == AuthType.FORWARD
        assert settings.webhook_client_auth_header == "X-Auth"


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


class TestAppSettings:
    """Test cases for main AppSettings class."""

    def test_app_settings_defaults(self) -> None:
        """Test default app settings."""
        settings = AppSettings()

        assert isinstance(settings.logging, LoggingSettings)
        assert isinstance(settings.ocr, OCRSettings)
        assert isinstance(settings.output_format, OutputFormatSettings)
        assert isinstance(settings.stockpile_types, StockpileTypesSettings)
        # scanner field should exist
        assert hasattr(settings, "scanner")

    def test_app_settings_custom_values(self) -> None:
        """Test app settings with custom values."""
        settings = AppSettings(
            logging=LoggingSettings(log_level="DEBUG", rotate_logs=True),
            ocr=OCRSettings(height=1080, box_width=100),
            output_format=OutputFormatSettings(
                output_format=OutputFormat.FILE, file_path="custom.txt"
            ),
        )

        assert settings.logging.log_level == "DEBUG"
        assert settings.logging.rotate_logs is True
        assert settings.ocr.height == 1080
        assert settings.ocr.box_width == 100
        assert settings.output_format.output_format == OutputFormat.FILE
        assert settings.output_format.file_path == "custom.txt"

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
        env_vars = {
            "FS_OUTPUT_FORMAT__OUTPUT_FORMAT": "file",
            "FS_OUTPUT_FORMAT__FILE_PATH": "env.txt",
            "FS_OCR__BOX_WIDTH": "100",
            "FS_LOGGING__LOG_LEVEL": "WARNING",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = AppSettings()

            assert settings.output_format.output_format == OutputFormat.FILE
            assert settings.output_format.file_path == "env.txt"
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
        assert hasattr(settings, "output_format")
        assert hasattr(settings, "stockpile_types")

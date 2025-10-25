"""Tests for core.logging module.

This module contains comprehensive tests for the logging configuration system,
including various logging levels, file outputs, formatting, and error handling.
"""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from foxhole_stockpiles.core.logging import setup_logging
from foxhole_stockpiles.core.settings.sections.logging import LoggingSettings


@pytest.fixture
def default_logging_settings() -> LoggingSettings:
    """Create default LoggingSettings instance for testing.

    Returns:
        LoggingSettings: A default logging settings instance.
    """
    return LoggingSettings()


class TestSetupLogging:
    """Test suite for the setup_logging function.

    This class contains tests for the logging setup functionality,
    including different handlers, log levels, formats, and file operations.
    """

    def test_default_setup(self, default_logging_settings: LoggingSettings) -> None:
        """Test default logging setup with stdout handler.

        Args:
            default_logging_settings (LoggingSettings): Default logging settings fixture.

        Validates that the default configuration creates a StreamHandler
        with INFO level logging to stdout.
        """
        with patch("logging.basicConfig") as mock_config:
            setup_logging(default_logging_settings)

            mock_config.assert_called_once()
            args, kwargs = mock_config.call_args

            assert kwargs["level"] == "INFO"  # LoggingSettings uses string levels
            assert len(kwargs["handlers"]) == 1
            assert isinstance(kwargs["handlers"][0], logging.StreamHandler)
            assert kwargs["force"] is True
            assert kwargs["format"] == "[%(asctime)s] %(levelname)s [%(name)s] %(message)s"

    def test_custom_log_level(self) -> None:
        """Test setting custom log level.

        Validates that custom log levels are properly applied to the
        logging configuration.
        """
        settings = LoggingSettings(log_level="DEBUG")

        with patch("logging.basicConfig") as mock_config:
            setup_logging(settings)

            args, kwargs = mock_config.call_args
            assert kwargs["level"] == "DEBUG"

    def test_file_logging(self, tmp_path: Path) -> None:
        """Test logging to a file.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        log_file = tmp_path / "test.log"
        settings = LoggingSettings(log_file=str(log_file))

        with patch("logging.basicConfig") as mock_config:
            setup_logging(settings)

            args, kwargs = mock_config.call_args
            assert len(kwargs["handlers"]) == 1
            assert isinstance(kwargs["handlers"][0], logging.FileHandler)

    def test_file_logging_creates_directory(self, tmp_path: Path) -> None:
        """Test that log directory is created if it doesn't exist.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        log_file = tmp_path / "subdir" / "test.log"
        settings = LoggingSettings(log_file=str(log_file))

        with patch("logging.basicConfig") as mock_config:
            setup_logging(settings)

            assert log_file.parent.exists()
            args, kwargs = mock_config.call_args
            assert isinstance(kwargs["handlers"][0], logging.FileHandler)

    def test_file_logging_with_rotation(self, tmp_path: Path) -> None:
        """Test logging to a file with rotation enabled.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        log_file = tmp_path / "test.log"
        settings = LoggingSettings(log_file=str(log_file), rotate_logs=True)

        with patch("logging.basicConfig") as mock_config:
            setup_logging(settings)

            args, kwargs = mock_config.call_args
            assert len(kwargs["handlers"]) == 1
            # Should be TimedRotatingFileHandler when rotation is enabled
            from logging.handlers import TimedRotatingFileHandler

            assert isinstance(kwargs["handlers"][0], TimedRotatingFileHandler)

    def test_custom_format_string(self) -> None:
        """Test setting custom format string.

        Validates that custom format strings are properly applied to
        the logging configuration.
        """
        custom_format = "%(levelname)s: %(message)s"
        settings = LoggingSettings(log_format=custom_format)

        with patch("logging.basicConfig") as mock_config:
            setup_logging(settings)

            args, kwargs = mock_config.call_args
            assert kwargs["format"] == custom_format

    def test_custom_date_format(self) -> None:
        """Test setting custom date format.

        Validates that custom date formats are properly applied to
        the logging configuration.
        """
        custom_date_format = "%Y/%m/%d %H:%M:%S"
        settings = LoggingSettings(date_format=custom_date_format)

        with (
            patch("logging.basicConfig"),
            patch("logging.Formatter") as mock_formatter,
        ):
            setup_logging(settings)

            # Check that Formatter was called with the custom date format
            mock_formatter.assert_called_once_with(
                fmt="[%(asctime)s] %(levelname)s [%(name)s] %(message)s", datefmt=custom_date_format
            )

    def test_all_parameters(self, tmp_path: Path) -> None:
        """Test with all parameters customized.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        log_file = tmp_path / "custom.log"
        custom_format = "%(levelname)s: %(message)s"
        custom_date_format = "%Y/%m/%d %H:%M:%S"

        settings = LoggingSettings(
            log_level="WARNING",
            log_file=str(log_file),
            log_format=custom_format,
            date_format=custom_date_format,
            rotate_logs=True,
        )

        with patch("logging.basicConfig") as mock_config:
            setup_logging(settings)

            args, kwargs = mock_config.call_args
            assert kwargs["level"] == "WARNING"
            assert kwargs["format"] == custom_format
            from logging.handlers import TimedRotatingFileHandler

            assert isinstance(kwargs["handlers"][0], TimedRotatingFileHandler)
            assert kwargs["force"] is True

    def test_empty_log_file_uses_stdout(self) -> None:
        """Test that empty log_file string uses stdout handler.

        Validates that providing an empty string for log_file falls back
        to using a StreamHandler for stdout output.
        """
        settings = LoggingSettings(log_file="")

        with patch("logging.basicConfig") as mock_config:
            setup_logging(settings)

            args, kwargs = mock_config.call_args
            assert isinstance(kwargs["handlers"][0], logging.StreamHandler)

    def test_none_log_file_uses_stdout(self) -> None:
        """Test that None log_file uses stdout handler.

        Validates that providing None for log_file uses a StreamHandler
        for stdout output.
        """
        settings = LoggingSettings(log_file=None)

        with patch("logging.basicConfig") as mock_config:
            setup_logging(settings)

            args, kwargs = mock_config.call_args
            assert isinstance(kwargs["handlers"][0], logging.StreamHandler)

    def test_logger_specific_settings(self) -> None:
        """Test logger-specific settings configuration.

        Validates that logger-specific settings are handled correctly.
        """
        settings = LoggingSettings(loggers={"foxhole_stockpiles": "DEBUG", "uvicorn": "WARNING"})

        with patch("logging.basicConfig") as mock_config:
            setup_logging(settings)

            # The function should still call basicConfig
            mock_config.assert_called_once()

            # Logger-specific settings would be handled elsewhere in the application
            # This test just verifies the settings can be created and passed to setup_logging
            assert settings.loggers == {"foxhole_stockpiles": "DEBUG", "uvicorn": "WARNING"}

    def test_handler_formatter_setup(self, tmp_path: Path) -> None:
        """Test that handler formatter is properly configured.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        log_file = tmp_path / "test.log"
        custom_format = "%(message)s"
        custom_date_format = "%H:%M:%S"

        settings = LoggingSettings(
            log_file=str(log_file), log_format=custom_format, date_format=custom_date_format
        )

        with (
            patch("logging.basicConfig"),
            patch("logging.Formatter") as mock_formatter,
            patch("logging.FileHandler.setFormatter") as mock_set_formatter,
        ):
            setup_logging(settings)

            # Verify formatter was created with correct parameters
            mock_formatter.assert_called_once_with(fmt=custom_format, datefmt=custom_date_format)

            # Verify setFormatter was called on the handler
            mock_set_formatter.assert_called_once()

"""Tests for core.logging module.

This module contains comprehensive tests for the logging configuration system,
including various logging levels, file outputs, formatting, and error handling.
"""

import logging
from collections.abc import Generator
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import pytest

from foxhole_stockpiles.core.logging import (
    APP_FILE_HANDLER_NAME,
    APP_STREAM_HANDLER_NAME,
    QT_GUI_HANDLER_NAME,
    _get_handler_by_name,
    _remove_handler_by_name,
    setup_logging,
)
from foxhole_stockpiles.core.settings.sections.logging import LoggingSettings


@pytest.fixture
def default_logging_settings() -> LoggingSettings:
    """Create default LoggingSettings instance for testing.

    Returns:
        LoggingSettings: A default logging settings instance.
    """
    return LoggingSettings()


@pytest.fixture
def clean_root_logger() -> Generator[logging.Logger, None, None]:
    """Get root logger and clean up app handlers before/after test.

    Yields:
        logging.Logger: The root logger with app handlers removed.
    """
    root_logger = logging.getLogger()
    # Remove app handlers before test
    _remove_handler_by_name(root_logger, APP_STREAM_HANDLER_NAME)
    _remove_handler_by_name(root_logger, APP_FILE_HANDLER_NAME)

    yield root_logger

    # Clean up after test
    _remove_handler_by_name(root_logger, APP_STREAM_HANDLER_NAME)
    _remove_handler_by_name(root_logger, APP_FILE_HANDLER_NAME)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_handler_by_name_found(self) -> None:
        """Test finding a handler by name."""
        logger = logging.getLogger("test_get_handler")
        handler = logging.StreamHandler()
        handler.set_name("test_handler")
        logger.addHandler(handler)

        result = _get_handler_by_name(logger, "test_handler")
        assert result is handler

        # Cleanup
        logger.removeHandler(handler)

    def test_get_handler_by_name_not_found(self) -> None:
        """Test that None is returned when handler not found."""
        logger = logging.getLogger("test_get_handler_not_found")
        result = _get_handler_by_name(logger, "nonexistent")
        assert result is None

    def test_remove_handler_by_name(self) -> None:
        """Test removing a handler by name."""
        logger = logging.getLogger("test_remove_handler")
        handler = logging.StreamHandler()
        handler.set_name("to_remove")
        logger.addHandler(handler)

        _remove_handler_by_name(logger, "to_remove")

        assert _get_handler_by_name(logger, "to_remove") is None

    def test_remove_handler_by_name_not_found(self) -> None:
        """Test that removing nonexistent handler doesn't raise."""
        logger = logging.getLogger("test_remove_nonexistent")
        # Should not raise
        _remove_handler_by_name(logger, "nonexistent")


class TestSetupLogging:
    """Test suite for the setup_logging function.

    This class contains tests for the logging setup functionality,
    including different handlers, log levels, formats, and file operations.
    """

    def test_default_setup(
        self, default_logging_settings: LoggingSettings, clean_root_logger: logging.Logger
    ) -> None:
        """Test default logging setup with stdout handler.

        Args:
            default_logging_settings: Default logging settings fixture.
            clean_root_logger: Clean root logger fixture.
        """
        setup_logging(default_logging_settings)

        handler = _get_handler_by_name(clean_root_logger, APP_STREAM_HANDLER_NAME)
        assert handler is not None
        assert isinstance(handler, logging.StreamHandler)
        assert clean_root_logger.level == logging.INFO

    def test_custom_log_level(self, clean_root_logger: logging.Logger) -> None:
        """Test setting custom log level."""
        settings = LoggingSettings(log_level="DEBUG")

        setup_logging(settings)

        assert clean_root_logger.level == logging.DEBUG
        handler = _get_handler_by_name(clean_root_logger, APP_STREAM_HANDLER_NAME)
        assert handler is not None
        assert handler.level == logging.DEBUG

    def test_file_logging(self, tmp_path: Path, clean_root_logger: logging.Logger) -> None:
        """Test logging to a file.

        Args:
            tmp_path: Temporary directory path from pytest fixture.
            clean_root_logger: Clean root logger fixture.
        """
        log_file = tmp_path / "test.log"
        settings = LoggingSettings(log_file=str(log_file))

        setup_logging(settings)

        handler = _get_handler_by_name(clean_root_logger, APP_FILE_HANDLER_NAME)
        assert handler is not None
        assert isinstance(handler, logging.FileHandler)

    def test_file_logging_creates_directory(
        self, tmp_path: Path, clean_root_logger: logging.Logger
    ) -> None:
        """Test that log directory is created if it doesn't exist.

        Args:
            tmp_path: Temporary directory path from pytest fixture.
            clean_root_logger: Clean root logger fixture.
        """
        log_file = tmp_path / "subdir" / "test.log"
        settings = LoggingSettings(log_file=str(log_file))

        setup_logging(settings)

        assert log_file.parent.exists()
        handler = _get_handler_by_name(clean_root_logger, APP_FILE_HANDLER_NAME)
        assert isinstance(handler, logging.FileHandler)

    def test_file_logging_with_rotation(
        self, tmp_path: Path, clean_root_logger: logging.Logger
    ) -> None:
        """Test logging to a file with rotation enabled.

        Args:
            tmp_path: Temporary directory path from pytest fixture.
            clean_root_logger: Clean root logger fixture.
        """
        log_file = tmp_path / "test.log"
        settings = LoggingSettings(log_file=str(log_file), rotate_logs=True)

        setup_logging(settings)

        handler = _get_handler_by_name(clean_root_logger, APP_FILE_HANDLER_NAME)
        assert handler is not None
        assert isinstance(handler, TimedRotatingFileHandler)

    def test_custom_format_string(self, clean_root_logger: logging.Logger) -> None:
        """Test setting custom format string."""
        custom_format = "%(levelname)s: %(message)s"
        settings = LoggingSettings(log_format=custom_format)

        setup_logging(settings)

        handler = _get_handler_by_name(clean_root_logger, APP_STREAM_HANDLER_NAME)
        assert handler is not None
        assert handler.formatter is not None
        assert handler.formatter._fmt == custom_format

    def test_custom_date_format(self, clean_root_logger: logging.Logger) -> None:
        """Test setting custom date format."""
        custom_date_format = "%Y/%m/%d %H:%M:%S"
        settings = LoggingSettings(date_format=custom_date_format)

        setup_logging(settings)

        handler = _get_handler_by_name(clean_root_logger, APP_STREAM_HANDLER_NAME)
        assert handler is not None
        assert handler.formatter is not None
        assert handler.formatter.datefmt == custom_date_format

    def test_all_parameters(self, tmp_path: Path, clean_root_logger: logging.Logger) -> None:
        """Test with all parameters customized.

        Args:
            tmp_path: Temporary directory path from pytest fixture.
            clean_root_logger: Clean root logger fixture.
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

        setup_logging(settings)

        assert clean_root_logger.level == logging.WARNING
        handler = _get_handler_by_name(clean_root_logger, APP_FILE_HANDLER_NAME)
        assert handler is not None
        assert isinstance(handler, TimedRotatingFileHandler)
        assert handler.formatter is not None
        assert handler.formatter._fmt == custom_format
        assert handler.formatter.datefmt == custom_date_format

    def test_empty_log_file_uses_stdout(self, clean_root_logger: logging.Logger) -> None:
        """Test that empty log_file string uses stdout handler."""
        settings = LoggingSettings(log_file="")

        setup_logging(settings)

        handler = _get_handler_by_name(clean_root_logger, APP_STREAM_HANDLER_NAME)
        assert handler is not None
        assert isinstance(handler, logging.StreamHandler)

    def test_none_log_file_uses_stdout(self, clean_root_logger: logging.Logger) -> None:
        """Test that None log_file uses stdout handler."""
        settings = LoggingSettings(log_file=None)

        setup_logging(settings)

        handler = _get_handler_by_name(clean_root_logger, APP_STREAM_HANDLER_NAME)
        assert handler is not None
        assert isinstance(handler, logging.StreamHandler)

    def test_logger_specific_settings(self, clean_root_logger: logging.Logger) -> None:
        """Test logger-specific settings configuration."""
        settings = LoggingSettings(loggers={"foxhole_stockpiles": "DEBUG", "uvicorn": "WARNING"})

        setup_logging(settings)

        # Verify logger-specific levels were set
        assert logging.getLogger("foxhole_stockpiles").level == logging.DEBUG
        assert logging.getLogger("uvicorn").level == logging.WARNING

    def test_handler_formatter_setup(
        self, tmp_path: Path, clean_root_logger: logging.Logger
    ) -> None:
        """Test that handler formatter is properly configured.

        Args:
            tmp_path: Temporary directory path from pytest fixture.
            clean_root_logger: Clean root logger fixture.
        """
        log_file = tmp_path / "test.log"
        custom_format = "%(message)s"
        custom_date_format = "%H:%M:%S"

        settings = LoggingSettings(
            log_file=str(log_file), log_format=custom_format, date_format=custom_date_format
        )

        setup_logging(settings)

        handler = _get_handler_by_name(clean_root_logger, APP_FILE_HANDLER_NAME)
        assert handler is not None
        assert handler.formatter is not None
        assert handler.formatter._fmt == custom_format
        assert handler.formatter.datefmt == custom_date_format

    def test_preserves_qt_handler(self, clean_root_logger: logging.Logger) -> None:
        """Test that Qt GUI handler is preserved when setup_logging is called."""
        # Add a mock Qt handler
        qt_handler = logging.StreamHandler()
        qt_handler.set_name(QT_GUI_HANDLER_NAME)
        clean_root_logger.addHandler(qt_handler)

        settings = LoggingSettings()
        setup_logging(settings)

        # Qt handler should still be there
        preserved_handler = _get_handler_by_name(clean_root_logger, QT_GUI_HANDLER_NAME)
        assert preserved_handler is qt_handler

        # Cleanup
        clean_root_logger.removeHandler(qt_handler)

    def test_replaces_existing_app_handler(self, clean_root_logger: logging.Logger) -> None:
        """Test that existing app handler is replaced on subsequent calls."""
        settings1 = LoggingSettings(log_level="INFO")
        setup_logging(settings1)

        handler1 = _get_handler_by_name(clean_root_logger, APP_STREAM_HANDLER_NAME)
        assert handler1 is not None

        settings2 = LoggingSettings(log_level="DEBUG")
        setup_logging(settings2)

        handler2 = _get_handler_by_name(clean_root_logger, APP_STREAM_HANDLER_NAME)
        assert handler2 is not None
        assert handler2 is not handler1
        assert handler2.level == logging.DEBUG

    def test_no_duplicate_handlers(self, clean_root_logger: logging.Logger) -> None:
        """Test that calling setup_logging multiple times doesn't create duplicates."""
        settings = LoggingSettings()

        setup_logging(settings)
        setup_logging(settings)
        setup_logging(settings)

        # Count handlers with our name
        count = sum(
            1
            for h in clean_root_logger.handlers
            if getattr(h, "name", None) == APP_STREAM_HANDLER_NAME
        )
        assert count == 1

"""Tests for LoggingTab."""

from typing import Any
from unittest.mock import patch

import pytest

from foxhole_stockpiles.core.settings.sections.logging import LoggingSettings
from foxhole_stockpiles.gui.widgets.config_tabs.logging_tab import LoggingTab


@pytest.fixture
def logging_tab(qtbot: Any) -> LoggingTab:
    """Create a LoggingTab instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        LoggingTab: Tab instance
    """
    tab = LoggingTab()
    qtbot.addWidget(tab)
    return tab


def test_logging_tab_initialization(logging_tab: LoggingTab) -> None:
    """Test LoggingTab initialization.

    Args:
        logging_tab: LoggingTab instance
    """
    assert logging_tab.log_level_input is not None
    assert logging_tab.log_format_input is not None
    assert logging_tab.date_format_input is not None
    assert logging_tab.rotate_logs_input is not None
    assert logging_tab.log_file_input is not None


def test_logging_tab_default_values(logging_tab: LoggingTab) -> None:
    """Test default values are set correctly.

    Args:
        logging_tab: LoggingTab instance
    """
    assert logging_tab.log_level_input.currentText() == "INFO"


def test_logging_tab_log_level_options(logging_tab: LoggingTab) -> None:
    """Test log level combo box has correct options.

    Args:
        logging_tab: LoggingTab instance
    """
    levels = [
        logging_tab.log_level_input.itemText(i) for i in range(logging_tab.log_level_input.count())
    ]
    assert "DEBUG" in levels
    assert "INFO" in levels
    assert "WARNING" in levels
    assert "ERROR" in levels
    assert "CRITICAL" in levels


def test_logging_tab_set_values(logging_tab: LoggingTab) -> None:
    """Test setting values from settings object.

    Args:
        logging_tab: LoggingTab instance
    """
    settings = LoggingSettings(
        log_level="DEBUG",
        log_format="%(levelname)s - %(message)s",
        date_format="%Y-%m-%d",
        rotate_logs=True,
        log_file="/var/log/app.log",
    )

    logging_tab.set_values(settings)

    assert logging_tab.log_level_input.currentText() == "DEBUG"
    assert logging_tab.log_format_input.text() == "%(levelname)s - %(message)s"
    assert logging_tab.date_format_input.text() == "%Y-%m-%d"
    assert logging_tab.rotate_logs_input.isChecked()
    assert logging_tab.log_file_input.text() == "/var/log/app.log"


def test_logging_tab_set_values_no_log_file(logging_tab: LoggingTab) -> None:
    """Test setting values with no log file.

    Args:
        logging_tab: LoggingTab instance
    """
    settings = LoggingSettings(log_file=None)

    logging_tab.set_values(settings)

    assert logging_tab.log_file_input.text() == ""


def test_logging_tab_get_values(logging_tab: LoggingTab) -> None:
    """Test getting values from widgets.

    Args:
        logging_tab: LoggingTab instance
    """
    logging_tab.log_level_input.setCurrentText("ERROR")
    logging_tab.log_format_input.setText("%(asctime)s - %(message)s")
    logging_tab.date_format_input.setText("%H:%M:%S")
    logging_tab.rotate_logs_input.setChecked(False)
    logging_tab.log_file_input.setText("/tmp/test.log")

    settings = logging_tab.get_values()

    assert settings.log_level == "ERROR"
    assert settings.log_format == "%(asctime)s - %(message)s"
    assert settings.date_format == "%H:%M:%S"
    assert not settings.rotate_logs
    assert settings.log_file == "/tmp/test.log"


def test_logging_tab_get_values_empty_log_file(logging_tab: LoggingTab) -> None:
    """Test getting values with empty log file.

    Args:
        logging_tab: LoggingTab instance
    """
    logging_tab.log_file_input.setText("")

    settings = logging_tab.get_values()

    assert settings.log_file is None


def test_logging_tab_get_values_whitespace_log_file(logging_tab: LoggingTab) -> None:
    """Test getting values with whitespace-only log file.

    Args:
        logging_tab: LoggingTab instance
    """
    logging_tab.log_file_input.setText("   ")

    settings = logging_tab.get_values()

    # Whitespace should be preserved (validation happens in pydantic)
    assert settings.log_file == "   "


def test_logging_tab_browse_log_file(qtbot: Any, logging_tab: LoggingTab) -> None:
    """Test browse log file button.

    Args:
        qtbot: PyQt test fixture
        logging_tab: LoggingTab instance
    """
    test_path = "/path/to/logfile.log"

    with patch(
        "foxhole_stockpiles.gui.widgets.config_tabs.logging_tab.QFileDialog.getSaveFileName"
    ) as mock_dialog:
        mock_dialog.return_value = (test_path, "Log Files (*.log)")

        logging_tab.browse_log_file()

        assert logging_tab.log_file_input.text() == test_path
        mock_dialog.assert_called_once()


def test_logging_tab_browse_log_file_cancel(qtbot: Any, logging_tab: LoggingTab) -> None:
    """Test browse log file cancel.

    Args:
        qtbot: PyQt test fixture
        logging_tab: LoggingTab instance
    """
    original_text = logging_tab.log_file_input.text()

    with patch(
        "foxhole_stockpiles.gui.widgets.config_tabs.logging_tab.QFileDialog.getSaveFileName"
    ) as mock_dialog:
        mock_dialog.return_value = ("", "")

        logging_tab.browse_log_file()

        # Should not change text
        assert logging_tab.log_file_input.text() == original_text


def test_logging_tab_set_values_default_settings(logging_tab: LoggingTab) -> None:
    """Test setting values with default settings object.

    Args:
        logging_tab: LoggingTab instance
    """
    settings = LoggingSettings()

    logging_tab.set_values(settings)

    assert logging_tab.log_level_input.currentText() == settings.log_level.upper()
    assert logging_tab.log_format_input.text() == settings.log_format
    assert logging_tab.date_format_input.text() == settings.date_format


def test_logging_tab_log_level_case_insensitive(logging_tab: LoggingTab) -> None:
    """Test log level is converted to uppercase.

    Args:
        logging_tab: LoggingTab instance
    """
    settings = LoggingSettings(log_level="debug")

    logging_tab.set_values(settings)

    assert logging_tab.log_level_input.currentText() == "DEBUG"


def test_logging_tab_rotate_logs_checkbox(logging_tab: LoggingTab) -> None:
    """Test rotate logs checkbox behavior.

    Args:
        logging_tab: LoggingTab instance
    """
    logging_tab.rotate_logs_input.setChecked(True)
    assert logging_tab.rotate_logs_input.isChecked()

    logging_tab.rotate_logs_input.setChecked(False)
    assert not logging_tab.rotate_logs_input.isChecked()


def test_logging_tab_all_log_levels_selectable(logging_tab: LoggingTab) -> None:
    """Test all log levels can be selected.

    Args:
        logging_tab: LoggingTab instance
    """
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        logging_tab.log_level_input.setCurrentText(level)
        assert logging_tab.log_level_input.currentText() == level


def test_logging_tab_get_values_preserves_format_strings(logging_tab: LoggingTab) -> None:
    """Test that format strings are preserved exactly.

    Args:
        logging_tab: LoggingTab instance
    """
    custom_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    custom_date = "%Y-%m-%d %H:%M:%S"

    logging_tab.log_format_input.setText(custom_format)
    logging_tab.date_format_input.setText(custom_date)

    settings = logging_tab.get_values()

    assert settings.log_format == custom_format
    assert settings.date_format == custom_date


def test_logging_tab_empty_format_strings(logging_tab: LoggingTab) -> None:
    """Test with empty format strings.

    Args:
        logging_tab: LoggingTab instance
    """
    logging_tab.log_format_input.setText("")
    logging_tab.date_format_input.setText("")

    settings = logging_tab.get_values()

    # Empty strings should be preserved
    assert settings.log_format == ""
    assert settings.date_format == ""

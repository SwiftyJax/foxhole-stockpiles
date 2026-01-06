"""Tests for MainWindow."""

from typing import Any
from unittest.mock import patch

import pytest
from PyQt6.QtWidgets import QMenuBar

from foxhole_stockpiles.gui.windows.main_window import MainWindow


@pytest.fixture
def window(qtbot: Any) -> MainWindow:
    """Create a MainWindow instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        MainWindow: Window instance
    """
    with patch("foxhole_stockpiles.gui.widgets.server_control_panel.ScannerClient"):
        window = MainWindow()
        qtbot.addWidget(window)
        return window


def test_window_initialization(window: MainWindow) -> None:
    """Test MainWindow initialization.

    Args:
        window (MainWindow): Window instance
    """
    assert "FS (Foxhole Stockpiles)" in window.windowTitle()
    assert window.server_panel is not None
    assert window.centralWidget() == window.server_panel


def test_window_has_menu_bar(window: MainWindow) -> None:
    """Test MainWindow has menu bar.

    Args:
        window (MainWindow): Window instance
    """
    menu_bar = window.menuBar()
    assert menu_bar is not None
    assert isinstance(menu_bar, QMenuBar)


def test_window_file_menu_exists(window: MainWindow) -> None:
    """Test File menu exists.

    Args:
        window (MainWindow): Window instance
    """
    menu_bar = window.menuBar()
    assert menu_bar is not None
    actions = menu_bar.actions()

    file_menu_found = False
    for action in actions:
        if action.text() == "&File":
            file_menu_found = True
            break

    assert file_menu_found


def test_window_help_menu_exists(window: MainWindow) -> None:
    """Test Help menu exists.

    Args:
        window (MainWindow): Window instance
    """
    menu_bar = window.menuBar()
    assert menu_bar is not None
    actions = menu_bar.actions()

    help_menu_found = False
    for action in actions:
        if action.text() == "&Help":
            help_menu_found = True
            break

    assert help_menu_found


def test_window_show_configuration(qtbot: Any, window: MainWindow) -> None:
    """Test showing configuration window.

    Args:
        qtbot: PyQt test fixture
        window (MainWindow): Window instance
    """
    with patch("foxhole_stockpiles.gui.windows.main_window.ConfigWindow") as mock_config_class:
        mock_config = mock_config_class.return_value

        window.show_configuration()

        mock_config_class.assert_called_once_with(window)
        mock_config.setWindowModality.assert_called_once()
        mock_config.show.assert_called_once()


def test_window_show_about(qtbot: Any, window: MainWindow) -> None:
    """Test showing about dialog.

    Args:
        qtbot: PyQt test fixture
        window (MainWindow): Window instance
    """
    with patch("foxhole_stockpiles.gui.windows.main_window.QMessageBox.about") as mock_about:
        window.show_about()

        mock_about.assert_called_once()
        call_args = mock_about.call_args
        assert call_args[0][0] == window
        assert call_args[0][1] == "About FS"
        assert "Foxhole Stockpiles" in call_args[0][2]


def test_window_show_icon_import(qtbot: Any, window: MainWindow) -> None:
    """Test showing icon import window.

    Args:
        qtbot: PyQt test fixture
        window (MainWindow): Window instance
    """
    with patch("foxhole_stockpiles.gui.windows.main_window.IconImportWindow") as mock_import_class:
        mock_import = mock_import_class.return_value

        window.show_icon_import()

        mock_import_class.assert_called_once_with(window)
        mock_import.setWindowModality.assert_called_once()
        mock_import.show.assert_called_once()


def test_window_show_database_info_with_config(qtbot: Any, window: MainWindow) -> None:
    """Test showing database info window with configured database.

    Args:
        qtbot: PyQt test fixture
        window (MainWindow): Window instance
    """
    with patch("foxhole_stockpiles.gui.windows.main_window.AppSettings") as mock_settings_class:
        mock_settings = mock_settings_class.return_value
        mock_settings.scanner.database_path = "/path/to/db.h5"

        with patch(
            "foxhole_stockpiles.gui.windows.main_window.DatabaseInfoWindow"
        ) as mock_info_class:
            mock_info = mock_info_class.return_value

            window.show_database_info()

            mock_info_class.assert_called_once_with(window, initial_db_path="/path/to/db.h5")
            mock_info.exec.assert_called_once()


def test_window_show_database_info_no_config(qtbot: Any, window: MainWindow) -> None:
    """Test showing database info window without configured database.

    Args:
        qtbot: PyQt test fixture
        window (MainWindow): Window instance
    """
    with patch(
        "foxhole_stockpiles.gui.windows.main_window.AppSettings", side_effect=Exception("No config")
    ):
        with patch(
            "foxhole_stockpiles.gui.windows.main_window.DatabaseInfoWindow"
        ) as mock_info_class:
            mock_info = mock_info_class.return_value

            window.show_database_info()

            mock_info_class.assert_called_once_with(window, initial_db_path=None)
            mock_info.exec.assert_called_once()


def test_window_scan_screenshot(qtbot: Any, window: MainWindow) -> None:
    """Test scanning screenshot from menu.

    Args:
        qtbot: PyQt test fixture
        window (MainWindow): Window instance
    """
    with patch.object(window.server_panel, "scan_screenshot_from_menu") as mock_scan:
        window.scan_screenshot()

        mock_scan.assert_called_once()


def test_window_quit_application(qtbot: Any, window: MainWindow) -> None:
    """Test quitting application.

    Args:
        qtbot: PyQt test fixture
        window (MainWindow): Window instance
    """
    from PyQt6.QtWidgets import QApplication

    with patch.object(QApplication, "quit") as mock_quit:
        window.quit_application()

        mock_quit.assert_called_once()

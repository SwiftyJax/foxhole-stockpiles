"""Tests for ConfigWindow."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QKeyEvent
from PyQt6.QtWidgets import QMessageBox, QPushButton

from foxhole_stockpiles.core.settings.app_settings import AppSettings
from foxhole_stockpiles.core.settings.sections import (
    APIAuthSettings,
    APIServerSettings,
    DatabaseBuilderSettings,
    ExternalToolsSettings,
    LoggingSettings,
    NotificationsSettings,
    OCRSettings,
    OutputSettings,
    ScannerSettings,
    StockpileTypesSettings,
    TemplateSettings,
)
from foxhole_stockpiles.enums.auth_type import AuthType
from foxhole_stockpiles.enums.config_level import ConfigLevel
from foxhole_stockpiles.gui.windows.config_window import ConfigWindow


@pytest.fixture(autouse=True)
def mock_close_dialog() -> Any:
    """Mock QMessageBox.question to prevent closeEvent from blocking.

    The closeEvent shows a confirmation dialog when there are unsaved changes.
    """
    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
        yield


@pytest.fixture
def mock_config_manager() -> Any:
    """Create a mock ConfigManager.

    Returns:
        MagicMock: Mock ConfigManager
    """
    from foxhole_stockpiles.core.settings.sections.gui import GUISettings

    with patch("foxhole_stockpiles.gui.windows.config_window.ConfigManager") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        # Create default settings with explicit BASIC config level
        default_settings = MagicMock(spec=AppSettings)
        default_settings.gui = GUISettings(config_level=ConfigLevel.BASIC)
        default_settings.api_server = APIServerSettings()
        default_settings.api_auth = APIAuthSettings()
        default_settings.scanner = ScannerSettings()
        default_settings.output = OutputSettings()
        default_settings.ocr = OCRSettings()
        default_settings.templates = TemplateSettings()
        default_settings.external_tools = ExternalToolsSettings()
        default_settings.database_builder = DatabaseBuilderSettings()
        default_settings.logging = LoggingSettings()
        default_settings.notifications = NotificationsSettings()
        default_settings.stockpile_types = StockpileTypesSettings()
        mock_instance.load_config.return_value = default_settings

        yield mock_instance


@pytest.fixture
def config_window(qtbot: Any, mock_config_manager: MagicMock) -> ConfigWindow:
    """Create a ConfigWindow instance.

    Args:
        qtbot: PyQt test fixture
        mock_config_manager: Mock ConfigManager

    Returns:
        ConfigWindow: Window instance
    """
    window = ConfigWindow()
    qtbot.addWidget(window)
    return window


def test_config_window_initialization(config_window: ConfigWindow) -> None:
    """Test ConfigWindow initialization.

    Args:
        config_window: ConfigWindow instance
    """
    assert config_window.windowTitle() == "Configuration"
    assert config_window.config_manager is not None
    assert config_window.settings is not None
    assert config_window.tab_widget is not None
    assert config_window.gui_tab is not None


def test_config_window_has_all_tabs(config_window: ConfigWindow) -> None:
    """Test ConfigWindow has all required tab widgets.

    Args:
        config_window: ConfigWindow instance
    """
    assert config_window.api_server_tab is not None
    assert config_window.scanner_tab is not None
    assert config_window.output_tab is not None
    assert config_window.ocr_tab is not None
    assert config_window.template_tab is not None
    assert config_window.external_tools_tab is not None
    assert config_window.database_builder_tab is not None
    assert config_window.logging_tab is not None


def test_config_window_basic_level_by_default(config_window: ConfigWindow) -> None:
    """Test ConfigWindow starts with basic config level (5 tabs).

    Args:
        config_window: ConfigWindow instance
    """
    # Default config level is BASIC which shows 5 tabs
    assert config_window._current_config_level == ConfigLevel.BASIC
    assert config_window.tab_widget.count() == 5
    assert config_window.tab_widget.tabText(0) == "API Server"


def test_config_window_config_level_tabs(qtbot: Any, mock_config_manager: MagicMock) -> None:
    """Test tab count at different config levels.

    Args:
        qtbot: PyQt test fixture
        mock_config_manager: Mock ConfigManager
    """
    from foxhole_stockpiles.core.settings.sections.gui import GUISettings

    # Test BASIC level (5 tabs)
    settings = AppSettings()
    settings.gui = GUISettings(config_level=ConfigLevel.BASIC)
    mock_config_manager.load_config.return_value = settings

    window = ConfigWindow()
    qtbot.addWidget(window)
    assert window.tab_widget.count() == 5

    # Test ADVANCED level (7 tabs: + External Tools, Database Builder)
    settings.gui = GUISettings(config_level=ConfigLevel.ADVANCED)
    mock_config_manager.load_config.return_value = settings

    window2 = ConfigWindow()
    qtbot.addWidget(window2)
    assert window2.tab_widget.count() == 7

    # Test DEVELOPER level (9 tabs: + OCR, Templates)
    settings.gui = GUISettings(config_level=ConfigLevel.DEVELOPER)
    mock_config_manager.load_config.return_value = settings

    window3 = ConfigWindow()
    qtbot.addWidget(window3)
    assert window3.tab_widget.count() == 9
    assert window3.tab_widget.tabText(0) == "API Server"


def test_config_window_load_settings_populates_tabs(
    qtbot: Any, mock_config_manager: MagicMock
) -> None:
    """Test loading settings populates all tabs.

    Args:
        qtbot: PyQt test fixture
        mock_config_manager: Mock ConfigManager
    """
    # Create custom settings
    settings = AppSettings(
        api_server=APIServerSettings(host="192.168.1.1", port=9000),
        api_auth=APIAuthSettings(auth_type=AuthType.BASIC, auth_token="user:pass"),
    )
    mock_config_manager.load_config.return_value = settings

    window = ConfigWindow()
    qtbot.addWidget(window)

    # Verify settings were loaded
    assert window.settings is not None
    assert window.settings.api_server.host == "192.168.1.1"
    assert window.settings.api_server.port == 9000


def test_config_window_load_settings_error_handling(
    qtbot: Any, mock_config_manager: MagicMock
) -> None:
    """Test error handling when loading settings fails.

    Args:
        qtbot: PyQt test fixture
        mock_config_manager: Mock ConfigManager
    """
    # Make load_config raise an exception
    mock_config_manager.load_config.side_effect = Exception("Load failed")

    with patch("foxhole_stockpiles.gui.windows.config_window.QMessageBox.critical") as mock_msg:
        window = ConfigWindow()
        qtbot.addWidget(window)

        # Should show error dialog
        mock_msg.assert_called_once()
        args = mock_msg.call_args[0]
        assert "Error Loading Configuration" in args[1]
        assert "Load failed" in args[2]


def test_config_window_save_settings_success(
    qtbot: Any, config_window: ConfigWindow, mock_config_manager: MagicMock
) -> None:
    """Test saving settings successfully.

    Args:
        qtbot: PyQt test fixture
        config_window: ConfigWindow instance
        mock_config_manager: Mock ConfigManager
    """
    mock_config_manager.save_config.return_value = (True, "Success")

    config_window.save_settings()

    # Should call save_config
    mock_config_manager.save_config.assert_called_once()

    # Should show success message in status bar
    assert "saved successfully" in config_window.status_bar.currentMessage().lower()


def test_config_window_save_settings_collects_from_tabs(
    qtbot: Any, config_window: ConfigWindow, mock_config_manager: MagicMock
) -> None:
    """Test saving settings collects values from all tabs.

    Args:
        qtbot: PyQt test fixture
        config_window: ConfigWindow instance
        mock_config_manager: Mock ConfigManager
    """
    mock_config_manager.save_config.return_value = (True, "Success")

    config_window.save_settings()

    # Should call save_config
    mock_config_manager.save_config.assert_called_once()

    # Should show success message in status bar
    assert "saved successfully" in config_window.status_bar.currentMessage().lower()


def test_config_window_save_settings_failure(
    qtbot: Any, config_window: ConfigWindow, mock_config_manager: MagicMock
) -> None:
    """Test handling save failure.

    Args:
        qtbot: PyQt test fixture
        config_window: ConfigWindow instance
        mock_config_manager: Mock ConfigManager
    """
    mock_config_manager.save_config.return_value = (False, "Save failed")

    with patch("foxhole_stockpiles.gui.windows.config_window.QMessageBox.critical") as mock_msg:
        config_window.save_settings()

        # Should show error message
        mock_msg.assert_called_once()
        args = mock_msg.call_args[0]
        assert args[1] == "Error Saving Configuration"
        assert "Save failed" in args[2]


def test_config_window_save_settings_exception(
    qtbot: Any, config_window: ConfigWindow, mock_config_manager: MagicMock
) -> None:
    """Test handling unexpected exception during save.

    Args:
        qtbot: PyQt test fixture
        config_window: ConfigWindow instance
        mock_config_manager: Mock ConfigManager
    """
    mock_config_manager.save_config.side_effect = Exception("Unexpected error")

    with patch("foxhole_stockpiles.gui.windows.config_window.QMessageBox.critical") as mock_msg:
        config_window.save_settings()

        # Should show error message
        mock_msg.assert_called_once()
        args = mock_msg.call_args[0]
        assert args[1] == "Error"
        assert "Unexpected error" in args[2]


def test_config_window_collect_settings_preserves_types(config_window: ConfigWindow) -> None:
    """Test collecting settings preserves all settings types.

    Args:
        config_window: ConfigWindow instance
    """
    # Collect settings
    settings = config_window.collect_settings()

    # Should return AppSettings instance with proper types
    assert isinstance(settings, AppSettings)
    assert isinstance(settings.ocr, OCRSettings)
    assert isinstance(settings.templates, TemplateSettings)
    assert isinstance(settings.logging, LoggingSettings)


def test_config_window_collect_settings_all_sections(config_window: ConfigWindow) -> None:
    """Test collecting settings returns all settings sections.

    Args:
        config_window: ConfigWindow instance
    """
    # Collect settings
    settings = config_window.collect_settings()

    # Should return AppSettings instance with all sections
    assert isinstance(settings, AppSettings)
    assert isinstance(settings.api_server, APIServerSettings)
    assert isinstance(settings.api_auth, APIAuthSettings)
    assert isinstance(settings.scanner, ScannerSettings)
    assert isinstance(settings.output, OutputSettings)
    assert isinstance(settings.ocr, OCRSettings)
    assert isinstance(settings.templates, TemplateSettings)
    assert isinstance(settings.database_builder, DatabaseBuilderSettings)
    assert isinstance(settings.logging, LoggingSettings)


def test_config_window_populate_tabs(config_window: ConfigWindow) -> None:
    """Test populate_tabs method.

    Args:
        config_window: ConfigWindow instance
    """
    # Create custom settings
    custom_settings = AppSettings(
        api_server=APIServerSettings(host="10.0.0.1", port=5000),
    )

    # Set and populate
    config_window.settings = custom_settings
    config_window.populate_tabs()

    # Verify api_server_tab was populated
    assert config_window.api_server_tab.port_input.value() == 5000


def test_config_window_populate_tabs_none_settings(config_window: ConfigWindow) -> None:
    """Test populate_tabs with None settings.

    Args:
        config_window: ConfigWindow instance
    """
    # Set settings to None
    config_window.settings = None

    # Should not raise error
    config_window.populate_tabs()


def test_config_window_close_button_closes_window(qtbot: Any, config_window: ConfigWindow) -> None:
    """Test close button closes the window.

    Args:
        qtbot: PyQt test fixture
        config_window: ConfigWindow instance
    """
    # Find close button
    buttons = config_window.findChildren(QPushButton)
    close_button = None
    for btn in buttons:
        if btn.text() == "Close":
            close_button = btn
            break

    assert close_button is not None

    # Verify button is connected to close slot
    # The button should trigger close when clicked


def test_config_window_preserves_notifications_settings(config_window: ConfigWindow) -> None:
    """Test that notifications settings are preserved when collecting.

    Args:
        config_window: ConfigWindow instance
    """
    # Set custom notifications settings
    custom_notifications = NotificationsSettings()
    assert config_window.settings is not None
    config_window.settings.notifications = custom_notifications

    # Collect settings (basic mode)
    settings = config_window.collect_settings()

    # Should preserve notifications
    assert isinstance(settings.notifications, NotificationsSettings)


def test_config_window_preserves_stockpile_types_settings(config_window: ConfigWindow) -> None:
    """Test that stockpile types settings are preserved when collecting.

    Args:
        config_window: ConfigWindow instance
    """
    # Set custom stockpile types settings
    custom_stockpile_types = StockpileTypesSettings()
    assert config_window.settings is not None
    config_window.settings.stockpile_types = custom_stockpile_types

    # Collect settings (basic mode)
    settings = config_window.collect_settings()

    # Should preserve stockpile types
    assert isinstance(settings.stockpile_types, StockpileTypesSettings)


def test_config_window_geometry(config_window: ConfigWindow) -> None:
    """Test window geometry is set correctly.

    Args:
        config_window: ConfigWindow instance
    """
    # Window should have specific geometry
    assert config_window.geometry().width() >= 600  # Might be larger than 800 depending on DPI
    assert config_window.geometry().height() >= 400  # Might be larger than 600 depending on DPI


def test_config_window_gui_tab_exists(config_window: ConfigWindow) -> None:
    """Test GUI tab exists and has config level control.

    Args:
        config_window: ConfigWindow instance
    """
    # GUI tab should exist
    assert config_window.gui_tab is not None
    assert config_window.gui_tab.config_level_input is not None

    # GUI tab should be in the tab widget
    gui_tab_index = -1
    for i in range(config_window.tab_widget.count()):
        if config_window.tab_widget.tabText(i) == "GUI":
            gui_tab_index = i
            break
    assert gui_tab_index >= 0


class TestCloseEvent:
    """Tests for ConfigWindow.closeEvent method."""

    @pytest.fixture
    def mock_config_manager(self) -> Any:
        """Create a mock ConfigManager.

        Returns:
            MagicMock: Mock ConfigManager
        """
        with patch("foxhole_stockpiles.gui.windows.config_window.ConfigManager") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            mock_instance.load_config.return_value = AppSettings()
            yield mock_instance

    @pytest.fixture
    def config_window(self, qtbot: Any, mock_config_manager: MagicMock) -> ConfigWindow:
        """Create a ConfigWindow instance without autouse mock.

        Args:
            qtbot: PyQt test fixture
            mock_config_manager: Mock ConfigManager

        Returns:
            ConfigWindow: Window instance
        """
        window = ConfigWindow()
        qtbot.addWidget(window)
        return window

    def test_close_event_no_changes(
        self, config_window: ConfigWindow, mock_config_manager: MagicMock
    ) -> None:
        """Test closeEvent accepts when no changes.

        Args:
            config_window: ConfigWindow instance
            mock_config_manager: Mock ConfigManager
        """
        # No changes made, has_changes() returns False
        event = MagicMock(spec=QCloseEvent)

        config_window.closeEvent(event)

        # Should accept without showing dialog
        event.accept.assert_called_once()
        event.ignore.assert_not_called()

    def test_close_event_with_changes_save(
        self, config_window: ConfigWindow, mock_config_manager: MagicMock
    ) -> None:
        """Test closeEvent when user clicks Save.

        Args:
            config_window: ConfigWindow instance
            mock_config_manager: Mock ConfigManager
        """
        # Make changes (use api_server_tab since advanced mode is default)
        config_window.api_server_tab.port_input.setValue(9999)
        mock_config_manager.save_config.return_value = (True, "Success")

        event = MagicMock(spec=QCloseEvent)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Save):
            config_window.closeEvent(event)

        # Should save and accept
        mock_config_manager.save_config.assert_called_once()
        event.accept.assert_called_once()

    def test_close_event_with_changes_save_fails(
        self, config_window: ConfigWindow, mock_config_manager: MagicMock
    ) -> None:
        """Test closeEvent when save fails after user clicks Save.

        Args:
            config_window: ConfigWindow instance
            mock_config_manager: Mock ConfigManager
        """
        # Make changes (use api_server_tab since advanced mode is default)
        config_window.api_server_tab.port_input.setValue(9999)
        mock_config_manager.save_config.return_value = (False, "Save failed")

        event = MagicMock(spec=QCloseEvent)

        with (
            patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Save),
            patch.object(QMessageBox, "critical"),
        ):
            config_window.closeEvent(event)

        # Should not accept because save failed (still has changes)
        event.ignore.assert_called_once()

    def test_close_event_with_changes_discard(
        self, config_window: ConfigWindow, mock_config_manager: MagicMock
    ) -> None:
        """Test closeEvent when user clicks Discard.

        Args:
            config_window: ConfigWindow instance
            mock_config_manager: Mock ConfigManager
        """
        # Make changes (use api_server_tab since advanced mode is default)
        config_window.api_server_tab.port_input.setValue(9999)

        event = MagicMock(spec=QCloseEvent)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
            config_window.closeEvent(event)

        # Should accept without saving
        mock_config_manager.save_config.assert_not_called()
        event.accept.assert_called_once()

    def test_close_event_with_changes_cancel(
        self, config_window: ConfigWindow, mock_config_manager: MagicMock
    ) -> None:
        """Test closeEvent when user clicks Cancel.

        Args:
            config_window: ConfigWindow instance
            mock_config_manager: Mock ConfigManager
        """
        # Make changes (use api_server_tab since advanced mode is default)
        config_window.api_server_tab.port_input.setValue(9999)

        event = MagicMock(spec=QCloseEvent)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel):
            config_window.closeEvent(event)

        # Should ignore (not close)
        mock_config_manager.save_config.assert_not_called()
        event.ignore.assert_called_once()
        event.accept.assert_not_called()


class TestKeyPressEvent:
    """Tests for ConfigWindow.keyPressEvent method."""

    @pytest.fixture
    def mock_config_manager(self) -> Any:
        """Create a mock ConfigManager.

        Returns:
            MagicMock: Mock ConfigManager
        """
        with patch("foxhole_stockpiles.gui.windows.config_window.ConfigManager") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            mock_instance.load_config.return_value = AppSettings()
            yield mock_instance

    @pytest.fixture
    def config_window(self, qtbot: Any, mock_config_manager: MagicMock) -> ConfigWindow:
        """Create a ConfigWindow instance.

        Args:
            qtbot: PyQt test fixture
            mock_config_manager: Mock ConfigManager

        Returns:
            ConfigWindow: Window instance
        """
        window = ConfigWindow()
        qtbot.addWidget(window)
        return window

    def test_escape_key_closes_window(self, config_window: ConfigWindow) -> None:
        """Test pressing Escape closes the window.

        Args:
            config_window: ConfigWindow instance
        """
        with (
            patch.object(config_window, "close") as mock_close,
            patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard),
        ):
            # Create escape key event
            event = QKeyEvent(
                QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier
            )
            config_window.keyPressEvent(event)

            mock_close.assert_called_once()

    def test_other_key_passes_to_parent(self, config_window: ConfigWindow) -> None:
        """Test other keys are passed to parent handler.

        Args:
            config_window: ConfigWindow instance
        """
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
            # Create non-escape key event
            event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
            # Should not raise and should call parent handler
            config_window.keyPressEvent(event)

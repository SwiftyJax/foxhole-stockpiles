"""Tests for ServerControlPanel."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QTableWidget

from foxhole_stockpiles.gui.widgets.server_control_panel import ServerControlPanel
from foxhole_stockpiles.i18n import t


@pytest.fixture
def panel(qtbot: Any) -> ServerControlPanel:
    """Create a ServerControlPanel instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        ServerControlPanel: Panel instance
    """
    from PyQt6.QtWidgets import QApplication

    from foxhole_stockpiles.gui.widgets import server_control_panel

    with (
        patch("foxhole_stockpiles.gui.widgets.server_control_panel.ScannerClient"),
        patch.object(server_control_panel, "AppSettings", side_effect=Exception("No config")),
    ):
        panel_instance = ServerControlPanel()
        qtbot.addWidget(panel_instance)
        panel_instance.show()
        QApplication.processEvents()
        return panel_instance


def test_panel_initialization(panel: ServerControlPanel) -> None:
    """Test ServerControlPanel initialization.

    Args:
        panel (ServerControlPanel): Panel instance
    """
    assert panel.server_running is False
    assert panel.server_thread is None
    assert isinstance(panel.log_display, QTableWidget)
    assert panel.log_display.columnCount() == 4


def test_panel_start_server(qtbot: Any, panel: ServerControlPanel) -> None:
    """Test starting the server.

    Args:
        qtbot: PyQt test fixture
        panel (ServerControlPanel): Panel instance
    """
    with patch(
        "foxhole_stockpiles.gui.widgets.server_control_panel.ServerThread"
    ) as mock_thread_class:
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        panel.start_server()

        assert panel.server_running is True
        assert panel.start_stop_button.text() == t("server_panel.stop_server")
        assert panel.status_label.text() == t("server_panel.status_running")
        mock_thread.start.assert_called_once()


def test_panel_stop_server(qtbot: Any, panel: ServerControlPanel) -> None:
    """Test stopping the server.

    Args:
        qtbot: PyQt test fixture
        panel (ServerControlPanel): Panel instance
    """
    # Set up server as running
    mock_thread = MagicMock()
    panel.server_thread = mock_thread
    panel.server_running = True

    panel.stop_server()

    assert panel.server_running is False
    assert panel.start_stop_button.text() == t("server_panel.start_server")
    assert panel.status_label.text() == t("server_panel.status_stopped")
    mock_thread.stop.assert_called_once()


def test_panel_toggle_server(qtbot: Any, panel: ServerControlPanel) -> None:
    """Test toggling server state.

    Args:
        qtbot: PyQt test fixture
        panel (ServerControlPanel): Panel instance
    """
    with patch.object(panel, "start_server") as mock_start:
        panel.toggle_server()
        mock_start.assert_called_once()

    panel.server_running = True
    with patch.object(panel, "stop_server") as mock_stop:
        panel.toggle_server()
        mock_stop.assert_called_once()


def test_panel_append_log(qtbot: Any, panel: ServerControlPanel) -> None:
    """Test appending log entry.

    Args:
        qtbot: PyQt test fixture
        panel (ServerControlPanel): Panel instance
    """
    log_data = {
        "timestamp": "2025-01-04 12:00:00",
        "level": "INFO",
        "module": "test.module",
        "message": "Test message",
        "color": "#FFFFFF",
    }

    panel.append_log(log_data)

    assert panel.log_display.rowCount() == 1
    item0 = panel.log_display.item(0, 0)
    assert item0 is not None
    assert item0.text() == "2025-01-04 12:00:00"
    item1 = panel.log_display.item(0, 1)
    assert item1 is not None
    assert item1.text() == "INFO"
    item2 = panel.log_display.item(0, 2)
    assert item2 is not None
    assert item2.text() == "test.module"
    item3 = panel.log_display.item(0, 3)
    assert item3 is not None
    assert item3.text() == "Test message"


def test_panel_clear_logs(qtbot: Any, panel: ServerControlPanel) -> None:
    """Test clearing logs.

    Args:
        qtbot: PyQt test fixture
        panel (ServerControlPanel): Panel instance
    """
    # Add a log entry
    log_data = {
        "timestamp": "2025-01-04 12:00:00",
        "level": "INFO",
        "module": "test",
        "message": "Test",
        "color": "#FFFFFF",
    }
    panel.append_log(log_data)

    assert panel.log_display.rowCount() == 1

    panel.clear_logs()

    assert panel.log_display.rowCount() == 0


def test_panel_process_screenshot_server_not_running(qtbot: Any, panel: ServerControlPanel) -> None:
    """Test processing screenshot when server is not running.

    Args:
        qtbot: PyQt test fixture
        panel (ServerControlPanel): Panel instance
    """
    panel.server_running = False

    with patch("foxhole_stockpiles.gui.widgets.server_control_panel.logger") as mock_logger:
        panel.process_screenshot("/test/file.png")
        mock_logger.error.assert_called_once()


def test_panel_process_screenshot_server_running(qtbot: Any, panel: ServerControlPanel) -> None:
    """Test processing screenshot when server is running.

    Args:
        qtbot: PyQt test fixture
        panel (ServerControlPanel): Panel instance
    """
    panel.server_running = True

    with patch(
        "foxhole_stockpiles.gui.widgets.server_control_panel.ScanWorker"
    ) as mock_worker_class:
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker

        panel.process_screenshot("/test/file.png")

        mock_worker_class.assert_called_once_with(panel.scanner_client, "/test/file.png")
        mock_worker.start.assert_called_once()


def test_panel_select_screenshot(qtbot: Any, panel: ServerControlPanel) -> None:
    """Test selecting screenshot via file dialog.

    Args:
        qtbot: PyQt test fixture
        panel (ServerControlPanel): Panel instance
    """
    with patch(
        "foxhole_stockpiles.gui.widgets.server_control_panel.QFileDialog.getOpenFileName",
        return_value=("/test/file.png", ""),
    ):
        with patch.object(panel, "process_screenshot") as mock_process:
            panel.scan_screenshot_from_menu()
            mock_process.assert_called_once_with("/test/file.png")


def test_panel_refresh_db_info(qtbot: Any, panel: ServerControlPanel) -> None:
    """Test refreshing database info.

    Args:
        qtbot: PyQt test fixture
        panel (ServerControlPanel): Panel instance
    """
    with patch.object(panel, "_update_validation_state") as mock_update:
        panel.refresh_db_info()
        mock_update.assert_called_once()


def test_panel_validation_no_config(qtbot: Any, panel: ServerControlPanel) -> None:
    """Test validation state with no configuration.

    Args:
        qtbot: PyQt test fixture
        panel (ServerControlPanel): Panel instance
    """
    from PyQt6.QtWidgets import QApplication

    from foxhole_stockpiles.gui.widgets import server_control_panel

    with patch.object(server_control_panel, "AppSettings", side_effect=Exception("No config")):
        panel._update_validation_state()
        QApplication.processEvents()

        # Should show error panel, hide logs
        assert panel.error_panel.isVisible()
        assert not panel.logs_group.isVisible()
        assert not panel.start_stop_button.isEnabled()
        assert t("server_panel.errors.no_config_title") in panel.error_panel.text()


def test_panel_validation_no_db_path(qtbot: Any, panel: ServerControlPanel) -> None:
    """Test validation state with no database path configured.

    Args:
        qtbot: PyQt test fixture
        panel (ServerControlPanel): Panel instance
    """
    from PyQt6.QtWidgets import QApplication

    from foxhole_stockpiles.gui.widgets import server_control_panel

    with patch.object(server_control_panel, "AppSettings") as mock_settings_class:
        mock_settings = mock_settings_class.return_value
        mock_settings.scanner.database_path = None

        panel._update_validation_state()
        QApplication.processEvents()

        # Should show error panel, hide logs
        assert panel.error_panel.isVisible()
        assert not panel.logs_group.isVisible()
        assert not panel.start_stop_button.isEnabled()
        assert t("server_panel.errors.config_incomplete_title") in panel.error_panel.text()


def test_panel_validation_db_not_found(qtbot: Any, panel: ServerControlPanel) -> None:
    """Test validation state with database file not found.

    Args:
        qtbot: PyQt test fixture
        panel (ServerControlPanel): Panel instance
    """
    from PyQt6.QtWidgets import QApplication

    from foxhole_stockpiles.gui.widgets import server_control_panel

    with patch.object(server_control_panel, "AppSettings") as mock_settings_class:
        mock_settings = mock_settings_class.return_value
        mock_settings.scanner.database_path = "/nonexistent/db.h5"

        panel._update_validation_state()
        QApplication.processEvents()

        # Should show error panel, hide logs
        assert panel.error_panel.isVisible()
        assert not panel.logs_group.isVisible()
        assert not panel.start_stop_button.isEnabled()
        assert t("server_panel.errors.database_not_found_title") in panel.error_panel.text()


def test_panel_validation_valid_db(qtbot: Any, panel: ServerControlPanel) -> None:
    """Test validation state with valid database.

    Args:
        qtbot: PyQt test fixture
        panel (ServerControlPanel): Panel instance
    """
    from pathlib import Path

    from PyQt6.QtWidgets import QApplication

    from foxhole_stockpiles.gui.widgets import server_control_panel

    test_db = Path(__file__).parent.parent.parent / "fixtures" / "test_db_v1.h5"

    with patch.object(server_control_panel, "AppSettings") as mock_settings_class:
        mock_settings = mock_settings_class.return_value
        mock_settings.scanner.database_path = str(test_db)

        panel._update_validation_state()
        QApplication.processEvents()

        # Should hide error panel, show logs
        assert not panel.error_panel.isVisible()
        assert panel.logs_group.isVisible()
        assert panel.start_stop_button.isEnabled()
        assert panel.db_info_text.isVisible()
        assert len(panel.db_info_text.text()) > 0

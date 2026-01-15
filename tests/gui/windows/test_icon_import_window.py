"""Tests for IconImportWindow."""

from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QMimeData, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QMessageBox

from foxhole_stockpiles.core.settings.app_settings import AppSettings
from foxhole_stockpiles.core.settings.sections.database_builder import DatabaseBuilderSettings
from foxhole_stockpiles.gui.utils.icon_import_worker import IconImportWorker
from foxhole_stockpiles.gui.windows.icon_import_window import IconImportWindow


# Prevent any GUI dialogs from appearing during test cleanup
@pytest.fixture(autouse=True)
def prevent_dialog_on_close() -> Generator[None, None, None]:
    """Prevent dialogs during window cleanup."""
    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        yield


@pytest.fixture
def mock_configured_settings(tmp_path: Path) -> AppSettings:
    """Create mock settings with proper configuration.

    Args:
        tmp_path: Temporary directory path

    Returns:
        AppSettings: Mock settings with all required tools configured
    """
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text("{}")

    extractor_tool = tmp_path / "repak.exe"
    extractor_tool.write_text("")

    converter_tool = tmp_path / "umodel.exe"
    converter_tool.write_text("")

    return AppSettings(
        database_builder=DatabaseBuilderSettings(
            extractor_tool=extractor_tool,
            converter_tool=converter_tool,
            catalog_file=catalog_file,
        ),
    )


@pytest.fixture
def mock_unconfigured_settings() -> AppSettings:
    """Create mock settings without configuration.

    Returns:
        AppSettings: Mock settings with missing tools
    """
    return AppSettings(
        database_builder=DatabaseBuilderSettings(),
    )


@pytest.fixture
def configured_window(
    qtbot: Any, mock_configured_settings: AppSettings
) -> Generator[IconImportWindow, None, None]:
    """Create a configured IconImportWindow instance.

    Args:
        qtbot: PyQt test fixture
        mock_configured_settings: Mock configured settings

    Yields:
        IconImportWindow: Window instance
    """
    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.get_settings",
        return_value=mock_configured_settings,
    ):
        window = IconImportWindow()
        qtbot.addWidget(window)
        yield window
        # Cleanup: stop any running workers
        if window.import_worker and window.import_worker.isRunning():
            window.import_worker.stop()
            window.import_worker.wait()


@pytest.fixture
def unconfigured_window(
    qtbot: Any, mock_unconfigured_settings: AppSettings
) -> Generator[IconImportWindow, None, None]:
    """Create an unconfigured IconImportWindow instance.

    Args:
        qtbot: PyQt test fixture
        mock_unconfigured_settings: Mock unconfigured settings

    Yields:
        IconImportWindow: Window instance
    """
    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.get_settings",
        return_value=mock_unconfigured_settings,
    ):
        window = IconImportWindow()
        qtbot.addWidget(window)
        yield window
        # Cleanup: stop any running workers
        if window.import_worker and window.import_worker.isRunning():
            window.import_worker.stop()
            window.import_worker.wait()


# ===== Initialization Tests =====


def test_icon_import_window_initialization_configured(configured_window: IconImportWindow) -> None:
    """Test IconImportWindow initialization when configured.

    Args:
        configured_window: Configured window instance
    """
    assert configured_window.windowTitle() == "Build Database"
    assert configured_window.is_configured is True
    assert configured_window.import_worker is None
    assert configured_window.mod_pak_files == []
    assert configured_window.vanilla_pak_file is None
    assert configured_window.log_handler is not None


def test_icon_import_window_initialization_unconfigured(
    unconfigured_window: IconImportWindow,
) -> None:
    """Test IconImportWindow initialization when not configured.

    Args:
        unconfigured_window: Unconfigured window instance
    """
    assert unconfigured_window.windowTitle() == "Build Database"
    assert unconfigured_window.is_configured is False


def test_icon_import_window_widgets_exist(configured_window: IconImportWindow) -> None:
    """Test that all required widgets exist.

    Args:
        configured_window: Configured window instance
    """
    assert configured_window.vanilla_pak_display is not None
    assert configured_window.mod_pak_list_widget is not None
    assert configured_window.mod_name_input is not None
    assert configured_window.overwrite_checkbox is not None
    assert configured_window.start_button is not None
    assert configured_window.cancel_button is not None
    assert configured_window.log_display is not None


def test_icon_import_window_cancel_button_disabled(configured_window: IconImportWindow) -> None:
    """Test cancel button is disabled initially.

    Args:
        configured_window: Configured window instance
    """
    assert configured_window.cancel_button.isEnabled() is False


# ===== Configuration Check Tests =====


def test_check_configuration_all_present(tmp_path: Path) -> None:
    """Test configuration check when all tools are present.

    Args:
        tmp_path: Temporary directory path
    """
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text("{}")

    extractor_tool = tmp_path / "repak.exe"
    extractor_tool.write_text("")

    converter_tool = tmp_path / "umodel.exe"
    converter_tool.write_text("")

    settings = AppSettings(
        database_builder=DatabaseBuilderSettings(
            extractor_tool=extractor_tool,
            converter_tool=converter_tool,
            catalog_file=catalog_file,
        ),
    )

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.get_settings", return_value=settings
    ):
        window = IconImportWindow()
        assert window._check_configuration() is True


def test_check_configuration_missing_extractor(tmp_path: Path) -> None:
    """Test configuration check when extractor tool is missing.

    Args:
        tmp_path: Temporary directory path
    """
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text("{}")

    converter_tool = tmp_path / "umodel.exe"
    converter_tool.write_text("")

    settings = AppSettings(
        database_builder=DatabaseBuilderSettings(
            extractor_tool=None,
            converter_tool=converter_tool,
            catalog_file=catalog_file,
        ),
    )

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.get_settings", return_value=settings
    ):
        window = IconImportWindow()
        assert window._check_configuration() is False


def test_check_configuration_missing_converter(tmp_path: Path) -> None:
    """Test configuration check when converter tool is missing.

    Args:
        tmp_path: Temporary directory path
    """
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text("{}")

    extractor_tool = tmp_path / "repak.exe"
    extractor_tool.write_text("")

    settings = AppSettings(
        database_builder=DatabaseBuilderSettings(
            extractor_tool=extractor_tool,
            converter_tool=None,
            catalog_file=catalog_file,
        ),
    )

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.get_settings", return_value=settings
    ):
        window = IconImportWindow()
        assert window._check_configuration() is False


def test_check_configuration_missing_catalog(tmp_path: Path) -> None:
    """Test configuration check when catalog file is missing.

    Args:
        tmp_path: Temporary directory path
    """
    extractor_tool = tmp_path / "repak.exe"
    extractor_tool.write_text("")

    converter_tool = tmp_path / "umodel.exe"
    converter_tool.write_text("")

    settings = AppSettings(
        database_builder=DatabaseBuilderSettings(
            extractor_tool=extractor_tool,
            converter_tool=converter_tool,
            catalog_file=None,
        ),
    )

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.get_settings", return_value=settings
    ):
        window = IconImportWindow()
        assert window._check_configuration() is False


def test_check_configuration_file_not_exists(tmp_path: Path) -> None:
    """Test configuration check when files don't exist.

    Args:
        tmp_path: Temporary directory path
    """
    settings = AppSettings(
        database_builder=DatabaseBuilderSettings(
            extractor_tool=Path("/nonexistent/repak.exe"),
            converter_tool=Path("/nonexistent/umodel.exe"),
            catalog_file=Path("/nonexistent/catalog.json"),
        ),
    )

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.get_settings", return_value=settings
    ):
        window = IconImportWindow()
        assert window._check_configuration() is False


# ===== PAK File Management Tests =====


def test_add_mod_pak_files(qtbot: Any, configured_window: IconImportWindow, tmp_path: Path) -> None:
    """Test adding PAK files via file dialog.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
        tmp_path: Temporary directory path
    """
    test_pak1 = str(tmp_path / "test1.pak")
    test_pak2 = str(tmp_path / "test2.pak")

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QFileDialog.getOpenFileNames"
    ) as mock_dialog:
        mock_dialog.return_value = ([test_pak1, test_pak2], "PAK Files (*.pak)")

        configured_window.add_mod_pak_files()

        assert configured_window.mod_pak_files == [test_pak1, test_pak2]
        assert configured_window.mod_pak_list_widget.count() == 2
        item0 = configured_window.mod_pak_list_widget.item(0)
        item1 = configured_window.mod_pak_list_widget.item(1)
        assert item0 is not None and item0.text() == test_pak1
        assert item1 is not None and item1.text() == test_pak2


def test_add_mod_pak_files_no_duplicates(
    qtbot: Any, configured_window: IconImportWindow, tmp_path: Path
) -> None:
    """Test adding duplicate PAK files doesn't duplicate entries.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
        tmp_path: Temporary directory path
    """
    test_pak = str(tmp_path / "test.pak")

    # Add once
    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QFileDialog.getOpenFileNames"
    ) as mock_dialog:
        mock_dialog.return_value = ([test_pak], "PAK Files (*.pak)")
        configured_window.add_mod_pak_files()

    # Try to add again
    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QFileDialog.getOpenFileNames"
    ) as mock_dialog:
        mock_dialog.return_value = ([test_pak], "PAK Files (*.pak)")
        configured_window.add_mod_pak_files()

    # Should still be only one entry
    assert len(configured_window.mod_pak_files) == 1
    assert configured_window.mod_pak_list_widget.count() == 1


def test_add_mod_pak_files_cancel(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test canceling add PAK files dialog.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QFileDialog.getOpenFileNames"
    ) as mock_dialog:
        mock_dialog.return_value = ([], "")

        configured_window.add_mod_pak_files()

        assert configured_window.mod_pak_files == []
        assert configured_window.mod_pak_list_widget.count() == 0


def test_remove_selected_paks(
    qtbot: Any, configured_window: IconImportWindow, tmp_path: Path
) -> None:
    """Test removing selected PAK files.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
        tmp_path: Temporary directory path
    """
    test_pak1 = str(tmp_path / "test1.pak")
    test_pak2 = str(tmp_path / "test2.pak")

    # Add files
    configured_window.mod_pak_files = [test_pak1, test_pak2]
    configured_window.mod_pak_list_widget.addItem(test_pak1)
    configured_window.mod_pak_list_widget.addItem(test_pak2)

    # Select first item
    item0 = configured_window.mod_pak_list_widget.item(0)
    assert item0 is not None
    item0.setSelected(True)

    # Remove
    configured_window.remove_selected_mod_paks()

    # Only second should remain
    assert configured_window.mod_pak_files == [test_pak2]
    assert configured_window.mod_pak_list_widget.count() == 1
    remaining_item = configured_window.mod_pak_list_widget.item(0)
    assert remaining_item is not None and remaining_item.text() == test_pak2


def test_clear_all_paks(qtbot: Any, configured_window: IconImportWindow, tmp_path: Path) -> None:
    """Test clearing all PAK files.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
        tmp_path: Temporary directory path
    """
    test_pak1 = str(tmp_path / "test1.pak")
    test_pak2 = str(tmp_path / "test2.pak")

    # Add files
    configured_window.mod_pak_files = [test_pak1, test_pak2]
    configured_window.mod_pak_list_widget.addItem(test_pak1)
    configured_window.mod_pak_list_widget.addItem(test_pak2)

    # Clear
    configured_window.clear_all_mod_paks()

    assert configured_window.mod_pak_files == []
    assert configured_window.mod_pak_list_widget.count() == 0


# ===== Drag and Drop Tests =====


def test_pak_drag_enter_event(configured_window: IconImportWindow) -> None:
    """Test drag enter event accepts drags.

    Args:
        configured_window: Configured window instance
    """
    mock_event = MagicMock(spec=QDragEnterEvent)
    configured_window.pak_drag_enter_event(mock_event)
    mock_event.accept.assert_called_once()


def test_pak_drag_enter_event_none(configured_window: IconImportWindow) -> None:
    """Test drag enter event with None event.

    Args:
        configured_window: Configured window instance
    """
    # Should not raise exception
    configured_window.pak_drag_enter_event(None)


def test_pak_drop_event(configured_window: IconImportWindow, tmp_path: Path) -> None:
    """Test drop event adds PAK files.

    Args:
        configured_window: Configured window instance
        tmp_path: Temporary directory path
    """
    test_pak = str(tmp_path / "test.pak")

    # Create mock drop event
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(test_pak)])

    mock_event = MagicMock(spec=QDropEvent)
    mock_event.mimeData.return_value = mime_data

    configured_window.pak_drop_event(mock_event)

    assert test_pak in configured_window.mod_pak_files
    assert configured_window.mod_pak_list_widget.count() == 1
    mock_event.accept.assert_called_once()


def test_pak_drop_event_non_pak_file(configured_window: IconImportWindow, tmp_path: Path) -> None:
    """Test drop event ignores non-PAK files.

    Args:
        configured_window: Configured window instance
        tmp_path: Temporary directory path
    """
    test_txt = str(tmp_path / "test.txt")

    # Create mock drop event
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(test_txt)])

    mock_event = MagicMock(spec=QDropEvent)
    mock_event.mimeData.return_value = mime_data

    configured_window.pak_drop_event(mock_event)

    assert configured_window.mod_pak_files == []
    assert configured_window.mod_pak_list_widget.count() == 0


def test_pak_drop_event_none(configured_window: IconImportWindow) -> None:
    """Test drop event with None event.

    Args:
        configured_window: Configured window instance
    """
    # Should not raise exception
    configured_window.pak_drop_event(None)


# ===== Validation Tests =====


def test_validate_inputs_no_mod_pak_files(configured_window: IconImportWindow) -> None:
    """Test validation fails when no mod PAK files are added.

    Args:
        configured_window: Configured window instance
    """
    configured_window.mod_name_input.setText("test_mod")

    is_valid, error_msg = configured_window.validate_inputs()

    assert is_valid is False
    assert "at least one mod PAK file" in error_msg


def test_validate_inputs_no_mod_name(configured_window: IconImportWindow) -> None:
    """Test validation fails when mod name is empty.

    Args:
        configured_window: Configured window instance
    """
    configured_window.mod_pak_files = ["test.pak"]

    is_valid, error_msg = configured_window.validate_inputs()

    assert is_valid is False
    assert "mod name" in error_msg


def test_validate_inputs_valid(configured_window: IconImportWindow) -> None:
    """Test validation succeeds with valid inputs.

    Args:
        configured_window: Configured window instance
    """
    configured_window.mod_pak_files = ["test.pak"]
    configured_window.mod_name_input.setText("test_mod")

    is_valid, error_msg = configured_window.validate_inputs()

    assert is_valid is True
    assert error_msg == ""


# ===== Import Process Tests =====


def test_start_import_validation_fails(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test start import shows warning when validation fails.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QMessageBox.warning"
    ) as mock_warning:
        configured_window.start_import()

        mock_warning.assert_called_once()
        args = mock_warning.call_args[0]
        assert args[1] == "Validation Error"


def test_start_import_success(
    qtbot: Any, configured_window: IconImportWindow, tmp_path: Path
) -> None:
    """Test successful start of import process.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
        tmp_path: Temporary directory path
    """
    configured_window.mod_pak_files = ["test.pak"]
    configured_window.mod_name_input.setText("test_mod")

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.IconImportWorker"
    ) as mock_worker_class:
        mock_worker = MagicMock(spec=IconImportWorker)
        mock_worker_class.return_value = mock_worker

        configured_window.start_import()

        # Worker should be created and started
        assert configured_window.import_worker is not None
        mock_worker.start.assert_called_once()

        # Buttons should be updated
        assert configured_window.start_button.isEnabled() is False
        assert configured_window.cancel_button.isEnabled() is True
        assert configured_window.mod_name_input.isEnabled() is False


def test_start_import_no_catalog(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test start import when catalog file is not configured.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    configured_window.mod_pak_files = ["test.pak"]
    configured_window.mod_name_input.setText("test_mod")
    configured_window.settings.database_builder.catalog_file = None

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        with patch(
            "foxhole_stockpiles.gui.windows.icon_import_window.QMessageBox.critical"
        ) as mock_critical:
            configured_window.start_import()

            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert "Catalog file not configured" in args[2]


def test_cancel_import_not_running(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test cancel import when worker is not running.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    # Should not raise exception
    configured_window.cancel_import()


def test_cancel_import_user_confirms(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test cancel import when user confirms.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    # Create mock worker
    mock_worker = MagicMock(spec=IconImportWorker)
    mock_worker.isRunning.return_value = True
    configured_window.import_worker = mock_worker

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        configured_window.cancel_import()

        mock_worker.stop.assert_called_once()
        mock_worker.wait.assert_called_once()


def test_on_import_finished_success(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test import finished handler on success.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    # Disable buttons as if import was running
    configured_window.start_button.setEnabled(False)
    configured_window.cancel_button.setEnabled(True)
    configured_window.mod_name_input.setEnabled(False)
    configured_window.overwrite_checkbox.setEnabled(False)

    # Clear logs before test
    configured_window.clear_logs()

    configured_window.on_import_finished(True)

    # Buttons should be re-enabled
    assert configured_window.start_button.isEnabled() is True
    assert configured_window.cancel_button.isEnabled() is False
    assert configured_window.mod_name_input.isEnabled() is True
    assert configured_window.overwrite_checkbox.isEnabled() is True

    # Should add success log message
    assert configured_window.log_display.rowCount() == 1
    message_item = configured_window.log_display.item(0, 3)
    assert message_item is not None and "completed successfully" in message_item.text().lower()


def test_on_import_finished_failure(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test import finished handler on failure.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    # Disable buttons as if import was running
    configured_window.start_button.setEnabled(False)
    configured_window.cancel_button.setEnabled(True)

    configured_window.on_import_finished(False)

    # Buttons should be re-enabled
    assert configured_window.start_button.isEnabled() is True
    assert configured_window.cancel_button.isEnabled() is False


def test_on_import_error(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test import error handler.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    # Clear logs before test
    configured_window.clear_logs()

    configured_window.on_import_error("Test error message")

    # Should add error log message
    assert configured_window.log_display.rowCount() == 1
    level_item = configured_window.log_display.item(0, 1)
    message_item = configured_window.log_display.item(0, 3)
    assert level_item is not None and level_item.text() == "ERROR"
    assert message_item is not None and "Test error message" in message_item.text()


# ===== Log Display Tests =====


def test_append_log(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test appending log entries.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    log_data = {
        "timestamp": "12:00:00",
        "level": "INFO",
        "module": "test_module",
        "message": "Test message",
        "color": "#FFFFFF",
    }

    configured_window.append_log(log_data)

    assert configured_window.log_display.rowCount() == 1
    item_0_0 = configured_window.log_display.item(0, 0)
    item_0_1 = configured_window.log_display.item(0, 1)
    item_0_2 = configured_window.log_display.item(0, 2)
    item_0_3 = configured_window.log_display.item(0, 3)
    assert item_0_0 is not None and item_0_0.text() == "12:00:00"
    assert item_0_1 is not None and item_0_1.text() == "INFO"
    assert item_0_2 is not None and item_0_2.text() == "test_module"
    assert item_0_3 is not None and item_0_3.text() == "Test message"


def test_append_multiple_logs(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test appending multiple log entries.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    log1 = {
        "timestamp": "12:00:00",
        "level": "INFO",
        "module": "module1",
        "message": "Message 1",
        "color": "#FFFFFF",
    }
    log2 = {
        "timestamp": "12:00:01",
        "level": "ERROR",
        "module": "module2",
        "message": "Message 2",
        "color": "#FF0000",
    }

    configured_window.append_log(log1)
    configured_window.append_log(log2)

    assert configured_window.log_display.rowCount() == 2


def test_clear_logs(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test clearing log entries.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    # Add some logs
    log_data = {
        "timestamp": "12:00:00",
        "level": "INFO",
        "module": "test_module",
        "message": "Test message",
        "color": "#FFFFFF",
    }
    configured_window.append_log(log_data)
    configured_window.append_log(log_data)

    assert configured_window.log_display.rowCount() == 2

    # Clear
    configured_window.clear_logs()

    assert configured_window.log_display.rowCount() == 0


# ===== Close Event Tests =====


def test_close_event_no_worker(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test close event when no worker is running.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    mock_event = MagicMock()

    configured_window.closeEvent(mock_event)

    mock_event.accept.assert_called_once()
    mock_event.ignore.assert_not_called()


def test_close_event_worker_not_running(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test close event when worker exists but is not running.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    mock_worker = MagicMock(spec=IconImportWorker)
    mock_worker.isRunning.return_value = False
    configured_window.import_worker = mock_worker

    mock_event = MagicMock()

    configured_window.closeEvent(mock_event)

    mock_event.accept.assert_called_once()
    mock_event.ignore.assert_not_called()


def test_close_event_worker_running_user_confirms(
    qtbot: Any, configured_window: IconImportWindow
) -> None:
    """Test close event when worker is running and user confirms.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    mock_worker = MagicMock(spec=IconImportWorker)
    mock_worker.isRunning.return_value = True
    configured_window.import_worker = mock_worker

    mock_event = MagicMock()

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        configured_window.closeEvent(mock_event)

        mock_worker.stop.assert_called_once()
        mock_worker.wait.assert_called_once()
        mock_event.accept.assert_called_once()
        mock_event.ignore.assert_not_called()


def test_close_event_worker_running_user_declines(
    qtbot: Any, configured_window: IconImportWindow
) -> None:
    """Test close event when worker is running and user declines.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    mock_worker = MagicMock(spec=IconImportWorker)
    mock_worker.isRunning.return_value = True
    configured_window.import_worker = mock_worker

    mock_event = MagicMock()

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QMessageBox.question"
    ) as mock_question:
        mock_question.return_value = QMessageBox.StandardButton.No

        configured_window.closeEvent(mock_event)

        mock_worker.stop.assert_not_called()
        mock_event.accept.assert_not_called()
        mock_event.ignore.assert_called_once()


# ===== Additional Coverage Tests =====


def test_start_import_invalid_mod_name(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test start import with invalid mod name.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    configured_window.mod_pak_files = ["test.pak"]
    configured_window.mod_name_input.setText("invalid/mod<name>")  # Invalid characters

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QMessageBox.critical"
    ) as mock_critical:
        configured_window.start_import()

        mock_critical.assert_called_once()
        assert "Invalid Mod Name" in str(mock_critical.call_args)
        assert configured_window.import_worker is None


def test_clear_vanilla_pak(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test clearing vanilla PAK selection.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    configured_window.vanilla_pak_file = "test.pak"
    configured_window.vanilla_pak_display.setText("test.pak")

    configured_window.clear_vanilla_pak()

    assert configured_window.vanilla_pak_file is None
    assert configured_window.vanilla_pak_display.text() == ""


def test_copy_selected_logs(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test copying selected log rows to clipboard.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    # Add some log entries
    configured_window.append_log(
        {
            "timestamp": "2024-01-01 12:00:00",
            "level": "INFO",
            "module": "test.module",
            "message": "Test message 1",
            "color": "#FFFFFF",
        }
    )
    configured_window.append_log(
        {
            "timestamp": "2024-01-01 12:00:01",
            "level": "ERROR",
            "module": "test.module",
            "message": "Test message 2",
            "color": "#FF0000",
        }
    )

    # Select all rows
    configured_window.log_display.selectAll()

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QApplication.clipboard"
    ) as mock_clipboard:
        mock_clipboard_instance = MagicMock()
        mock_clipboard.return_value = mock_clipboard_instance

        configured_window._copy_selected_logs()

        # Check clipboard was called with formatted text
        mock_clipboard_instance.setText.assert_called_once()
        clipboard_text = mock_clipboard_instance.setText.call_args[0][0]
        assert "[2024-01-01 12:00:00] INFO test.module: Test message 1" in clipboard_text
        assert "[2024-01-01 12:00:01] ERROR test.module: Test message 2" in clipboard_text


# ===== QFileDialog Tests =====


def test_select_vanilla_pak_file_selected(
    qtbot: Any, configured_window: IconImportWindow, tmp_path: Path
) -> None:
    """Test selecting a vanilla PAK file via dialog.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
        tmp_path: Temporary directory path
    """
    test_pak = str(tmp_path / "FoxholeVanilla.pak")

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QFileDialog.getOpenFileName"
    ) as mock_dialog:
        mock_dialog.return_value = (test_pak, "PAK Files (*.pak)")

        configured_window.select_vanilla_pak()

        assert configured_window.vanilla_pak_file == test_pak
        assert configured_window.vanilla_pak_display.text() == test_pak


def test_select_vanilla_pak_cancelled(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test cancelling vanilla PAK file dialog.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QFileDialog.getOpenFileName"
    ) as mock_dialog:
        mock_dialog.return_value = ("", "")

        configured_window.select_vanilla_pak()

        assert configured_window.vanilla_pak_file is None
        assert configured_window.vanilla_pak_display.text() == ""


def test_select_database_path_file_selected(
    qtbot: Any, configured_window: IconImportWindow, tmp_path: Path
) -> None:
    """Test selecting a database path via dialog.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
        tmp_path: Temporary directory path
    """
    test_db = str(tmp_path / "database.h5")

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QFileDialog.getSaveFileName"
    ) as mock_dialog:
        mock_dialog.return_value = (test_db, "HDF5 Database (*.h5)")

        configured_window.select_database_path()

        assert configured_window.db_path_input.text() == test_db


def test_select_database_path_adds_h5_extension(
    qtbot: Any, configured_window: IconImportWindow, tmp_path: Path
) -> None:
    """Test that .h5 extension is added if missing.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
        tmp_path: Temporary directory path
    """
    test_db = str(tmp_path / "database")  # No extension

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QFileDialog.getSaveFileName"
    ) as mock_dialog:
        mock_dialog.return_value = (test_db, "HDF5 Database (*.h5)")

        configured_window.select_database_path()

        assert configured_window.db_path_input.text() == test_db + ".h5"


def test_select_database_path_cancelled(qtbot: Any, configured_window: IconImportWindow) -> None:
    """Test cancelling database path dialog.

    Args:
        qtbot: PyQt test fixture
        configured_window: Configured window instance
    """
    original_text = configured_window.db_path_input.text()

    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.QFileDialog.getSaveFileName"
    ) as mock_dialog:
        mock_dialog.return_value = ("", "")

        configured_window.select_database_path()

        # Should not change the current value
        assert configured_window.db_path_input.text() == original_text


def test_validate_inputs_no_db_path(configured_window: IconImportWindow) -> None:
    """Test validation fails when database path is empty.

    Args:
        configured_window: Configured window instance
    """
    configured_window.mod_pak_files = ["test.pak"]
    configured_window.mod_name_input.setText("test_mod")
    configured_window.db_path_input.setText("")

    is_valid, error_msg = configured_window.validate_inputs()

    assert is_valid is False
    assert "database file" in error_msg.lower()


# ===== Platform-Specific Path Tests =====


def test_get_default_pak_directory_windows(configured_window: IconImportWindow) -> None:
    """Test default PAK directory on Windows when Steam path exists.

    Args:
        configured_window: Configured window instance
    """
    steam_path = "C:/Program Files (x86)/Steam/steamapps/common/Foxhole/War/Content/Paks"

    with (
        patch("foxhole_stockpiles.gui.windows.icon_import_window.platform.system") as mock_system,
        patch("foxhole_stockpiles.gui.windows.icon_import_window.Path") as mock_path_class,
    ):
        mock_system.return_value = "Windows"

        # Mock Path.cwd() to return a default path
        mock_cwd = MagicMock()
        mock_path_class.cwd.return_value = mock_cwd

        # Mock the Steam path to exist
        mock_steam_path = MagicMock()
        mock_steam_path.exists.return_value = True
        mock_steam_path.__str__ = MagicMock(return_value=steam_path)  # type: ignore[method-assign]

        # Make Path() return different mocks based on the argument
        def path_constructor(arg: str) -> MagicMock:
            if "Steam" in arg:
                return mock_steam_path
            return mock_cwd

        mock_path_class.side_effect = path_constructor

        result = configured_window._get_default_pak_directory()

        assert result == steam_path


def test_get_default_pak_directory_windows_no_steam(configured_window: IconImportWindow) -> None:
    """Test default PAK directory on Windows when Steam path doesn't exist.

    Args:
        configured_window: Configured window instance
    """
    with (
        patch("foxhole_stockpiles.gui.windows.icon_import_window.platform.system") as mock_system,
        patch("foxhole_stockpiles.gui.windows.icon_import_window.Path") as mock_path_class,
    ):
        mock_system.return_value = "Windows"

        # Mock Path.cwd() to return a default path
        mock_cwd = MagicMock()
        mock_cwd.__str__ = MagicMock(return_value="/home/user")  # type: ignore[method-assign]
        mock_path_class.cwd.return_value = mock_cwd

        # Mock the Steam path to not exist
        mock_steam_path = MagicMock()
        mock_steam_path.exists.return_value = False

        def path_constructor(arg: str) -> MagicMock:
            if "Steam" in arg:
                return mock_steam_path
            return mock_cwd

        mock_path_class.side_effect = path_constructor

        result = configured_window._get_default_pak_directory()

        assert result == "/home/user"


def test_get_default_pak_directory_wsl(configured_window: IconImportWindow) -> None:
    """Test default PAK directory on WSL when path exists.

    Args:
        configured_window: Configured window instance
    """
    wsl_path = "/mnt/c/Program Files (x86)/Steam/steamapps/common/Foxhole/War/Content/Paks"

    with (
        patch("foxhole_stockpiles.gui.windows.icon_import_window.platform.system") as mock_system,
        patch("foxhole_stockpiles.gui.windows.icon_import_window.Path") as mock_path_class,
        patch(
            "builtins.open",
            MagicMock(
                return_value=MagicMock(
                    __enter__=lambda self: MagicMock(
                        read=lambda: "Linux version microsoft-standard-WSL2"
                    ),
                    __exit__=lambda *args: None,
                )
            ),
        ),
    ):
        mock_system.return_value = "Linux"

        # Mock Path.cwd()
        mock_cwd = MagicMock()
        mock_path_class.cwd.return_value = mock_cwd

        # Mock the WSL path to exist
        mock_wsl_path = MagicMock()
        mock_wsl_path.exists.return_value = True
        mock_wsl_path.__str__ = MagicMock(return_value=wsl_path)  # type: ignore[method-assign]

        def path_constructor(arg: str) -> MagicMock:
            if "/mnt/c" in arg:
                return mock_wsl_path
            return mock_cwd

        mock_path_class.side_effect = path_constructor

        result = configured_window._get_default_pak_directory()

        assert result == wsl_path


def test_get_default_pak_directory_linux_not_wsl(configured_window: IconImportWindow) -> None:
    """Test default PAK directory on native Linux.

    Args:
        configured_window: Configured window instance
    """
    with (
        patch("foxhole_stockpiles.gui.windows.icon_import_window.platform.system") as mock_system,
        patch("foxhole_stockpiles.gui.windows.icon_import_window.Path") as mock_path_class,
        patch(
            "builtins.open",
            MagicMock(
                return_value=MagicMock(
                    __enter__=lambda self: MagicMock(read=lambda: "Linux version 6.1.0-generic"),
                    __exit__=lambda *args: None,
                )
            ),
        ),
    ):
        mock_system.return_value = "Linux"

        # Mock Path.cwd()
        mock_cwd = MagicMock()
        mock_cwd.__str__ = MagicMock(return_value="/home/user")  # type: ignore[method-assign]
        mock_path_class.cwd.return_value = mock_cwd

        result = configured_window._get_default_pak_directory()

        assert result == "/home/user"


def test_get_default_pak_directory_linux_oserror(configured_window: IconImportWindow) -> None:
    """Test default PAK directory on Linux when /proc/version can't be read.

    Args:
        configured_window: Configured window instance
    """
    with (
        patch("foxhole_stockpiles.gui.windows.icon_import_window.platform.system") as mock_system,
        patch("foxhole_stockpiles.gui.windows.icon_import_window.Path") as mock_path_class,
        patch("builtins.open", side_effect=OSError("Permission denied")),
    ):
        mock_system.return_value = "Linux"

        # Mock Path.cwd()
        mock_cwd = MagicMock()
        mock_cwd.__str__ = MagicMock(return_value="/home/user")  # type: ignore[method-assign]
        mock_path_class.cwd.return_value = mock_cwd

        result = configured_window._get_default_pak_directory()

        assert result == "/home/user"


def test_get_default_pak_directory_macos(configured_window: IconImportWindow) -> None:
    """Test default PAK directory on macOS (unsupported platform).

    Args:
        configured_window: Configured window instance
    """
    with (
        patch("foxhole_stockpiles.gui.windows.icon_import_window.platform.system") as mock_system,
        patch("foxhole_stockpiles.gui.windows.icon_import_window.Path") as mock_path_class,
    ):
        mock_system.return_value = "Darwin"

        # Mock Path.cwd()
        mock_cwd = MagicMock()
        mock_cwd.__str__ = MagicMock(return_value="/Users/user")  # type: ignore[method-assign]
        mock_path_class.cwd.return_value = mock_cwd

        result = configured_window._get_default_pak_directory()

        assert result == "/Users/user"


# ===== Settings Dialog Tests =====


def test_open_settings_dialog_accepted_and_configured(
    qtbot: Any,
    mock_unconfigured_settings: AppSettings,
    mock_configured_settings: AppSettings,
) -> None:
    """Test opening settings dialog, saving, and becoming configured.

    Args:
        qtbot: PyQt test fixture
        mock_unconfigured_settings: Mock unconfigured settings
        mock_configured_settings: Mock configured settings
    """
    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.get_settings",
        return_value=mock_unconfigured_settings,
    ):
        window = IconImportWindow()
        qtbot.addWidget(window)

        assert window.is_configured is False

        with (
            patch(
                "foxhole_stockpiles.gui.windows.icon_import_window.DatabaseBuilderSettingsDialog"
            ) as mock_dialog_class,
            patch(
                "foxhole_stockpiles.gui.windows.icon_import_window.reload_settings",
                return_value=mock_configured_settings,
            ),
            patch(
                "foxhole_stockpiles.gui.windows.icon_import_window.get_settings",
                return_value=mock_configured_settings,
            ),
        ):
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = True  # Dialog accepted
            mock_dialog_class.return_value = mock_dialog

            window._open_settings_dialog()

            mock_dialog_class.assert_called_once_with(window)
            mock_dialog.exec.assert_called_once()
            assert window.is_configured is True


def test_open_settings_dialog_rejected(qtbot: Any, mock_unconfigured_settings: AppSettings) -> None:
    """Test opening settings dialog and cancelling.

    Args:
        qtbot: PyQt test fixture
        mock_unconfigured_settings: Mock unconfigured settings
    """
    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.get_settings",
        return_value=mock_unconfigured_settings,
    ):
        window = IconImportWindow()
        qtbot.addWidget(window)

        assert window.is_configured is False

        with (
            patch(
                "foxhole_stockpiles.gui.windows.icon_import_window.DatabaseBuilderSettingsDialog"
            ) as mock_dialog_class,
            patch(
                "foxhole_stockpiles.gui.windows.icon_import_window.reload_settings"
            ) as mock_reload,
        ):
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = False  # Dialog rejected
            mock_dialog_class.return_value = mock_dialog

            window._open_settings_dialog()

            mock_dialog_class.assert_called_once_with(window)
            mock_dialog.exec.assert_called_once()
            mock_reload.assert_not_called()  # Should not reload if rejected
            assert window.is_configured is False  # Still unconfigured


def test_open_settings_dialog_accepted_but_still_unconfigured(
    qtbot: Any, mock_unconfigured_settings: AppSettings
) -> None:
    """Test opening settings dialog, saving but still not properly configured.

    Args:
        qtbot: PyQt test fixture
        mock_unconfigured_settings: Mock unconfigured settings
    """
    with patch(
        "foxhole_stockpiles.gui.windows.icon_import_window.get_settings",
        return_value=mock_unconfigured_settings,
    ):
        window = IconImportWindow()
        qtbot.addWidget(window)

        assert window.is_configured is False

        with (
            patch(
                "foxhole_stockpiles.gui.windows.icon_import_window.DatabaseBuilderSettingsDialog"
            ) as mock_dialog_class,
            patch(
                "foxhole_stockpiles.gui.windows.icon_import_window.reload_settings",
                return_value=mock_unconfigured_settings,
            ),
            patch(
                "foxhole_stockpiles.gui.windows.icon_import_window.get_settings",
                return_value=mock_unconfigured_settings,
            ),
        ):
            mock_dialog = MagicMock()
            mock_dialog.exec.return_value = True  # Dialog accepted
            mock_dialog_class.return_value = mock_dialog

            window._open_settings_dialog()

            # Still unconfigured because settings weren't properly set
            assert window.is_configured is False

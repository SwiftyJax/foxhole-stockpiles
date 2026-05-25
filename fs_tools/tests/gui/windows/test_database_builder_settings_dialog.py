"""Tests for DatabaseBuilderSettingsDialog."""

from typing import Any
from unittest.mock import patch

import pytest

from foxhole_stockpiles.core.settings.app_settings import AppSettings
from foxhole_stockpiles.core.settings.sections.database_builder import DatabaseBuilderSettings
from foxhole_stockpiles.i18n import t
from fs_tools.gui.windows.database_builder_settings_dialog import (
    DatabaseBuilderSettingsDialog,
)


@pytest.fixture
def dialog(qtbot: Any) -> DatabaseBuilderSettingsDialog:
    """Create a DatabaseBuilderSettingsDialog instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        DatabaseBuilderSettingsDialog: Dialog instance
    """
    with patch("fs_tools.gui.windows.database_builder_settings_dialog.get_settings"):
        dialog = DatabaseBuilderSettingsDialog()
        qtbot.addWidget(dialog)
        return dialog


def test_dialog_initialization(dialog: DatabaseBuilderSettingsDialog) -> None:
    """Test DatabaseBuilderSettingsDialog initialization.

    Args:
        dialog (DatabaseBuilderSettingsDialog): Dialog instance
    """
    assert t("database_builder_settings.title") in dialog.windowTitle()
    assert dialog.db_builder_tab is not None
    assert dialog.config_manager is not None
    assert dialog.status_label is not None


def test_dialog_has_save_and_cancel_buttons(dialog: DatabaseBuilderSettingsDialog) -> None:
    """Test dialog has Save and Cancel buttons.

    Args:
        dialog (DatabaseBuilderSettingsDialog): Dialog instance
    """
    # Find the button box
    button_box = None
    for child in dialog.children():
        if hasattr(child, "standardButtons"):
            button_box = child
            break

    assert button_box is not None


def test_load_settings_success(qtbot: Any) -> None:
    """Test loading settings successfully.

    Args:
        qtbot: PyQt test fixture
    """
    mock_settings = AppSettings()

    with patch(
        "fs_tools.gui.windows.database_builder_settings_dialog.get_settings"
    ) as mock_get_settings:
        mock_get_settings.return_value = mock_settings

        dialog = DatabaseBuilderSettingsDialog()
        qtbot.addWidget(dialog)

        mock_get_settings.assert_called()


def test_save_and_accept_success(qtbot: Any) -> None:
    """Test saving settings successfully.

    Args:
        qtbot: PyQt test fixture
    """
    mock_settings = AppSettings()

    with patch(
        "fs_tools.gui.windows.database_builder_settings_dialog.get_settings"
    ) as mock_get_settings:
        mock_get_settings.return_value = mock_settings

        with patch(
            "fs_tools.gui.windows.database_builder_settings_dialog.ConfigManager"
        ) as mock_config_class:
            mock_config = mock_config_class.return_value
            mock_config.save_config.return_value = (True, "Success")

            dialog = DatabaseBuilderSettingsDialog()
            qtbot.addWidget(dialog)

            # Mock the get_values method
            new_db_settings = DatabaseBuilderSettings()

            with patch.object(dialog.db_builder_tab, "get_values", return_value=new_db_settings):
                # Trigger save
                dialog._save_and_accept()

                # Verify save was called
                mock_config.save_config.assert_called_once()
                saved_settings = mock_config.save_config.call_args[0][0]
                assert saved_settings.database_builder == new_db_settings


def test_save_and_accept_failure(qtbot: Any) -> None:
    """Test saving settings failure shows error in status label.

    Args:
        qtbot: PyQt test fixture
    """
    mock_settings = AppSettings()

    with patch(
        "fs_tools.gui.windows.database_builder_settings_dialog.get_settings"
    ) as mock_get_settings:
        mock_get_settings.return_value = mock_settings

        with patch(
            "fs_tools.gui.windows.database_builder_settings_dialog.ConfigManager"
        ) as mock_config_class:
            mock_config = mock_config_class.return_value
            mock_config.save_config.return_value = (False, "Save failed")

            dialog = DatabaseBuilderSettingsDialog()
            qtbot.addWidget(dialog)

            # Mock the get_values method
            new_db_settings = DatabaseBuilderSettings()

            with patch.object(dialog.db_builder_tab, "get_values", return_value=new_db_settings):
                dialog._save_and_accept()

                # Error should be shown in status label
                assert "Save failed" in dialog.status_label.text()
                assert not dialog.status_label.isHidden()


def test_save_and_accept_exception(qtbot: Any) -> None:
    """Test saving settings when exception occurs.

    Args:
        qtbot: PyQt test fixture
    """
    mock_settings = AppSettings()

    with patch(
        "fs_tools.gui.windows.database_builder_settings_dialog.get_settings"
    ) as mock_get_settings:
        mock_get_settings.return_value = mock_settings

        with patch(
            "fs_tools.gui.windows.database_builder_settings_dialog.ConfigManager"
        ) as mock_config_class:
            mock_config = mock_config_class.return_value
            mock_config.save_config.side_effect = Exception("Test error")

            dialog = DatabaseBuilderSettingsDialog()
            qtbot.addWidget(dialog)

            # Mock the get_values method
            new_db_settings = DatabaseBuilderSettings()

            with patch.object(dialog.db_builder_tab, "get_values", return_value=new_db_settings):
                dialog._save_and_accept()

                # Error should be shown in status label
                assert "Test error" in dialog.status_label.text()
                assert not dialog.status_label.isHidden()

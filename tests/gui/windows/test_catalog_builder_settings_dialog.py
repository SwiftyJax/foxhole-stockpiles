"""Tests for CatalogBuilderSettingsDialog."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from foxhole_stockpiles.core.settings.app_settings import AppSettings
from foxhole_stockpiles.core.settings.sections.external_tools import ExternalToolsSettings
from foxhole_stockpiles.gui.windows.catalog_builder_settings_dialog import (
    CatalogBuilderSettingsDialog,
)
from foxhole_stockpiles.i18n import t


@pytest.fixture
def dialog(qtbot: Any) -> CatalogBuilderSettingsDialog:
    """Create a CatalogBuilderSettingsDialog instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        CatalogBuilderSettingsDialog: Dialog instance
    """
    with patch("foxhole_stockpiles.gui.windows.catalog_builder_settings_dialog.get_settings"):
        dialog = CatalogBuilderSettingsDialog()
        qtbot.addWidget(dialog)
        return dialog


def test_dialog_initialization(dialog: CatalogBuilderSettingsDialog) -> None:
    """Test CatalogBuilderSettingsDialog initialization.

    Args:
        dialog: CatalogBuilderSettingsDialog instance
    """
    assert t("catalog_builder_settings.title") in dialog.windowTitle()
    assert dialog.external_tools_tab is not None
    assert dialog.config_manager is not None
    assert dialog.status_label is not None


def test_dialog_minimum_size(dialog: CatalogBuilderSettingsDialog) -> None:
    """Test dialog has minimum size set.

    Args:
        dialog: CatalogBuilderSettingsDialog instance
    """
    assert dialog.minimumWidth() >= 600
    assert dialog.minimumHeight() >= 300


def test_dialog_has_save_and_cancel_buttons(dialog: CatalogBuilderSettingsDialog) -> None:
    """Test dialog has Save and Cancel buttons.

    Args:
        dialog: CatalogBuilderSettingsDialog instance
    """
    # Find the button box
    button_box = None
    for child in dialog.children():
        if hasattr(child, "standardButtons"):
            button_box = child
            break

    assert button_box is not None


def test_external_tools_tab_shows_repak_and_uassetgui(
    dialog: CatalogBuilderSettingsDialog,
) -> None:
    """Test external tools tab shows repak and uassetgui, not umodel.

    Args:
        dialog: CatalogBuilderSettingsDialog instance
    """
    tab = dialog.external_tools_tab

    # Should have repak and uassetgui
    assert tab.repak_input is not None
    assert tab.uassetgui_input is not None

    # Should not have umodel
    assert tab.umodel_input is None


def test_load_settings_success(qtbot: Any) -> None:
    """Test loading settings successfully.

    Args:
        qtbot: PyQt test fixture
    """
    mock_settings = AppSettings(
        external_tools=ExternalToolsSettings(
            repak=Path("/path/to/repak"),
            uassetgui=Path("/path/to/uassetgui"),
        )
    )

    with patch(
        "foxhole_stockpiles.gui.windows.catalog_builder_settings_dialog.get_settings"
    ) as mock_get_settings:
        mock_get_settings.return_value = mock_settings

        dialog = CatalogBuilderSettingsDialog()
        qtbot.addWidget(dialog)

        mock_get_settings.assert_called()
        # Check values were loaded
        assert dialog.external_tools_tab.repak_input is not None
        assert dialog.external_tools_tab.uassetgui_input is not None
        assert dialog.external_tools_tab.repak_input.text() == "/path/to/repak"
        assert dialog.external_tools_tab.uassetgui_input.text() == "/path/to/uassetgui"


def test_save_and_accept_success(qtbot: Any) -> None:
    """Test saving settings successfully.

    Args:
        qtbot: PyQt test fixture
    """
    mock_settings = AppSettings()

    with patch(
        "foxhole_stockpiles.gui.windows.catalog_builder_settings_dialog.get_settings"
    ) as mock_get_settings:
        mock_get_settings.return_value = mock_settings

        with patch(
            "foxhole_stockpiles.gui.windows.catalog_builder_settings_dialog.ConfigManager"
        ) as mock_config_class:
            mock_config = mock_config_class.return_value
            mock_config.save_config.return_value = (True, "Success")

            dialog = CatalogBuilderSettingsDialog()
            qtbot.addWidget(dialog)

            # Set some values
            assert dialog.external_tools_tab.repak_input is not None
            assert dialog.external_tools_tab.uassetgui_input is not None
            dialog.external_tools_tab.repak_input.setText("/new/repak.exe")
            dialog.external_tools_tab.uassetgui_input.setText("/new/uassetgui.exe")

            # Trigger save
            dialog._save_and_accept()

            # Verify save was called
            mock_config.save_config.assert_called_once()
            saved_settings = mock_config.save_config.call_args[0][0]
            assert saved_settings.external_tools.repak == Path("/new/repak.exe")
            assert saved_settings.external_tools.uassetgui == Path("/new/uassetgui.exe")


def test_save_and_accept_preserves_umodel(qtbot: Any) -> None:
    """Test saving settings preserves umodel (which is not shown in this dialog).

    Args:
        qtbot: PyQt test fixture
    """
    existing_umodel = Path("/existing/umodel.exe")
    mock_settings = AppSettings(
        external_tools=ExternalToolsSettings(
            umodel=existing_umodel,
        )
    )

    with patch(
        "foxhole_stockpiles.gui.windows.catalog_builder_settings_dialog.get_settings"
    ) as mock_get_settings:
        mock_get_settings.return_value = mock_settings

        with patch(
            "foxhole_stockpiles.gui.windows.catalog_builder_settings_dialog.ConfigManager"
        ) as mock_config_class:
            mock_config = mock_config_class.return_value
            mock_config.save_config.return_value = (True, "Success")

            dialog = CatalogBuilderSettingsDialog()
            qtbot.addWidget(dialog)

            # Set repak and uassetgui
            assert dialog.external_tools_tab.repak_input is not None
            assert dialog.external_tools_tab.uassetgui_input is not None
            dialog.external_tools_tab.repak_input.setText("/new/repak.exe")
            dialog.external_tools_tab.uassetgui_input.setText("/new/uassetgui.exe")

            # Trigger save
            dialog._save_and_accept()

            # Verify umodel was preserved
            saved_settings = mock_config.save_config.call_args[0][0]
            assert saved_settings.external_tools.umodel == existing_umodel


def test_save_and_accept_failure(qtbot: Any) -> None:
    """Test saving settings failure shows error in status label.

    Args:
        qtbot: PyQt test fixture
    """
    mock_settings = AppSettings()

    with patch(
        "foxhole_stockpiles.gui.windows.catalog_builder_settings_dialog.get_settings"
    ) as mock_get_settings:
        mock_get_settings.return_value = mock_settings

        with patch(
            "foxhole_stockpiles.gui.windows.catalog_builder_settings_dialog.ConfigManager"
        ) as mock_config_class:
            mock_config = mock_config_class.return_value
            mock_config.save_config.return_value = (False, "Save failed")

            dialog = CatalogBuilderSettingsDialog()
            qtbot.addWidget(dialog)

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
        "foxhole_stockpiles.gui.windows.catalog_builder_settings_dialog.get_settings"
    ) as mock_get_settings:
        mock_get_settings.return_value = mock_settings

        with patch(
            "foxhole_stockpiles.gui.windows.catalog_builder_settings_dialog.ConfigManager"
        ) as mock_config_class:
            mock_config = mock_config_class.return_value
            mock_config.save_config.side_effect = Exception("Test error")

            dialog = CatalogBuilderSettingsDialog()
            qtbot.addWidget(dialog)

            dialog._save_and_accept()

            # Error should be shown in status label
            assert "Test error" in dialog.status_label.text()
            assert not dialog.status_label.isHidden()


def test_status_label_initially_hidden(dialog: CatalogBuilderSettingsDialog) -> None:
    """Test status label is initially hidden.

    Args:
        dialog: CatalogBuilderSettingsDialog instance
    """
    assert dialog.status_label.isHidden()

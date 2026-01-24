"""Tests for GUITab."""

from typing import Any

import pytest

from foxhole_stockpiles.core.settings.sections.gui import GUISettings
from foxhole_stockpiles.enums.config_level import ConfigLevel
from foxhole_stockpiles.gui.widgets.config_tabs.gui_tab import GUITab


@pytest.fixture
def gui_tab(qtbot: Any) -> GUITab:
    """Create a GUITab instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        GUITab: Tab instance
    """
    tab = GUITab()
    qtbot.addWidget(tab)
    return tab


def test_gui_tab_initialization(gui_tab: GUITab) -> None:
    """Test GUITab initialization.

    Args:
        gui_tab: GUITab instance
    """
    assert gui_tab.config_level_input is not None
    assert gui_tab.minimize_to_tray_input is not None
    assert gui_tab.warning_label is not None


def test_gui_tab_default_values(gui_tab: GUITab) -> None:
    """Test default values are set correctly.

    Args:
        gui_tab: GUITab instance
    """
    # Default should be basic
    assert gui_tab.config_level_input.currentData() == ConfigLevel.BASIC
    # Minimize to tray should be unchecked by default
    assert not gui_tab.minimize_to_tray_input.isChecked()


def test_gui_tab_config_level_options(gui_tab: GUITab) -> None:
    """Test config level combo box has correct options.

    Args:
        gui_tab: GUITab instance
    """
    assert gui_tab.config_level_input.count() == 3
    assert gui_tab.config_level_input.itemData(0) == ConfigLevel.BASIC
    assert gui_tab.config_level_input.itemData(1) == ConfigLevel.ADVANCED
    assert gui_tab.config_level_input.itemData(2) == ConfigLevel.DEVELOPER


def test_gui_tab_warning_label_hidden_for_basic(gui_tab: GUITab) -> None:
    """Test warning label is hidden for basic level.

    Args:
        gui_tab: GUITab instance
    """
    gui_tab.config_level_input.setCurrentIndex(0)  # Basic
    # Use isHidden() instead of isVisible() since parent widget is not shown
    assert gui_tab.warning_label.isHidden()


def test_gui_tab_warning_label_shown_for_advanced(gui_tab: GUITab) -> None:
    """Test warning label is shown for advanced level.

    Args:
        gui_tab: GUITab instance
    """
    gui_tab.config_level_input.setCurrentIndex(1)  # Advanced
    # Use isHidden() instead of isVisible() since parent widget is not shown
    assert not gui_tab.warning_label.isHidden()
    assert "Advanced mode" in gui_tab.warning_label.text()


def test_gui_tab_warning_label_shown_for_developer(gui_tab: GUITab) -> None:
    """Test warning label is shown for developer level.

    Args:
        gui_tab: GUITab instance
    """
    gui_tab.config_level_input.setCurrentIndex(2)  # Developer
    # Use isHidden() instead of isVisible() since parent widget is not shown
    assert not gui_tab.warning_label.isHidden()
    assert "Developer mode" in gui_tab.warning_label.text()


def test_gui_tab_set_values(gui_tab: GUITab) -> None:
    """Test setting values from settings object.

    Args:
        gui_tab: GUITab instance
    """
    settings = GUISettings(
        config_level=ConfigLevel.ADVANCED,
        minimize_to_tray=True,
    )

    gui_tab.set_values(settings)

    assert gui_tab.config_level_input.currentData() == ConfigLevel.ADVANCED
    assert gui_tab.minimize_to_tray_input.isChecked()


def test_gui_tab_set_values_basic(gui_tab: GUITab) -> None:
    """Test setting values with basic level.

    Args:
        gui_tab: GUITab instance
    """
    settings = GUISettings(
        config_level=ConfigLevel.BASIC,
        minimize_to_tray=False,
    )

    gui_tab.set_values(settings)

    assert gui_tab.config_level_input.currentData() == ConfigLevel.BASIC
    assert not gui_tab.minimize_to_tray_input.isChecked()


def test_gui_tab_set_values_developer(gui_tab: GUITab) -> None:
    """Test setting values with developer level.

    Args:
        gui_tab: GUITab instance
    """
    settings = GUISettings(
        config_level=ConfigLevel.DEVELOPER,
        minimize_to_tray=True,
    )

    gui_tab.set_values(settings)

    assert gui_tab.config_level_input.currentData() == ConfigLevel.DEVELOPER
    assert gui_tab.minimize_to_tray_input.isChecked()


def test_gui_tab_get_values(gui_tab: GUITab) -> None:
    """Test getting values from widgets.

    Args:
        gui_tab: GUITab instance
    """
    gui_tab.config_level_input.setCurrentIndex(1)  # Advanced
    gui_tab.minimize_to_tray_input.setChecked(True)

    settings = gui_tab.get_values()

    assert settings.config_level == ConfigLevel.ADVANCED
    assert settings.minimize_to_tray is True


def test_gui_tab_get_values_basic(gui_tab: GUITab) -> None:
    """Test getting values with basic level.

    Args:
        gui_tab: GUITab instance
    """
    gui_tab.config_level_input.setCurrentIndex(0)  # Basic
    gui_tab.minimize_to_tray_input.setChecked(False)

    settings = gui_tab.get_values()

    assert settings.config_level == ConfigLevel.BASIC
    assert settings.minimize_to_tray is False


def test_gui_tab_get_config_level(gui_tab: GUITab) -> None:
    """Test get_config_level method.

    Args:
        gui_tab: GUITab instance
    """
    gui_tab.config_level_input.setCurrentIndex(0)
    assert gui_tab.get_config_level() == ConfigLevel.BASIC

    gui_tab.config_level_input.setCurrentIndex(1)
    assert gui_tab.get_config_level() == ConfigLevel.ADVANCED

    gui_tab.config_level_input.setCurrentIndex(2)
    assert gui_tab.get_config_level() == ConfigLevel.DEVELOPER


def test_gui_tab_minimize_to_tray_toggle(gui_tab: GUITab) -> None:
    """Test minimize to tray checkbox toggle.

    Args:
        gui_tab: GUITab instance
    """
    assert not gui_tab.minimize_to_tray_input.isChecked()

    gui_tab.minimize_to_tray_input.setChecked(True)
    assert gui_tab.minimize_to_tray_input.isChecked()

    gui_tab.minimize_to_tray_input.setChecked(False)
    assert not gui_tab.minimize_to_tray_input.isChecked()


def test_gui_tab_warning_style_changes(gui_tab: GUITab) -> None:
    """Test warning label style changes based on level.

    Args:
        gui_tab: GUITab instance
    """
    # Advanced should have yellow/warning style
    gui_tab.config_level_input.setCurrentIndex(1)  # Advanced
    style = gui_tab.warning_label.styleSheet()
    assert "#fff3cd" in style or "#856404" in style  # Yellow warning colors

    # Developer should have red/danger style
    gui_tab.config_level_input.setCurrentIndex(2)  # Developer
    style = gui_tab.warning_label.styleSheet()
    assert "#f8d7da" in style or "#721c24" in style  # Red danger colors

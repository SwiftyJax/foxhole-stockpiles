"""Tests for TemplateTab."""

from typing import Any
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QMessageBox

from foxhole_stockpiles.core.settings.sections.templates import TemplateSettings
from foxhole_stockpiles.gui.widgets.config_tabs.template_tab import TemplateTab


@pytest.fixture
def template_tab(qtbot: Any) -> TemplateTab:
    """Create a TemplateTab instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        TemplateTab: Tab instance
    """
    tab = TemplateTab()
    qtbot.addWidget(tab)
    return tab


def test_template_tab_initialization(template_tab: TemplateTab) -> None:
    """Test TemplateTab initialization.

    Args:
        template_tab: TemplateTab instance
    """
    assert template_tab.red_mult_input is not None
    assert template_tab.green_mult_input is not None
    assert template_tab.blue_mult_input is not None
    assert template_tab.red_offset_input is not None
    assert template_tab.green_offset_input is not None
    assert template_tab.blue_offset_input is not None


def test_template_tab_default_values(template_tab: TemplateTab) -> None:
    """Test default values are set correctly.

    Args:
        template_tab: TemplateTab instance
    """
    assert template_tab.red_mult_input.value() == 154
    assert template_tab.green_mult_input.value() == 152
    assert template_tab.blue_mult_input.value() == 145
    assert template_tab.red_offset_input.value() == 89
    assert template_tab.green_offset_input.value() == 87
    assert template_tab.blue_offset_input.value() == 82


def test_template_tab_multiplier_ranges(template_tab: TemplateTab) -> None:
    """Test multiplier inputs have correct range.

    Args:
        template_tab: TemplateTab instance
    """
    assert template_tab.red_mult_input.minimum() == 0
    assert template_tab.red_mult_input.maximum() == 255
    assert template_tab.green_mult_input.minimum() == 0
    assert template_tab.green_mult_input.maximum() == 255
    assert template_tab.blue_mult_input.minimum() == 0
    assert template_tab.blue_mult_input.maximum() == 255


def test_template_tab_offset_ranges(template_tab: TemplateTab) -> None:
    """Test offset inputs have correct range.

    Args:
        template_tab: TemplateTab instance
    """
    assert template_tab.red_offset_input.minimum() == 0
    assert template_tab.red_offset_input.maximum() == 255
    assert template_tab.green_offset_input.minimum() == 0
    assert template_tab.green_offset_input.maximum() == 255
    assert template_tab.blue_offset_input.minimum() == 0
    assert template_tab.blue_offset_input.maximum() == 255


def test_template_tab_set_values(template_tab: TemplateTab) -> None:
    """Test setting values from settings object.

    Args:
        template_tab: TemplateTab instance
    """
    settings = TemplateSettings(
        crate_red_multiplier=200,
        crate_green_multiplier=180,
        crate_blue_multiplier=160,
        crate_red_offset=100,
        crate_green_offset=90,
        crate_blue_offset=80,
    )

    template_tab.set_values(settings)

    assert template_tab.red_mult_input.value() == 200
    assert template_tab.green_mult_input.value() == 180
    assert template_tab.blue_mult_input.value() == 160
    assert template_tab.red_offset_input.value() == 100
    assert template_tab.green_offset_input.value() == 90
    assert template_tab.blue_offset_input.value() == 80


def test_template_tab_get_values(template_tab: TemplateTab) -> None:
    """Test getting values from widgets.

    Args:
        template_tab: TemplateTab instance
    """
    template_tab.red_mult_input.setValue(150)
    template_tab.green_mult_input.setValue(140)
    template_tab.blue_mult_input.setValue(130)
    template_tab.red_offset_input.setValue(120)
    template_tab.green_offset_input.setValue(110)
    template_tab.blue_offset_input.setValue(100)

    settings = template_tab.get_values()

    assert settings.crate_red_multiplier == 150
    assert settings.crate_green_multiplier == 140
    assert settings.crate_blue_multiplier == 130
    assert settings.crate_red_offset == 120
    assert settings.crate_green_offset == 110
    assert settings.crate_blue_offset == 100


def test_template_tab_reset_all_to_defaults_confirmed(
    qtbot: Any, template_tab: TemplateTab
) -> None:
    """Test reset all to defaults when confirmed.

    Args:
        qtbot: PyQt test fixture
        template_tab: TemplateTab instance
    """
    # Change some values
    template_tab.red_mult_input.setValue(100)
    template_tab.green_mult_input.setValue(100)

    with patch(
        "foxhole_stockpiles.gui.widgets.config_tabs.template_tab.QMessageBox.question"
    ) as mock_msg:
        mock_msg.return_value = QMessageBox.StandardButton.Yes

        template_tab.reset_all_to_defaults()

        # Should reset to defaults
        defaults = TemplateSettings()
        assert template_tab.red_mult_input.value() == defaults.crate_red_multiplier
        assert template_tab.green_mult_input.value() == defaults.crate_green_multiplier


def test_template_tab_reset_all_to_defaults_cancelled(
    qtbot: Any, template_tab: TemplateTab
) -> None:
    """Test reset all to defaults when cancelled.

    Args:
        qtbot: PyQt test fixture
        template_tab: TemplateTab instance
    """
    # Change some values
    template_tab.red_mult_input.setValue(100)
    original_value = 100

    with patch(
        "foxhole_stockpiles.gui.widgets.config_tabs.template_tab.QMessageBox.question"
    ) as mock_msg:
        mock_msg.return_value = QMessageBox.StandardButton.No

        template_tab.reset_all_to_defaults()

        # Should not reset
        assert template_tab.red_mult_input.value() == original_value


def test_template_tab_min_multiplier_boundary(template_tab: TemplateTab) -> None:
    """Test multipliers at minimum boundary.

    Args:
        template_tab: TemplateTab instance
    """
    template_tab.red_mult_input.setValue(0)
    template_tab.green_mult_input.setValue(0)
    template_tab.blue_mult_input.setValue(0)

    settings = template_tab.get_values()

    assert settings.crate_red_multiplier == 0
    assert settings.crate_green_multiplier == 0
    assert settings.crate_blue_multiplier == 0


def test_template_tab_max_multiplier_boundary(template_tab: TemplateTab) -> None:
    """Test multipliers at maximum boundary.

    Args:
        template_tab: TemplateTab instance
    """
    template_tab.red_mult_input.setValue(255)
    template_tab.green_mult_input.setValue(255)
    template_tab.blue_mult_input.setValue(255)

    settings = template_tab.get_values()

    assert settings.crate_red_multiplier == 255
    assert settings.crate_green_multiplier == 255
    assert settings.crate_blue_multiplier == 255


def test_template_tab_min_offset_boundary(template_tab: TemplateTab) -> None:
    """Test offsets at minimum boundary.

    Args:
        template_tab: TemplateTab instance
    """
    template_tab.red_offset_input.setValue(0)
    template_tab.green_offset_input.setValue(0)
    template_tab.blue_offset_input.setValue(0)

    settings = template_tab.get_values()

    assert settings.crate_red_offset == 0
    assert settings.crate_green_offset == 0
    assert settings.crate_blue_offset == 0


def test_template_tab_max_offset_boundary(template_tab: TemplateTab) -> None:
    """Test offsets at maximum boundary.

    Args:
        template_tab: TemplateTab instance
    """
    template_tab.red_offset_input.setValue(255)
    template_tab.green_offset_input.setValue(255)
    template_tab.blue_offset_input.setValue(255)

    settings = template_tab.get_values()

    assert settings.crate_red_offset == 255
    assert settings.crate_green_offset == 255
    assert settings.crate_blue_offset == 255


def test_template_tab_set_values_default_settings(template_tab: TemplateTab) -> None:
    """Test setting values with default settings object.

    Args:
        template_tab: TemplateTab instance
    """
    settings = TemplateSettings()

    template_tab.set_values(settings)

    assert template_tab.red_mult_input.value() == settings.crate_red_multiplier
    assert template_tab.green_mult_input.value() == settings.crate_green_multiplier
    assert template_tab.blue_mult_input.value() == settings.crate_blue_multiplier
    assert template_tab.red_offset_input.value() == settings.crate_red_offset
    assert template_tab.green_offset_input.value() == settings.crate_green_offset
    assert template_tab.blue_offset_input.value() == settings.crate_blue_offset


def test_template_tab_all_inputs_are_spin_boxes(template_tab: TemplateTab) -> None:
    """Test all inputs are spin boxes.

    Args:
        template_tab: TemplateTab instance
    """
    from PySide6.QtWidgets import QSpinBox

    assert isinstance(template_tab.red_mult_input, QSpinBox)
    assert isinstance(template_tab.green_mult_input, QSpinBox)
    assert isinstance(template_tab.blue_mult_input, QSpinBox)
    assert isinstance(template_tab.red_offset_input, QSpinBox)
    assert isinstance(template_tab.green_offset_input, QSpinBox)
    assert isinstance(template_tab.blue_offset_input, QSpinBox)


def test_template_tab_mixed_values(template_tab: TemplateTab) -> None:
    """Test with mixed min and max values.

    Args:
        template_tab: TemplateTab instance
    """
    template_tab.red_mult_input.setValue(0)
    template_tab.green_mult_input.setValue(255)
    template_tab.blue_mult_input.setValue(128)
    template_tab.red_offset_input.setValue(255)
    template_tab.green_offset_input.setValue(0)
    template_tab.blue_offset_input.setValue(64)

    settings = template_tab.get_values()

    assert settings.crate_red_multiplier == 0
    assert settings.crate_green_multiplier == 255
    assert settings.crate_blue_multiplier == 128
    assert settings.crate_red_offset == 255
    assert settings.crate_green_offset == 0
    assert settings.crate_blue_offset == 64

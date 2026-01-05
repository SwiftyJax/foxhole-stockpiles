"""Tests for AdvancedSettingRow."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QLineEdit, QSpinBox

from foxhole_stockpiles.gui.utils.advanced_setting_widget import AdvancedSettingRow


@pytest.fixture
def widget(qtbot: Any) -> AdvancedSettingRow:
    """Create an AdvancedSettingRow instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        AdvancedSettingRow: Widget instance
    """
    input_widget = QLineEdit()
    widget = AdvancedSettingRow("Test Setting", input_widget, "This is a warning")
    qtbot.addWidget(widget)
    return widget


def test_widget_initialization(widget: AdvancedSettingRow) -> None:
    """Test AdvancedSettingRow initialization.

    Args:
        widget (AdvancedSettingRow): Widget instance
    """
    # Widget should have an input widget
    assert widget.input_widget is not None
    assert isinstance(widget.input_widget, QLineEdit)


def test_widget_has_warning_icon(widget: AdvancedSettingRow) -> None:
    """Test widget has warning icon with tooltip.

    Args:
        widget (AdvancedSettingRow): Widget instance
    """
    # Check that layout contains widgets (warning label and input widget)
    layout = widget.layout()
    assert layout is not None
    assert layout.count() >= 2  # At least warning label and input widget


def test_widget_set_reset_callback(qtbot: Any, widget: AdvancedSettingRow) -> None:
    """Test setting reset callback adds reset button.

    Args:
        qtbot: PyQt test fixture
        widget (AdvancedSettingRow): Widget instance
    """
    callback = MagicMock()
    layout = widget.layout()
    assert layout is not None
    initial_count = layout.count()

    widget.set_reset_callback(callback)

    # Should have added a reset button
    assert layout.count() == initial_count + 1


def test_widget_reset_button_calls_callback(qtbot: Any) -> None:
    """Test reset button calls callback when clicked.

    Args:
        qtbot: PyQt test fixture
    """
    callback = MagicMock()
    input_widget = QLineEdit()
    widget = AdvancedSettingRow("Test", input_widget, "Warning text")
    qtbot.addWidget(widget)

    widget.set_reset_callback(callback)

    # Find the reset button (last widget in layout)
    layout = widget.layout()
    assert layout is not None
    item = layout.itemAt(layout.count() - 1)
    assert item is not None
    reset_button = item.widget()
    assert reset_button is not None

    # Click it
    qtbot.mouseClick(reset_button, Qt.MouseButton.LeftButton)

    callback.assert_called_once()


def test_widget_with_spinbox(qtbot: Any) -> None:
    """Test widget with QSpinBox input.

    Args:
        qtbot: PyQt test fixture
    """
    spin_box = QSpinBox()
    spin_box.setValue(42)
    widget = AdvancedSettingRow("Number Setting", spin_box, "Warning about numbers")
    qtbot.addWidget(widget)

    assert widget.input_widget == spin_box
    assert spin_box.value() == 42


def test_widget_with_checkbox(qtbot: Any) -> None:
    """Test widget with QCheckBox input.

    Args:
        qtbot: PyQt test fixture
    """
    checkbox = QCheckBox()
    checkbox.setChecked(True)
    widget = AdvancedSettingRow("Bool Setting", checkbox, "Warning about booleans")
    qtbot.addWidget(widget)

    assert widget.input_widget == checkbox
    assert checkbox.isChecked()


def test_widget_warning_tooltip_contains_text(qtbot: Any) -> None:
    """Test warning tooltip contains the warning text.

    Args:
        qtbot: PyQt test fixture
    """
    warning_text = "Custom warning message"
    input_widget = QLineEdit()
    widget = AdvancedSettingRow("Test", input_widget, warning_text)
    qtbot.addWidget(widget)

    # Get the warning label (first widget in layout)
    layout = widget.layout()
    assert layout is not None
    item = layout.itemAt(0)
    assert item is not None
    warning_label = item.widget()
    assert warning_label is not None

    # Tooltip should contain our warning text
    assert warning_text in warning_label.toolTip()

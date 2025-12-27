"""Utility for creating advanced setting widgets with warnings and reset buttons."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


def get_model_default(model_class: type[BaseModel], field_name: str) -> Any:
    """Get the default value for a field from a Pydantic model.

    Args:
        model_class (type[BaseModel]): The Pydantic model class.
        field_name (str): The name of the field.

    Returns:
        Any: The default value for the field.
    """
    field_info = model_class.model_fields.get(field_name)
    if field_info and field_info.default is not None:
        return field_info.default
    # If no default, return the default_factory result
    if field_info and field_info.default_factory is not None:
        factory = field_info.default_factory
        if callable(factory):
            return factory()  # type: ignore[call-arg]
    return None


class AdvancedSettingRow(QWidget):
    """Widget that wraps a setting input with warning icon and reset button."""

    def __init__(
        self,
        label: str,
        input_widget: QWidget,
        warning_text: str,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the advanced setting row.

        Args:
            label (str): Label text for the setting.
            input_widget (QWidget): The input widget (QLineEdit, QSpinBox, etc.).
            warning_text (str): Warning tooltip text.
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.input_widget = input_widget

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Warning icon
        warning_label = QLabel("⚠️")
        warning_label.setToolTip(
            f"<b>Advanced Setting</b><br>{warning_text}<br><br>"
            f"Modifying this setting incorrectly can cause system failures."
        )
        warning_label.setStyleSheet("QLabel { color: #ff9800; font-size: 14px; }")
        layout.addWidget(warning_label)

        # Input widget
        layout.addWidget(input_widget, 1)

    def set_reset_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback for the reset button.

        Args:
            callback (Callable[[], None]): Function to call when reset is clicked.
        """
        reset_btn = QPushButton("↺")
        reset_btn.setFixedWidth(30)
        reset_btn.setToolTip("Reset to default value")
        reset_btn.clicked.connect(callback)
        reset_btn.setStyleSheet("QPushButton { font-size: 16px; }")
        layout = self.layout()
        if layout is not None:
            layout.addWidget(reset_btn)

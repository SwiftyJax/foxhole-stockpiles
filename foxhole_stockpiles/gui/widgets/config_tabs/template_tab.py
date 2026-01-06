"""Template settings tab."""

from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.templates import TemplateSettings


class TemplateTab(QWidget):
    """Tab for Template configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Template tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Add warning header
        warning_header = QWidget()
        warning_layout = QHBoxLayout(warning_header)
        warning_layout.setContentsMargins(0, 0, 0, 0)

        info_label = QLabel(
            "⚠️ <b>Advanced Settings:</b> Template settings configure crate overlay "
            "color transformation. "
            "These values are used when generating crated versions of item icons. "
            "<b style='color: #d32f2f;'>Incorrect values will break template generation.</b>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "QLabel { background-color: palette(alternate-base); padding: 10px; "
            "border: 2px solid #FF9800; }"
        )
        warning_layout.addWidget(info_label, 1)

        reset_all_btn = QPushButton("Reset All to Defaults")
        reset_all_btn.clicked.connect(self.reset_all_to_defaults)
        reset_all_btn.setStyleSheet("QPushButton { padding: 8px; }")
        warning_layout.addWidget(reset_all_btn)

        layout.addWidget(warning_header)

        # RGB Multipliers Group
        multipliers_group = QGroupBox("RGB Multipliers (0-255)")
        multipliers_layout = QFormLayout()
        multipliers_group.setLayout(multipliers_layout)

        red_mult_label = QLabel("Red Multiplier:")
        red_mult_label.setToolTip(
            "Red channel multiplier for crate overlay color transformation.\n\n"
            "Value 0-255, will be divided by 255 during processing.\n"
            "Controls how much of the red channel is retained in crated item icons."
        )
        self.red_mult_input = QSpinBox()
        self.red_mult_input.setRange(0, 255)
        self.red_mult_input.setValue(154)
        multipliers_layout.addRow(red_mult_label, self.red_mult_input)

        green_mult_label = QLabel("Green Multiplier:")
        green_mult_label.setToolTip(
            "Green channel multiplier for crate overlay color transformation.\n\n"
            "Value 0-255, will be divided by 255 during processing.\n"
            "Controls how much of the green channel is retained in crated item icons."
        )
        self.green_mult_input = QSpinBox()
        self.green_mult_input.setRange(0, 255)
        self.green_mult_input.setValue(152)
        multipliers_layout.addRow(green_mult_label, self.green_mult_input)

        blue_mult_label = QLabel("Blue Multiplier:")
        blue_mult_label.setToolTip(
            "Blue channel multiplier for crate overlay color transformation.\n\n"
            "Value 0-255, will be divided by 255 during processing.\n"
            "Controls how much of the blue channel is retained in crated item icons."
        )
        self.blue_mult_input = QSpinBox()
        self.blue_mult_input.setRange(0, 255)
        self.blue_mult_input.setValue(145)
        multipliers_layout.addRow(blue_mult_label, self.blue_mult_input)

        layout.addWidget(multipliers_group)

        # RGB Offsets Group
        offsets_group = QGroupBox("RGB Offsets (0-255)")
        offsets_layout = QFormLayout()
        offsets_group.setLayout(offsets_layout)

        red_offset_label = QLabel("Red Offset:")
        red_offset_label.setToolTip(
            "Red channel offset added after multiplication.\n\n"
            "Value 0-255. Adjusts the base red level of crated item icons.\n"
            "Used to match the brownish crate overlay color."
        )
        self.red_offset_input = QSpinBox()
        self.red_offset_input.setRange(0, 255)
        self.red_offset_input.setValue(89)
        offsets_layout.addRow(red_offset_label, self.red_offset_input)

        green_offset_label = QLabel("Green Offset:")
        green_offset_label.setToolTip(
            "Green channel offset added after multiplication.\n\n"
            "Value 0-255. Adjusts the base green level of crated item icons.\n"
            "Used to match the brownish crate overlay color."
        )
        self.green_offset_input = QSpinBox()
        self.green_offset_input.setRange(0, 255)
        self.green_offset_input.setValue(87)
        offsets_layout.addRow(green_offset_label, self.green_offset_input)

        blue_offset_label = QLabel("Blue Offset:")
        blue_offset_label.setToolTip(
            "Blue channel offset added after multiplication.\n\n"
            "Value 0-255. Adjusts the base blue level of crated item icons.\n"
            "Used to match the brownish crate overlay color."
        )
        self.blue_offset_input = QSpinBox()
        self.blue_offset_input.setRange(0, 255)
        self.blue_offset_input.setValue(82)
        offsets_layout.addRow(blue_offset_label, self.blue_offset_input)

        layout.addWidget(offsets_group)

        layout.addStretch()

    def reset_all_to_defaults(self) -> None:
        """Reset all template settings to default values from the model."""
        reply = QMessageBox.question(
            self,
            "Reset Template Settings",
            "Reset all template settings to default values?\n\n"
            "This will restore the factory defaults for crate color transformation.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            defaults = TemplateSettings()
            self.set_values(defaults)

    def set_values(self, settings: TemplateSettings) -> None:
        """Set widget values from settings.

        Args:
            settings (TemplateSettings): TemplateSettings instance to load values from.
        """
        self.red_mult_input.setValue(settings.crate_red_multiplier)
        self.green_mult_input.setValue(settings.crate_green_multiplier)
        self.blue_mult_input.setValue(settings.crate_blue_multiplier)
        self.red_offset_input.setValue(settings.crate_red_offset)
        self.green_offset_input.setValue(settings.crate_green_offset)
        self.blue_offset_input.setValue(settings.crate_blue_offset)

    def get_values(self) -> TemplateSettings:
        """Get current values from widgets.

        Returns:
            TemplateSettings: TemplateSettings instance with current values from widgets
        """
        return TemplateSettings(
            crate_red_multiplier=self.red_mult_input.value(),
            crate_green_multiplier=self.green_mult_input.value(),
            crate_blue_multiplier=self.blue_mult_input.value(),
            crate_red_offset=self.red_offset_input.value(),
            crate_green_offset=self.green_offset_input.value(),
            crate_blue_offset=self.blue_offset_input.value(),
        )

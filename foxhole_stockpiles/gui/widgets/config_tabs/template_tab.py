"""Template settings tab."""

from PySide6.QtWidgets import (
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
from foxhole_stockpiles.i18n import off_language_changed, on_language_changed, t


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

        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet(
            "QLabel { background-color: palette(alternate-base); padding: 10px; "
            "border: 2px solid #FF9800; }"
        )
        warning_layout.addWidget(self.info_label, 1)

        self.reset_all_btn = QPushButton()
        self.reset_all_btn.clicked.connect(self.reset_all_to_defaults)
        self.reset_all_btn.setStyleSheet("QPushButton { padding: 8px; }")
        warning_layout.addWidget(self.reset_all_btn)

        layout.addWidget(warning_header)

        # RGB Multipliers Group
        self.multipliers_group = QGroupBox()
        multipliers_layout = QFormLayout()
        self.multipliers_group.setLayout(multipliers_layout)

        self.red_mult_label = QLabel()
        self.red_mult_input = QSpinBox()
        self.red_mult_input.setRange(0, 255)
        self.red_mult_input.setValue(154)
        multipliers_layout.addRow(self.red_mult_label, self.red_mult_input)

        self.green_mult_label = QLabel()
        self.green_mult_input = QSpinBox()
        self.green_mult_input.setRange(0, 255)
        self.green_mult_input.setValue(152)
        multipliers_layout.addRow(self.green_mult_label, self.green_mult_input)

        self.blue_mult_label = QLabel()
        self.blue_mult_input = QSpinBox()
        self.blue_mult_input.setRange(0, 255)
        self.blue_mult_input.setValue(145)
        multipliers_layout.addRow(self.blue_mult_label, self.blue_mult_input)

        layout.addWidget(self.multipliers_group)

        # RGB Offsets Group
        self.offsets_group = QGroupBox()
        offsets_layout = QFormLayout()
        self.offsets_group.setLayout(offsets_layout)

        self.red_offset_label = QLabel()
        self.red_offset_input = QSpinBox()
        self.red_offset_input.setRange(0, 255)
        self.red_offset_input.setValue(89)
        offsets_layout.addRow(self.red_offset_label, self.red_offset_input)

        self.green_offset_label = QLabel()
        self.green_offset_input = QSpinBox()
        self.green_offset_input.setRange(0, 255)
        self.green_offset_input.setValue(87)
        offsets_layout.addRow(self.green_offset_label, self.green_offset_input)

        self.blue_offset_label = QLabel()
        self.blue_offset_input = QSpinBox()
        self.blue_offset_input.setRange(0, 255)
        self.blue_offset_input.setValue(82)
        offsets_layout.addRow(self.blue_offset_label, self.blue_offset_input)

        layout.addWidget(self.offsets_group)

        layout.addStretch()

        # Apply translations
        self.retranslate()

        # Connect to language change signal with cleanup
        self._language_callback = self._on_language_changed
        on_language_changed(self._language_callback)
        self.destroyed.connect(lambda cb=self._language_callback: off_language_changed(cb))

    def _on_language_changed(self, _language: str) -> None:
        """Handle language change event."""
        self.retranslate()

    def retranslate(self) -> None:
        """Update all translatable strings."""
        self.info_label.setText(t("template_tab.warning_header"))
        self.reset_all_btn.setText(t("template_tab.reset_all"))

        self.multipliers_group.setTitle(t("template_tab.multipliers_group"))
        self.offsets_group.setTitle(t("template_tab.offsets_group"))

        self.red_mult_label.setText(t("template_tab.red_mult"))
        self.red_mult_label.setToolTip(t("template_tab.red_mult_tooltip"))

        self.green_mult_label.setText(t("template_tab.green_mult"))
        self.green_mult_label.setToolTip(t("template_tab.green_mult_tooltip"))

        self.blue_mult_label.setText(t("template_tab.blue_mult"))
        self.blue_mult_label.setToolTip(t("template_tab.blue_mult_tooltip"))

        self.red_offset_label.setText(t("template_tab.red_offset"))
        self.red_offset_label.setToolTip(t("template_tab.red_offset_tooltip"))

        self.green_offset_label.setText(t("template_tab.green_offset"))
        self.green_offset_label.setToolTip(t("template_tab.green_offset_tooltip"))

        self.blue_offset_label.setText(t("template_tab.blue_offset"))
        self.blue_offset_label.setToolTip(t("template_tab.blue_offset_tooltip"))

    def reset_all_to_defaults(self) -> None:
        """Reset all template settings to default values from the model."""
        reply = QMessageBox.question(
            self,
            t("template_tab.reset_title"),
            t("template_tab.reset_message"),
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

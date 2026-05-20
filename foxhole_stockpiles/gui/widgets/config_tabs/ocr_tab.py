"""OCR settings tab."""

from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.ocr import OCRSettings
from foxhole_stockpiles.i18n import off_language_changed, on_language_changed, t


class OCRTab(QWidget):
    """Tab for OCR configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the OCR tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        # Use scroll area for long form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self._form_layout = QFormLayout(scroll_content)
        scroll.setWidget(scroll_content)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

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

        self._form_layout.addRow(warning_header)

        # Height (base resolution)
        self.height_label = QLabel()
        self.height_input = QSpinBox()
        self.height_input.setRange(1080, 4320)
        self.height_input.setValue(2160)
        self._form_layout.addRow(self.height_label, self.height_input)

        # Box dimensions
        self.box_width_label = QLabel()
        self.box_width_input = QSpinBox()
        self.box_width_input.setRange(10, 500)
        self._form_layout.addRow(self.box_width_label, self.box_width_input)

        self.box_height_label = QLabel()
        self.box_height_input = QSpinBox()
        self.box_height_input.setRange(10, 500)
        self._form_layout.addRow(self.box_height_label, self.box_height_input)

        # Offsets
        self.column_offset_label = QLabel()
        self.column_offset_input = QSpinBox()
        self.column_offset_input.setRange(0, 1000)
        self._form_layout.addRow(self.column_offset_label, self.column_offset_input)

        self.row_offset_label = QLabel()
        self.row_offset_input = QSpinBox()
        self.row_offset_input.setRange(0, 1000)
        self._form_layout.addRow(self.row_offset_label, self.row_offset_input)

        self.group_offset_label = QLabel()
        self.group_offset_input = QSpinBox()
        self.group_offset_input.setRange(0, 1000)
        self._form_layout.addRow(self.group_offset_label, self.group_offset_input)

        # Title region
        self.title_margin_label = QLabel()
        self.title_margin_input = QSpinBox()
        self.title_margin_input.setRange(0, 500)
        self._form_layout.addRow(self.title_margin_label, self.title_margin_input)

        self.title_min_width_label = QLabel()
        self.title_min_width_input = QSpinBox()
        self.title_min_width_input.setRange(0, 1000)
        self._form_layout.addRow(self.title_min_width_label, self.title_min_width_input)

        self.title_height_label = QLabel()
        self.title_height_input = QSpinBox()
        self.title_height_input.setRange(0, 500)
        self._form_layout.addRow(self.title_height_label, self.title_height_input)

        # Icon to quantity offset
        self.icon_to_quantity_label = QLabel()
        self.icon_to_quantity_offset_input = QSpinBox()
        self.icon_to_quantity_offset_input.setRange(0, 500)
        self._form_layout.addRow(self.icon_to_quantity_label, self.icon_to_quantity_offset_input)

        # Gamma thresholds
        self.gray_lower_label = QLabel()
        self.gray_lower_input = QSpinBox()
        self.gray_lower_input.setRange(0, 255)
        self._form_layout.addRow(self.gray_lower_label, self.gray_lower_input)

        self.gray_upper_label = QLabel()
        self.gray_upper_input = QSpinBox()
        self.gray_upper_input.setRange(0, 255)
        self._form_layout.addRow(self.gray_upper_label, self.gray_upper_input)

        # Pixel tolerance
        self.pixel_diff_label = QLabel()
        self.pixel_diff_tolerance_input = QSpinBox()
        self.pixel_diff_tolerance_input.setRange(0, 50)
        self._form_layout.addRow(self.pixel_diff_label, self.pixel_diff_tolerance_input)

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
        self.info_label.setText(t("ocr_tab.warning_header"))
        self.reset_all_btn.setText(t("ocr_tab.reset_all"))

        self.height_label.setText(t("ocr_tab.base_height"))
        self.height_label.setToolTip(t("ocr_tab.base_height_tooltip"))

        self.box_width_label.setText(t("ocr_tab.box_width"))
        self.box_width_label.setToolTip(t("ocr_tab.box_width_tooltip"))

        self.box_height_label.setText(t("ocr_tab.box_height"))
        self.box_height_label.setToolTip(t("ocr_tab.box_height_tooltip"))

        self.column_offset_label.setText(t("ocr_tab.column_offset"))
        self.column_offset_label.setToolTip(t("ocr_tab.column_offset_tooltip"))

        self.row_offset_label.setText(t("ocr_tab.row_offset"))
        self.row_offset_label.setToolTip(t("ocr_tab.row_offset_tooltip"))

        self.group_offset_label.setText(t("ocr_tab.group_offset"))
        self.group_offset_label.setToolTip(t("ocr_tab.group_offset_tooltip"))

        self.title_margin_label.setText(t("ocr_tab.title_margin"))
        self.title_margin_label.setToolTip(t("ocr_tab.title_margin_tooltip"))

        self.title_min_width_label.setText(t("ocr_tab.title_min_width"))
        self.title_min_width_label.setToolTip(t("ocr_tab.title_min_width_tooltip"))

        self.title_height_label.setText(t("ocr_tab.title_height"))
        self.title_height_label.setToolTip(t("ocr_tab.title_height_tooltip"))

        self.icon_to_quantity_label.setText(t("ocr_tab.icon_to_quantity_offset"))
        self.icon_to_quantity_label.setToolTip(t("ocr_tab.icon_to_quantity_tooltip"))

        self.gray_lower_label.setText(t("ocr_tab.gray_lower"))
        self.gray_lower_label.setToolTip(t("ocr_tab.gray_lower_tooltip"))

        self.gray_upper_label.setText(t("ocr_tab.gray_upper"))
        self.gray_upper_label.setToolTip(t("ocr_tab.gray_upper_tooltip"))

        self.pixel_diff_label.setText(t("ocr_tab.pixel_diff_tolerance"))
        self.pixel_diff_label.setToolTip(t("ocr_tab.pixel_diff_tooltip"))

    def reset_all_to_defaults(self) -> None:
        """Reset all OCR settings to default values from the model."""
        reply = QMessageBox.question(
            self,
            t("ocr_tab.reset_title"),
            t("ocr_tab.reset_message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            defaults = OCRSettings()
            self.set_values(defaults)

    def set_values(self, settings: OCRSettings) -> None:
        """Set widget values from settings.

        Args:
            settings (OCRSettings): OCRSettings instance to load values from.
        """
        self.height_input.setValue(settings.height)
        self.box_width_input.setValue(settings.box_width)
        self.box_height_input.setValue(settings.box_height)
        self.column_offset_input.setValue(settings.column_offset)
        self.row_offset_input.setValue(settings.row_offset)
        self.group_offset_input.setValue(settings.group_offset)
        self.title_margin_input.setValue(settings.title_margin)
        self.title_min_width_input.setValue(settings.title_min_width)
        self.title_height_input.setValue(settings.title_height)
        self.icon_to_quantity_offset_input.setValue(settings.icon_to_quantity_offset)
        self.gray_lower_input.setValue(settings.gray_lower)
        self.gray_upper_input.setValue(settings.gray_upper)
        self.pixel_diff_tolerance_input.setValue(settings.pixel_diff_tolerance)

    def get_values(self) -> OCRSettings:
        """Get current values from widgets.

        Returns:
            OCRSettings: OCRSettings instance with current values from widgets
        """
        return OCRSettings(
            height=self.height_input.value(),
            box_width=self.box_width_input.value(),
            box_height=self.box_height_input.value(),
            column_offset=self.column_offset_input.value(),
            row_offset=self.row_offset_input.value(),
            group_offset=self.group_offset_input.value(),
            title_margin=self.title_margin_input.value(),
            title_min_width=self.title_min_width_input.value(),
            title_height=self.title_height_input.value(),
            icon_to_quantity_offset=self.icon_to_quantity_offset_input.value(),
            gray_lower=self.gray_lower_input.value(),
            gray_upper=self.gray_upper_input.value(),
            pixel_diff_tolerance=self.pixel_diff_tolerance_input.value(),
        )

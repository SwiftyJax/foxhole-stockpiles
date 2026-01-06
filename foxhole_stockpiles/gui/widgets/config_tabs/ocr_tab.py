"""OCR settings tab."""

from PyQt6.QtWidgets import (
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
        layout = QFormLayout(scroll_content)
        scroll.setWidget(scroll_content)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        # Add warning header
        warning_header = QWidget()
        warning_layout = QHBoxLayout(warning_header)
        warning_layout.setContentsMargins(0, 0, 0, 0)

        info_label = QLabel(
            "⚠️ <b>Advanced Settings:</b> OCR settings define the layout dimensions "
            "for stockpile detection. "
            "These are scaled from 2160p base resolution. "
            "<b style='color: #d32f2f;'>Incorrect values will cause detection to fail "
            "completely.</b>"
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

        layout.addRow(warning_header)

        # Height (base resolution)
        height_label = QLabel("Base Height:")
        height_label.setToolTip(
            "Base screen resolution height for layout calculations.\n\n"
            "All layout dimensions are scaled from this base (2160p).\n"
            "Default: 2160 (for 4K screenshots)."
        )
        self.height_input = QSpinBox()
        self.height_input.setRange(1080, 4320)
        self.height_input.setValue(2160)
        layout.addRow(height_label, self.height_input)

        # Box dimensions
        box_width_label = QLabel("Box Width:")
        box_width_label.setToolTip(
            "Width of each quantity box in the stockpile grid.\n\n"
            "Measured in pixels at base resolution.\n"
            "Incorrect values will cause detection to fail."
        )
        self.box_width_input = QSpinBox()
        self.box_width_input.setRange(10, 500)
        layout.addRow(box_width_label, self.box_width_input)

        box_height_label = QLabel("Box Height:")
        box_height_label.setToolTip(
            "Height of each quantity box in the stockpile grid.\n\n"
            "Measured in pixels at base resolution.\n"
            "Incorrect values will cause detection to fail."
        )
        self.box_height_input = QSpinBox()
        self.box_height_input.setRange(10, 500)
        layout.addRow(box_height_label, self.box_height_input)

        # Offsets
        column_offset_label = QLabel("Column Offset:")
        column_offset_label.setToolTip(
            "Horizontal spacing between columns in the stockpile grid.\n\n"
            "Measured in pixels at base resolution.\n"
            "Affects how the scanner moves from one column to the next."
        )
        self.column_offset_input = QSpinBox()
        self.column_offset_input.setRange(0, 1000)
        layout.addRow(column_offset_label, self.column_offset_input)

        row_offset_label = QLabel("Row Offset:")
        row_offset_label.setToolTip(
            "Vertical spacing between rows in the stockpile grid.\n\n"
            "Measured in pixels at base resolution.\n"
            "Affects how the scanner moves from one row to the next."
        )
        self.row_offset_input = QSpinBox()
        self.row_offset_input.setRange(0, 1000)
        layout.addRow(row_offset_label, self.row_offset_input)

        group_offset_label = QLabel("Group Offset:")
        group_offset_label.setToolTip(
            "Vertical spacing between stockpile groups.\n\n"
            "Measured in pixels at base resolution.\n"
            "Used when multiple stockpile sections are stacked vertically."
        )
        self.group_offset_input = QSpinBox()
        self.group_offset_input.setRange(0, 1000)
        layout.addRow(group_offset_label, self.group_offset_input)

        # Title region
        title_margin_label = QLabel("Title Margin:")
        title_margin_label.setToolTip(
            "Margin around stockpile title text.\n\n"
            "Used for detecting and extracting stockpile names.\n"
            "Affects title region boundary detection."
        )
        self.title_margin_input = QSpinBox()
        self.title_margin_input.setRange(0, 500)
        layout.addRow(title_margin_label, self.title_margin_input)

        title_min_width_label = QLabel("Title Min Width:")
        title_min_width_label.setToolTip(
            "Minimum width for a valid title region.\n\n"
            "Helps filter out false title detections.\n"
            "Too low may include noise, too high may skip short titles."
        )
        self.title_min_width_input = QSpinBox()
        self.title_min_width_input.setRange(0, 1000)
        layout.addRow(title_min_width_label, self.title_min_width_input)

        title_height_label = QLabel("Title Height:")
        title_height_label.setToolTip(
            "Expected height of stockpile title text.\n\n"
            "Used for title region extraction.\n"
            "Should match the game's title font size at base resolution."
        )
        self.title_height_input = QSpinBox()
        self.title_height_input.setRange(0, 500)
        layout.addRow(title_height_label, self.title_height_input)

        # Icon to quantity offset
        icon_to_quantity_label = QLabel("Icon to Quantity Offset:")
        icon_to_quantity_label.setToolTip(
            "Horizontal offset from quantity box to item icon (icon is to the left).\n\n"
            "Measured in pixels at base resolution.\n"
            "Used to locate the item icon relative to its quantity box."
        )
        self.icon_to_quantity_offset_input = QSpinBox()
        self.icon_to_quantity_offset_input.setRange(0, 500)
        layout.addRow(icon_to_quantity_label, self.icon_to_quantity_offset_input)

        # Gamma thresholds
        gray_lower_label = QLabel("Gray Lower Threshold:")
        gray_lower_label.setToolTip(
            "Lower grayscale threshold for quantity box detection (0-255).\n\n"
            "Depends on user's screen gamma settings.\n"
            "Typical range: 15-98. Adjust if quantity boxes aren't detected properly."
        )
        self.gray_lower_input = QSpinBox()
        self.gray_lower_input.setRange(0, 255)
        layout.addRow(gray_lower_label, self.gray_lower_input)

        gray_upper_label = QLabel("Gray Upper Threshold:")
        gray_upper_label.setToolTip(
            "Upper grayscale threshold for quantity box detection (0-255).\n\n"
            "Depends on user's screen gamma settings.\n"
            "Typical range: 15-98. Adjust if quantity boxes aren't detected properly."
        )
        self.gray_upper_input = QSpinBox()
        self.gray_upper_input.setRange(0, 255)
        layout.addRow(gray_upper_label, self.gray_upper_input)

        # Pixel tolerance
        pixel_diff_label = QLabel("Pixel Diff Tolerance:")
        pixel_diff_label.setToolTip(
            "Allowed pixel variation for any detection calculation.\n\n"
            "Accounts for minor position shifts across different resolutions.\n"
            "Example: Icon column alignment may vary by 1-2 pixels depending on resolution."
        )
        self.pixel_diff_tolerance_input = QSpinBox()
        self.pixel_diff_tolerance_input.setRange(0, 50)
        layout.addRow(pixel_diff_label, self.pixel_diff_tolerance_input)

    def reset_all_to_defaults(self) -> None:
        """Reset all OCR settings to default values from the model."""
        reply = QMessageBox.question(
            self,
            "Reset OCR Settings",
            "Reset all OCR settings to default values?\n\n"
            "This will restore the factory defaults for layout detection.",
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

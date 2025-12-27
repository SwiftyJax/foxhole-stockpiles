"""Scanner settings tab."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.scanner import ScannerSettings


class ScannerTab(QWidget):
    """Tab for Scanner configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Scanner tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        # Use scroll area for potentially long form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QFormLayout(scroll_content)
        scroll.setWidget(scroll_content)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        # Database Path (required)
        db_label = QLabel("Database Path:")
        db_label.setToolTip(
            "Path to the template database file containing item icons for recognition.\n\n"
            "This is a required HDF5 (.h5) file that must be generated before scanning.\n"
            "Use the 'update-db' command to create or update this file."
        )
        db_layout = QHBoxLayout()
        self.database_path_input = QLineEdit()
        self.database_path_input.setPlaceholderText("Path to template database (.h5 file)")
        db_browse = QPushButton("Browse...")
        db_browse.clicked.connect(self.browse_database)
        db_layout.addWidget(self.database_path_input)
        db_layout.addWidget(db_browse)
        layout.addRow(db_label, db_layout)

        # Template Cache Size
        cache_label = QLabel("Template Cache Size:")
        cache_label.setToolTip(
            "Number of template resolutions to keep in memory for faster matching.\n\n"
            "Maximum: 16 (total number of supported resolutions).\n"
            "Setting higher than 16 has no effect.\n"
            "Recommended: 0, 1, or 2 for low-memory servers."
        )
        self.cache_size_input = QSpinBox()
        self.cache_size_input.setRange(0, 16)
        self.cache_size_input.setValue(16)
        layout.addRow(cache_label, self.cache_size_input)

        # Early Exit Threshold
        early_exit_label = QLabel("Early Exit Threshold:")
        early_exit_label.setToolTip(
            "Confidence threshold to stop searching early when a good match is found.\n\n"
            "Value between 0.0-1.0. Set to 0.0 to disable (always check all templates).\n"
            "Recommended: 0.99x (0.990-0.999) for speed, or 0.0 for accuracy.\n"
            "Intermediate values can cause false detections for some items."
        )
        self.early_exit_input = QDoubleSpinBox()
        self.early_exit_input.setRange(0.0, 1.0)
        self.early_exit_input.setSingleStep(0.01)
        self.early_exit_input.setDecimals(3)
        self.early_exit_input.setValue(0.0)
        layout.addRow(early_exit_label, self.early_exit_input)

        # Confidence Gap
        confidence_gap_label = QLabel("Confidence Gap:")
        confidence_gap_label.setToolTip(
            "Controls when alternative matches are included in JSON output as candidates.\n\n"
            "All items with confidence within this gap from the best match are included.\n"
            "Set to 0.0 to disable candidates (only include best match).\n\n"
            "Recommended: 0.1 (typically results in few items with alternatives per stockpile).\n"
            "At 0.2, about half the items will have candidates."
        )
        self.confidence_gap_input = QDoubleSpinBox()
        self.confidence_gap_input.setRange(0.0, 1.0)
        self.confidence_gap_input.setSingleStep(0.01)
        self.confidence_gap_input.setDecimals(3)
        self.confidence_gap_input.setValue(0.0)
        layout.addRow(confidence_gap_label, self.confidence_gap_input)

        # Custom Model
        custom_model_label = QLabel("Custom OCR Model:")
        custom_model_label.setStyleSheet("QLabel { color: #d32f2f; font-weight: bold; }")
        custom_model_label.setToolTip(
            "⚠️ CRITICAL: Custom Tesseract OCR model for number recognition.\n\n"
            "Default: 'renner_numbers' (optimized for Foxhole stockpile numbers).\n"
            "Changing this may cause number recognition to fail completely."
        )
        custom_model_layout = QHBoxLayout()
        self.custom_model_input = QLineEdit()
        self.custom_model_input.setPlaceholderText("renner_numbers")
        custom_model_reset = QPushButton("Reset")
        custom_model_reset.clicked.connect(self.reset_custom_model)
        custom_model_layout.addWidget(self.custom_model_input)
        custom_model_layout.addWidget(custom_model_reset)
        layout.addRow(custom_model_label, custom_model_layout)

        # Tessdata Path
        tessdata_label = QLabel("Tessdata Path:")
        tessdata_label.setStyleSheet("QLabel { color: #d32f2f; font-weight: bold; }")
        tessdata_label.setToolTip(
            "⚠️ CRITICAL: Path to Tesseract OCR data files directory.\n\n"
            "Default: './tessdata' (bundled with the application).\n"
            "Incorrect path will cause OCR text recognition to fail."
        )
        tessdata_layout = QHBoxLayout()
        self.tessdata_path_input = QLineEdit()
        self.tessdata_path_input.setPlaceholderText("./tessdata")
        tessdata_browse = QPushButton("Browse...")
        tessdata_browse.clicked.connect(self.browse_tessdata)
        tessdata_reset = QPushButton("Reset")
        tessdata_reset.clicked.connect(self.reset_tessdata_path)
        tessdata_layout.addWidget(self.tessdata_path_input)
        tessdata_layout.addWidget(tessdata_browse)
        tessdata_layout.addWidget(tessdata_reset)
        layout.addRow(tessdata_label, tessdata_layout)

        # Debug Mode
        debug_label = QLabel("Debug Mode:")
        debug_label.setToolTip(
            "Save debug images showing the detection process.\n\n"
            "Saves to current directory:\n"
            "• stockpile_detection_result.png - Original image with detection boxes\n"
            "• stockpile_quantities_result.png - Composite quantities image\n"
            "• stockpile_name_region.png - Extracted name region\n"
            "• stockpile_type_region.png - Extracted type region\n"
            "• stockpile_shard.png - Extracted shard region\n\n"
            "Useful for troubleshooting detection issues."
        )
        self.debug_mode_input = QCheckBox("Save debug images during scanning")
        layout.addRow(debug_label, self.debug_mode_input)

        # Extract Icons
        extract_label = QLabel("Extract Icons:")
        extract_label.setToolTip(
            "Save each detected item icon as a separate image file.\n\n"
            "Icons are saved to './icons/' folder with format: 'XXX_CODE.png'\n"
            "where XXX is the icon index (000, 001, etc.) and CODE is the detected item.\n\n"
            "Development setting - useful for creating new templates or debugging detection."
        )
        self.extract_icons_input = QCheckBox("Save detected icon images")
        layout.addRow(extract_label, self.extract_icons_input)

        # Screenshots Folder
        screenshots_label = QLabel("Screenshots Folder:")
        screenshots_label.setToolTip(
            "Optional folder to automatically save processed screenshots.\n\n"
            "When set, scanned images are saved to daily subfolders (YYYY-MM-DD)\n"
            "with format: Date_Time_StorageType_Name_Resolution.png\n\n"
            "Leave empty to disable screenshot archiving."
        )
        screenshots_layout = QHBoxLayout()
        self.screenshots_folder_input = QLineEdit()
        self.screenshots_folder_input.setPlaceholderText("Optional: folder to save screenshots")
        screenshots_browse = QPushButton("Browse...")
        screenshots_browse.clicked.connect(self.browse_screenshots)
        screenshots_layout.addWidget(self.screenshots_folder_input)
        screenshots_layout.addWidget(screenshots_browse)
        layout.addRow(screenshots_label, screenshots_layout)

        # Max NCC Candidates
        ncc_label = QLabel("Max NCC Candidates:")
        ncc_label.setToolTip(
            "Maximum number of template candidates to evaluate with NCC "
            "(Normalized Cross-Correlation).\n\n"
            "After perceptual hash pre-filtering, this limits detailed matching.\n"
            "Higher values are more accurate but slower. Recommended: 25."
        )
        self.max_ncc_input = QSpinBox()
        self.max_ncc_input.setRange(1, 100)
        self.max_ncc_input.setValue(25)
        layout.addRow(ncc_label, self.max_ncc_input)

        # pHash Threshold
        phash_label = QLabel("pHash Threshold:")
        phash_label.setToolTip(
            "Perceptual hash distance threshold for template pre-filtering.\n\n"
            "Lower values (0-10) are stricter, higher values (10-20) are more lenient.\n"
            "Too low may miss valid items, too high slows down matching.\n"
            "Recommended: 12 for balanced speed and accuracy."
        )
        self.phash_threshold_input = QSpinBox()
        self.phash_threshold_input.setRange(0, 64)
        self.phash_threshold_input.setValue(12)
        layout.addRow(phash_label, self.phash_threshold_input)

    def browse_database(self) -> None:
        """Open file dialog for database path."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Template Database",
            "",
            "HDF5 Files (*.h5);;All Files (*)",
        )
        if filepath:
            self.database_path_input.setText(filepath)

    def browse_tessdata(self) -> None:
        """Open folder dialog for tessdata path."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Tessdata Directory",
            "",
        )
        if folder:
            self.tessdata_path_input.setText(folder)

    def browse_screenshots(self) -> None:
        """Open folder dialog for screenshots folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Screenshots Directory",
            "",
        )
        if folder:
            self.screenshots_folder_input.setText(folder)

    def reset_custom_model(self) -> None:
        """Reset custom OCR model to default value."""
        defaults = ScannerSettings()
        self.custom_model_input.setText(defaults.custom_model)

    def reset_tessdata_path(self) -> None:
        """Reset tessdata path to default value."""
        defaults = ScannerSettings()
        self.tessdata_path_input.setText(str(defaults.tessdata_path))

    def set_values(self, settings: ScannerSettings) -> None:
        """Set widget values from settings.

        Args:
            settings (ScannerSettings): ScannerSettings instance to load values from.
        """
        self.database_path_input.setText(
            str(settings.database_path) if settings.database_path else ""
        )
        self.cache_size_input.setValue(settings.template_cache_size)
        self.early_exit_input.setValue(settings.early_exit_threshold)
        self.confidence_gap_input.setValue(settings.confidence_gap)
        self.custom_model_input.setText(settings.custom_model)
        self.tessdata_path_input.setText(str(settings.tessdata_path))
        self.debug_mode_input.setChecked(settings.debug_mode)
        self.extract_icons_input.setChecked(settings.extract_icons)
        self.screenshots_folder_input.setText(settings.screenshots_folder or "")
        self.max_ncc_input.setValue(settings.max_ncc_candidates)
        self.phash_threshold_input.setValue(settings.phash_threshold)

    def get_values(self) -> ScannerSettings:
        """Get current values from widgets.

        Returns:
            ScannerSettings: ScannerSettings instance with current values from widgets.
        """
        db_path_text = self.database_path_input.text()
        return ScannerSettings(
            database_path=Path(db_path_text) if db_path_text else None,
            template_cache_size=self.cache_size_input.value(),
            early_exit_threshold=self.early_exit_input.value(),
            confidence_gap=self.confidence_gap_input.value(),
            custom_model=self.custom_model_input.text(),
            tessdata_path=self.tessdata_path_input.text(),
            debug_mode=self.debug_mode_input.isChecked(),
            extract_icons=self.extract_icons_input.isChecked(),
            screenshots_folder=self.screenshots_folder_input.text() or "",
            max_ncc_candidates=self.max_ncc_input.value(),
            phash_threshold=self.phash_threshold_input.value(),
        )

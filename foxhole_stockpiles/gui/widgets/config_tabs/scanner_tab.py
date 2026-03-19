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
from foxhole_stockpiles.enums.config_level import ConfigLevel
from foxhole_stockpiles.i18n import off_language_changed, on_language_changed, t


class ScannerTab(QWidget):
    """Tab for Scanner configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Scanner tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        # Lists to track widgets at each level
        self._advanced_widgets: list[QWidget] = []
        self._developer_widgets: list[QWidget] = []
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        # Use scroll area for potentially long form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self._form_layout = QFormLayout(scroll_content)
        scroll.setWidget(scroll_content)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        # Database Path (required) - BASIC
        self.db_label = QLabel()
        db_layout_widget = QWidget()
        db_layout = QHBoxLayout(db_layout_widget)
        db_layout.setContentsMargins(0, 0, 0, 0)
        self.database_path_input = QLineEdit()
        self.db_browse = QPushButton()
        self.db_browse.clicked.connect(self.browse_database)
        db_layout.addWidget(self.database_path_input)
        db_layout.addWidget(self.db_browse)
        self._form_layout.addRow(self.db_label, db_layout_widget)

        # Template Cache Size - BASIC
        self.cache_label = QLabel()
        self.cache_size_input = QSpinBox()
        self.cache_size_input.setRange(0, 16)
        self.cache_size_input.setValue(16)
        self._form_layout.addRow(self.cache_label, self.cache_size_input)

        # Early Exit Threshold - BASIC
        self.early_exit_label = QLabel()
        self.early_exit_input = QDoubleSpinBox()
        self.early_exit_input.setRange(0.0, 1.0)
        self.early_exit_input.setSingleStep(0.01)
        self.early_exit_input.setDecimals(3)
        self.early_exit_input.setValue(0.0)
        self._form_layout.addRow(self.early_exit_label, self.early_exit_input)

        # Confidence Gap - BASIC
        self.confidence_gap_label = QLabel()
        self.confidence_gap_input = QDoubleSpinBox()
        self.confidence_gap_input.setRange(0.0, 1.0)
        self.confidence_gap_input.setSingleStep(0.01)
        self.confidence_gap_input.setDecimals(3)
        self.confidence_gap_input.setValue(0.0)
        self._form_layout.addRow(self.confidence_gap_label, self.confidence_gap_input)

        # Screenshots Folder - BASIC
        self.screenshots_label = QLabel()
        screenshots_layout_widget = QWidget()
        screenshots_layout = QHBoxLayout(screenshots_layout_widget)
        screenshots_layout.setContentsMargins(0, 0, 0, 0)
        self.screenshots_folder_input = QLineEdit()
        self.screenshots_browse = QPushButton()
        self.screenshots_browse.clicked.connect(self.browse_screenshots)
        screenshots_layout.addWidget(self.screenshots_folder_input)
        screenshots_layout.addWidget(self.screenshots_browse)
        self._form_layout.addRow(self.screenshots_label, screenshots_layout_widget)

        # === ADVANCED LEVEL OPTIONS ===

        # Max NCC Candidates - ADVANCED
        self._ncc_label = QLabel()
        self.max_ncc_input = QSpinBox()
        self.max_ncc_input.setRange(1, 100)
        self.max_ncc_input.setValue(25)
        self._form_layout.addRow(self._ncc_label, self.max_ncc_input)
        self._advanced_widgets.extend([self._ncc_label, self.max_ncc_input])

        # pHash Threshold - ADVANCED
        self._phash_label = QLabel()
        self.phash_threshold_input = QSpinBox()
        self.phash_threshold_input.setRange(0, 64)
        self.phash_threshold_input.setValue(12)
        self._form_layout.addRow(self._phash_label, self.phash_threshold_input)
        self._advanced_widgets.extend([self._phash_label, self.phash_threshold_input])

        # NCC Tiebreaker Threshold - ADVANCED
        self._tiebreaker_label = QLabel()
        self.tiebreaker_threshold_input = QDoubleSpinBox()
        self.tiebreaker_threshold_input.setRange(0.0, 0.1)
        self.tiebreaker_threshold_input.setSingleStep(0.001)
        self.tiebreaker_threshold_input.setDecimals(3)
        self.tiebreaker_threshold_input.setValue(0.002)
        self._form_layout.addRow(self._tiebreaker_label, self.tiebreaker_threshold_input)
        self._advanced_widgets.extend([self._tiebreaker_label, self.tiebreaker_threshold_input])

        # Debug Mode - ADVANCED
        self._debug_label = QLabel()
        self.debug_mode_input = QCheckBox()
        self._form_layout.addRow(self._debug_label, self.debug_mode_input)
        self._advanced_widgets.extend([self._debug_label, self.debug_mode_input])

        # Extract Icons - ADVANCED
        self._extract_label = QLabel()
        self.extract_icons_input = QCheckBox()
        self._form_layout.addRow(self._extract_label, self.extract_icons_input)
        self._advanced_widgets.extend([self._extract_label, self.extract_icons_input])

        # === DEVELOPER LEVEL OPTIONS ===

        # Custom Model - DEVELOPER
        self._custom_model_label = QLabel()
        self._custom_model_label.setStyleSheet("QLabel { color: #d32f2f; font-weight: bold; }")
        self._custom_model_widget = QWidget()
        custom_model_layout = QHBoxLayout(self._custom_model_widget)
        custom_model_layout.setContentsMargins(0, 0, 0, 0)
        self.custom_model_input = QLineEdit()
        self.custom_model_input.setPlaceholderText("renner_numbers")
        self.custom_model_reset = QPushButton(t("common.reset"))
        self.custom_model_reset.clicked.connect(self.reset_custom_model)
        custom_model_layout.addWidget(self.custom_model_input)
        custom_model_layout.addWidget(self.custom_model_reset)
        self._form_layout.addRow(self._custom_model_label, self._custom_model_widget)
        self._developer_widgets.extend([self._custom_model_label, self._custom_model_widget])

        # Tessdata Path - DEVELOPER
        self._tessdata_label = QLabel()
        self._tessdata_label.setStyleSheet("QLabel { color: #d32f2f; font-weight: bold; }")
        self._tessdata_widget = QWidget()
        tessdata_layout = QHBoxLayout(self._tessdata_widget)
        tessdata_layout.setContentsMargins(0, 0, 0, 0)
        self.tessdata_path_input = QLineEdit()
        self.tessdata_path_input.setPlaceholderText("./tessdata")
        self.tessdata_browse = QPushButton()
        self.tessdata_browse.clicked.connect(self.browse_tessdata)
        self.tessdata_reset = QPushButton(t("common.reset"))
        self.tessdata_reset.clicked.connect(self.reset_tessdata_path)
        tessdata_layout.addWidget(self.tessdata_path_input)
        tessdata_layout.addWidget(self.tessdata_browse)
        tessdata_layout.addWidget(self.tessdata_reset)
        self._form_layout.addRow(self._tessdata_label, self._tessdata_widget)
        self._developer_widgets.extend([self._tessdata_label, self._tessdata_widget])

        # Apply translations
        self.retranslate()

        # Connect to language change signal with cleanup
        self._language_callback = self._on_language_changed
        on_language_changed(self._language_callback)
        self.destroyed.connect(lambda: off_language_changed(self._language_callback))

    def _on_language_changed(self, _language: str) -> None:
        """Handle language change event."""
        self.retranslate()

    def retranslate(self) -> None:
        """Update all translatable strings."""
        # Database Path
        self.db_label.setText(t("scanner_tab.database_path"))
        self.db_label.setToolTip(t("scanner_tab.database_path_tooltip"))
        self.database_path_input.setPlaceholderText(t("scanner_tab.database_path_placeholder"))
        self.db_browse.setText(t("common.browse"))

        # Template Cache Size
        self.cache_label.setText(t("scanner_tab.cache_size"))
        self.cache_label.setToolTip(t("scanner_tab.cache_size_tooltip"))

        # Early Exit Threshold
        self.early_exit_label.setText(t("scanner_tab.early_exit"))
        self.early_exit_label.setToolTip(t("scanner_tab.early_exit_tooltip"))

        # Confidence Gap
        self.confidence_gap_label.setText(t("scanner_tab.confidence_gap"))
        self.confidence_gap_label.setToolTip(t("scanner_tab.confidence_gap_tooltip"))

        # Screenshots Folder
        self.screenshots_label.setText(t("scanner_tab.screenshots_folder"))
        self.screenshots_label.setToolTip(t("scanner_tab.screenshots_folder_tooltip"))
        self.screenshots_folder_input.setPlaceholderText(
            t("scanner_tab.screenshots_folder_placeholder")
        )
        self.screenshots_browse.setText(t("common.browse"))

        # Advanced: Max NCC Candidates
        self._ncc_label.setText(t("scanner_tab.max_ncc"))
        self._ncc_label.setToolTip(t("scanner_tab.max_ncc_tooltip"))

        # Advanced: pHash Threshold
        self._phash_label.setText(t("scanner_tab.phash_threshold"))
        self._phash_label.setToolTip(t("scanner_tab.phash_tooltip"))

        # Advanced: NCC Tiebreaker Threshold
        self._tiebreaker_label.setText(t("scanner_tab.tiebreaker_threshold"))
        self._tiebreaker_label.setToolTip(t("scanner_tab.tiebreaker_tooltip"))

        # Advanced: Debug Mode
        self._debug_label.setText(t("scanner_tab.debug_mode"))
        self._debug_label.setToolTip(t("scanner_tab.debug_mode_tooltip"))
        self.debug_mode_input.setText(t("scanner_tab.debug_mode_checkbox"))

        # Advanced: Extract Icons
        self._extract_label.setText(t("scanner_tab.extract_icons"))
        self._extract_label.setToolTip(t("scanner_tab.extract_icons_tooltip"))
        self.extract_icons_input.setText(t("scanner_tab.extract_icons_checkbox"))

        # Developer: Custom Model
        self._custom_model_label.setText(t("scanner_tab.custom_model"))
        self._custom_model_label.setToolTip(t("scanner_tab.custom_model_tooltip"))
        self.custom_model_reset.setText(t("common.reset"))

        # Developer: Tessdata Path
        self._tessdata_label.setText(t("scanner_tab.tessdata_path"))
        self._tessdata_label.setToolTip(t("scanner_tab.tessdata_tooltip"))
        self.tessdata_browse.setText(t("common.browse"))
        self.tessdata_reset.setText(t("common.reset"))

    def set_config_level(self, level: ConfigLevel) -> None:
        """Show or hide fields based on the configuration level.

        Args:
            level (ConfigLevel): The configuration level to set.
        """
        # Advanced widgets are visible at advanced and developer levels
        for widget in self._advanced_widgets:
            widget.setVisible(level.is_at_least(ConfigLevel.ADVANCED))

        # Developer widgets are only visible at developer level
        for widget in self._developer_widgets:
            widget.setVisible(level.is_at_least(ConfigLevel.DEVELOPER))

    def browse_database(self) -> None:
        """Open file dialog for database path."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            t("scanner_tab.select_database"),
            "",
            "HDF5 Files (*.h5);;All Files (*)",
        )
        if filepath:
            self.database_path_input.setText(filepath)

    def browse_tessdata(self) -> None:
        """Open folder dialog for tessdata path."""
        folder = QFileDialog.getExistingDirectory(
            self,
            t("scanner_tab.select_tessdata"),
            "",
        )
        if folder:
            self.tessdata_path_input.setText(folder)

    def browse_screenshots(self) -> None:
        """Open folder dialog for screenshots folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            t("scanner_tab.select_screenshots"),
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
        self.tiebreaker_threshold_input.setValue(settings.ncc_tiebreaker_threshold)

    def get_values(self) -> ScannerSettings:
        """Get current values from widgets.

        Returns:
            ScannerSettings: ScannerSettings instance with current values from widgets
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
            ncc_tiebreaker_threshold=self.tiebreaker_threshold_input.value(),
        )

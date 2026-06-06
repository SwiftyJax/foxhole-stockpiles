"""SAV Processing settings tab."""

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.sav_processing import SavProcessingSettings
from foxhole_stockpiles.core.utils import auto_detect_savefile
from foxhole_stockpiles.i18n import off_language_changed, on_language_changed, t


class SavProcessingTab(QWidget):
    """Tab for SAV Processing configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the SAV Processing tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Form layout for all fields
        form_layout = QFormLayout()

        # SAV file path
        self.sav_file_label = QLabel()
        sav_path_layout = QHBoxLayout()
        self.sav_file_input = QLineEdit()
        sav_path_layout.addWidget(self.sav_file_input)
        self.sav_autodetect_btn = QPushButton()
        self.sav_autodetect_btn.clicked.connect(self._auto_detect_sav_file)
        sav_path_layout.addWidget(self.sav_autodetect_btn)
        self.sav_browse_btn = QPushButton()
        self.sav_browse_btn.clicked.connect(self._browse_sav_file)
        sav_path_layout.addWidget(self.sav_browse_btn)
        self.sav_clear_btn = QPushButton()
        self.sav_clear_btn.clicked.connect(self._clear_sav_file)
        sav_path_layout.addWidget(self.sav_clear_btn)
        form_layout.addRow(self.sav_file_label, sav_path_layout)

        # Poll interval
        self.poll_interval_label = QLabel()
        self.poll_interval_input = QDoubleSpinBox()
        self.poll_interval_input.setRange(0.1, 60.0)
        self.poll_interval_input.setSingleStep(0.5)
        self.poll_interval_input.setDecimals(1)
        self.poll_interval_input.setSuffix(" s")
        form_layout.addRow(self.poll_interval_label, self.poll_interval_input)

        # Emit all on start
        self.emit_all_label = QLabel()
        self.emit_all_checkbox = QCheckBox()
        form_layout.addRow(self.emit_all_label, self.emit_all_checkbox)

        layout.addLayout(form_layout)
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
        self.sav_file_label.setText(t("sav_processing_tab.sav_file_label"))
        self.sav_file_label.setToolTip(t("sav_processing_tab.sav_file_tooltip"))
        self.sav_file_input.setPlaceholderText(t("sav_processing_tab.sav_file_placeholder"))
        self.sav_autodetect_btn.setText(t("sav_processing_tab.auto_detect"))
        self.sav_browse_btn.setText(t("common.browse"))
        self.sav_clear_btn.setText(t("common.clear"))

        self.poll_interval_label.setText(t("sav_processing_tab.poll_interval_label"))
        self.poll_interval_label.setToolTip(t("sav_processing_tab.poll_interval_tooltip"))

        self.emit_all_label.setText(t("sav_processing_tab.emit_all_label"))
        self.emit_all_label.setToolTip(t("sav_processing_tab.emit_all_tooltip"))
        self.emit_all_checkbox.setText(t("sav_processing_tab.emit_all_checkbox"))

    def _auto_detect_sav_file(self) -> None:
        """Auto-detect the SAV file from default locations."""
        detected = auto_detect_savefile()
        if detected:
            self.sav_file_input.setText(str(detected))
        else:
            QMessageBox.information(
                self,
                t("sav_processing_tab.auto_detect_title"),
                t("sav_processing_tab.auto_detect_not_found"),
            )

    def _browse_sav_file(self) -> None:
        """Open file dialog to select SAV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("sav_processing_tab.select_sav_file"),
            "",
            t("sav_processing_tab.sav_file_filter"),
        )
        if file_path:
            self.sav_file_input.setText(file_path)

    def _clear_sav_file(self) -> None:
        """Clear the SAV file path."""
        self.sav_file_input.clear()

    def set_values(self, settings: SavProcessingSettings) -> None:
        """Set widget values from settings.

        Args:
            settings (SavProcessingSettings): SavProcessingSettings instance to load
                values from.
        """
        self.sav_file_input.setText(str(settings.sav_file_path) if settings.sav_file_path else "")
        self.poll_interval_input.setValue(settings.poll_interval)
        self.emit_all_checkbox.setChecked(settings.emit_all_on_start)

    def get_values(self) -> SavProcessingSettings:
        """Get current values from widgets.

        Returns:
            SavProcessingSettings: SavProcessingSettings instance with current values.
        """
        sav_path_text = self.sav_file_input.text().strip()

        return SavProcessingSettings(
            sav_file_path=Path(sav_path_text) if sav_path_text else None,
            poll_interval=self.poll_interval_input.value(),
            emit_all_on_start=self.emit_all_checkbox.isChecked(),
        )

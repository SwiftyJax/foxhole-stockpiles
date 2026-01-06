"""Configuration window with tabbed interface for all settings."""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QKeyEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.app_settings import AppSettings
from foxhole_stockpiles.core.settings.sections import (
    DatabaseBuilderSettings,
    LoggingSettings,
    NotificationsSettings,
    OCRSettings,
    StockpileTypesSettings,
    TemplateSettings,
)
from foxhole_stockpiles.gui.utils.config_manager import ConfigManager
from foxhole_stockpiles.gui.widgets.config_tabs.api_auth_tab import APIAuthTab
from foxhole_stockpiles.gui.widgets.config_tabs.api_server_tab import APIServerTab
from foxhole_stockpiles.gui.widgets.config_tabs.basic_config_tab import BasicConfigTab
from foxhole_stockpiles.gui.widgets.config_tabs.database_builder_tab import DatabaseBuilderTab
from foxhole_stockpiles.gui.widgets.config_tabs.logging_tab import LoggingTab
from foxhole_stockpiles.gui.widgets.config_tabs.ocr_tab import OCRTab
from foxhole_stockpiles.gui.widgets.config_tabs.output_tab import OutputTab
from foxhole_stockpiles.gui.widgets.config_tabs.scanner_tab import ScannerTab
from foxhole_stockpiles.gui.widgets.config_tabs.template_tab import TemplateTab

logger = logging.getLogger(__name__)


class ConfigWindow(QMainWindow):
    """Configuration window for managing application settings."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the configuration window.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.config_manager = ConfigManager()
        self.settings: AppSettings | None = None

        self.init_ui()
        self.load_settings()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Configuration")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Add mode toggle at top
        toggle_layout = QHBoxLayout()
        self.advanced_mode_checkbox = QCheckBox("Show Advanced Settings")
        self.advanced_mode_checkbox.setToolTip(
            "Show all advanced configuration options.\n\n"
            "When disabled, only essential settings are shown for basic users."
        )
        self.advanced_mode_checkbox.stateChanged.connect(self.toggle_mode)
        toggle_layout.addWidget(self.advanced_mode_checkbox)

        # Add hint about hovering labels
        hint_label = QLabel("💡 Tip: Hover over labels for help")
        hint_label.setStyleSheet("QLabel { color: gray; font-size: 11px; }")
        toggle_layout.addWidget(hint_label)

        toggle_layout.addStretch()
        layout.addLayout(toggle_layout)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create basic configuration tab
        self.basic_config_tab = BasicConfigTab()

        # Create advanced configuration tabs
        self.api_server_tab = APIServerTab()
        self.api_auth_tab = APIAuthTab()
        self.scanner_tab = ScannerTab()
        self.output_tab = OutputTab()
        self.ocr_tab = OCRTab()
        self.template_tab = TemplateTab()
        self.database_builder_tab = DatabaseBuilderTab()
        self.logging_tab = LoggingTab()

        # Initialize in basic mode
        self.toggle_mode()

        # Create button box
        button_box = QDialogButtonBox()

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        button_box.addButton(save_button, QDialogButtonBox.ButtonRole.AcceptRole)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_box.addButton(close_button, QDialogButtonBox.ButtonRole.RejectRole)

        layout.addWidget(button_box)

        # Add status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def toggle_mode(self) -> None:
        """Toggle between basic and advanced mode."""
        # Clear all tabs
        self.tab_widget.clear()

        if self.advanced_mode_checkbox.isChecked():
            # Advanced mode - show all detailed tabs
            self.tab_widget.addTab(self.api_server_tab, "API Server")
            self.tab_widget.addTab(self.api_auth_tab, "API Authentication")
            self.tab_widget.addTab(self.scanner_tab, "Scanner")
            self.tab_widget.addTab(self.output_tab, "Output")
            self.tab_widget.addTab(self.ocr_tab, "OCR")
            self.tab_widget.addTab(self.template_tab, "Templates")
            self.tab_widget.addTab(self.database_builder_tab, "Database Builder")
            self.tab_widget.addTab(self.logging_tab, "Logging")
        else:
            # Basic mode - show only basic configuration tab
            self.tab_widget.addTab(self.basic_config_tab, "Configuration")

    def load_settings(self) -> None:
        """Load settings from configuration file."""
        try:
            self.settings = self.config_manager.load_config()
            self.populate_tabs()
            logger.info("Settings loaded successfully")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading Configuration",
                f"Failed to load configuration:\n{e}",
            )
            logger.error("Failed to load settings: %s", e)

    def populate_tabs(self) -> None:
        """Populate all tabs with current settings."""
        if not self.settings:
            return

        # Populate basic tab
        self.basic_config_tab.set_values(
            self.settings.api_server,
            self.settings.api_auth,
            self.settings.scanner,
            self.settings.output,
        )

        # Populate advanced tabs
        self.api_server_tab.set_values(self.settings.api_server)
        self.api_auth_tab.set_values(self.settings.api_auth)
        self.scanner_tab.set_values(self.settings.scanner)
        self.output_tab.set_values(self.settings.output)
        self.ocr_tab.set_values(self.settings.ocr)
        self.template_tab.set_values(self.settings.templates)
        self.database_builder_tab.set_values(self.settings.database_builder)
        self.logging_tab.set_values(self.settings.logging)

    def collect_settings(self) -> AppSettings:
        """Collect settings from tabs based on current mode.

        Returns:
            AppSettings: AppSettings instance with current values from tabs
        """
        if self.advanced_mode_checkbox.isChecked():
            # Advanced mode - collect from detailed tabs
            return AppSettings(
                api_server=self.api_server_tab.get_values(),
                api_auth=self.api_auth_tab.get_values(),
                scanner=self.scanner_tab.get_values(),
                output=self.output_tab.get_values(),
                ocr=self.ocr_tab.get_values(),
                templates=self.template_tab.get_values(),
                database_builder=self.database_builder_tab.get_values(),
                logging=self.logging_tab.get_values(),
                notifications=(
                    self.settings.notifications if self.settings else NotificationsSettings()
                ),
                stockpile_types=(
                    self.settings.stockpile_types if self.settings else StockpileTypesSettings()
                ),
            )
        else:
            # Basic mode - collect from basic tab and preserve other settings
            api_server, api_auth, scanner, output = self.basic_config_tab.get_values()

            return AppSettings(
                api_server=api_server,
                api_auth=api_auth,
                scanner=scanner,
                output=output,
                # Preserve advanced settings from loaded config
                ocr=self.settings.ocr if self.settings else OCRSettings(),
                templates=self.settings.templates if self.settings else TemplateSettings(),
                database_builder=(
                    self.settings.database_builder if self.settings else DatabaseBuilderSettings()
                ),
                logging=self.settings.logging if self.settings else LoggingSettings(),
                notifications=(
                    self.settings.notifications if self.settings else NotificationsSettings()
                ),
                stockpile_types=(
                    self.settings.stockpile_types if self.settings else StockpileTypesSettings()
                ),
            )

    def save_settings(self) -> None:
        """Save current settings to configuration file."""
        try:
            # Collect settings from tabs (already validated by Pydantic)
            new_settings = self.collect_settings()

            # Save settings
            success, msg = self.config_manager.save_config(new_settings)

            if success:
                self.settings = new_settings
                self.status_bar.showMessage("Configuration saved successfully!", 3000)
                logger.info("Settings saved successfully")
            else:
                QMessageBox.critical(
                    self,
                    "Error Saving Configuration",
                    msg,
                )
                logger.error("Failed to save settings: %s", msg)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An unexpected error occurred:\n{e}",
            )
            logger.error("Unexpected error saving settings: %s", e, exc_info=True)

    def has_changes(self) -> bool:
        """Check if current settings differ from loaded settings.

        Returns:
            bool: True if there are unsaved changes
        """
        if not self.settings:
            return False

        try:
            current_settings = self.collect_settings()
            return current_settings != self.settings
        except Exception:
            # If we can't collect settings, assume no changes
            return False

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        """Handle key press events.

        Args:
            event (QKeyEvent | None): Key press event
        """
        if event and event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Handle window close event to check for unsaved changes.

        Args:
            event (QCloseEvent | None): Close event
        """
        if self.has_changes():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "There are pending changes. Do you want to save them?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )

            if reply == QMessageBox.StandardButton.Save:
                self.save_settings()
                # Only close if save was successful (no more changes)
                if not self.has_changes() and event:
                    event.accept()
                elif event:
                    event.ignore()
            elif reply == QMessageBox.StandardButton.Discard:
                if event:
                    event.accept()
            else:  # Cancel
                if event:
                    event.ignore()
        else:
            if event:
                event.accept()

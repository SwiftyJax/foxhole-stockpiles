"""Configuration window with tabbed interface for all settings."""

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QKeyEvent
from PyQt6.QtWidgets import (
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

from foxhole_stockpiles.core.settings import reload_settings
from foxhole_stockpiles.core.settings.app_settings import AppSettings
from foxhole_stockpiles.core.settings.sections import NotificationsSettings
from foxhole_stockpiles.enums.config_level import ConfigLevel
from foxhole_stockpiles.gui.utils.config_manager import ConfigManager
from foxhole_stockpiles.gui.widgets.config_tabs.api_server_tab import APIServerTab
from foxhole_stockpiles.gui.widgets.config_tabs.database_builder_tab import DatabaseBuilderTab
from foxhole_stockpiles.gui.widgets.config_tabs.external_tools_tab import ExternalToolsTab
from foxhole_stockpiles.gui.widgets.config_tabs.gui_tab import GUITab
from foxhole_stockpiles.gui.widgets.config_tabs.logging_tab import LoggingTab
from foxhole_stockpiles.gui.widgets.config_tabs.ocr_tab import OCRTab
from foxhole_stockpiles.gui.widgets.config_tabs.output_tab import OutputTab
from foxhole_stockpiles.gui.widgets.config_tabs.scanner_tab import ScannerTab
from foxhole_stockpiles.gui.widgets.config_tabs.stockpile_types_tab import StockpileTypesTab
from foxhole_stockpiles.gui.widgets.config_tabs.template_tab import TemplateTab

logger = logging.getLogger(__name__)


class ConfigWindow(QMainWindow):
    """Configuration window for managing application settings."""

    # Signal emitted when the window is closed
    closed = pyqtSignal()

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
        self.setGeometry(100, 100, 950, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Add hint about hovering labels at top
        hint_layout = QHBoxLayout()
        hint_label = QLabel("Tip: Hover over labels for help")
        hint_label.setStyleSheet("QLabel { color: gray; font-size: 11px; }")
        hint_layout.addWidget(hint_label)
        hint_layout.addStretch()
        layout.addLayout(hint_layout)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create configuration tabs
        self.api_server_tab = APIServerTab()
        self.scanner_tab = ScannerTab()
        self.output_tab = OutputTab()
        self.ocr_tab = OCRTab()
        self.template_tab = TemplateTab()
        self.external_tools_tab = ExternalToolsTab()
        self.database_builder_tab = DatabaseBuilderTab()
        self.logging_tab = LoggingTab()
        self.gui_tab = GUITab()
        self.stockpile_types_tab = StockpileTypesTab()

        # Track current config level
        self._current_config_level: ConfigLevel = ConfigLevel.BASIC

        # Initialize tabs (will be updated after settings load)
        self._build_tabs()

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

    def _build_tabs(self) -> None:
        """Build tabs based on current config level."""
        # Remember current tab if possible
        current_tab_text = ""
        if self.tab_widget.currentIndex() >= 0:
            current_tab_text = self.tab_widget.tabText(self.tab_widget.currentIndex())

        # Clear all tabs
        self.tab_widget.clear()

        level = self._current_config_level

        # Always visible tabs (Basic level)
        self.tab_widget.addTab(self.api_server_tab, "API Server")
        self.tab_widget.addTab(self.scanner_tab, "Scanner")
        self.tab_widget.addTab(self.output_tab, "Output")

        # Developer-only tabs
        if level.is_at_least(ConfigLevel.DEVELOPER):
            self.tab_widget.addTab(self.ocr_tab, "OCR")
            self.tab_widget.addTab(self.template_tab, "Templates")

        # Advanced and Developer tabs
        if level.is_at_least(ConfigLevel.ADVANCED):
            self.tab_widget.addTab(self.stockpile_types_tab, "Stockpile Types")
            self.tab_widget.addTab(self.external_tools_tab, "External Tools")
            self.tab_widget.addTab(self.database_builder_tab, "Database Builder")

        # Always visible tabs (continued)
        self.tab_widget.addTab(self.logging_tab, "Logging")
        self.tab_widget.addTab(self.gui_tab, "GUI")

        # Update field visibility in tabs based on level
        self.scanner_tab.set_config_level(level)
        self.api_server_tab.set_config_level(level)
        self.logging_tab.set_config_level(level)

        # Try to restore previous tab
        if current_tab_text:
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == current_tab_text:
                    self.tab_widget.setCurrentIndex(i)
                    break

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

        # Set config level first (affects tab visibility and field visibility)
        self._current_config_level = self.settings.gui.config_level
        self._build_tabs()

        # Populate tabs
        self.api_server_tab.set_values(self.settings.api_server, self.settings.api_auth)
        self.scanner_tab.set_values(self.settings.scanner)
        self.output_tab.set_values(self.settings.output)
        self.ocr_tab.set_values(self.settings.ocr)
        self.template_tab.set_values(self.settings.templates)
        self.external_tools_tab.set_values(self.settings.external_tools)
        self.database_builder_tab.set_values(self.settings.database_builder)
        self.logging_tab.set_values(self.settings.logging)
        self.gui_tab.set_values(self.settings.gui)
        self.stockpile_types_tab.set_values(self.settings.stockpile_types)

    def collect_settings(self) -> AppSettings:
        """Collect settings from all tabs.

        Returns:
            AppSettings: AppSettings instance with current values from tabs
        """
        return AppSettings(
            api_server=self.api_server_tab.get_server_values(),
            api_auth=self.api_server_tab.get_auth_values(),
            scanner=self.scanner_tab.get_values(),
            output=self.output_tab.get_values(),
            ocr=self.ocr_tab.get_values(),
            templates=self.template_tab.get_values(),
            external_tools=self.external_tools_tab.get_values(),
            database_builder=self.database_builder_tab.get_values(),
            logging=self.logging_tab.get_values(),
            gui=self.gui_tab.get_values(),
            notifications=(
                self.settings.notifications if self.settings else NotificationsSettings()
            ),
            stockpile_types=self.stockpile_types_tab.get_values(),
        )

    def save_settings(self) -> None:
        """Save current settings to configuration file."""
        try:
            # Collect settings from tabs (already validated by Pydantic)
            new_settings = self.collect_settings()

            # Check if config level changed
            config_level_changed = new_settings.gui.config_level != self._current_config_level

            # Save settings
            success, msg = self.config_manager.save_config(new_settings)

            if success:
                self.settings = new_settings
                # Clear the settings cache so new settings take effect
                # Note: dependency caches are cleared when server stops
                reload_settings()

                # Rebuild tabs if config level changed
                if config_level_changed:
                    self._current_config_level = new_settings.gui.config_level
                    self._build_tabs()
                    # Re-populate tabs with current settings
                    self.populate_tabs()
                    level = new_settings.gui.config_level
                    self.status_bar.showMessage(
                        f"Configuration saved. Tabs updated for {level} mode.", 5000
                    )
                else:
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

        current_settings = self.collect_settings()
        return current_settings != self.settings

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
        should_close = False

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
                should_close = not self.has_changes()
            elif reply == QMessageBox.StandardButton.Discard:
                should_close = True
            # else: Cancel - should_close remains False
        else:
            should_close = True

        if event:
            if should_close:
                event.accept()
                self.closed.emit()
            else:
                event.ignore()

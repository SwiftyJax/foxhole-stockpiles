"""Database builder settings dialog."""

import logging

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings import get_settings
from foxhole_stockpiles.gui.utils.config_manager import ConfigManager
from foxhole_stockpiles.gui.widgets.config_tabs.database_builder_tab import DatabaseBuilderTab
from foxhole_stockpiles.gui.widgets.config_tabs.external_tools_tab import ExternalToolsTab
from foxhole_stockpiles.i18n import off_language_changed, on_language_changed, t

logger = logging.getLogger(__name__)


class DatabaseBuilderSettingsDialog(QDialog):
    """Dialog for configuring database builder settings.

    This dialog configures:
    - External tools: repak (extractor) and umodel (converter)
    - Database builder settings: catalog file, resolutions, workers
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the database builder settings dialog.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.config_manager = ConfigManager()
        self.init_ui()
        self._load_current_settings()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)

        layout = QVBoxLayout(self)

        # Add info header
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet(
            "QLabel { background-color: palette(alternate-base); padding: 10px; "
            "border: 2px solid #2196F3; }"
        )
        layout.addWidget(self.info_label)

        # Add external tools tab (repak + umodel, not uassetgui)
        self.external_tools_tab = ExternalToolsTab(
            show_repak=True,
            show_umodel=True,
            show_uassetgui=False,
        )
        layout.addWidget(self.external_tools_tab)

        # Add the database builder tab
        self.db_builder_tab = DatabaseBuilderTab()
        layout.addWidget(self.db_builder_tab)

        # Add status label for error messages
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("QLabel { color: red; padding: 5px; }")
        self.status_label.hide()
        layout.addWidget(self.status_label)

        # Add dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

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
        self.setWindowTitle(t("database_builder_settings.title"))
        self.info_label.setText(t("database_builder_settings.info"))

    def _load_current_settings(self) -> None:
        """Load current settings into the tabs."""
        settings = get_settings()
        self.external_tools_tab.set_values(settings.external_tools)
        self.db_builder_tab.set_values(settings.database_builder)

    def _save_and_accept(self) -> None:
        """Save settings and accept dialog."""
        # Get current settings and update both sections
        current_settings = get_settings()

        # Merge external tools (only update repak and umodel, preserve uassetgui)
        new_external_tools = self.external_tools_tab.merge_with_existing(
            current_settings.external_tools
        )
        new_db_builder_settings = self.db_builder_tab.get_values()

        updated_settings = current_settings.model_copy(
            update={
                "external_tools": new_external_tools,
                "database_builder": new_db_builder_settings,
            }
        )

        # Save settings
        try:
            success, msg = self.config_manager.save_config(updated_settings)
        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            self.status_label.setText(f"Error: {e}")
            self.status_label.show()
            return

        if success:
            logger.info("Database builder settings saved successfully")
            self.accept()
        else:
            logger.error("Failed to save settings: %s", msg)
            self.status_label.setText(f"Failed to save: {msg}")
            self.status_label.show()

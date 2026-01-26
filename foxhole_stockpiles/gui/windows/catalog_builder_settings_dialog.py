"""Catalog builder settings dialog."""

import logging

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings import get_settings
from foxhole_stockpiles.gui.utils.config_manager import ConfigManager
from foxhole_stockpiles.gui.widgets.config_tabs.external_tools_tab import ExternalToolsTab
from foxhole_stockpiles.i18n import off_language_changed, on_language_changed, t

logger = logging.getLogger(__name__)


class CatalogBuilderSettingsDialog(QDialog):
    """Dialog for configuring catalog builder settings.

    This dialog configures:
    - External tools: repak (extractor) and uassetgui (JSON converter)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the catalog builder settings dialog.

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
        self.setMinimumHeight(300)

        layout = QVBoxLayout(self)

        # Add info header
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet(
            "QLabel { background-color: palette(alternate-base); padding: 10px; "
            "border: 2px solid #2196F3; }"
        )
        layout.addWidget(self.info_label)

        # Add external tools tab (repak + uassetgui, not umodel)
        self.external_tools_tab = ExternalToolsTab(
            show_repak=True,
            show_umodel=False,
            show_uassetgui=True,
        )
        layout.addWidget(self.external_tools_tab)

        # Add status label for error messages
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("QLabel { color: red; padding: 5px; }")
        self.status_label.hide()
        layout.addWidget(self.status_label)

        layout.addStretch()

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
        self.destroyed.connect(lambda: off_language_changed(self._language_callback))

    def _on_language_changed(self, _language: str) -> None:
        """Handle language change event."""
        self.retranslate()

    def retranslate(self) -> None:
        """Update all translatable strings."""
        self.setWindowTitle(t("catalog_builder_settings.title"))
        self.info_label.setText(t("catalog_builder_settings.info"))

    def _load_current_settings(self) -> None:
        """Load current settings into the tab."""
        settings = get_settings()
        self.external_tools_tab.set_values(settings.external_tools)

    def _save_and_accept(self) -> None:
        """Save settings and accept dialog."""
        # Get current settings and update external_tools section
        current_settings = get_settings()

        # Merge external tools (only update repak and uassetgui, preserve umodel)
        new_external_tools = self.external_tools_tab.merge_with_existing(
            current_settings.external_tools
        )

        updated_settings = current_settings.model_copy(
            update={"external_tools": new_external_tools}
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
            logger.info("Catalog builder settings saved successfully")
            self.accept()
        else:
            logger.error("Failed to save settings: %s", msg)
            self.status_label.setText(f"Failed to save: {msg}")
            self.status_label.show()

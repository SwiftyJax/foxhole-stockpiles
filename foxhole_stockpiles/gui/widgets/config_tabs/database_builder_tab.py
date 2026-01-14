"""Database Builder settings tab."""

import os
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.database_builder import DatabaseBuilderSettings
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution


class DatabaseBuilderTab(QWidget):
    """Tab for Database Builder configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Database Builder tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Add info header
        info_header = QWidget()
        info_layout = QHBoxLayout(info_header)
        info_layout.setContentsMargins(0, 0, 0, 0)

        info_label = QLabel(
            "ℹ️ <b>Database Builder:</b> Configure tools and files required for "
            "importing new icons to the database. "
            "These settings are used by the <b>Database → Build...</b> feature."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "QLabel { background-color: palette(alternate-base); padding: 10px; "
            "border: 2px solid #2196F3; }"
        )
        info_layout.addWidget(info_label, 1)

        layout.addWidget(info_header)

        # Tools and Files Group
        tools_group = QGroupBox("Required Tools and Files")
        tools_layout = QFormLayout()
        tools_group.setLayout(tools_layout)

        # Extractor tool
        extractor_label = QLabel("Extractor Tool (repak):")
        extractor_label.setToolTip(
            "Path to repak executable for extracting PAK files.\n\n"
            "Required for the 'Build Database' feature.\n"
            "Download from: https://github.com/trumank/repak"
        )
        extractor_layout = QHBoxLayout()
        self.extractor_tool_input = QLineEdit()
        self.extractor_tool_input.setPlaceholderText("Path to repak executable")
        self.extractor_tool_input.textChanged.connect(self._update_download_buttons)
        extractor_layout.addWidget(self.extractor_tool_input)
        self.extractor_download_btn = QPushButton("Download")
        self.extractor_download_btn.setMaximumWidth(80)
        self.extractor_download_btn.clicked.connect(
            lambda: self._open_url("https://github.com/trumank/repak/releases")
        )
        extractor_layout.addWidget(self.extractor_download_btn)
        extractor_browse_btn = QPushButton("Browse...")
        extractor_browse_btn.clicked.connect(self.browse_extractor_tool)
        extractor_layout.addWidget(extractor_browse_btn)
        tools_layout.addRow(extractor_label, extractor_layout)

        # Converter tool
        converter_label = QLabel("Converter Tool (umodel):")
        converter_label.setToolTip(
            "Path to umodel executable for converting UAsset files to PNG.\n\n"
            "Required for the 'Build Database' feature.\n"
            "Download from: https://www.gildor.org/en/projects/umodel"
        )
        converter_layout = QHBoxLayout()
        self.converter_tool_input = QLineEdit()
        self.converter_tool_input.setPlaceholderText("Path to umodel executable")
        self.converter_tool_input.textChanged.connect(self._update_download_buttons)
        converter_layout.addWidget(self.converter_tool_input)
        self.converter_download_btn = QPushButton("Download")
        self.converter_download_btn.setMaximumWidth(80)
        self.converter_download_btn.clicked.connect(
            lambda: self._open_url("https://www.gildor.org/en/projects/umodel")
        )
        converter_layout.addWidget(self.converter_download_btn)
        converter_browse_btn = QPushButton("Browse...")
        converter_browse_btn.clicked.connect(self.browse_converter_tool)
        converter_layout.addWidget(converter_browse_btn)
        tools_layout.addRow(converter_label, converter_layout)

        # Catalog file
        catalog_label = QLabel("Catalog File (catalog.json):")
        catalog_label.setToolTip(
            "Path to catalog.json file that defines all game items.\n\n"
            "Required for the 'Build Database' feature.\n"
            "This file maps item codes to their icon paths.\n\n"
            "Download from: https://github.com/xurxogr/foxhole-stockpiles/tree/main/data"
        )
        catalog_layout = QHBoxLayout()
        self.catalog_file_input = QLineEdit()
        self.catalog_file_input.setPlaceholderText("Path to catalog.json")
        self.catalog_file_input.textChanged.connect(self._update_download_buttons)
        catalog_layout.addWidget(self.catalog_file_input)
        self.catalog_download_btn = QPushButton("Download")
        self.catalog_download_btn.setMaximumWidth(80)
        self.catalog_download_btn.clicked.connect(
            lambda: self._open_url("https://github.com/xurxogr/foxhole-stockpiles/tree/main/data")
        )
        catalog_layout.addWidget(self.catalog_download_btn)
        catalog_browse_btn = QPushButton("Browse...")
        catalog_browse_btn.clicked.connect(self.browse_catalog_file)
        catalog_layout.addWidget(catalog_browse_btn)
        tools_layout.addRow(catalog_label, catalog_layout)

        # Workers
        cpu_count = os.cpu_count() or 1
        workers_label = QLabel("Workers:")
        workers_label.setToolTip(
            "Number of parallel processes for database building.\n\n"
            "Set to 0 to auto-detect (uses CPU count).\n"
            "Set to 1 to disable multiprocessing."
        )
        workers_layout = QHBoxLayout()
        self.workers_spinbox = QSpinBox()
        self.workers_spinbox.setMinimum(0)
        self.workers_spinbox.setMaximum(cpu_count)
        self.workers_spinbox.setValue(0)
        self.workers_spinbox.setFixedWidth(80)
        workers_layout.addWidget(self.workers_spinbox)
        workers_hint = QLabel(f"(0 = auto-detect, max {cpu_count} cores)")
        workers_hint.setStyleSheet("color: gray; font-size: 11px;")
        workers_layout.addWidget(workers_hint)
        workers_layout.addStretch()
        tools_layout.addRow(workers_label, workers_layout)

        layout.addWidget(tools_group)

        # Resolutions Group
        resolutions_group = QGroupBox("Target Resolutions")
        resolutions_layout = QVBoxLayout()
        resolutions_group.setLayout(resolutions_layout)

        resolutions_info = QLabel(
            "Select which resolutions to generate when importing icons. "
            "Check 'All Resolutions' to generate all supported resolutions."
        )
        resolutions_info.setWordWrap(True)
        resolutions_layout.addWidget(resolutions_info)

        self.resolution_list = QListWidget()
        self.resolution_list.setMaximumHeight(200)

        # Add "All" option first
        all_item = self.resolution_list.addItem("All Resolutions")
        if all_item is None:
            all_item = self.resolution_list.item(0)
        if all_item:
            all_item.setFlags(all_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            all_item.setCheckState(Qt.CheckState.Checked)  # Default to all
            all_item.setData(Qt.ItemDataRole.UserRole, "all")

        # Add individual resolutions
        for resolution in SupportedResolution:
            item = self.resolution_list.addItem(resolution.value)
            if item is None:
                item = self.resolution_list.item(self.resolution_list.count() - 1)
            if item:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)  # Default to all
                item.setData(Qt.ItemDataRole.UserRole, resolution.value)

        self.resolution_list.itemChanged.connect(self._handle_resolution_selection)
        resolutions_layout.addWidget(self.resolution_list)

        layout.addWidget(resolutions_group)

        # Status info
        status_label = QLabel(
            "<b>Note:</b> All three files must be configured for the 'Build Database' "
            "feature to work. If any are missing, the feature will be disabled."
        )
        status_label.setWordWrap(True)
        status_label.setStyleSheet(
            "QLabel { background-color: palette(alternate-base); padding: 8px; "
            "border: 2px solid #FF9800; margin-top: 10px; }"
        )
        layout.addWidget(status_label)

        layout.addStretch()

        # Initial update of download button visibility
        self._update_download_buttons()

    def _update_download_buttons(self) -> None:
        """Update visibility of download buttons based on whether fields are empty."""
        self.extractor_download_btn.setVisible(not self.extractor_tool_input.text().strip())
        self.converter_download_btn.setVisible(not self.converter_tool_input.text().strip())
        self.catalog_download_btn.setVisible(not self.catalog_file_input.text().strip())

    def _open_url(self, url: str) -> None:
        """Open URL in default browser.

        Args:
            url (str): URL to open
        """
        QDesktopServices.openUrl(QUrl(url))

    def browse_extractor_tool(self) -> None:
        """Open file dialog to select extractor tool (repak)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Extractor Tool (repak)",
            "",
            "All Files (*)",
        )
        if file_path:
            self.extractor_tool_input.setText(file_path)

    def browse_converter_tool(self) -> None:
        """Open file dialog to select converter tool (umodel)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Converter Tool (umodel)",
            "",
            "All Files (*)",
        )
        if file_path:
            self.converter_tool_input.setText(file_path)

    def browse_catalog_file(self) -> None:
        """Open file dialog to select catalog file (catalog.json)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Catalog File (catalog.json)",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if file_path:
            self.catalog_file_input.setText(file_path)

    def _handle_resolution_selection(self, item: object) -> None:
        """Handle resolution selection changes in the list.

        Args:
            item (object): The list item that changed
        """
        if not hasattr(item, "data") or not hasattr(item, "checkState"):
            return

        # Temporarily disconnect to avoid recursion
        self.resolution_list.itemChanged.disconnect(self._handle_resolution_selection)

        try:
            item_data = item.data(Qt.ItemDataRole.UserRole)
            is_checked = item.checkState() == Qt.CheckState.Checked

            if item_data == "all":
                # Check/uncheck all items
                for i in range(self.resolution_list.count()):
                    list_item = self.resolution_list.item(i)
                    if list_item:
                        list_item.setCheckState(
                            Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked
                        )
            else:
                # Check if all individual items are now checked
                all_checked = True
                for i in range(1, self.resolution_list.count()):  # Skip "All" item at index 0
                    list_item = self.resolution_list.item(i)
                    if list_item and list_item.checkState() != Qt.CheckState.Checked:
                        all_checked = False
                        break

                # Update "All" checkbox accordingly
                all_item = self.resolution_list.item(0)
                if all_item:
                    all_item.setCheckState(
                        Qt.CheckState.Checked if all_checked else Qt.CheckState.Unchecked
                    )

        finally:
            # Reconnect
            self.resolution_list.itemChanged.connect(self._handle_resolution_selection)

    def set_values(self, settings: DatabaseBuilderSettings) -> None:
        """Set widget values from settings.

        Args:
            settings (DatabaseBuilderSettings): DatabaseBuilderSettings instance to load
                values from.
        """
        self.extractor_tool_input.setText(
            str(settings.extractor_tool) if settings.extractor_tool else ""
        )
        self.converter_tool_input.setText(
            str(settings.converter_tool) if settings.converter_tool else ""
        )
        self.catalog_file_input.setText(str(settings.catalog_file) if settings.catalog_file else "")
        self.workers_spinbox.setValue(settings.workers if settings.workers is not None else 0)

        # Set resolution checkboxes
        # Disconnect to avoid triggering events during setup
        try:
            self.resolution_list.itemChanged.disconnect(self._handle_resolution_selection)
        except TypeError:
            # Not connected yet on first load
            pass

        try:
            target_resolutions = settings.target_resolutions

            if target_resolutions is None:
                # None explicitly means all resolutions
                for i in range(self.resolution_list.count()):
                    item = self.resolution_list.item(i)
                    if item:
                        item.setCheckState(Qt.CheckState.Checked)
            elif len(target_resolutions) == 0:
                # Empty list means no resolutions (uncheck all)
                for i in range(self.resolution_list.count()):
                    item = self.resolution_list.item(i)
                    if item:
                        item.setCheckState(Qt.CheckState.Unchecked)
            else:
                # Specific resolutions selected
                # First uncheck all
                for i in range(self.resolution_list.count()):
                    item = self.resolution_list.item(i)
                    if item:
                        item.setCheckState(Qt.CheckState.Unchecked)

                # Check only the selected resolutions
                for i in range(1, self.resolution_list.count()):  # Skip "All" at index 0
                    item = self.resolution_list.item(i)
                    if item:
                        res_value = item.data(Qt.ItemDataRole.UserRole)
                        if res_value in target_resolutions:
                            item.setCheckState(Qt.CheckState.Checked)

                # Check "All" if all individual items are now checked
                all_checked = all(
                    item.checkState() == Qt.CheckState.Checked
                    for i in range(1, self.resolution_list.count())
                    if (item := self.resolution_list.item(i)) is not None
                )
                all_item = self.resolution_list.item(0)
                if all_item:
                    all_item.setCheckState(
                        Qt.CheckState.Checked if all_checked else Qt.CheckState.Unchecked
                    )

        finally:
            # Reconnect
            self.resolution_list.itemChanged.connect(self._handle_resolution_selection)

        # Update download button visibility
        self._update_download_buttons()

    def get_values(self) -> DatabaseBuilderSettings:
        """Get current values from widgets.

        Returns:
            DatabaseBuilderSettings: DatabaseBuilderSettings instance with current values
                from widgets
        """
        # Get values, convert empty strings to None
        extractor_text = self.extractor_tool_input.text().strip()
        converter_text = self.converter_tool_input.text().strip()
        catalog_text = self.catalog_file_input.text().strip()

        # Get selected resolutions
        all_item = self.resolution_list.item(0)
        all_selected = all_item and all_item.checkState() == Qt.CheckState.Checked

        # Collect individual selections
        selected_resolutions = []
        for i in range(1, self.resolution_list.count()):
            item = self.resolution_list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                res_value = item.data(Qt.ItemDataRole.UserRole)
                if res_value and res_value != "all":
                    selected_resolutions.append(res_value)

        # Determine what to save:
        # - If "All" is checked OR all individual items are checked → None (means all)
        # - If specific items are checked → list of those items
        # - If nothing is checked → empty list (though this shouldn't normally happen)
        if all_selected:
            target_resolutions = None  # Explicitly None means all
        elif selected_resolutions:
            target_resolutions = selected_resolutions
        else:
            # Nothing selected - save as empty list
            target_resolutions = []

        # Get workers value (0 means auto-detect, which we store as None)
        workers_value = self.workers_spinbox.value()
        workers = workers_value if workers_value > 0 else None

        return DatabaseBuilderSettings(
            extractor_tool=Path(extractor_text) if extractor_text else None,
            converter_tool=Path(converter_text) if converter_text else None,
            catalog_file=Path(catalog_text) if catalog_text else None,
            target_resolutions=target_resolutions,
            workers=workers,
        )

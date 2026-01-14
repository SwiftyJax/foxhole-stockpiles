"""Icon import window for importing new icons to the database."""

import logging
import platform
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QDragEnterEvent, QDropEvent, QKeyEvent, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings import get_settings
from foxhole_stockpiles.gui.utils.icon_import_worker import IconImportWorker
from foxhole_stockpiles.gui.utils.qt_log_handler import QtLogHandler

logger = logging.getLogger(__name__)


class IconImportWindow(QMainWindow):
    """Window for importing new icons to the database."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the icon import window.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.import_worker: IconImportWorker | None = None
        self.vanilla_pak_file: str | None = None
        self.mod_pak_files: list[str] = []

        # Setup log handler (shared across all imports)
        self.log_handler = QtLogHandler()
        self.log_handler.log_message.connect(self.append_log)
        self.log_handler.setLevel(logging.INFO)

        # Check if database builder is configured
        self.settings = get_settings()
        self.is_configured = self._check_configuration()

        self.init_ui()

        # Disable UI if not configured
        if not self.is_configured:
            self._disable_ui_with_warning()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Build Database")
        self.setGeometry(100, 100, 900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Vanilla PAK Section
        vanilla_group = QGroupBox("Vanilla PAK File (Optional)")
        vanilla_layout = QVBoxLayout()
        vanilla_group.setLayout(vanilla_layout)

        # Info text about vanilla PAK
        vanilla_info = QLabel(
            "ℹ️ Contains shared resources (crate icon, subicons) that mods depend on. "
            "Extracted automatically if needed."
        )
        vanilla_info.setWordWrap(True)
        vanilla_info.setStyleSheet(
            "QLabel { "
            "border: 2px solid #2196F3; "
            "border-radius: 4px; "
            "padding: 6px; "
            "font-size: 11px; "
            "background-color: palette(alternate-base); "
            "}"
        )
        vanilla_layout.addWidget(vanilla_info)

        # Vanilla PAK file path display
        vanilla_path_layout = QHBoxLayout()
        self.vanilla_pak_display = QLineEdit()
        self.vanilla_pak_display.setReadOnly(True)
        self.vanilla_pak_display.setPlaceholderText("No vanilla PAK selected")
        vanilla_path_layout.addWidget(self.vanilla_pak_display)

        # Vanilla PAK buttons
        vanilla_browse_button = QPushButton("Browse...")
        vanilla_browse_button.clicked.connect(self.select_vanilla_pak)
        vanilla_path_layout.addWidget(vanilla_browse_button)

        vanilla_clear_button = QPushButton("Clear")
        vanilla_clear_button.clicked.connect(self.clear_vanilla_pak)
        vanilla_path_layout.addWidget(vanilla_clear_button)

        vanilla_layout.addLayout(vanilla_path_layout)
        layout.addWidget(vanilla_group)

        # Mod PAK Files Section
        mod_pak_group = QGroupBox("Mod PAK Files")
        mod_pak_layout = QVBoxLayout()
        mod_pak_group.setLayout(mod_pak_layout)

        # Mod PAK file list
        self.mod_pak_list_widget = QListWidget()
        self.mod_pak_list_widget.setAcceptDrops(True)
        self.mod_pak_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.mod_pak_list_widget.dragEnterEvent = self.pak_drag_enter_event  # type: ignore[method-assign]
        self.mod_pak_list_widget.dropEvent = self.pak_drop_event  # type: ignore[method-assign]
        # Limit height to 5 rows
        self.mod_pak_list_widget.setMaximumHeight(100)
        mod_pak_layout.addWidget(self.mod_pak_list_widget)

        # Mod PAK file buttons
        mod_pak_buttons_layout = QHBoxLayout()
        add_mod_pak_button = QPushButton("Add PAK Files...")
        add_mod_pak_button.clicked.connect(self.add_mod_pak_files)
        mod_pak_buttons_layout.addWidget(add_mod_pak_button)

        remove_mod_pak_button = QPushButton("Remove Selected")
        remove_mod_pak_button.clicked.connect(self.remove_selected_mod_paks)
        mod_pak_buttons_layout.addWidget(remove_mod_pak_button)

        clear_mod_pak_button = QPushButton("Clear All")
        clear_mod_pak_button.clicked.connect(self.clear_all_mod_paks)
        mod_pak_buttons_layout.addWidget(clear_mod_pak_button)

        mod_pak_buttons_layout.addStretch()
        mod_pak_layout.addLayout(mod_pak_buttons_layout)

        layout.addWidget(mod_pak_group)

        # Configuration Section
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()
        config_group.setLayout(config_layout)

        # Mod name
        mod_name_layout = QHBoxLayout()
        mod_name_layout.addWidget(QLabel("Mod Name:"))
        self.mod_name_input = QLineEdit()
        self.mod_name_input.setPlaceholderText("e.g., vanilla, mymod")
        mod_name_layout.addWidget(self.mod_name_input)
        config_layout.addLayout(mod_name_layout)

        # Overwrite option
        self.overwrite_checkbox = QCheckBox("Overwrite existing data")
        self.overwrite_checkbox.setToolTip(
            "If checked, existing templates with the same item-resolution will be overwritten"
        )
        config_layout.addWidget(self.overwrite_checkbox)

        # Database path row
        db_path_layout = QHBoxLayout()
        db_path_layout.addWidget(QLabel("Destination Database:"))
        self.db_path_input = QLineEdit()
        db_path = self.settings.scanner.database_path
        self.db_path_input.setText(str(db_path) if db_path else "")
        self.db_path_input.setPlaceholderText("Select database file (.h5)")
        self.db_path_input.setToolTip("Database file where templates will be saved")
        db_path_layout.addWidget(self.db_path_input)

        db_browse_button = QPushButton("Browse...")
        db_browse_button.clicked.connect(self.select_database_path)
        db_path_layout.addWidget(db_browse_button)
        config_layout.addLayout(db_path_layout)

        layout.addWidget(config_group)

        # Logs Section
        logs_group = QGroupBox("Process Logs")
        logs_layout = QVBoxLayout()
        logs_group.setLayout(logs_layout)

        self.log_display = QTableWidget()
        self.log_display.setColumnCount(4)
        self.log_display.setHorizontalHeaderLabels(["Time", "Level", "Module", "Message"])
        self.log_display.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.log_display.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.log_display.setWordWrap(True)  # Enable word wrap for multi-line content
        vertical_header = self.log_display.verticalHeader()
        if vertical_header:
            vertical_header.setVisible(False)
            # Auto-resize rows to fit content
            vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.log_display.setStyleSheet(
            "QTableWidget { background-color: #1E1E1E; gridline-color: #3E3E3E; }"
        )

        # Set column widths
        header = self.log_display.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        # Set minimum column widths
        self.log_display.setColumnWidth(0, 150)  # Time
        self.log_display.setColumnWidth(1, 80)  # Level
        self.log_display.setColumnWidth(2, 250)  # Module

        # Enable copy on CTRL-C
        self.log_display.keyPressEvent = self._log_key_press_event  # type: ignore[assignment,method-assign]

        logs_layout.addWidget(self.log_display)

        layout.addWidget(logs_group, stretch=1)  # Expand to use maximum available space

        # Action Buttons (at bottom)
        action_buttons_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Import")
        self.start_button.clicked.connect(self.start_import)
        action_buttons_layout.addWidget(self.start_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_import)
        self.cancel_button.setEnabled(False)
        action_buttons_layout.addWidget(self.cancel_button)

        action_buttons_layout.addStretch()

        clear_logs_button = QPushButton("Clear Logs")
        clear_logs_button.clicked.connect(self.clear_logs)
        action_buttons_layout.addWidget(clear_logs_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        action_buttons_layout.addWidget(close_button)

        layout.addLayout(action_buttons_layout)

    def _check_configuration(self) -> bool:
        """Check if database builder is properly configured.

        Returns:
            bool: True if all required settings are configured, False otherwise
        """
        db_builder = self.settings.database_builder

        # Check if all three required paths are configured and exist
        if not db_builder.extractor_tool or not db_builder.extractor_tool.exists():
            return False
        if not db_builder.converter_tool or not db_builder.converter_tool.exists():
            return False
        if not db_builder.catalog_file or not db_builder.catalog_file.exists():
            return False

        return True

    def _disable_ui_with_warning(self) -> None:
        """Disable the UI and show configuration warning."""
        # Create warning overlay
        warning_widget = QWidget(self)
        warning_layout = QVBoxLayout(warning_widget)
        warning_layout.setContentsMargins(20, 20, 20, 20)

        # Add spacer
        warning_layout.addStretch()

        # Warning message
        warning_label = QLabel(
            "<h2>⚠️ Configuration Required</h2>"
            "<p><b>The Database Builder is not properly configured.</b></p>"
            "<p>To use the Database Builder feature, you need to configure:</p>"
            "<ul>"
            "<li><b>Extractor Tool</b> (repak.exe) - for extracting PAK files</li>"
            "<li><b>Converter Tool</b> (umodel.exe) - for converting UAsset files</li>"
            "<li><b>Catalog File</b> (catalog.json) - defines all game items</li>"
            "</ul>"
            "<p><b>How to configure:</b></p>"
            "<ol>"
            "<li>Go to <b>File → Configuration...</b></li>"
            "<li>Enable <b>Show Advanced Settings</b></li>"
            "<li>Go to the <b>Database Builder</b> tab</li>"
            "<li>Configure all three required files</li>"
            "<li>Click <b>Save</b></li>"
            "<li>Reopen this window</li>"
            "</ol>"
        )
        warning_label.setWordWrap(True)
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_label.setStyleSheet(
            "QLabel { "
            "border: 2px solid #FF9800; "
            "border-radius: 8px; "
            "padding: 30px; "
            "font-size: 13px; "
            "background-color: palette(alternate-base); "
            "}"
        )
        warning_layout.addWidget(warning_label)

        # Add spacer
        warning_layout.addStretch()

        # Close button
        close_button_layout = QHBoxLayout()
        close_button_layout.addStretch()
        close_button = QPushButton("Close")
        close_button.setFixedWidth(100)
        close_button.clicked.connect(self.close)
        close_button_layout.addWidget(close_button)
        close_button_layout.addStretch()
        warning_layout.addLayout(close_button_layout)

        # Set warning widget as central widget
        self.setCentralWidget(warning_widget)

    def _get_default_pak_directory(self) -> str:
        """Get default directory for PAK files based on platform.

        Returns:
            str: Default directory path for PAK files
        """
        system = platform.system()

        if system == "Windows":
            # Windows: C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks
            default_path = Path(
                "C:/Program Files (x86)/Steam/steamapps/common/Foxhole/War/Content/Paks"
            )
        elif system == "Linux":
            # Check if running under WSL
            try:
                with open("/proc/version") as f:
                    version_info = f.read().lower()
                    if "microsoft" in version_info or "wsl" in version_info:
                        # WSL: /mnt/c/Program Files (x86)/Steam/...
                        default_path = Path(
                            "/mnt/c/Program Files (x86)/Steam/steamapps/common/"
                            "Foxhole/War/Content/Paks"
                        )
                    else:
                        # Regular Linux: use current directory
                        default_path = Path.cwd()
            except OSError:
                # If we can't read /proc/version, assume regular Linux
                default_path = Path.cwd()
        else:
            # Other platforms (macOS, etc.): use current directory
            default_path = Path.cwd()

        # Return as string, use current directory if default doesn't exist
        if default_path.exists():
            return str(default_path)
        return str(Path.cwd())

    def select_vanilla_pak(self) -> None:
        """Open file dialog to select vanilla PAK file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Vanilla PAK File",
            self._get_default_pak_directory(),
            "PAK Files (*.pak);;All Files (*)",
        )
        if file_path:
            self.vanilla_pak_file = file_path
            self.vanilla_pak_display.setText(file_path)

    def clear_vanilla_pak(self) -> None:
        """Clear the vanilla PAK file selection."""
        self.vanilla_pak_file = None
        self.vanilla_pak_display.clear()

    def select_database_path(self) -> None:
        """Open file dialog to select database file."""
        # Start from current path if set, otherwise use current directory
        current_path = self.db_path_input.text().strip()
        start_dir = str(Path(current_path).parent) if current_path else str(Path.cwd())

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Database File",
            start_dir,
            "HDF5 Database (*.h5);;All Files (*)",
        )
        if file_path:
            # Ensure .h5 extension
            if not file_path.endswith(".h5"):
                file_path += ".h5"
            self.db_path_input.setText(file_path)

    def add_mod_pak_files(self) -> None:
        """Open file dialog to add mod PAK files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Mod PAK Files",
            self._get_default_pak_directory(),
            "PAK Files (*.pak);;All Files (*)",
        )
        if files:
            for file_path in files:
                if file_path not in self.mod_pak_files:
                    self.mod_pak_files.append(file_path)
                    self.mod_pak_list_widget.addItem(file_path)

    def remove_selected_mod_paks(self) -> None:
        """Remove selected mod PAK files from the list."""
        selected_items = self.mod_pak_list_widget.selectedItems()
        for item in selected_items:
            row = self.mod_pak_list_widget.row(item)
            self.mod_pak_list_widget.takeItem(row)
            if item.text() in self.mod_pak_files:
                self.mod_pak_files.remove(item.text())

    def clear_all_mod_paks(self) -> None:
        """Clear all mod PAK files from the list."""
        self.mod_pak_list_widget.clear()
        self.mod_pak_files.clear()

    def pak_drag_enter_event(self, e: QDragEnterEvent | None) -> None:
        """Handle drag enter event for PAK files.

        Args:
            e (QDragEnterEvent | None): Drag event
        """
        if e:
            e.accept()

    def pak_drop_event(self, event: QDropEvent | None) -> None:
        """Handle drop event for mod PAK files.

        Args:
            event (QDropEvent | None): Drop event
        """
        if not event:
            return

        mime_data = event.mimeData()
        if mime_data:
            urls = mime_data.urls()
            if urls:
                for url in urls:
                    filepath = url.toLocalFile()
                    if filepath and filepath.endswith(".pak"):
                        if filepath not in self.mod_pak_files:
                            self.mod_pak_files.append(filepath)
                            self.mod_pak_list_widget.addItem(filepath)
        event.accept()

    def validate_inputs(self) -> tuple[bool, str]:
        """Validate user inputs before starting import.

        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        if not self.mod_pak_files:
            return False, "Please add at least one mod PAK file"

        mod_name = self.mod_name_input.text().strip()
        if not mod_name:
            return False, "Please enter a mod name"

        db_path = self.db_path_input.text().strip()
        if not db_path:
            return False, "Please select a destination database file"

        return True, ""

    def start_import(self) -> None:
        """Start the icon import process."""
        # Validate inputs
        is_valid, error_msg = self.validate_inputs()
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error_msg)
            return

        mod_name = self.mod_name_input.text().strip()
        db_path = Path(self.db_path_input.text().strip())

        # Disable inputs and start button
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.mod_name_input.setEnabled(False)
        self.overwrite_checkbox.setEnabled(False)
        self.db_path_input.setEnabled(False)

        # Clear logs
        self.clear_logs()

        # Add log handler to root logger and apply configured log level
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)

        # Apply user's configured log level to root logger
        configured_level = getattr(logging, self.settings.logging.log_level.upper(), logging.INFO)
        root_logger.setLevel(configured_level)

        # Get catalog from settings
        catalog_path = self.settings.database_builder.catalog_file
        if not catalog_path:
            QMessageBox.critical(self, "Error", "Catalog file not configured in settings")
            return

        # Create and start worker
        try:
            self.import_worker = IconImportWorker(
                mod_pak_files=self.mod_pak_files,
                mod_name=mod_name,
                catalog_path=catalog_path,
                overwrite=self.overwrite_checkbox.isChecked(),
                vanilla_pak_file=self.vanilla_pak_file,
                database_path=db_path,
            )
        except ValueError as e:
            QMessageBox.critical(self, "Invalid Mod Name", str(e))
            logger.error("Invalid mod name: %s", e)
            return

        self.import_worker.finished.connect(self.on_import_finished)
        self.import_worker.error.connect(self.on_import_error)
        self.import_worker.start()

        logger.info("Icon import process started for mod: %s", mod_name)

    def cancel_import(self) -> None:
        """Cancel the running import process."""
        if self.import_worker and self.import_worker.isRunning():
            logger.warning("User requested import cancellation")
            self.import_worker.stop()
            self.import_worker.wait()
            self.on_import_finished(False)

    def on_import_finished(self, success: bool) -> None:
        """Handle import process completion.

        Args:
            success (bool): Whether the import was successful
        """
        # Close and remove log handler
        root_logger = logging.getLogger()
        root_logger.removeHandler(self.log_handler)
        self.log_handler.close()

        # Add final status message to logs
        from datetime import datetime

        if success:
            status_log = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": "INFO",
                "module": "icon_import",
                "message": "✓ Import completed successfully!",
                "color": "#00FF00",  # Green
            }
        else:
            status_log = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": "WARNING",
                "module": "icon_import",
                "message": "⚠ Import was cancelled",
                "color": "#FFA500",  # Orange
            }
        self.append_log(status_log)

        # Re-enable inputs
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.mod_name_input.setEnabled(True)
        self.overwrite_checkbox.setEnabled(True)
        self.db_path_input.setEnabled(True)

    def on_import_error(self, error_msg: str) -> None:
        """Handle import process error.

        Args:
            error_msg (str): Error message
        """
        # Add error message to logs
        from datetime import datetime

        error_log = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": "ERROR",
            "module": "icon_import",
            "message": f"✗ Import error: {error_msg}",
            "color": "#FF0000",  # Red
        }
        self.append_log(error_log)

    def append_log(self, log_data: dict[str, str]) -> None:
        """Append a log entry to the log display.

        Args:
            log_data (dict[str, str]): Dictionary containing timestamp, level, module, message,
                and color
        """
        row_position = self.log_display.rowCount()
        self.log_display.insertRow(row_position)

        color = QColor(log_data["color"])
        brush = QBrush(color)

        # Create table items
        time_item = QTableWidgetItem(log_data["timestamp"])
        time_item.setForeground(brush)

        level_item = QTableWidgetItem(log_data["level"])
        level_item.setForeground(brush)

        module_item = QTableWidgetItem(log_data["module"])
        module_item.setForeground(brush)

        message_item = QTableWidgetItem(log_data["message"])
        message_item.setForeground(brush)
        # Enable text wrapping for message item and align to top
        message_item.setTextAlignment(int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop))

        # Add items to table
        self.log_display.setItem(row_position, 0, time_item)
        self.log_display.setItem(row_position, 1, level_item)
        self.log_display.setItem(row_position, 2, module_item)
        self.log_display.setItem(row_position, 3, message_item)

        # Resize row to fit content
        self.log_display.resizeRowToContents(row_position)

        # Auto-scroll to bottom
        self.log_display.scrollToBottom()

    def clear_logs(self) -> None:
        """Clear the log display."""
        self.log_display.setRowCount(0)

    def _log_key_press_event(self, event: QKeyEvent | None) -> None:
        """Handle key press events in log display.

        Args:
            event (QKeyEvent | None): Key event
        """
        if not event:
            return

        # Handle CTRL-C for copying selected rows
        if event.matches(QKeySequence.StandardKey.Copy):
            self._copy_selected_logs()
        else:
            # Call the default implementation for other keys
            QTableWidget.keyPressEvent(self.log_display, event)

    def _copy_selected_logs(self) -> None:
        """Copy selected log rows to clipboard."""
        selected_rows = self.log_display.selectionModel()
        if not selected_rows:
            return

        selected_indexes = selected_rows.selectedRows()
        if not selected_indexes:
            return

        # Build text from selected rows
        lines = []
        for index in sorted(selected_indexes, key=lambda x: x.row()):
            row = index.row()
            time_item = self.log_display.item(row, 0)
            level_item = self.log_display.item(row, 1)
            module_item = self.log_display.item(row, 2)
            message_item = self.log_display.item(row, 3)

            if time_item and level_item and module_item and message_item:
                # Format: [Time] LEVEL Module: Message
                line = (
                    f"[{time_item.text()}] {level_item.text()} "
                    f"{module_item.text()}: {message_item.text()}"
                )
                lines.append(line)

        if lines:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText("\n".join(lines))

    def closeEvent(self, event: object) -> None:
        """Handle window close event.

        Args:
            event (object): Close event
        """
        if self.import_worker and self.import_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Import In Progress",
                "An import is currently running. Are you sure you want to close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.import_worker.stop()
                self.import_worker.wait()
                event.accept()  # type: ignore[attr-defined]
            else:
                event.ignore()  # type: ignore[attr-defined]
        else:
            event.accept()  # type: ignore[attr-defined]

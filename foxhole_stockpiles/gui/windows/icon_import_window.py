"""Icon import window for importing new icons to the database."""

import logging
import platform
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
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
        self.pak_files: list[str] = []

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
        self.setWindowTitle("Import Icons to Database")
        self.setGeometry(100, 100, 900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # PAK Files Section
        pak_group = QGroupBox("PAK Files")
        pak_layout = QVBoxLayout()
        pak_group.setLayout(pak_layout)

        # PAK file list
        self.pak_list_widget = QListWidget()
        self.pak_list_widget.setAcceptDrops(True)
        self.pak_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.pak_list_widget.dragEnterEvent = self.pak_drag_enter_event  # type: ignore[method-assign]
        self.pak_list_widget.dropEvent = self.pak_drop_event  # type: ignore[method-assign]
        pak_layout.addWidget(self.pak_list_widget)

        # PAK file buttons
        pak_buttons_layout = QHBoxLayout()
        add_pak_button = QPushButton("Add PAK Files...")
        add_pak_button.clicked.connect(self.add_pak_files)
        pak_buttons_layout.addWidget(add_pak_button)

        remove_pak_button = QPushButton("Remove Selected")
        remove_pak_button.clicked.connect(self.remove_selected_paks)
        pak_buttons_layout.addWidget(remove_pak_button)

        clear_pak_button = QPushButton("Clear All")
        clear_pak_button.clicked.connect(self.clear_all_paks)
        pak_buttons_layout.addWidget(clear_pak_button)

        pak_buttons_layout.addStretch()
        pak_layout.addLayout(pak_buttons_layout)

        layout.addWidget(pak_group)

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

        # Destination database (read-only)
        db_layout = QHBoxLayout()
        db_layout.addWidget(QLabel("Destination Database:"))
        self.db_path_display = QLineEdit()
        self.db_path_display.setReadOnly(True)
        self.db_path_display.setStyleSheet(
            "QLineEdit { background-color: #F0F0F0; color: #606060; }"
        )
        db_path = self.settings.scanner.database_path
        self.db_path_display.setText(str(db_path) if db_path else "Not configured")
        self.db_path_display.setToolTip(
            "Database file where templates will be saved\n"
            "Configure in: File → Configuration → Scanner tab"
        )
        db_layout.addWidget(self.db_path_display)
        config_layout.addLayout(db_layout)

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
        vertical_header = self.log_display.verticalHeader()
        if vertical_header:
            vertical_header.setVisible(False)
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

        logs_layout.addWidget(self.log_display)

        # Log controls
        log_controls = QHBoxLayout()
        clear_logs_button = QPushButton("Clear Logs")
        clear_logs_button.clicked.connect(self.clear_logs)
        log_controls.addStretch()
        log_controls.addWidget(clear_logs_button)
        logs_layout.addLayout(log_controls)

        layout.addWidget(logs_group)

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
            "<p>To use the Icon Import feature, you need to configure:</p>"
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
            "background-color: #fff3e0; "
            "border: 2px solid #ff9800; "
            "border-radius: 8px; "
            "padding: 30px; "
            "font-size: 13px; "
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

    def add_pak_files(self) -> None:
        """Open file dialog to add PAK files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PAK Files",
            self._get_default_pak_directory(),
            "PAK Files (*.pak);;All Files (*)",
        )
        if files:
            for file_path in files:
                if file_path not in self.pak_files:
                    self.pak_files.append(file_path)
                    self.pak_list_widget.addItem(file_path)

    def remove_selected_paks(self) -> None:
        """Remove selected PAK files from the list."""
        selected_items = self.pak_list_widget.selectedItems()
        for item in selected_items:
            row = self.pak_list_widget.row(item)
            self.pak_list_widget.takeItem(row)
            if item.text() in self.pak_files:
                self.pak_files.remove(item.text())

    def clear_all_paks(self) -> None:
        """Clear all PAK files from the list."""
        self.pak_list_widget.clear()
        self.pak_files.clear()

    def pak_drag_enter_event(self, e: QDragEnterEvent | None) -> None:
        """Handle drag enter event for PAK files.

        Args:
            e (QDragEnterEvent | None): Drag event
        """
        if e:
            e.accept()

    def pak_drop_event(self, event: QDropEvent | None) -> None:
        """Handle drop event for PAK files.

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
                        if filepath not in self.pak_files:
                            self.pak_files.append(filepath)
                            self.pak_list_widget.addItem(filepath)
        event.accept()

    def validate_inputs(self) -> tuple[bool, str]:
        """Validate user inputs before starting import.

        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        if not self.pak_files:
            return False, "Please add at least one PAK file"

        mod_name = self.mod_name_input.text().strip()
        if not mod_name:
            return False, "Please enter a mod name"

        return True, ""

    def start_import(self) -> None:
        """Start the icon import process."""
        # Validate inputs
        is_valid, error_msg = self.validate_inputs()
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error_msg)
            return

        mod_name = self.mod_name_input.text().strip()

        # Disable inputs and start button
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.mod_name_input.setEnabled(False)
        self.overwrite_checkbox.setEnabled(False)

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
        self.import_worker = IconImportWorker(
            pak_files=self.pak_files,
            mod_name=mod_name,
            catalog_path=catalog_path,
            overwrite=self.overwrite_checkbox.isChecked(),
        )

        self.import_worker.finished.connect(self.on_import_finished)
        self.import_worker.error.connect(self.on_import_error)
        self.import_worker.start()

        logger.info("Icon import process started for mod: %s", mod_name)

    def cancel_import(self) -> None:
        """Cancel the running import process."""
        if self.import_worker and self.import_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Cancel Import",
                "Are you sure you want to cancel the import process?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                logger.warning("User requested import cancellation")
                self.import_worker.stop()
                self.import_worker.wait()
                self.on_import_finished(False)

    def on_import_finished(self, success: bool) -> None:
        """Handle import process completion.

        Args:
            success (bool): Whether the import was successful
        """
        # Remove log handler
        root_logger = logging.getLogger()
        root_logger.removeHandler(self.log_handler)

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

        # Add items to table
        self.log_display.setItem(row_position, 0, time_item)
        self.log_display.setItem(row_position, 1, level_item)
        self.log_display.setItem(row_position, 2, module_item)
        self.log_display.setItem(row_position, 3, message_item)

        # Auto-scroll to bottom
        self.log_display.scrollToBottom()

    def clear_logs(self) -> None:
        """Clear the log display."""
        self.log_display.setRowCount(0)

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

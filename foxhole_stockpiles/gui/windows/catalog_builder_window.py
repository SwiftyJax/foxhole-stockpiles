"""Catalog builder window for building item catalog from PAK files."""

import logging
import os
import platform
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QKeyEvent, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.core.settings import get_settings, reload_settings
from foxhole_stockpiles.gui.utils.catalog_builder_worker import CatalogBuilderWorker
from foxhole_stockpiles.gui.utils.qt_log_handler import QtLogHandler
from foxhole_stockpiles.gui.windows.catalog_builder_settings_dialog import (
    CatalogBuilderSettingsDialog,
)

logger = logging.getLogger(__name__)


class CatalogBuilderWindow(QMainWindow):
    """Window for building item catalog from PAK files."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the catalog builder window.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.build_worker: CatalogBuilderWorker | None = None
        self.pak_file: str | None = None

        # Check if catalog builder is configured
        self.settings = get_settings()
        self.is_configured = self._check_configuration()

        # Setup log handler
        self.log_handler = QtLogHandler()
        self.log_handler.log_message.connect(self.append_log)
        log_level = getattr(logging, self.settings.logging.log_level.upper(), logging.INFO)
        self.log_handler.setLevel(log_level)

        self.init_ui()

        # Disable UI if not configured
        if not self.is_configured:
            self._disable_ui_with_warning()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Build Catalog")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # PAK File Section
        pak_group = QGroupBox("PAK File")
        pak_layout = QVBoxLayout()
        pak_group.setLayout(pak_layout)

        # Info text
        pak_info = QLabel(
            "Select the Foxhole PAK file (War-WindowsNoEditor.pak) to build the catalog from."
        )
        pak_info.setWordWrap(True)
        pak_layout.addWidget(pak_info)

        # PAK file path display
        pak_path_layout = QHBoxLayout()
        self.pak_display = QLineEdit()
        self.pak_display.setReadOnly(True)
        self.pak_display.setPlaceholderText("No PAK file selected")
        pak_path_layout.addWidget(self.pak_display)

        self.pak_browse_button = QPushButton("Browse...")
        self.pak_browse_button.clicked.connect(self.select_pak_file)
        pak_path_layout.addWidget(self.pak_browse_button)

        pak_layout.addLayout(pak_path_layout)
        layout.addWidget(pak_group)

        # Output Section
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()
        output_group.setLayout(output_layout)

        # Output path
        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(QLabel("Catalog File:"))
        self.output_path_input = QLineEdit()
        self.output_path_input.setText("catalog.json")
        self.output_path_input.setPlaceholderText("Path for output catalog.json")
        output_path_layout.addWidget(self.output_path_input)

        output_browse_button = QPushButton("Browse...")
        output_browse_button.clicked.connect(self.select_output_path)
        output_path_layout.addWidget(output_browse_button)

        output_layout.addLayout(output_path_layout)

        # Workers
        cpu_count = os.cpu_count() or 1
        workers_layout = QHBoxLayout()
        workers_layout.addWidget(QLabel("Workers:"))
        self.workers_spinbox = QSpinBox()
        self.workers_spinbox.setMinimum(1)
        self.workers_spinbox.setMaximum(cpu_count)
        self.workers_spinbox.setValue(cpu_count)
        self.workers_spinbox.setToolTip("Number of parallel processes for uasset conversion.")
        self.workers_spinbox.setFixedWidth(80)
        workers_layout.addWidget(self.workers_spinbox)
        workers_hint = QLabel(f"({cpu_count} cores detected)")
        workers_hint.setStyleSheet("color: gray; font-size: 11px;")
        workers_layout.addWidget(workers_hint)
        workers_layout.addStretch()

        output_layout.addLayout(workers_layout)
        layout.addWidget(output_group)

        # Logs Section
        logs_group = QGroupBox("Process Logs")
        logs_layout = QVBoxLayout()
        logs_group.setLayout(logs_layout)

        self.log_display = QTableWidget()
        self.log_display.setColumnCount(4)
        self.log_display.setHorizontalHeaderLabels(["Time", "Level", "Module", "Message"])
        self.log_display.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.log_display.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.log_display.setWordWrap(True)
        vertical_header = self.log_display.verticalHeader()
        if vertical_header:
            vertical_header.setVisible(False)
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

        self.log_display.setColumnWidth(0, 150)
        self.log_display.setColumnWidth(1, 80)
        self.log_display.setColumnWidth(2, 250)

        # Enable copy on CTRL-C
        self.log_display.keyPressEvent = self._log_key_press_event  # type: ignore[assignment,method-assign]

        logs_layout.addWidget(self.log_display)
        layout.addWidget(logs_group, stretch=1)

        # Action Buttons
        action_buttons_layout = QHBoxLayout()

        self.start_button = QPushButton("Build Catalog")
        self.start_button.clicked.connect(self.start_build)
        action_buttons_layout.addWidget(self.start_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_build)
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
        """Check if catalog builder is properly configured.

        Returns:
            bool: True if all required tools are configured, False otherwise
        """
        external_tools = self.settings.external_tools

        # Check if repak and uassetgui are configured and exist
        if not external_tools.repak or not external_tools.repak.exists():
            return False
        if not external_tools.uassetgui or not external_tools.uassetgui.exists():
            return False

        return True

    def _disable_ui_with_warning(self) -> None:
        """Disable the UI and show configuration warning."""
        warning_widget = QWidget(self)
        warning_layout = QVBoxLayout(warning_widget)
        warning_layout.setContentsMargins(20, 20, 20, 20)

        warning_layout.addStretch()

        warning_label = QLabel(
            "<h2>Configuration Required</h2>"
            "<p><b>The Catalog Builder is not properly configured.</b></p>"
            "<p>To use the Catalog Builder feature, you need to configure:</p>"
            "<ul>"
            "<li><b>Extractor Tool</b> (repak) - for extracting PAK files</li>"
            "<li><b>JSON Converter</b> (UAssetGUI) - for converting UAsset files to JSON</li>"
            "</ul>"
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

        warning_layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        configure_button = QPushButton("Configure...")
        configure_button.setFixedWidth(120)
        configure_button.clicked.connect(self._open_settings_dialog)
        button_layout.addWidget(configure_button)

        close_button = QPushButton("Close")
        close_button.setFixedWidth(100)
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        button_layout.addStretch()
        warning_layout.addLayout(button_layout)

        self.setCentralWidget(warning_widget)

    def _open_settings_dialog(self) -> None:
        """Open the catalog builder settings dialog."""
        dialog = CatalogBuilderSettingsDialog(self)
        if dialog.exec():
            reload_settings()
            self.settings = get_settings()
            self.is_configured = self._check_configuration()

            if self.is_configured:
                self.init_ui()
                logger.info("Catalog builder configured successfully")

    def _get_default_pak_directory(self) -> str:
        """Get default directory for PAK files based on platform.

        Returns:
            str: Default directory path for PAK files
        """
        default_path = Path.cwd()
        system = platform.system()

        if system == "Windows":
            steam_path = Path(
                "C:/Program Files (x86)/Steam/steamapps/common/Foxhole/War/Content/Paks"
            )
            if steam_path.exists():
                default_path = steam_path
        elif system == "Linux":
            try:
                with open("/proc/version") as f:
                    version_info = f.read().lower()
                    if "microsoft" in version_info or "wsl" in version_info:
                        wsl_path = Path(
                            "/mnt/c/Program Files (x86)/Steam/steamapps/common/"
                            "Foxhole/War/Content/Paks"
                        )
                        if wsl_path.exists():
                            default_path = wsl_path
            except OSError:
                pass

        return str(default_path)

    def select_pak_file(self) -> None:
        """Open file dialog to select PAK file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PAK File",
            self._get_default_pak_directory(),
            "PAK Files (*.pak);;All Files (*)",
        )
        if file_path:
            self.pak_file = file_path
            self.pak_display.setText(file_path)

    def select_output_path(self) -> None:
        """Open file dialog to select output catalog path."""
        current_path = self.output_path_input.text().strip()
        start_dir = str(Path(current_path).parent) if current_path else str(Path.cwd())

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Output Catalog File",
            start_dir,
            "JSON Files (*.json);;All Files (*)",
        )
        if file_path:
            if not file_path.endswith(".json"):
                file_path += ".json"
            self.output_path_input.setText(file_path)

    def validate_inputs(self) -> tuple[bool, str]:
        """Validate user inputs before starting build.

        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        if not self.pak_file:
            return False, "Please select a PAK file"

        if not Path(self.pak_file).exists():
            return False, "The selected PAK file does not exist"

        output_path = self.output_path_input.text().strip()
        if not output_path:
            return False, "Please specify an output path for the catalog"

        return True, ""

    def start_build(self) -> None:
        """Start the catalog build process."""
        is_valid, error_msg = self.validate_inputs()
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error_msg)
            return

        # Disable inputs
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.pak_browse_button.setEnabled(False)
        self.output_path_input.setEnabled(False)
        self.workers_spinbox.setEnabled(False)

        # Clear logs
        self.clear_logs()

        # Add log handler
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        configured_level = getattr(logging, self.settings.logging.log_level.upper(), logging.INFO)
        root_logger.setLevel(configured_level)

        # Create and start worker
        self.build_worker = CatalogBuilderWorker(
            pak_file=Path(self.pak_file),  # type: ignore[arg-type]
            output_path=Path(self.output_path_input.text().strip()),
            extractor_tool=self.settings.external_tools.repak,  # type: ignore[arg-type]
            converter_tool=self.settings.external_tools.uassetgui,  # type: ignore[arg-type]
            workers=self.workers_spinbox.value(),
        )
        self.build_worker.finished.connect(self.on_build_finished)
        self.build_worker.error.connect(self.on_build_error)
        self.build_worker.progress.connect(self.on_build_progress)
        self.build_worker.start()

        logger.info("Catalog build process started")

    def cancel_build(self) -> None:
        """Cancel the running build process."""
        if self.build_worker and self.build_worker.isRunning():
            logger.warning("User requested build cancellation")
            self.build_worker.stop()
            self.build_worker.wait()
            self.on_build_finished(False)

    def on_build_finished(self, success: bool) -> None:
        """Handle build process completion.

        Args:
            success (bool): Whether the build was successful
        """
        root_logger = logging.getLogger()
        root_logger.removeHandler(self.log_handler)

        from datetime import datetime

        if success:
            status_log = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": "INFO",
                "module": "catalog_builder",
                "message": "Catalog build completed successfully!",
                "color": "#00FF00",
            }
        else:
            status_log = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": "WARNING",
                "module": "catalog_builder",
                "message": "Build was cancelled",
                "color": "#FFA500",
            }
        self.append_log(status_log)

        # Re-enable inputs
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.pak_browse_button.setEnabled(True)
        self.output_path_input.setEnabled(True)
        self.workers_spinbox.setEnabled(True)

    def on_build_error(self, error_msg: str) -> None:
        """Handle build process error.

        Args:
            error_msg (str): Error message
        """
        from datetime import datetime

        error_log = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": "ERROR",
            "module": "catalog_builder",
            "message": f"Build error: {error_msg}",
            "color": "#FF0000",
        }
        self.append_log(error_log)

    def on_build_progress(self, message: str) -> None:
        """Handle build progress update.

        Args:
            message (str): Progress message
        """
        from datetime import datetime

        progress_log = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": "INFO",
            "module": "catalog_builder",
            "message": message,
            "color": "#2196F3",
        }
        self.append_log(progress_log)

    def append_log(self, log_data: dict[str, str]) -> None:
        """Append a log entry to the log display.

        Args:
            log_data (dict[str, str]): Dictionary containing log data
        """
        row_position = self.log_display.rowCount()
        self.log_display.insertRow(row_position)

        color = QColor(log_data["color"])
        brush = QBrush(color)

        time_item = QTableWidgetItem(log_data["timestamp"])
        time_item.setForeground(brush)

        level_item = QTableWidgetItem(log_data["level"])
        level_item.setForeground(brush)

        module_item = QTableWidgetItem(log_data["module"])
        module_item.setForeground(brush)

        message_item = QTableWidgetItem(log_data["message"])
        message_item.setForeground(brush)
        message_item.setTextAlignment(int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop))

        self.log_display.setItem(row_position, 0, time_item)
        self.log_display.setItem(row_position, 1, level_item)
        self.log_display.setItem(row_position, 2, module_item)
        self.log_display.setItem(row_position, 3, message_item)

        self.log_display.resizeRowToContents(row_position)
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

        if event.matches(QKeySequence.StandardKey.Copy):
            self._copy_selected_logs()
        else:
            QTableWidget.keyPressEvent(self.log_display, event)

    def _copy_selected_logs(self) -> None:
        """Copy selected log rows to clipboard."""
        selected_rows = self.log_display.selectionModel()
        if not selected_rows:
            return

        selected_indexes = selected_rows.selectedRows()
        if not selected_indexes:
            return

        lines = []
        for index in sorted(selected_indexes, key=lambda x: x.row()):
            row = index.row()
            time_item = self.log_display.item(row, 0)
            level_item = self.log_display.item(row, 1)
            module_item = self.log_display.item(row, 2)
            message_item = self.log_display.item(row, 3)

            if time_item and level_item and module_item and message_item:
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
        if self.build_worker and self.build_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Build In Progress",
                "A build is currently running. Are you sure you want to close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.build_worker.stop()
                self.build_worker.wait()
                self._cleanup_and_accept(event)
            else:
                event.ignore()  # type: ignore[attr-defined]
        else:
            self._cleanup_and_accept(event)

    def _cleanup_and_accept(self, event: object) -> None:
        """Clean up resources and accept close event.

        Args:
            event (object): Close event
        """
        self.log_handler.close()
        event.accept()  # type: ignore[attr-defined]

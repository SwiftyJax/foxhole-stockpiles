"""Server control panel widget for managing the FastAPI server and scanning screenshots."""

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.gui.utils.qt_log_handler import QtLogHandler
from foxhole_stockpiles.gui.utils.scan_worker import ScanWorker
from foxhole_stockpiles.gui.utils.scanner_client import ScannerClient
from foxhole_stockpiles.gui.utils.server_thread import ServerThread

logger = logging.getLogger(__name__)


class ServerControlPanel(QWidget):
    """Panel for controlling the FastAPI server and scanning screenshots."""

    server_started = pyqtSignal()
    server_stopped = pyqtSignal()
    screenshot_dropped = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the server control panel.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.server_running = False
        self.server_thread: ServerThread | None = None

        # Setup log handler
        self.log_handler = QtLogHandler()
        self.log_handler.log_message.connect(self.append_log)

        # Setup scanner client
        self.scanner_client = ScannerClient()

        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Top section: Server Control and Drop Zone side by side
        top_layout = QHBoxLayout()

        # Server Control Group (left side)
        server_group = QGroupBox("")
        server_group.setMaximumHeight(100)
        server_layout = QHBoxLayout()
        server_group.setLayout(server_layout)

        self.start_stop_button = QPushButton("Start Server")
        self.start_stop_button.clicked.connect(self.toggle_server)
        self.start_stop_button.setFixedWidth(120)
        server_layout.addWidget(self.start_stop_button)

        self.status_label = QLabel("Status: Stopped")
        self.status_label.setStyleSheet("QLabel { font-weight: bold; }")
        server_layout.addWidget(self.status_label)

        server_layout.addStretch()

        top_layout.addWidget(server_group, 1)

        # Screenshot Scanning Group (right side)
        scan_group = QGroupBox("")
        scan_group.setMaximumHeight(100)
        scan_layout = QVBoxLayout()
        scan_group.setLayout(scan_layout)

        # Drop zone
        self.drop_zone = QLabel("Drop screenshot here or click to select file")
        self.drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_zone.setStyleSheet(
            "QLabel { "
            "border: 2px dashed #aaa; "
            "border-radius: 8px; "
            "background-color: #f5f5f5; "
            "color: #666; "
            "font-size: 12px; "
            "padding: 10px; "
            "}"
        )
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.mousePressEvent = self.select_screenshot  # type: ignore[assignment]
        self.drop_zone.dragEnterEvent = self.drag_enter_event  # type: ignore[assignment]
        self.drop_zone.dropEvent = self.drop_event  # type: ignore[assignment]
        scan_layout.addWidget(self.drop_zone)

        top_layout.addWidget(scan_group, 2)

        layout.addLayout(top_layout)

        # Server Logs Group (full width below)
        logs_group = QGroupBox("")
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

    def toggle_server(self) -> None:
        """Toggle server start/stop."""
        if self.server_running:
            self.stop_server()
        else:
            self.start_server()

    def start_server(self) -> None:
        """Start the FastAPI server."""
        logger.info("Starting server...")

        # Add log handler to root logger to capture all logs
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)

        # Create and start server thread
        self.server_thread = ServerThread()
        self.server_thread.start()

        self.server_running = True
        self.start_stop_button.setText("Stop Server")
        self.status_label.setText("Status: Running")
        self.status_label.setStyleSheet("QLabel { font-weight: bold; color: green; }")
        self.server_started.emit()

    def stop_server(self) -> None:
        """Stop the FastAPI server."""
        logger.info("Stopping server...")

        # Stop server thread
        if self.server_thread:
            self.server_thread.stop()
            self.server_thread = None

        # Remove log handler
        root_logger = logging.getLogger()
        root_logger.removeHandler(self.log_handler)

        self.server_running = False
        self.start_stop_button.setText("Start Server")
        self.status_label.setText("Status: Stopped")
        self.status_label.setStyleSheet("QLabel { font-weight: bold; color: red; }")
        self.server_stopped.emit()

    def select_screenshot(self, event: object) -> None:
        """Open file dialog to select a screenshot.

        Args:
            event (object): Mouse event (unused)
        """
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Screenshot",
            "",
            "Images (*.png *.jpg *.jpeg);;All Files (*)",
        )
        if filepath:
            self.process_screenshot(filepath)

    def drag_enter_event(self, event: object) -> None:
        """Handle drag enter event.

        Args:
            event (object): Drag event
        """
        # Type checking is disabled for this method since we're dynamically assigning it
        event.accept()  # type: ignore[attr-defined]

    def drop_event(self, event: object) -> None:
        """Handle drop event.

        Args:
            event (object): Drop event
        """
        # Type checking is disabled for this method since we're dynamically assigning it
        urls = event.mimeData().urls()  # type: ignore[attr-defined]
        if urls:
            filepath = urls[0].toLocalFile()
            if filepath:
                self.process_screenshot(filepath)
        event.accept()  # type: ignore[attr-defined]

    def process_screenshot(self, filepath: str) -> None:
        """Process a screenshot file.

        Args:
            filepath (str): Path to the screenshot file
        """
        # Check if server is running
        if not self.server_running:
            logger.error("Cannot scan: Server is not running!")
            return

        # Scan the screenshot in background thread
        worker = ScanWorker(self.scanner_client, filepath)
        worker.finished.connect(lambda: self.screenshot_dropped.emit(filepath))
        worker.start()

        # Keep reference to prevent garbage collection
        if not hasattr(self, "_scan_workers"):
            self._scan_workers = []
        self._scan_workers.append(worker)
        worker.finished.connect(lambda: self._scan_workers.remove(worker))

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

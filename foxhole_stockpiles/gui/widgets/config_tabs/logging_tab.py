"""Logging settings tab."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from foxhole_stockpiles.core.settings.sections.logging import LoggingSettings


class LoggingTab(QWidget):
    """Tab for Logging configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Logging tab.

        Args:
            parent (QWidget | None): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QFormLayout(self)

        # Log Level
        log_level_label = QLabel("Log Level:")
        log_level_label.setToolTip(
            "Minimum log level to record:\n\n"
            "• DEBUG - Very detailed logs for troubleshooting\n"
            "• INFO - General operational information (recommended)\n"
            "• WARNING - Warning messages and errors\n"
            "• ERROR - Only error messages\n"
            "• CRITICAL - Only critical failures"
        )
        self.log_level_input = QComboBox()
        self.log_level_input.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_input.setCurrentText("INFO")
        layout.addRow(log_level_label, self.log_level_input)

        # Log Format
        log_format_label = QLabel("Log Format:")
        log_format_label.setToolTip(
            "Python logging format string.\n\n"
            "Common placeholders:\n"
            "• %(asctime)s - Timestamp\n"
            "• %(name)s - Logger name\n"
            "• %(levelname)s - Log level (DEBUG, INFO, etc.)\n"
            "• %(message)s - Log message\n\n"
            "See Python logging documentation for more options."
        )
        self.log_format_input = QLineEdit()
        self.log_format_input.setPlaceholderText(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        layout.addRow(log_format_label, self.log_format_input)

        # Date Format
        date_format_label = QLabel("Date Format:")
        date_format_label.setToolTip(
            "Date/time format for log timestamps.\n\n"
            "Uses Python strftime format codes:\n"
            "• %Y - 4-digit year\n"
            "• %m - 2-digit month\n"
            "• %d - 2-digit day\n"
            "• %H - 24-hour hour\n"
            "• %M - 2-digit minute\n"
            "• %S - 2-digit second\n\n"
            "Example: %Y-%m-%d %H:%M:%S produces 2025-01-15 14:30:45"
        )
        self.date_format_input = QLineEdit()
        self.date_format_input.setPlaceholderText("%Y-%m-%d %H:%M:%S")
        layout.addRow(date_format_label, self.date_format_input)

        # Rotate Logs
        rotate_logs_label = QLabel("Rotate Logs:")
        rotate_logs_label.setToolTip(
            "Automatically rotate log files when they get too large.\n\n"
            "When enabled, old logs are archived and new log files are created.\n"
            "Prevents log files from consuming too much disk space."
        )
        self.rotate_logs_input = QCheckBox("Enable log rotation")
        layout.addRow(rotate_logs_label, self.rotate_logs_input)

        # Log File
        log_file_label = QLabel("Log File:")
        log_file_label.setToolTip(
            "Optional path to save log messages to a file.\n\n"
            "If not specified, logs are only written to console.\n"
            "Useful for debugging and keeping a record of operations."
        )
        log_file_layout = QHBoxLayout()
        self.log_file_input = QLineEdit()
        self.log_file_input.setPlaceholderText("Optional: path to log file")
        log_browse = QPushButton("Browse...")
        log_browse.clicked.connect(self.browse_log_file)
        log_file_layout.addWidget(self.log_file_input)
        log_file_layout.addWidget(log_browse)
        layout.addRow(log_file_label, log_file_layout)

    def browse_log_file(self) -> None:
        """Open file dialog for log file path."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Select Log File",
            "",
            "Log Files (*.log);;All Files (*)",
        )
        if filepath:
            self.log_file_input.setText(filepath)

    def set_values(self, settings: LoggingSettings) -> None:
        """Set widget values from settings.

        Args:
            settings (LoggingSettings): LoggingSettings instance to load values from.
        """
        self.log_level_input.setCurrentText(settings.log_level.upper())
        self.log_format_input.setText(settings.log_format)
        self.date_format_input.setText(settings.date_format)
        self.rotate_logs_input.setChecked(settings.rotate_logs)
        self.log_file_input.setText(str(settings.log_file) if settings.log_file else "")

    def get_values(self) -> LoggingSettings:
        """Get current values from widgets.

        Returns:
            LoggingSettings: LoggingSettings instance with current values from widgets
        """
        return LoggingSettings(
            log_level=self.log_level_input.currentText(),
            log_format=self.log_format_input.text(),
            date_format=self.date_format_input.text(),
            rotate_logs=self.rotate_logs_input.isChecked(),
            log_file=self.log_file_input.text() or None,
        )

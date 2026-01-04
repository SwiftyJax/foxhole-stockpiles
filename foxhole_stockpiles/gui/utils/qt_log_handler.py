"""Qt log handler for capturing logs and emitting them to GUI."""

import logging
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal


class QtLogHandler(logging.Handler, QObject):
    """Custom log handler that emits log records as Qt signals."""

    log_message = pyqtSignal(dict)

    def __init__(self) -> None:
        """Initialize the Qt log handler."""
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record.

        Args:
            record (logging.LogRecord): Log record to emit
        """
        try:
            # Determine color based on logger name and level
            if "gui" in record.name or "scanner_client" in record.name:
                color = "#00BFFF"  # Client logs in cyan
            else:
                color = "#FFFFFF"  # Server logs in white

            # Override with level-specific colors
            if record.levelno >= logging.ERROR:
                color = "#FF6B6B"  # Red for errors
            elif record.levelno >= logging.WARNING:
                color = "#FFA500"  # Orange for warnings

            # Emit structured log data
            log_data = {
                "timestamp": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "module": record.name,
                "message": record.getMessage(),
                "color": color,
            }
            self.log_message.emit(log_data)
        except Exception:
            self.handleError(record)

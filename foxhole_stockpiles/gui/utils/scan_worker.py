"""Worker thread for scanning screenshots in background."""

from PyQt6.QtCore import QThread, pyqtSignal

from foxhole_stockpiles.gui.utils.scanner_client import ScannerClient


class ScanWorker(QThread):
    """Worker thread for scanning screenshots."""

    finished = pyqtSignal()

    def __init__(self, scanner_client: ScannerClient, filepath: str) -> None:
        """Initialize the scan worker.

        Args:
            scanner_client (ScannerClient): Scanner client instance
            filepath (str): Path to the screenshot file
        """
        super().__init__()
        self.scanner_client = scanner_client
        self.filepath = filepath

    def run(self) -> None:
        """Run the scan in background thread."""
        self.scanner_client.scan_screenshot(self.filepath)
        self.finished.emit()

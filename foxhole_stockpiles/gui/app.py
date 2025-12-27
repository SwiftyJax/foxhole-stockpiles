"""Qt application launcher."""

import sys

from PyQt6.QtWidgets import QApplication

from foxhole_stockpiles import __version__
from foxhole_stockpiles.gui.windows.main_window import MainWindow


def launch_gui() -> None:
    """Launch the PyQt6 GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("FS")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("FS")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

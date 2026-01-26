"""Qt application launcher."""

import logging
import multiprocessing
import sys

from PyQt6.QtWidgets import QApplication

from foxhole_stockpiles import __version__
from foxhole_stockpiles.gui.windows.main_window import MainWindow
from foxhole_stockpiles.i18n import get_translator

logger = logging.getLogger(__name__)


def _load_language_from_settings() -> str:
    """Load language setting from config file.

    Returns:
        str: Language code (defaults to 'en' if not found)
    """
    try:
        from foxhole_stockpiles.core.settings.app_settings import AppSettings

        settings = AppSettings()
        return settings.gui.language
    except Exception as e:
        logger.debug("Could not load language from settings: %s", e)
        return "en"


def launch_gui() -> None:
    """Launch the PyQt6 GUI application."""
    # Required for multiprocessing to work correctly in frozen executables (PyInstaller)
    # This must be called before any other multiprocessing code runs
    multiprocessing.freeze_support()

    # Initialize translator with user's language preference
    language = _load_language_from_settings()
    get_translator(language)

    app = QApplication(sys.argv)
    app.setApplicationName("FS")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("FS")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    launch_gui()

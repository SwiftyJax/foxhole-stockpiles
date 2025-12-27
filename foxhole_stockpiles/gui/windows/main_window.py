"""Main application window."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles import __version__
from foxhole_stockpiles.gui.windows.config_window import ConfigWindow


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle(f"FS (Foxhole Stockpiles) - v{__version__}")
        self.setGeometry(100, 100, 1000, 700)

        # Create central widget with placeholder content
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Welcome message
        welcome_label = QLabel(f"FS (Foxhole Stockpiles)\nVersion {__version__}")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("QLabel { font-size: 24px; font-weight: bold; padding: 20px; }")
        layout.addWidget(welcome_label)

        # Placeholder for server control
        placeholder_label = QLabel(
            "Server Control\n\nComing Soon\n\nUse File > Configuration to manage settings"
        )
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("QLabel { font-size: 16px; color: gray; padding: 20px; }")
        layout.addWidget(placeholder_label)

        # Create menu bar
        self.create_menu_bar()

        # Create status bar
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage("Ready")

    def create_menu_bar(self) -> None:
        """Create the menu bar."""
        menu_bar = self.menuBar()
        if menu_bar is None:
            return

        # File menu
        file_menu = menu_bar.addMenu("&File")
        if file_menu is None:
            return

        config_action = file_menu.addAction("&Configuration...")
        if config_action is not None:
            config_action.triggered.connect(self.show_configuration)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("E&xit")
        if exit_action is not None:
            exit_action.triggered.connect(self.close)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        if help_menu is None:
            return
        about_action = help_menu.addAction("&About")
        if about_action is not None:
            about_action.triggered.connect(self.show_about)

    def show_configuration(self) -> None:
        """Show configuration window as modal dialog centered on main window."""
        config_window = ConfigWindow(self)
        config_window.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Center the config window on the main window
        main_geometry = self.geometry()
        config_geometry = config_window.geometry()

        center_x = main_geometry.x() + (main_geometry.width() - config_geometry.width()) // 2
        center_y = main_geometry.y() + (main_geometry.height() - config_geometry.height()) // 2

        config_window.move(center_x, center_y)
        config_window.show()

    def show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About FS",
            f"<h2>FS (Foxhole Stockpiles)</h2>"
            f"<p>Version {__version__}</p>"
            f"<p>A tool for scanning and analyzing Foxhole game stockpiles.</p>"
            f"<p><b>Features:</b></p>"
            f"<ul>"
            f"<li>Stockpile screenshot scanning</li>"
            f"<li>Template database management</li>"
            f"<li>FastAPI server for remote scanning</li>"
            f"</ul>"
            f"<p><b>Links:</b></p>"
            f"<p><a href='https://github.com/xurxogr/foxhole-stockpiles'>GitHub Repository</a></p>"
            f"<p><a href='https://github.com/xurxogr/foxhole-stockpiles-client'>"
            f"FS Client (Complementary Tool)</a></p>"
            f"<hr>"
            f"<p>Copyright © 2024 Xurxogr</p>"
            f"<p>Licensed under the MIT License</p>",
        )

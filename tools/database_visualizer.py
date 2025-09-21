#!/usr/bin/env python3
"""Visual template database browser with filtering and zoom capabilities."""

import argparse
import pickle
import sys
from pathlib import Path

import cv2
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.icon_template import IconTemplate
from foxhole_stockpiles.services.template_database import TemplateDatabase


class DatabaseLoader(QThread):
    """Thread for loading all databases in background."""

    finished = pyqtSignal(object)  # all_databases_dict
    error = pyqtSignal(str)

    def __init__(self, database_path: Path) -> None:
        """Initialize the database loader.

        Args:
            database_path: Path to the database file to load.
        """
        super().__init__()
        self.database_path = database_path

    def run(self) -> None:
        """Load all databases in background thread.

        Emits:
            finished: Signal with loaded databases on success.
            error: Signal with error message on failure.
        """
        try:
            with open(self.database_path, "rb") as f:
                all_databases = pickle.load(f)

            self.finished.emit(all_databases)

        except Exception as e:
            self.error.emit(str(e))


class TemplateBrowser(QMainWindow):
    """Main window for browsing template database."""

    def __init__(self, database_path: Path) -> None:
        """Initialize the template browser.

        Args:
            database_path: Path to the database file to load.
        """
        super().__init__()
        self.database_path = database_path
        self.all_databases: dict[SupportedResolution, TemplateDatabase] = {}
        self.current_resolution: SupportedResolution | None = None
        self.database: TemplateDatabase | None = None
        self.filtered_templates: list[tuple[int, IconTemplate]] = []
        self.all_templates: list[tuple[int, IconTemplate]] = []
        self.loader_thread: DatabaseLoader | None = None

        self.init_ui()
        self.load_databases()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Template Database Browser")
        self.setGeometry(100, 100, 1400, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel - filters and list
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # Right panel - image display
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # Set initial splitter proportions (30% left, 70% right)
        splitter.setSizes([400, 1000])

    def create_left_panel(self) -> QWidget:
        """Create the left panel with filters and template list."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Filters section
        filters_group = QGroupBox("Filters")
        filters_layout = QGridLayout(filters_group)

        # Resolution filter
        filters_layout.addWidget(QLabel("Resolution:"), 0, 0)
        self.resolution_filter = QComboBox()
        self.resolution_filter.addItem("Loading...", None)
        self.resolution_filter.currentTextChanged.connect(self.on_resolution_changed)
        filters_layout.addWidget(self.resolution_filter, 0, 1)

        # Code filter
        filters_layout.addWidget(QLabel("Code:"), 1, 0)
        self.code_filter = QLineEdit()
        self.code_filter.setPlaceholderText("Enter item code...")
        self.code_filter.textChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.code_filter, 1, 1)

        # Faction filter
        filters_layout.addWidget(QLabel("Faction:"), 2, 0)
        self.faction_filter = QComboBox()
        self.faction_filter.addItem("All", None)
        for faction in ItemFaction:
            self.faction_filter.addItem(faction.value, faction)
        self.faction_filter.currentTextChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.faction_filter, 2, 1)

        # Category filter
        filters_layout.addWidget(QLabel("Category:"), 3, 0)
        self.category_filter = QComboBox()
        self.category_filter.addItem("All", None)
        for category in ItemCategory:
            self.category_filter.addItem(category.value, category)
        self.category_filter.currentTextChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.category_filter, 3, 1)

        # Mod filter
        filters_layout.addWidget(QLabel("Mod:"), 4, 0)
        self.mod_filter = QComboBox()
        self.mod_filter.addItem("All", "")
        self.mod_filter.currentTextChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.mod_filter, 4, 1)

        # Crated filter
        filters_layout.addWidget(QLabel("Crated:"), 5, 0)
        crated_layout = QHBoxLayout()
        self.crated_all = QCheckBox("All")
        self.crated_normal = QCheckBox("Normal")
        self.crated_crated = QCheckBox("Crated")
        self.crated_all.setChecked(True)
        self.crated_all.toggled.connect(self.on_crated_all_toggled)
        self.crated_normal.toggled.connect(self.apply_filters)
        self.crated_crated.toggled.connect(self.apply_filters)
        crated_layout.addWidget(self.crated_all)
        crated_layout.addWidget(self.crated_normal)
        crated_layout.addWidget(self.crated_crated)
        filters_layout.addLayout(crated_layout, 5, 1)

        # Clear filters button
        clear_button = QPushButton("Clear Filters")
        clear_button.clicked.connect(self.clear_filters)
        filters_layout.addWidget(clear_button, 6, 0, 1, 2)

        layout.addWidget(filters_group)

        # Loading progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results count
        self.results_label = QLabel("Loading...")
        layout.addWidget(self.results_label)

        # Template list
        self.template_list = QListWidget()
        self.template_list.itemClicked.connect(self.on_template_selected)
        layout.addWidget(self.template_list)

        return panel

    def create_right_panel(self) -> QWidget:
        """Create the right panel for image display."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Template info
        self.info_label = QLabel("Select a template to view details")
        self.info_label.setFont(QFont("Arial", 10))
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet(
            "QLabel { background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc; }"
        )
        layout.addWidget(self.info_label)

        # Image comparison area
        image_group = QGroupBox("Template Comparison (Size Matched)")
        image_layout = QHBoxLayout(image_group)

        # Current resolution image
        self.current_group = QGroupBox("Current Resolution")
        current_layout = QVBoxLayout(self.current_group)
        current_scroll = QScrollArea()
        self.current_image = QLabel("No image selected")
        self.current_image.setAlignment(Qt.AlignCenter)
        self.current_image.setMinimumHeight(200)
        self.current_image.setStyleSheet(
            "QLabel { border: 1px solid #ccc; background-color: white; }"
        )
        current_scroll.setWidget(self.current_image)
        current_scroll.setWidgetResizable(True)
        current_layout.addWidget(current_scroll)
        image_layout.addWidget(self.current_group)

        # Highest resolution image
        self.highest_group = QGroupBox("Highest Resolution")
        highest_layout = QVBoxLayout(self.highest_group)
        highest_scroll = QScrollArea()
        self.highest_image = QLabel("No image selected")
        self.highest_image.setAlignment(Qt.AlignCenter)
        self.highest_image.setMinimumHeight(200)
        self.highest_image.setStyleSheet(
            "QLabel { border: 1px solid #ccc; background-color: white; }"
        )
        highest_scroll.setWidget(self.highest_image)
        highest_scroll.setWidgetResizable(True)
        highest_layout.addWidget(highest_scroll)
        image_layout.addWidget(self.highest_group)

        layout.addWidget(image_group)

        return panel

    def on_crated_all_toggled(self, checked: bool) -> None:
        """Handle 'All' crated checkbox toggle."""
        if checked:
            self.crated_normal.setChecked(False)
            self.crated_crated.setChecked(False)
        self.apply_filters()

    def clear_filters(self) -> None:
        """Clear all filters."""
        self.code_filter.clear()
        self.faction_filter.setCurrentIndex(0)
        self.category_filter.setCurrentIndex(0)
        self.mod_filter.setCurrentIndex(0)
        self.crated_all.setChecked(True)
        self.crated_normal.setChecked(False)
        self.crated_crated.setChecked(False)

    def on_resolution_changed(self) -> None:
        """Handle resolution change."""
        resolution = self.resolution_filter.currentData()
        if resolution and resolution in self.all_databases:
            self.current_resolution = resolution
            self.database = self.all_databases[resolution]
            self.all_templates = list(enumerate(self.database.templates))

            # Update window title
            self.setWindowTitle(f"Template Database Browser - {resolution.value}p")

            # Populate mod filter with available mods for this resolution
            mods = sorted(set(t.mod for _, t in self.all_templates))
            current_mod = self.mod_filter.currentData()
            self.mod_filter.clear()
            self.mod_filter.addItem("All", "")
            for mod in mods:
                self.mod_filter.addItem(mod, mod)

            # Restore mod selection if it exists in new resolution
            if current_mod:
                index = self.mod_filter.findData(current_mod)
                if index >= 0:
                    self.mod_filter.setCurrentIndex(index)

            # Apply filters with new data
            self.apply_filters()

    def load_databases(self) -> None:
        """Load all template databases in background thread."""
        self.results_label.setText("Loading all databases...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        # Create and start loader thread
        self.loader_thread = DatabaseLoader(self.database_path)
        self.loader_thread.finished.connect(self.on_databases_loaded)
        self.loader_thread.error.connect(self.on_database_error)
        self.loader_thread.start()

    def on_databases_loaded(
        self, all_databases: dict[SupportedResolution, TemplateDatabase]
    ) -> None:
        """Handle successful database loading."""
        self.all_databases = all_databases

        # Populate resolution filter
        self.resolution_filter.clear()
        available_resolutions = sorted(all_databases.keys(), key=lambda x: int(x.value))

        for resolution in available_resolutions:
            self.resolution_filter.addItem(f"{resolution.value}p", resolution)

        # Select first resolution by default
        if available_resolutions:
            self.resolution_filter.setCurrentIndex(0)
            # This will trigger on_resolution_changed

        # Hide progress
        self.progress_bar.setVisible(False)

    def on_database_error(self, error_msg: str) -> None:
        """Handle database loading error."""
        self.progress_bar.setVisible(False)
        self.results_label.setText(f"Error loading database: {error_msg}")

    def apply_filters(self) -> None:
        """Apply current filters and update the template list."""
        if not self.database:
            return

        # Get filter values
        code_text = self.code_filter.text().lower()
        faction = self.faction_filter.currentData()
        category = self.category_filter.currentData()
        mod = self.mod_filter.currentData()

        # Crated filter logic
        show_all_crated = self.crated_all.isChecked()
        show_normal = self.crated_normal.isChecked()
        show_crated = self.crated_crated.isChecked()

        # Filter templates
        filtered: list[tuple[int, IconTemplate]] = []
        for idx, template in self.all_templates:
            # Code filter
            if code_text and code_text not in template.code.lower():
                continue

            # Faction filter
            if faction and template.faction != faction:
                continue

            # Category filter
            if category and template.category != category:
                continue

            # Mod filter
            if mod and template.mod != mod:
                continue

            # Crated filter
            if not show_all_crated:
                if template.crated and not show_crated:
                    continue
                if not template.crated and not show_normal:
                    continue

            filtered.append((idx, template))

        self.filtered_templates = filtered
        self.update_template_list()

    def update_template_list(self) -> None:
        """Update the template list widget."""
        self.template_list.clear()

        for idx, template in self.filtered_templates:
            crated_str = " (crated)" if template.crated else ""
            item_text = f"{template.code}{crated_str} | {template.faction.value} | {template.mod}"

            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, (idx, template))
            self.template_list.addItem(item)

        # Update results count
        total = len(self.all_templates)
        filtered = len(self.filtered_templates)
        self.results_label.setText(f"Showing {filtered} of {total} templates")

    def on_template_selected(self, item: QListWidgetItem) -> None:
        """Handle template selection."""
        idx, template = item.data(Qt.UserRole)

        # Find highest resolution available
        highest_resolution = max(self.all_databases.keys(), key=lambda x: int(x.value))

        # Find the same template in highest resolution
        highest_template = None
        if highest_resolution in self.all_databases:
            highest_db = self.all_databases[highest_resolution]
            for high_template in highest_db.templates:
                if (
                    high_template.code == template.code
                    and high_template.faction == template.faction
                    and high_template.mod == template.mod
                    and high_template.crated == template.crated
                    and high_template.category == template.category
                ):
                    highest_template = high_template
                    break

        # Update info label
        highest_info = ""
        if highest_template:
            highest_info = (
                f"<br><b>Highest Res Available:</b> {highest_template.resolution.value}px "
                f"(shape: {highest_template.image.shape})"
            )
        else:
            highest_info = f"<br><b>Highest Res:</b> Not found in {highest_resolution.value}px"

        info_text = (
            f"<b>Code:</b> {template.code}<br>"
            f"<b>Faction:</b> {template.faction.value}<br>"
            f"<b>Category:</b> {template.category.value}<br>"
            f"<b>Mod:</b> {template.mod}<br>"
            f"<b>Crated:</b> {template.crated}<br>"
            f"<b>Current Resolution:</b> {template.resolution.value}px<br>"
            f"<b>Current Shape:</b> {template.image.shape}<br>"
            f"<b>Database Index:</b> {idx}"
            f"{highest_info}"
        )
        self.info_label.setText(info_text)

        # Display comparison images
        self.display_comparison_images(template, highest_template)

    def display_comparison_images(
        self, current_template: IconTemplate | None, highest_template: IconTemplate | None
    ) -> None:
        """Display current and highest resolution templates at matching sizes."""
        if not current_template:
            return

        # Get dimensions
        current_rgb = cv2.cvtColor(current_template.image, cv2.COLOR_BGR2RGB)
        current_h, current_w, current_ch = current_rgb.shape

        # Display current resolution image (scaled to match target size)
        current_bytes_per_line = current_ch * current_w
        current_qt_image = QImage(
            current_rgb.data.tobytes(),
            current_w,
            current_h,
            current_bytes_per_line,
            QImage.Format_RGB888,
        )
        current_pixmap = QPixmap.fromImage(current_qt_image)

        # Calculate target size and scale based on highest resolution
        if highest_template:
            highest_rgb = cv2.cvtColor(highest_template.image, cv2.COLOR_BGR2RGB)
            highest_h, highest_w, highest_ch = highest_rgb.shape

            # Target size: highest resolution at 4x scale
            target_width = highest_w * 4
            target_height = highest_h * 4

            # Calculate scale factor for current resolution to match target size
            current_scale_x = target_width / current_w
            current_scale_y = target_height / current_h
            current_scale = min(current_scale_x, current_scale_y)  # Keep aspect ratio

            # Scale and display current image
            current_scaled = current_pixmap.scaled(
                int(current_w * current_scale),
                int(current_h * current_scale),
                Qt.KeepAspectRatio,
                Qt.FastTransformation,
            )

            # Display highest resolution image (4x)
            highest_bytes_per_line = highest_ch * highest_w
            highest_qt_image = QImage(
                highest_rgb.data.tobytes(),
                highest_w,
                highest_h,
                highest_bytes_per_line,
                QImage.Format_RGB888,
            )
            highest_pixmap = QPixmap.fromImage(highest_qt_image)

            # Scale highest to 4x
            highest_scaled = highest_pixmap.scaled(
                target_width, target_height, Qt.KeepAspectRatio, Qt.FastTransformation
            )

            self.highest_image.setPixmap(highest_scaled)
            self.highest_image.resize(highest_scaled.size())

            # Update group box title with highest resolution
            self.highest_group.setTitle(
                f"Highest Resolution ({highest_template.resolution.value}p - 4x)"
            )
        else:
            # Fallback: use 8x for current if no highest template
            current_scale = 8.0

            current_scaled = current_pixmap.scaled(
                int(current_w * current_scale),
                int(current_h * current_scale),
                Qt.KeepAspectRatio,
                Qt.FastTransformation,
            )

            # No highest resolution template found
            self.highest_image.setText("Template not found\nin highest resolution")
            self.highest_group.setTitle("Highest Resolution (Not Found)")

        self.current_image.setPixmap(current_scaled)
        self.current_image.resize(current_scaled.size())

        # Update group box title with current resolution and scale
        self.current_group.setTitle(
            f"Current Resolution ({current_template.resolution.value}p - {current_scale:.1f}x)"
        )


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Visual template database browser")
    parser.add_argument("--database", type=Path, required=True, help="Path to database file")

    args = parser.parse_args()

    # Check if database exists
    if not args.database.exists():
        print(f"Database file not found: {args.database}")
        sys.exit(1)

    # Create Qt application
    app = QApplication(sys.argv)

    # Create and show main window
    browser = TemplateBrowser(args.database)
    browser.show()

    # Run event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

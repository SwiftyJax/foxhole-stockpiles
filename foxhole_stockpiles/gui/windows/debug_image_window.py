"""Debug image viewer window for analyzing screenshot scanning results."""

import asyncio
import logging
from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.gui.utils.image_scan_worker import ImageScanWorker
from foxhole_stockpiles.i18n import off_language_changed, on_language_changed, t
from foxhole_stockpiles.models.detected_icon_info import DetectedIconInfo
from foxhole_stockpiles.models.scan_result import ScanResult
from foxhole_stockpiles.services.template_database import TemplateDatabase
from foxhole_stockpiles.services.template_manager import TemplateManager

logger = logging.getLogger(__name__)


class DatabaseLoader(QThread):
    """Thread for loading all databases in background."""

    finished = pyqtSignal(object)  # all_databases_dict
    error = pyqtSignal(str)

    def __init__(self, database_path: str) -> None:
        """Initialize the database loader.

        Args:
            database_path (str): Path to the database file to load.
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
            db_path = Path(self.database_path)
            manager = TemplateManager(database_path=db_path)
            all_databases = asyncio.run(manager.load_all_resolutions())
            self.finished.emit(all_databases)
        except Exception as e:
            logger.exception("Failed to load databases")
            self.error.emit(str(e))


class DebugImageWindow(QDialog):
    """Debug window for analyzing screenshot scanning results.

    Allows users to:
    1. Load a screenshot
    2. Run the scanning pipeline
    3. View detected items in a clickable list
    4. Click an item to highlight it in the screenshot and compare with templates
    """

    def __init__(self, parent: QWidget | None = None, database_path: str | None = None) -> None:
        """Initialize the debug image window.

        Args:
            parent (QWidget | None): Parent widget.
            database_path (str | None): Path to the database file to load.
        """
        super().__init__(parent)
        self.database_path = database_path
        self.all_databases: dict[SupportedResolution, TemplateDatabase] = {}
        self.scan_result: ScanResult | None = None
        self.selected_icon: DetectedIconInfo | None = None

        self.loader_thread: DatabaseLoader | None = None
        self.scan_worker: ImageScanWorker | None = None

        self.init_ui()

        if database_path:
            self.load_databases()

        # Connect to language change signal with cleanup
        self._language_callback = self._on_language_changed
        on_language_changed(self._language_callback)
        self.destroyed.connect(lambda: off_language_changed(self._language_callback))

    def _on_language_changed(self, _language: str) -> None:
        """Handle language change event."""
        self.retranslate()

    def retranslate(self) -> None:
        """Update all translatable strings."""
        self.setWindowTitle(t("debug_viewer.title"))
        self.browse_button.setText(t("common.browse"))
        self.items_group.setTitle(t("debug_viewer.detected_items"))
        self.screenshot_group.setTitle(t("debug_viewer.screenshot"))
        self.comparison_group.setTitle(t("debug_viewer.icon_comparison"))

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setMinimumSize(1400, 800)
        self.resize(1600, 900)

        main_layout = QVBoxLayout(self)

        # Top bar: Browse button and path (single line height)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        self.browse_button = QPushButton()
        self.browse_button.clicked.connect(self._on_browse_screenshot)
        top_bar.addWidget(self.browse_button)

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        top_bar.addWidget(self.path_edit, stretch=1)

        main_layout.addLayout(top_bar)

        # Main content: list on left (fixed width), screenshot and comparison on right
        content_layout = QHBoxLayout()

        # Left panel: Detected items list (fixed width)
        left_panel = self._create_left_panel()
        content_layout.addWidget(left_panel)

        # Right panel: Screenshot display and comparison (expandable)
        right_panel = self._create_right_panel()
        content_layout.addWidget(right_panel, stretch=1)

        main_layout.addLayout(content_layout)

        # Apply translations
        self.retranslate()

    def _create_left_panel(self) -> QWidget:
        """Create the left panel with detected items list.

        Returns:
            QWidget: The left panel widget.
        """
        panel = QWidget()
        panel.setFixedWidth(350)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.items_group = QGroupBox()
        items_layout = QVBoxLayout(self.items_group)

        self.items_list = QListWidget()
        self.items_list.currentItemChanged.connect(self._on_item_changed)
        items_layout.addWidget(self.items_list)

        layout.addWidget(self.items_group)
        return panel

    def _create_right_panel(self) -> QWidget:
        """Create the right panel with screenshot and comparison displays.

        Returns:
            QWidget: The right panel widget.
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Screenshot display (expandable)
        self.screenshot_group = QGroupBox()
        screenshot_layout = QVBoxLayout(self.screenshot_group)

        screenshot_scroll = QScrollArea()
        screenshot_scroll.setWidgetResizable(True)
        self.screenshot_label = QLabel()
        self.screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screenshot_label.setStyleSheet("QLabel { background-color: palette(base); }")
        screenshot_scroll.setWidget(self.screenshot_label)
        screenshot_layout.addWidget(screenshot_scroll)

        layout.addWidget(self.screenshot_group, stretch=1)

        # Icon comparison panel (fixed height)
        self.comparison_group = QGroupBox()
        self.comparison_group.setFixedHeight(400)
        comparison_layout = QVBoxLayout(self.comparison_group)

        comparison_scroll = QScrollArea()
        comparison_scroll.setWidgetResizable(True)
        self.comparison_widget = QWidget()
        self.comparison_layout = QHBoxLayout(self.comparison_widget)
        self.comparison_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        comparison_scroll.setWidget(self.comparison_widget)
        comparison_layout.addWidget(comparison_scroll)

        layout.addWidget(self.comparison_group)

        return panel

    def _on_browse_screenshot(self) -> None:
        """Handle browse screenshot button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("debug_viewer.select_screenshot"),
            "",
            t("server_panel.image_filter"),
        )
        if file_path:
            self.path_edit.setText(file_path)
            self._scan_screenshot(file_path)

    def _scan_screenshot(self, file_path: str) -> None:
        """Start scanning the screenshot.

        Args:
            file_path (str): Path to the screenshot file.
        """
        if not self.database_path:
            QMessageBox.warning(
                self,
                t("main_window.dialogs.no_database_title"),
                t("main_window.dialogs.no_database_message"),
            )
            return

        # Clear previous results
        self.items_list.clear()
        self.screenshot_label.clear()
        self._clear_comparison()
        self.scan_result = None
        self.selected_icon = None

        # Start scan worker
        self.scan_worker = ImageScanWorker(file_path, Path(self.database_path))
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.error.connect(self._on_scan_error)
        self.scan_worker.start()

    def _on_scan_finished(self, result: ScanResult) -> None:
        """Handle successful scan completion.

        Args:
            result (ScanResult): The scan result containing stockpile and icons.
        """
        self.scan_result = result

        # Populate items list
        for icon_info in result.detected_icons:
            crated_str = " [Crated]" if icon_info.crated else ""
            item_text = (
                f"{icon_info.index:03d}: {icon_info.code}{crated_str} "
                f"x{icon_info.quantity} ({icon_info.confidence:.1%})"
            )
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, icon_info)
            self.items_list.addItem(item)

        # Display screenshot
        self._display_screenshot(result.original_image)

        # Auto-select first item
        if self.items_list.count() > 0:
            self.items_list.setCurrentRow(0)
            self.items_list.setFocus()

    def _on_scan_error(self, error_msg: str) -> None:
        """Handle scan error.

        Args:
            error_msg (str): Error message.
        """
        logger.error("Scan failed: %s", error_msg)
        QMessageBox.warning(
            self,
            t("debug_viewer.scan_error_title"),
            error_msg,
        )

    def _display_screenshot(
        self, image: np.ndarray, highlight_icon: DetectedIconInfo | None = None
    ) -> None:
        """Display the screenshot with optional icon highlight.

        Args:
            image (np.ndarray): Image to display (BGR format).
            highlight_icon (DetectedIconInfo | None): Icon to highlight with green box.
        """
        display_image = image.copy()

        # Draw green rectangle around highlighted icon
        if highlight_icon:
            x, y = highlight_icon.position
            size = highlight_icon.size
            cv2.rectangle(
                display_image,
                (x, y),
                (x + size, y + size),
                (0, 255, 0),
                3,
            )

        # Convert BGR to RGB for Qt
        rgb_image = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w

        qt_image = QImage(
            rgb_image.data.tobytes(),
            w,
            h,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        )

        # Scale to fit while maintaining aspect ratio
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            self.screenshot_label.width() - 20,
            self.screenshot_label.height() - 20,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.screenshot_label.setPixmap(scaled_pixmap)

    def _on_item_changed(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        """Handle item selection change in the list (click or keyboard).

        Args:
            current (QListWidgetItem | None): The newly selected item.
            _previous (QListWidgetItem | None): The previously selected item.
        """
        if current is None:
            return

        icon_info: DetectedIconInfo = current.data(Qt.ItemDataRole.UserRole)
        self.selected_icon = icon_info

        # Highlight icon in screenshot
        if self.scan_result:
            self._display_screenshot(self.scan_result.original_image, icon_info)

        # Update comparison panel
        self._update_comparison(icon_info)

    def _update_comparison(self, icon_info: DetectedIconInfo) -> None:
        """Update the comparison panel with detected icon and templates from database.

        Shows: Detected icon | Screenshot resolution templates | Highest resolution templates

        Args:
            icon_info (DetectedIconInfo): The selected icon information.
        """
        self._clear_comparison()

        if not self.all_databases or not self.scan_result:
            return

        # Get resolutions
        screenshot_res = self._get_screenshot_resolution()
        highest_res = max(self.all_databases.keys(), key=lambda x: int(x.value))
        highest_db = self.all_databases[highest_res]
        target_size = highest_db.templates[0].image.shape[0] if highest_db.templates else 64

        # Display detected icon (scaled to match DB template size)
        detected_widget = self._create_icon_display(
            image=icon_info.icon_image,
            label=t("debug_viewer.detected"),
            sublabel=t("debug_viewer.scaled"),
            ncc_score=None,
            target_size=target_size,
        )
        self.comparison_layout.addWidget(detected_widget)

        # Add separator
        self._add_separator()

        # Display templates at screenshot resolution (scaled up)
        if screenshot_res and screenshot_res in self.all_databases:
            screenshot_db = self.all_databases[screenshot_res]
            for template in screenshot_db.templates:
                if template.code == icon_info.code and template.crated == icon_info.crated:
                    # Scale detected icon to template size for NCC calculation
                    detected_scaled = cv2.resize(
                        icon_info.icon_image,
                        (template.image.shape[1], template.image.shape[0]),
                        interpolation=cv2.INTER_AREA,
                    )

                    ncc_score = self._calculate_ncc(detected_scaled, template.image)

                    template_widget = self._create_icon_display(
                        image=template.image,
                        label=template.mod,
                        sublabel=f"({screenshot_res.value}p)",
                        ncc_score=ncc_score,
                        target_size=target_size,
                    )
                    self.comparison_layout.addWidget(template_widget)

            # Add separator before highest resolution
            self._add_separator()

        # Display templates at highest resolution
        for template in highest_db.templates:
            if template.code == icon_info.code and template.crated == icon_info.crated:
                # Scale detected icon to template size for NCC calculation
                detected_scaled = cv2.resize(
                    icon_info.icon_image,
                    (template.image.shape[1], template.image.shape[0]),
                    interpolation=cv2.INTER_AREA,
                )

                ncc_score = self._calculate_ncc(detected_scaled, template.image)

                template_widget = self._create_icon_display(
                    image=template.image,
                    label=template.mod,
                    sublabel=f"({highest_res.value}p)",
                    ncc_score=ncc_score,
                    target_size=template.image.shape[0],
                )
                self.comparison_layout.addWidget(template_widget)

        self.comparison_layout.addStretch()

    def _get_screenshot_resolution(self) -> SupportedResolution | None:
        """Get the SupportedResolution matching the screenshot.

        Returns:
            SupportedResolution | None: Matching resolution or None if not found.
        """
        if not self.scan_result or not self.scan_result.stockpile.resolution:
            return None

        # Resolution is like "1920x1080", extract height
        try:
            height_str = self.scan_result.stockpile.resolution.split("x")[1]
            height = int(height_str)

            # Find matching SupportedResolution
            for res in SupportedResolution:
                if int(res.value) == height:
                    return res
        except (IndexError, ValueError):
            pass

        return None

    def _add_separator(self) -> None:
        """Add a vertical separator to the comparison layout."""
        separator = QWidget()
        separator.setFixedWidth(2)
        separator.setStyleSheet("background-color: palette(mid);")
        self.comparison_layout.addWidget(separator)

    def _create_icon_display(
        self,
        image: np.ndarray,
        label: str,
        sublabel: str | None,
        ncc_score: float | None,
        target_size: int,
    ) -> QWidget:
        """Create a widget displaying an icon with label and optional NCC score.

        Args:
            image (np.ndarray): Image to display (BGR format).
            label (str): Label text (e.g., mod name or "Detected").
            sublabel (str | None): Second line label text (e.g., "(scaled)").
            ncc_score (float | None): NCC score to display, or None for detected icon.
            target_size (int): Target size for scaling.

        Returns:
            QWidget: Widget containing the icon display.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Scale image to 4x for visibility
        scale = 4
        scaled_size = target_size * scale

        # Resize image if needed to match target size first
        if image.shape[0] != target_size or image.shape[1] != target_size:
            image = cv2.resize(
                image,
                (target_size, target_size),
                interpolation=cv2.INTER_AREA,
            )

        # Scale up for display
        display_image = cv2.resize(
            image,
            (scaled_size, scaled_size),
            interpolation=cv2.INTER_NEAREST,
        )

        # Convert BGR to RGB for Qt
        rgb_image = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w

        qt_image = QImage(
            rgb_image.data.tobytes(),
            w,
            h,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        )
        pixmap = QPixmap.fromImage(qt_image)

        # Icon image
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setStyleSheet("QLabel { border: 1px solid palette(mid); }")
        layout.addWidget(image_label)

        # Label text
        text_label = QLabel(label)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(text_label)

        # Sublabel (if provided)
        if sublabel:
            sublabel_widget = QLabel(sublabel)
            sublabel_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sublabel_widget.setStyleSheet("QLabel { color: palette(mid); }")
            layout.addWidget(sublabel_widget)

        # NCC score (if provided)
        if ncc_score is not None:
            score_label = QLabel(f"NCC: {ncc_score:.3f}")
            score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Color based on score
            if ncc_score >= 0.95:
                color = "#4caf50"  # Green
            elif ncc_score >= 0.90:
                color = "#ff9800"  # Orange
            else:
                color = "#f44336"  # Red
            score_label.setStyleSheet(f"QLabel {{ color: {color}; }}")
            layout.addWidget(score_label)

        return widget

    def _calculate_ncc(self, image1: np.ndarray, image2: np.ndarray) -> float:
        """Calculate Normalized Cross-Correlation between two images.

        Args:
            image1 (np.ndarray): First image (BGR format).
            image2 (np.ndarray): Second image (BGR format).

        Returns:
            float: NCC score between 0 and 1.
        """
        # Convert to grayscale
        gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY).astype(np.float32)
        gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY).astype(np.float32)

        # Normalize
        gray1 = (gray1 - gray1.mean()) / (gray1.std() + 1e-8)
        gray2 = (gray2 - gray2.mean()) / (gray2.std() + 1e-8)

        # Calculate NCC
        ncc = np.sum(gray1 * gray2) / gray1.size
        return float(max(0.0, min(1.0, ncc)))

    def _clear_comparison(self) -> None:
        """Clear the comparison panel."""
        while self.comparison_layout.count():
            child = self.comparison_layout.takeAt(0)
            if child is not None:
                widget = child.widget()
                if widget is not None:
                    widget.deleteLater()

    def load_databases(self) -> None:
        """Load all template databases in background thread."""
        if not self.database_path:
            return

        self.loader_thread = DatabaseLoader(self.database_path)
        self.loader_thread.finished.connect(self._on_databases_loaded)
        self.loader_thread.error.connect(self._on_database_error)
        self.loader_thread.start()

    def _on_databases_loaded(
        self, all_databases: dict[SupportedResolution, TemplateDatabase]
    ) -> None:
        """Handle successful database loading.

        Args:
            all_databases (dict): Dictionary of resolution to database mappings.
        """
        self.all_databases = all_databases

    def _on_database_error(self, error_msg: str) -> None:
        """Handle database loading error.

        Args:
            error_msg (str): Error message.
        """
        logger.error("Failed to load database: %s", error_msg)
        QMessageBox.warning(
            self,
            t("debug_viewer.database_error_title"),
            error_msg,
        )

    def closeEvent(self, event: object) -> None:
        """Handle window close event.

        Args:
            event (object): Close event.
        """
        # Wait for threads to finish if running
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.wait()
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.wait()

        if hasattr(event, "accept"):
            event.accept()

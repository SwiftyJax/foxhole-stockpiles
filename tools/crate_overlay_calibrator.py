#!/usr/bin/env python3
"""Interactive Crate Color Tuner.

Real-time adjustment with brightness threshold for separate dark/light area control.
Uses OpenCV for all image processing, PyQt6 for GUI interface.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QImage, QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ClickableLabel(QLabel):
    """QLabel subclass that emits click events."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the clickable label.

        Args:
            parent (QWidget | None): Parent widget.
        """
        super().__init__(parent)
        self.click_handler: Callable[[QMouseEvent], None] | None = None

    def set_click_handler(self, handler: Callable[[QMouseEvent], None]) -> None:
        """Set the click handler function.

        Args:
            handler (Callable[[QMouseEvent], None]): Click handler function.
        """
        self.click_handler = handler

    def mousePressEvent(self, ev: QMouseEvent | None) -> None:
        """Handle mouse press events."""
        if ev and self.click_handler:
            self.click_handler(ev)
        super().mousePressEvent(ev)


class CrateTunerQt(QMainWindow):
    """Interactive tool for tuning crate color transformations with threshold control."""

    # Crate overlay constants
    CRATE_RATIO = 7 / 16
    CRATE_ALPHA = 0.75

    def __init__(
        self, icon_size: int = 64, icon_path: str | None = None, crate_path: str | None = None
    ) -> None:
        """Initialize the tuner.

        Args:
            icon_size (int): Size of the icon for display
            icon_path (str | None): Path to icon image file (optional)
            crate_path (str | None): Path to crate image file (optional)
        """
        super().__init__()
        self.icon_size = icon_size
        self.original_icon: NDArray[np.uint8] | None = None
        self.crate_icon: NDArray[np.uint8] | None = None
        self.current_result: NDArray[np.uint8] | None = None

        # Color transformation variables
        self.red_mult = 240 / 255
        self.green_mult = 234 / 255
        self.blue_mult = 220 / 255
        self.red_offset = 0
        self.green_offset = 0
        self.blue_offset = 0
        self.alpha_mult = 0.75

        # Manual sample selection
        self.light_sample_pos: tuple[int, int] | None = None  # (x, y) in final image coordinates
        self.dark_sample_pos: tuple[int, int] | None = None  # (x, y) in final image coordinates
        self.selection_mode = "light"  # "light" or "dark"
        self.link_offsets = True

        self.init_ui()

        # Load images if provided
        if icon_path:
            self.load_icon_from_path(icon_path)
        if crate_path:
            self.load_crate_from_path(crate_path)

        # If both images are loaded, update preview
        if self.original_icon is not None and self.crate_icon is not None:
            self.update_preview()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Crate Color Tuner")
        self.setGeometry(100, 100, 1800, 1100)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Left side controls
        controls_widget = QWidget()
        controls_widget.setFixedWidth(700)
        controls_layout = QVBoxLayout(controls_widget)

        # File loading section
        self.create_file_section(controls_layout)

        # Color transformation controls
        self.create_color_section(controls_layout)

        # Global controls
        self.create_global_controls(controls_layout)

        # Color sampling section
        self.create_sampling_section(controls_layout)

        controls_layout.addStretch()

        # Right side preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        # Preview section
        preview_group = QGroupBox("Preview")
        preview_group_layout = QVBoxLayout(preview_group)

        self.preview_label = ClickableLabel()
        self.preview_label.setMinimumSize(1000, 1000)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background-color: white; border: 1px solid gray;")
        self.preview_label.set_click_handler(self.on_preview_click)

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.preview_label)
        scroll_area.setWidgetResizable(True)
        preview_group_layout.addWidget(scroll_area)

        preview_layout.addWidget(preview_group)

        # Add to main layout
        main_layout.addWidget(controls_widget)
        main_layout.addWidget(preview_widget)

    def create_file_section(self, parent_layout: QVBoxLayout) -> None:
        """Create file loading section."""
        file_group = QGroupBox("Load Images")
        file_layout = QGridLayout(file_group)

        load_icon_btn = QPushButton("Load Icon")
        load_icon_btn.clicked.connect(self.load_icon)
        file_layout.addWidget(load_icon_btn, 0, 0)

        load_crate_btn = QPushButton("Load Crate")
        load_crate_btn.clicked.connect(self.load_crate)
        file_layout.addWidget(load_crate_btn, 0, 1)

        self.status_label = QLabel("Load icon and crate images to begin")
        file_layout.addWidget(self.status_label, 1, 0, 1, 2)

        parent_layout.addWidget(file_group)

    def create_color_section(self, parent_layout: QVBoxLayout) -> None:
        """Create color transformation controls."""
        color_group = QGroupBox("Color Transformation")
        color_layout = QGridLayout(color_group)

        # Multipliers
        color_layout.addWidget(QLabel("Multipliers (input/255):"), 0, 0, 1, 4)

        # Red
        color_layout.addWidget(QLabel("Red:"), 1, 0)
        self.red_input = QSpinBox()
        self.red_input.setRange(0, 510)
        self.red_input.setValue(240)
        self.red_input.valueChanged.connect(self.on_input_change)
        color_layout.addWidget(self.red_input, 1, 1)

        self.red_slider = QSlider(Qt.Orientation.Horizontal)
        self.red_slider.setRange(0, 2000)
        self.red_slider.setValue(int(self.red_mult * 1000))
        self.red_slider.valueChanged.connect(self.on_slider_change)
        color_layout.addWidget(self.red_slider, 1, 2)

        self.red_mult_label = QLabel("0.941")
        color_layout.addWidget(self.red_mult_label, 1, 3)

        # Green
        color_layout.addWidget(QLabel("Green:"), 2, 0)
        self.green_input = QSpinBox()
        self.green_input.setRange(0, 510)
        self.green_input.setValue(234)
        self.green_input.valueChanged.connect(self.on_input_change)
        color_layout.addWidget(self.green_input, 2, 1)

        self.green_slider = QSlider(Qt.Orientation.Horizontal)
        self.green_slider.setRange(0, 2000)
        self.green_slider.setValue(int(self.green_mult * 1000))
        self.green_slider.valueChanged.connect(self.on_slider_change)
        color_layout.addWidget(self.green_slider, 2, 2)

        self.green_mult_label = QLabel("0.918")
        color_layout.addWidget(self.green_mult_label, 2, 3)

        # Blue
        color_layout.addWidget(QLabel("Blue:"), 3, 0)
        self.blue_input = QSpinBox()
        self.blue_input.setRange(0, 510)
        self.blue_input.setValue(220)
        self.blue_input.valueChanged.connect(self.on_input_change)
        color_layout.addWidget(self.blue_input, 3, 1)

        self.blue_slider = QSlider(Qt.Orientation.Horizontal)
        self.blue_slider.setRange(0, 2000)
        self.blue_slider.setValue(int(self.blue_mult * 1000))
        self.blue_slider.valueChanged.connect(self.on_slider_change)
        color_layout.addWidget(self.blue_slider, 3, 2)

        self.blue_mult_label = QLabel("0.863")
        color_layout.addWidget(self.blue_mult_label, 3, 3)

        # Offsets
        color_layout.addWidget(QLabel("Offsets:"), 4, 0, 1, 4)

        self.link_offsets_cb = QCheckBox("Link offsets together")
        self.link_offsets_cb.setChecked(True)
        color_layout.addWidget(self.link_offsets_cb, 5, 0, 1, 2)

        # Red offset
        color_layout.addWidget(QLabel("Red:"), 6, 0)
        self.red_offset_slider = QSlider(Qt.Orientation.Horizontal)
        self.red_offset_slider.setRange(0, 255)
        self.red_offset_slider.setValue(0)
        self.red_offset_slider.valueChanged.connect(lambda v: self.on_offset_change(v, "red"))
        color_layout.addWidget(self.red_offset_slider, 6, 1)
        self.red_offset_label = QLabel("0")
        color_layout.addWidget(self.red_offset_label, 6, 2)

        # Green offset
        color_layout.addWidget(QLabel("Green:"), 7, 0)
        self.green_offset_slider = QSlider(Qt.Orientation.Horizontal)
        self.green_offset_slider.setRange(0, 255)
        self.green_offset_slider.setValue(0)
        self.green_offset_slider.valueChanged.connect(lambda v: self.on_offset_change(v, "green"))
        color_layout.addWidget(self.green_offset_slider, 7, 1)
        self.green_offset_label = QLabel("0")
        color_layout.addWidget(self.green_offset_label, 7, 2)

        # Blue offset
        color_layout.addWidget(QLabel("Blue:"), 8, 0)
        self.blue_offset_slider = QSlider(Qt.Orientation.Horizontal)
        self.blue_offset_slider.setRange(0, 255)
        self.blue_offset_slider.setValue(0)
        self.blue_offset_slider.valueChanged.connect(lambda v: self.on_offset_change(v, "blue"))
        color_layout.addWidget(self.blue_offset_slider, 8, 1)
        self.blue_offset_label = QLabel("0")
        color_layout.addWidget(self.blue_offset_label, 8, 2)

        parent_layout.addWidget(color_group)

    def create_global_controls(self, parent_layout: QVBoxLayout) -> None:
        """Create global controls section."""
        global_group = QGroupBox("Global Controls")
        global_layout = QGridLayout(global_group)

        # Alpha control
        global_layout.addWidget(QLabel("Alpha:"), 0, 0)
        self.alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(0, 1000)
        self.alpha_slider.setValue(int(self.alpha_mult * 1000))
        self.alpha_slider.valueChanged.connect(self.on_alpha_change)
        global_layout.addWidget(self.alpha_slider, 0, 1)
        self.alpha_label = QLabel("0.75")
        global_layout.addWidget(self.alpha_label, 0, 2)

        # Preset buttons
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_values)
        global_layout.addWidget(reset_btn, 1, 0)

        auto_calc_btn = QPushButton("Auto Calculate")
        auto_calc_btn.clicked.connect(self.auto_calculate)
        global_layout.addWidget(auto_calc_btn, 1, 1)

        parent_layout.addWidget(global_group)

    def create_sampling_section(self, parent_layout: QVBoxLayout) -> None:
        """Create color sampling section."""
        sample_group = QGroupBox("Color Samples")
        sample_layout = QGridLayout(sample_group)

        # Selection mode
        sample_layout.addWidget(QLabel("Click mode:"), 0, 0)
        self.light_radio = QRadioButton("Light")
        self.light_radio.setChecked(True)
        self.light_radio.toggled.connect(
            lambda checked: self.set_selection_mode("light" if checked else "dark")
        )
        sample_layout.addWidget(self.light_radio, 0, 1)

        self.dark_radio = QRadioButton("Dark")
        self.dark_radio.toggled.connect(
            lambda checked: self.set_selection_mode("dark" if checked else "light")
        )
        sample_layout.addWidget(self.dark_radio, 0, 2)

        # Instructions
        instructions = QLabel("Click on preview image to select sample points")
        instructions.setFont(QFont("Default", 9, -1, True))
        sample_layout.addWidget(instructions, 1, 0, 1, 3)

        # Light area sample
        sample_layout.addWidget(QLabel("Light area sample:"), 2, 0, 1, 3)
        self.sample_rgb_label = QLabel("R: -, G: -, B: -")
        self.sample_rgb_label.setFont(QFont("Default", 10, QFont.Weight.Bold))
        sample_layout.addWidget(self.sample_rgb_label, 3, 0, 1, 3)
        self.light_pos_label = QLabel("Position: not selected")
        self.light_pos_label.setFont(QFont("Default", 8))
        sample_layout.addWidget(self.light_pos_label, 4, 0, 1, 3)

        target_light = QLabel("Target: R: 182, G: 179, B: 170")
        target_light.setStyleSheet("color: blue;")
        sample_layout.addWidget(target_light, 5, 0, 1, 3)

        # Dark area sample
        sample_layout.addWidget(QLabel("Dark area sample:"), 6, 0, 1, 3)
        self.sample_bars_label = QLabel("R: -, G: -, B: -")
        self.sample_bars_label.setFont(QFont("Default", 10, QFont.Weight.Bold))
        sample_layout.addWidget(self.sample_bars_label, 7, 0, 1, 3)
        self.dark_pos_label = QLabel("Position: not selected")
        self.dark_pos_label.setFont(QFont("Default", 8))
        sample_layout.addWidget(self.dark_pos_label, 8, 0, 1, 3)

        target_dark = QLabel("Target: R: 75, G: 73, B: 69")
        target_dark.setStyleSheet("color: blue;")
        sample_layout.addWidget(target_dark, 9, 0, 1, 3)

        parent_layout.addWidget(sample_group)

    def set_selection_mode(self, mode: str) -> None:
        """Set the selection mode for sample points."""
        self.selection_mode = mode

    def load_icon_from_path(self, filename: str) -> bool:
        """Load the base icon image from a file path."""
        try:
            img = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError("Could not load image")

            # Convert color space based on number of channels
            if len(img.shape) == 3:
                if img.shape[2] == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
                elif img.shape[2] == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
            else:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGBA)

            # Ensure img is uint8 after color conversion
            self.original_icon = img.astype(np.uint8)
            self.status_label.setText(f"Icon loaded: {Path(filename).name}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load icon from {filename}: {e}")
            return False

    def load_crate_from_path(self, filename: str) -> bool:
        """Load the crate overlay image from a file path."""
        try:
            img = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError("Could not load image")

            # Convert color space based on number of channels
            if len(img.shape) == 3:
                if img.shape[2] == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
                elif img.shape[2] == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
            else:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGBA)

            # Ensure img is uint8 after color conversion
            self.crate_icon = img.astype(np.uint8)
            current_status = self.status_label.text()
            if "Icon loaded:" in current_status:
                self.status_label.setText(f"{current_status} | Crate loaded: {Path(filename).name}")
            else:
                self.status_label.setText(f"Crate loaded: {Path(filename).name}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load crate from {filename}: {e}")
            return False

    def load_icon(self) -> None:
        """Load the base icon image."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Icon Image", "", "Image files (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        if filename:
            if self.load_icon_from_path(filename):
                self.update_preview()

    def load_crate(self) -> None:
        """Load the crate overlay image."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Crate Image", "", "Image files (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        if filename:
            if self.load_crate_from_path(filename):
                self.update_preview()

    def on_preview_click(self, ev: QMouseEvent) -> None:
        """Handle clicks on the preview to select sample points."""
        if self.current_result is None:
            return

        # Get click position
        click_x = int(ev.position().x())
        click_y = int(ev.position().y())

        # Get label dimensions
        label_width = self.preview_label.width()
        label_height = self.preview_label.height()

        display_scale = 16
        display_size = self.icon_size * display_scale

        # Calculate image position (centered)
        img_x = max(0, (label_width - display_size) // 2)
        img_y = max(0, (label_height - display_size) // 2)

        # Convert click coordinates to image coordinates
        relative_x = click_x - img_x
        relative_y = click_y - img_y

        # Check if click is within the image
        if 0 <= relative_x < display_size and 0 <= relative_y < display_size:
            # Convert from display coordinates to actual image coordinates
            actual_x = int(relative_x / display_scale)
            actual_y = int(relative_y / display_scale)

            # Make sure coordinates are within bounds
            if 0 <= actual_x < self.icon_size and 0 <= actual_y < self.icon_size:
                # Store the sample position based on selection mode
                if self.selection_mode == "light":
                    self.light_sample_pos = (actual_x, actual_y)
                else:  # dark
                    self.dark_sample_pos = (actual_x, actual_y)

                # Update the sample display
                self.update_manual_samples()
                self.update_preview()  # Redraw with markers

    def update_manual_samples(self) -> None:
        """Update the RGB sample displays using manually selected points."""
        if self.current_result is None:
            return

        try:
            # Update light sample
            if self.light_sample_pos:
                x, y = self.light_sample_pos
                if 0 <= x < self.icon_size and 0 <= y < self.icon_size:
                    r, g, b, a = self.current_result[y, x]
                    self.sample_rgb_label.setText(f"R: {r}, G: {g}, B: {b}")
                    self.light_pos_label.setText(f"Position: ({x}, {y})")
                else:
                    self.sample_rgb_label.setText("R: -, G: -, B: -")
                    self.light_pos_label.setText("Position: out of bounds")
            else:
                self.sample_rgb_label.setText("R: -, G: -, B: -")
                self.light_pos_label.setText("Position: not selected")

            # Update dark sample
            if self.dark_sample_pos:
                x, y = self.dark_sample_pos
                if 0 <= x < self.icon_size and 0 <= y < self.icon_size:
                    r, g, b, a = self.current_result[y, x]
                    self.sample_bars_label.setText(f"R: {r}, G: {g}, B: {b}")
                    self.dark_pos_label.setText(f"Position: ({x}, {y})")
                else:
                    self.sample_bars_label.setText("R: -, G: -, B: -")
                    self.dark_pos_label.setText("Position: out of bounds")
            else:
                self.sample_bars_label.setText("R: -, G: -, B: -")
                self.dark_pos_label.setText("Position: not selected")

        except Exception as e:
            print(f"Error in update_manual_samples: {e}")

    def _block_signals(self, widgets: Sequence[QWidget], block: bool) -> None:
        """Block or unblock signals for multiple widgets.

        Args:
            widgets (Sequence[QWidget]): Sequence of QWidgets to block/unblock
            block (bool): True to block signals, False to unblock
        """
        for widget in widgets:
            widget.blockSignals(block)

    def _get_resized_crate_and_position(
        self,
    ) -> tuple[NDArray[np.uint8], int, int, int, int] | None:
        """Get resized crate and its position coordinates.

        Returns:
            Tuple of (crate_resized, crate_size, x_start, y_start, icon_size) or None if no crate
        """
        if self.crate_icon is None:
            return None

        crate_size = int(self.icon_size * self.CRATE_RATIO)
        crate_resized = cv2.resize(
            self.crate_icon, (crate_size, crate_size), interpolation=cv2.INTER_LINEAR
        ).astype(np.uint8)
        x_start = self.icon_size - crate_size
        y_start = self.icon_size - crate_size

        return crate_resized, crate_size, x_start, y_start, self.icon_size

    def on_input_change(self) -> None:
        """Handle input field changes and update multipliers."""
        try:
            self.red_mult = self.red_input.value() / 255.0
            self.green_mult = self.green_input.value() / 255.0
            self.blue_mult = self.blue_input.value() / 255.0

            # Update sliders (block signals to avoid circular updates)
            sliders = [self.red_slider, self.green_slider, self.blue_slider]
            self._block_signals(sliders, True)

            self.red_slider.setValue(int(self.red_mult * 1000))
            self.green_slider.setValue(int(self.green_mult * 1000))
            self.blue_slider.setValue(int(self.blue_mult * 1000))

            self._block_signals(sliders, False)

            self.update_labels()
            self.update_preview()
        except Exception:
            pass

    def on_slider_change(self) -> None:
        """Handle slider changes and update multipliers."""
        self.red_mult = self.red_slider.value() / 1000.0
        self.green_mult = self.green_slider.value() / 1000.0
        self.blue_mult = self.blue_slider.value() / 1000.0

        # Update input fields (block signals to avoid circular updates)
        inputs = [self.red_input, self.green_input, self.blue_input]
        self._block_signals(inputs, True)

        self.red_input.setValue(int(self.red_mult * 255))
        self.green_input.setValue(int(self.green_mult * 255))
        self.blue_input.setValue(int(self.blue_mult * 255))

        self._block_signals(inputs, False)

        self.update_labels()
        self.update_preview()

    def on_offset_change(self, value: int, channel: str) -> None:
        """Handle offset slider changes with optional linking."""
        if self.link_offsets_cb.isChecked():
            # Link all offsets together
            self.red_offset_slider.setValue(value)
            self.green_offset_slider.setValue(value)
            self.blue_offset_slider.setValue(value)
            self.red_offset = value
            self.green_offset = value
            self.blue_offset = value
        else:
            # Update individual channel
            if channel == "red":
                self.red_offset = value
            elif channel == "green":
                self.green_offset = value
            elif channel == "blue":
                self.blue_offset = value

        self.update_labels()
        self.update_preview()

    def on_alpha_change(self, value: int) -> None:
        """Handle alpha slider changes."""
        self.alpha_mult = value / 1000.0
        self.update_labels()
        self.update_preview()

    def update_labels(self) -> None:
        """Update all value labels."""
        self.red_mult_label.setText(f"{self.red_mult:.3f}")
        self.green_mult_label.setText(f"{self.green_mult:.3f}")
        self.blue_mult_label.setText(f"{self.blue_mult:.3f}")
        self.red_offset_label.setText(str(self.red_offset))
        self.green_offset_label.setText(str(self.green_offset))
        self.blue_offset_label.setText(str(self.blue_offset))
        self.alpha_label.setText(f"{self.alpha_mult:.3f}")

    def apply_color_transformation(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Apply uniform color transformation to an image array."""
        img_array = image.astype(np.float32)

        # Only process pixels that have significant alpha
        alpha_mask = img_array[:, :, 3] > 10

        # Apply color transformation to all pixels with alpha
        if np.any(alpha_mask):
            img_array[alpha_mask, 0] = img_array[alpha_mask, 0] * self.red_mult + self.red_offset
            img_array[alpha_mask, 1] = (
                img_array[alpha_mask, 1] * self.green_mult + self.green_offset
            )
            img_array[alpha_mask, 2] = img_array[alpha_mask, 2] * self.blue_mult + self.blue_offset

        # Clamp values and convert back
        img_array = np.clip(img_array, 0, 255)
        return img_array.astype(np.uint8)

    def create_result_image(self) -> NDArray[np.uint8] | None:
        """Create the final result image with crate overlay."""
        if self.original_icon is None or self.crate_icon is None:
            return None

        # Create base with black background
        result = np.zeros((self.icon_size, self.icon_size, 4), dtype=np.uint8)
        result[:, :, 3] = 255  # Set alpha to opaque

        # Resize main icon
        main_resized_raw = cv2.resize(
            self.original_icon, (self.icon_size, self.icon_size), interpolation=cv2.INTER_LANCZOS4
        )
        main_resized = main_resized_raw.astype(np.uint8)

        # Alpha composite main icon onto result
        composited = self.alpha_composite(result, main_resized)
        result[:] = composited

        # Apply color transformation to crate
        crate_transformed = self.apply_color_transformation(self.crate_icon)

        # Calculate crate size and position
        crate_size = int(self.icon_size * self.CRATE_RATIO)
        x_pos = self.icon_size - crate_size
        y_pos = self.icon_size - crate_size

        # Resize crate with LINEAR interpolation
        crate_resized = cv2.resize(
            crate_transformed, (crate_size, crate_size), interpolation=cv2.INTER_LINEAR
        )

        # Apply alpha blending with adjustable alpha
        result_region = result[y_pos : y_pos + crate_size, x_pos : x_pos + crate_size]

        # Apply custom alpha multiplier
        crate_alpha = (crate_resized[:, :, 3:4] / 255.0) * self.alpha_mult

        for c in range(3):
            result_region[:, :, c] = (1 - crate_alpha[:, :, 0]) * result_region[
                :, :, c
            ] + crate_alpha[:, :, 0] * crate_resized[:, :, c]

        result[y_pos : y_pos + crate_size, x_pos : x_pos + crate_size] = result_region

        return result

    def alpha_composite(
        self, base: NDArray[np.uint8], overlay: NDArray[np.uint8]
    ) -> NDArray[np.uint8]:
        """Alpha composite overlay onto base using OpenCV operations."""
        base_f = base.astype(np.float32)
        overlay_f = overlay.astype(np.float32)

        # Normalize alpha values
        alpha_overlay = overlay_f[:, :, 3:4] / 255.0
        alpha_base = base_f[:, :, 3:4] / 255.0

        # Calculate resulting alpha
        alpha_result = alpha_overlay + alpha_base * (1 - alpha_overlay)

        # Avoid division by zero
        alpha_result = np.where(alpha_result == 0, 1, alpha_result)

        # Calculate RGB channels
        for c in range(3):
            base_f[:, :, c] = (
                overlay_f[:, :, c] * alpha_overlay[:, :, 0]
                + base_f[:, :, c] * alpha_base[:, :, 0] * (1 - alpha_overlay[:, :, 0])
            ) / alpha_result[:, :, 0]

        # Set alpha channel
        base_f[:, :, 3:4] = alpha_result * 255.0

        return np.clip(base_f, 0, 255).astype(np.uint8)

    def opencv_to_qimage(self, cv_image: NDArray[np.uint8]) -> QImage:
        """Convert OpenCV image (RGBA) to QImage."""
        height, width, channel = cv_image.shape
        bytes_per_line = 4 * width
        # Convert to bytes for QImage constructor
        return QImage(
            cv_image.tobytes(), width, height, bytes_per_line, QImage.Format.Format_RGBA8888
        )

    def draw_sample_markers(self, pixmap: QPixmap) -> QPixmap:
        """Draw visual markers on the pixmap to show selected sample points."""
        if self.current_result is None:
            return pixmap

        from PyQt6.QtGui import QColor, QPainter, QPen

        painter = QPainter(pixmap)
        display_scale = 16

        label_width = self.preview_label.width()
        label_height = self.preview_label.height()
        display_size = self.icon_size * display_scale

        # Calculate image position (centered)
        img_x = max(0, (label_width - display_size) // 2)
        img_y = max(0, (label_height - display_size) // 2)

        # Draw light sample marker
        if self.light_sample_pos:
            x, y = self.light_sample_pos
            display_x = img_x + x * display_scale
            display_y = img_y + y * display_scale

            pen = QPen(QColor("yellow"), 3)
            painter.setPen(pen)
            painter.drawEllipse(display_x - 8, display_y - 8, 16, 16)
            painter.drawText(display_x - 5, display_y - 15, "L")

        # Draw dark sample marker
        if self.dark_sample_pos:
            x, y = self.dark_sample_pos
            display_x = img_x + x * display_scale
            display_y = img_y + y * display_scale

            pen = QPen(QColor("red"), 3)
            painter.setPen(pen)
            painter.drawEllipse(display_x - 8, display_y - 8, 16, 16)
            painter.drawText(display_x - 5, display_y - 15, "D")

        painter.end()
        return pixmap

    def update_preview(self) -> None:
        """Update the preview display."""
        if self.original_icon is None or self.crate_icon is None:
            return

        result = self.create_result_image()
        if result is not None:
            self.current_result = result

            # Scale for display
            display_scale = 16
            display_size = self.icon_size * display_scale

            # Resize using OpenCV
            result_display_raw = cv2.resize(
                result, (display_size, display_size), interpolation=cv2.INTER_NEAREST
            )
            result_display = result_display_raw.astype(np.uint8)

            # Convert to QImage and QPixmap
            qimage = self.opencv_to_qimage(result_display)
            pixmap = QPixmap.fromImage(qimage)

            # Draw sample markers
            pixmap = self.draw_sample_markers(pixmap)

            self.preview_label.setPixmap(pixmap)

            # Update color samples
            self.update_color_sample()

    def update_color_sample(self) -> None:
        """Update color samples - uses manual selection if available, otherwise auto-detect."""
        if self.current_result is None:
            return

        # If we have manual selections, use those
        if self.light_sample_pos or self.dark_sample_pos:
            self.update_manual_samples()
            return

        # Otherwise, fall back to automatic detection
        try:
            # Calculate crate position and size in final image
            crate_size = int(self.icon_size * self.CRATE_RATIO)
            crate_x = self.icon_size - crate_size
            crate_y = self.icon_size - crate_size

            # Sample multiple points to find actual light/dark areas in final result
            sample_points = []
            for y_ratio in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                for x_ratio in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                    sample_x = crate_x + int(crate_size * x_ratio)
                    sample_y = crate_y + int(crate_size * y_ratio)
                    if 0 <= sample_x < self.icon_size and 0 <= sample_y < self.icon_size:
                        r, g, b, a = self.current_result[sample_y, sample_x]
                        brightness = (int(r) + int(g) + int(b)) // 3
                        sample_points.append(
                            (brightness, int(r), int(g), int(b), sample_x, sample_y)
                        )

            if sample_points:
                # Sort by brightness
                sample_points.sort(key=lambda x: x[0])

                # Get lightest and darkest
                lightest = sample_points[-1]
                darkest = sample_points[0]

                # Update labels
                self.sample_rgb_label.setText(
                    f"R: {lightest[1]}, G: {lightest[2]}, B: {lightest[3]}"
                )
                self.light_pos_label.setText(f"Position: ({lightest[4]}, {lightest[5]}) auto")

                self.sample_bars_label.setText(f"R: {darkest[1]}, G: {darkest[2]}, B: {darkest[3]}")
                self.dark_pos_label.setText(f"Position: ({darkest[4]}, {darkest[5]}) auto")
            else:
                self.sample_rgb_label.setText("R: -, G: -, B: -")
                self.sample_bars_label.setText("R: -, G: -, B: -")
                self.light_pos_label.setText("Position: not found")
                self.dark_pos_label.setText("Position: not found")

        except Exception as e:
            print(f"Error in auto color sample: {e}")
            self.sample_rgb_label.setText("R: -, G: -, B: -")
            self.sample_bars_label.setText("R: -, G: -, B: -")

    def get_current_sample_colors(
        self,
    ) -> tuple[tuple[int, int, int] | None, tuple[int, int, int] | None]:
        """Get the current RGB values from manually selected or auto-detected sample points."""
        if self.current_result is None:
            return None, None

        try:
            light_rgb = None
            dark_rgb = None

            # Use manual selections if available
            if self.light_sample_pos:
                x, y = self.light_sample_pos
                if 0 <= x < self.icon_size and 0 <= y < self.icon_size:
                    r, g, b, a = self.current_result[y, x]
                    light_rgb = (int(r), int(g), int(b))

            if self.dark_sample_pos:
                x, y = self.dark_sample_pos
                if 0 <= x < self.icon_size and 0 <= y < self.icon_size:
                    r, g, b, a = self.current_result[y, x]
                    dark_rgb = (int(r), int(g), int(b))

            # If we don't have both manual selections, fall back to auto-detection
            if light_rgb is None or dark_rgb is None:
                crate_size = int(self.icon_size * self.CRATE_RATIO)
                crate_x = self.icon_size - crate_size
                crate_y = self.icon_size - crate_size

                sample_points = []
                for x_ratio in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                    for y_ratio in [0.3, 0.5, 0.7]:
                        sample_x = crate_x + int(crate_size * x_ratio)
                        sample_y = crate_y + int(crate_size * y_ratio)
                        if 0 <= sample_x < self.icon_size and 0 <= sample_y < self.icon_size:
                            r, g, b, a = self.current_result[sample_y, sample_x]
                            brightness = (int(r) + int(g) + int(b)) // 3
                            sample_points.append((brightness, int(r), int(g), int(b)))

                if len(sample_points) >= 2:
                    sample_points.sort(key=lambda x: x[0])

                    if light_rgb is None:
                        lightest = sample_points[-1]
                        light_rgb = (lightest[1], lightest[2], lightest[3])

                    if dark_rgb is None:
                        darkest = sample_points[0]
                        dark_rgb = (darkest[1], darkest[2], darkest[3])

            return light_rgb, dark_rgb

        except Exception as e:
            print(f"Error getting current sample colors: {e}")
            return None, None

    def get_original_sample_colors(
        self,
    ) -> tuple[tuple[int, int, int] | None, tuple[int, int, int] | None]:
        """Get the original RGB values from the crate at corresponding sample points."""
        result = self._get_resized_crate_and_position()
        if result is None:
            return None, None

        crate_resized, crate_size, x_start, y_start, icon_size = result

        try:
            light_rgb = None
            dark_rgb = None

            # Use manual selections if available (converted to crate coordinates)
            if self.light_sample_pos:
                final_x, final_y = self.light_sample_pos
                if (
                    final_x >= x_start
                    and final_y >= y_start
                    and final_x < icon_size
                    and final_y < icon_size
                ):
                    crate_x = final_x - x_start
                    crate_y = final_y - y_start

                    if 0 <= crate_x < crate_size and 0 <= crate_y < crate_size:
                        r, g, b, a = crate_resized[crate_y, crate_x]
                        light_rgb = (int(r), int(g), int(b))

            if self.dark_sample_pos:
                final_x, final_y = self.dark_sample_pos
                if (
                    final_x >= x_start
                    and final_y >= y_start
                    and final_x < icon_size
                    and final_y < icon_size
                ):
                    crate_x = final_x - x_start
                    crate_y = final_y - y_start

                    if 0 <= crate_x < crate_size and 0 <= crate_y < crate_size:
                        r, g, b, a = crate_resized[crate_y, crate_x]
                        dark_rgb = (int(r), int(g), int(b))

            # If we don't have both manual selections, fall back to auto-detection
            if light_rgb is None or dark_rgb is None:
                sample_points = []
                for y_ratio in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                    for x_ratio in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                        x = int(crate_size * x_ratio)
                        y = int(crate_size * y_ratio)
                        if 0 <= x < crate_size and 0 <= y < crate_size:
                            r, g, b, a = crate_resized[y, x]
                            brightness = (int(r) + int(g) + int(b)) // 3
                            sample_points.append((brightness, int(r), int(g), int(b), x, y))

                if len(sample_points) >= 2:
                    sample_points.sort(key=lambda x: x[0])

                    if light_rgb is None:
                        lightest = sample_points[-1]
                        light_rgb = (lightest[1], lightest[2], lightest[3])

                    if dark_rgb is None:
                        darkest = sample_points[0]
                        dark_rgb = (darkest[1], darkest[2], darkest[3])

            return light_rgb, dark_rgb

        except Exception as e:
            print(f"Error getting original sample colors: {e}")
            return None, None

    def get_background_colors(
        self,
    ) -> tuple[tuple[int, int, int] | None, tuple[int, int, int] | None]:
        """Get the background (base icon) colors under the crate sample positions."""
        if self.original_icon is None:
            return None, None

        try:
            # Create the base without the crate
            icon_size = self.icon_size
            result = np.zeros((icon_size, icon_size, 4), dtype=np.uint8)
            result[:, :, 3] = 255

            # Resize and composite main icon
            main_resized_raw = cv2.resize(
                self.original_icon, (icon_size, icon_size), interpolation=cv2.INTER_LANCZOS4
            )
            main_resized = main_resized_raw.astype(np.uint8)
            composited = self.alpha_composite(result, main_resized)

            light_rgb = None
            dark_rgb = None

            # Get background colors at sample positions
            if self.light_sample_pos:
                x, y = self.light_sample_pos
                if 0 <= x < icon_size and 0 <= y < icon_size:
                    r, g, b, a = composited[y, x]
                    light_rgb = (int(r), int(g), int(b))

            if self.dark_sample_pos:
                x, y = self.dark_sample_pos
                if 0 <= x < icon_size and 0 <= y < icon_size:
                    r, g, b, a = composited[y, x]
                    dark_rgb = (int(r), int(g), int(b))

            return light_rgb, dark_rgb

        except Exception as e:
            print(f"Error getting background colors: {e}")
            return None, None

    def get_crate_alpha_at_samples(self) -> tuple[float | None, float | None]:
        """Get the actual alpha values at the sample positions on the crate."""
        result = self._get_resized_crate_and_position()
        if result is None:
            return None, None

        crate_resized, crate_size, x_start, y_start, icon_size = result

        try:
            alpha_light = None
            alpha_dark = None

            # Get alpha at light sample position
            if self.light_sample_pos:
                final_x, final_y = self.light_sample_pos
                if (
                    final_x >= x_start
                    and final_y >= y_start
                    and final_x < icon_size
                    and final_y < icon_size
                ):
                    crate_x = final_x - x_start
                    crate_y = final_y - y_start
                    if 0 <= crate_x < crate_size and 0 <= crate_y < crate_size:
                        crate_alpha_pixel = float(crate_resized[crate_y, crate_x, 3])
                        alpha_light = (crate_alpha_pixel / 255.0) * self.alpha_mult

            # Get alpha at dark sample position
            if self.dark_sample_pos:
                final_x, final_y = self.dark_sample_pos
                if (
                    final_x >= x_start
                    and final_y >= y_start
                    and final_x < icon_size
                    and final_y < icon_size
                ):
                    crate_x = final_x - x_start
                    crate_y = final_y - y_start
                    if 0 <= crate_x < crate_size and 0 <= crate_y < crate_size:
                        crate_alpha_pixel = float(crate_resized[crate_y, crate_x, 3])
                        alpha_dark = (crate_alpha_pixel / 255.0) * self.alpha_mult

            return alpha_light, alpha_dark

        except Exception as e:
            print(f"Error getting crate alpha: {e}")
            return None, None

    def auto_calculate(self) -> None:
        """Calculate multipliers and offsets by comparing current result to targets."""
        if self.current_result is None:
            QMessageBox.warning(self, "Warning", "No result image available. Load images first.")
            return

        # Get current sample colors from the final transformed result
        current_light, current_dark = self.get_current_sample_colors()
        if current_light is None or current_dark is None:
            QMessageBox.critical(self, "Error", "Could not sample current result colors")
            return

        # Get original sample colors to calculate current transformation
        original_light, original_dark = self.get_original_sample_colors()
        if original_light is None or original_dark is None:
            QMessageBox.critical(self, "Error", "Could not sample original colors")
            return

        # Get the background colors (base icon colors under the crate positions)
        bg_light, bg_dark = self.get_background_colors()
        if bg_light is None or bg_dark is None:
            QMessageBox.critical(self, "Error", "Could not sample background colors")
            return

        # Target colors (final composited colors we want)
        light_target = (182, 179, 170)
        dark_target = (75, 73, 69)

        print("\nCurrent state:")
        print(f"Light area: current={current_light}, target={light_target}")
        print(f"Dark area: current={current_dark}, target={dark_target}")
        print(f"Original light: {original_light}")
        print(f"Original dark: {original_dark}")
        print(f"Background light: {bg_light}")
        print(f"Background dark: {bg_dark}")

        # Get the actual alpha values at the sample points
        # The crate alpha is: (crate_pixel_alpha / 255) * alpha_mult
        alpha_light, alpha_dark = self.get_crate_alpha_at_samples()
        if alpha_light is None or alpha_dark is None:
            QMessageBox.critical(self, "Error", "Could not get crate alpha values")
            return

        print(f"Alpha at light sample: {alpha_light:.3f}")
        print(f"Alpha at dark sample: {alpha_dark:.3f}")

        # Work backwards through alpha compositing to find what crate colors we need
        # Formula: result = (1 - alpha) * bg + alpha * foreground
        # So: foreground = (result - (1 - alpha) * bg) / alpha

        # Calculate target crate colors (before compositing)
        crate_light_target = []
        crate_dark_target = []
        for channel in range(3):
            # For light area
            result_light = float(light_target[channel])
            bg_light_val = float(bg_light[channel])
            if alpha_light > 0.01:
                crate_light = (result_light - (1 - alpha_light) * bg_light_val) / alpha_light
                crate_light_target.append(max(0, min(255, crate_light)))
            else:
                crate_light_target.append(result_light)

            # For dark area
            result_dark = float(dark_target[channel])
            bg_dark_val = float(bg_dark[channel])
            if alpha_dark > 0.01:
                crate_dark = (result_dark - (1 - alpha_dark) * bg_dark_val) / alpha_dark
                crate_dark_target.append(max(0, min(255, crate_dark)))
            else:
                crate_dark_target.append(result_dark)

        print(f"Crate light target (before compositing): {crate_light_target}")
        print(f"Crate dark target (before compositing): {crate_dark_target}")

        # Now calculate transformation: crate_color = original * mult + offset
        calculated_values: list[tuple[float, int]] = []
        for channel in range(3):
            o1 = float(original_light[channel])
            o2 = float(original_dark[channel])
            t1 = crate_light_target[channel]
            t2 = crate_dark_target[channel]

            mult: float
            offset_raw: float
            if abs(o1 - o2) < 1:
                if o1 > 0:
                    mult = t1 / o1
                    offset_raw = 0.0
                else:
                    mult = 1.0
                    offset_raw = t1
            else:
                mult = (t1 - t2) / (o1 - o2)
                offset_raw = t1 - o1 * mult

            mult = max(0, min(2.0, mult))
            offset = max(0, min(255, int(offset_raw)))

            calculated_values.append((mult, offset))

            print(
                f"Channel {channel}: original=({o1:.0f}, {o2:.0f}), "
                f"crate_target=({t1:.0f}, {t2:.0f})"
            )
            print(f"  Calculated: mult={mult:.3f}, offset={offset}")

        # Apply calculated values
        self.red_mult = calculated_values[0][0]
        self.green_mult = calculated_values[1][0]
        self.blue_mult = calculated_values[2][0]

        self.red_offset = calculated_values[0][1]
        self.green_offset = calculated_values[1][1]
        self.blue_offset = calculated_values[2][1]

        # Update UI controls (block signals to prevent feedback loop)
        all_controls = [
            self.red_input,
            self.green_input,
            self.blue_input,
            self.red_slider,
            self.green_slider,
            self.blue_slider,
            self.red_offset_slider,
            self.green_offset_slider,
            self.blue_offset_slider,
        ]
        self._block_signals(all_controls, True)

        self.red_input.setValue(int(calculated_values[0][0] * 255))
        self.green_input.setValue(int(calculated_values[1][0] * 255))
        self.blue_input.setValue(int(calculated_values[2][0] * 255))

        self.red_slider.setValue(int(calculated_values[0][0] * 1000))
        self.green_slider.setValue(int(calculated_values[1][0] * 1000))
        self.blue_slider.setValue(int(calculated_values[2][0] * 1000))

        self.red_offset_slider.setValue(calculated_values[0][1])
        self.green_offset_slider.setValue(calculated_values[1][1])
        self.blue_offset_slider.setValue(calculated_values[2][1])

        self._block_signals(all_controls, False)

        # Update display
        self.update_labels()
        self.update_preview()

        # Verify the result
        verification_light, verification_dark = self.get_current_sample_colors()
        print("\nVerification after applying calculated values:")
        print(f"Light area result: {verification_light}, target: {light_target}")
        print(f"Dark area result: {verification_dark}, target: {dark_target}")

        # Show detailed results
        result_msg = "Current → Target:\n"
        result_msg += f"Light: {current_light} → {light_target}\n"
        result_msg += f"Dark: {current_dark} → {dark_target}\n\n"
        result_msg += "Calculated transformation:\n"
        for channel_name, (mult, offset) in zip(
            ["Red", "Green", "Blue"], calculated_values, strict=False
        ):
            result_msg += f"{channel_name}: {mult:.3f}×original + {offset}\n"

        QMessageBox.information(self, "Auto Calculate Results", result_msg)

    def reset_values(self) -> None:
        """Reset all values to hardcoded defaults."""
        # Reset to default values
        self.red_mult = 240 / 255
        self.green_mult = 234 / 255
        self.blue_mult = 220 / 255
        self.red_offset = 0
        self.green_offset = 0
        self.blue_offset = 0
        self.alpha_mult = 0.75

        # Update UI controls
        self.red_input.setValue(240)
        self.green_input.setValue(234)
        self.blue_input.setValue(220)

        self.red_slider.setValue(int(self.red_mult * 1000))
        self.green_slider.setValue(int(self.green_mult * 1000))
        self.blue_slider.setValue(int(self.blue_mult * 1000))

        self.red_offset_slider.setValue(0)
        self.green_offset_slider.setValue(0)
        self.blue_offset_slider.setValue(0)

        self.alpha_slider.setValue(int(self.alpha_mult * 1000))

        self.link_offsets_cb.setChecked(True)

        # Update display
        self.update_labels()
        self.update_preview()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Interactive Crate Color Tuner")
    parser.add_argument("--size", type=int, default=64, help="Icon size (default: 64)")
    parser.add_argument("--icon", type=str, help="Path to icon image file")
    parser.add_argument("--crate", type=str, help="Path to crate image file")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = CrateTunerQt(icon_size=args.size, icon_path=args.icon, crate_path=args.crate)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

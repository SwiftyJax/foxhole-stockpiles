"""Tests for OCRTab."""

from typing import Any
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QMessageBox

from foxhole_stockpiles.core.settings.sections.ocr import OCRSettings
from foxhole_stockpiles.gui.widgets.config_tabs.ocr_tab import OCRTab


@pytest.fixture
def ocr_tab(qtbot: Any) -> OCRTab:
    """Create an OCRTab instance.

    Args:
        qtbot: PyQt test fixture

    Returns:
        OCRTab: Tab instance
    """
    tab = OCRTab()
    qtbot.addWidget(tab)
    # Initialize with default values to ensure all fields are valid
    tab.set_values(OCRSettings())
    return tab


def test_ocr_tab_initialization(ocr_tab: OCRTab) -> None:
    """Test OCRTab initialization.

    Args:
        ocr_tab: OCRTab instance
    """
    assert ocr_tab.height_input is not None
    assert ocr_tab.box_width_input is not None
    assert ocr_tab.box_height_input is not None
    assert ocr_tab.column_offset_input is not None
    assert ocr_tab.row_offset_input is not None
    assert ocr_tab.group_offset_input is not None
    assert ocr_tab.title_margin_input is not None
    assert ocr_tab.title_min_width_input is not None
    assert ocr_tab.title_height_input is not None
    assert ocr_tab.icon_to_quantity_offset_input is not None
    assert ocr_tab.gray_lower_input is not None
    assert ocr_tab.gray_upper_input is not None
    assert ocr_tab.pixel_diff_tolerance_input is not None


def test_ocr_tab_default_values(ocr_tab: OCRTab) -> None:
    """Test default values match OCRSettings defaults.

    Args:
        ocr_tab: OCRTab instance
    """
    assert ocr_tab.height_input.value() == 2160


def test_ocr_tab_height_range(ocr_tab: OCRTab) -> None:
    """Test height input has correct range.

    Args:
        ocr_tab: OCRTab instance
    """
    assert ocr_tab.height_input.minimum() == 1080
    assert ocr_tab.height_input.maximum() == 4320


def test_ocr_tab_box_width_range(ocr_tab: OCRTab) -> None:
    """Test box width input has correct range.

    Args:
        ocr_tab: OCRTab instance
    """
    assert ocr_tab.box_width_input.minimum() == 10
    assert ocr_tab.box_width_input.maximum() == 500


def test_ocr_tab_box_height_range(ocr_tab: OCRTab) -> None:
    """Test box height input has correct range.

    Args:
        ocr_tab: OCRTab instance
    """
    assert ocr_tab.box_height_input.minimum() == 10
    assert ocr_tab.box_height_input.maximum() == 500


def test_ocr_tab_gray_threshold_range(ocr_tab: OCRTab) -> None:
    """Test gray threshold inputs have correct range.

    Args:
        ocr_tab: OCRTab instance
    """
    assert ocr_tab.gray_lower_input.minimum() == 0
    assert ocr_tab.gray_lower_input.maximum() == 255
    assert ocr_tab.gray_upper_input.minimum() == 0
    assert ocr_tab.gray_upper_input.maximum() == 255


def test_ocr_tab_set_values(ocr_tab: OCRTab) -> None:
    """Test setting values from settings object.

    Args:
        ocr_tab: OCRTab instance
    """
    settings = OCRSettings(
        height=1920,
        box_width=100,
        box_height=50,
        column_offset=200,
        row_offset=150,
        group_offset=300,
        title_margin=10,
        title_min_width=200,
        title_height=40,
        icon_to_quantity_offset=75,
        gray_lower=20,
        gray_upper=90,
        pixel_diff_tolerance=3,
    )

    ocr_tab.set_values(settings)

    assert ocr_tab.height_input.value() == 1920
    assert ocr_tab.box_width_input.value() == 100
    assert ocr_tab.box_height_input.value() == 50
    assert ocr_tab.column_offset_input.value() == 200
    assert ocr_tab.row_offset_input.value() == 150
    assert ocr_tab.group_offset_input.value() == 300
    assert ocr_tab.title_margin_input.value() == 10
    assert ocr_tab.title_min_width_input.value() == 200
    assert ocr_tab.title_height_input.value() == 40
    assert ocr_tab.icon_to_quantity_offset_input.value() == 75
    assert ocr_tab.gray_lower_input.value() == 20
    assert ocr_tab.gray_upper_input.value() == 90
    assert ocr_tab.pixel_diff_tolerance_input.value() == 3


def test_ocr_tab_get_values(ocr_tab: OCRTab) -> None:
    """Test getting values from widgets.

    Args:
        ocr_tab: OCRTab instance
    """
    ocr_tab.height_input.setValue(3840)
    ocr_tab.box_width_input.setValue(120)
    ocr_tab.box_height_input.setValue(60)
    ocr_tab.column_offset_input.setValue(250)
    ocr_tab.row_offset_input.setValue(200)
    ocr_tab.group_offset_input.setValue(400)
    ocr_tab.title_margin_input.setValue(15)
    ocr_tab.title_min_width_input.setValue(250)
    ocr_tab.title_height_input.setValue(50)
    ocr_tab.icon_to_quantity_offset_input.setValue(80)
    ocr_tab.gray_lower_input.setValue(25)
    ocr_tab.gray_upper_input.setValue(95)
    ocr_tab.pixel_diff_tolerance_input.setValue(5)

    settings = ocr_tab.get_values()

    assert settings.height == 3840
    assert settings.box_width == 120
    assert settings.box_height == 60
    assert settings.column_offset == 250
    assert settings.row_offset == 200
    assert settings.group_offset == 400
    assert settings.title_margin == 15
    assert settings.title_min_width == 250
    assert settings.title_height == 50
    assert settings.icon_to_quantity_offset == 80
    assert settings.gray_lower == 25
    assert settings.gray_upper == 95
    assert settings.pixel_diff_tolerance == 5


def test_ocr_tab_reset_all_to_defaults_confirmed(qtbot: Any, ocr_tab: OCRTab) -> None:
    """Test reset all to defaults when confirmed.

    Args:
        qtbot: PyQt test fixture
        ocr_tab: OCRTab instance
    """
    # Change some values
    ocr_tab.height_input.setValue(1080)
    ocr_tab.box_width_input.setValue(50)

    with patch(
        "foxhole_stockpiles.gui.widgets.config_tabs.ocr_tab.QMessageBox.question"
    ) as mock_msg:
        mock_msg.return_value = QMessageBox.StandardButton.Yes

        ocr_tab.reset_all_to_defaults()

        # Should reset to defaults
        defaults = OCRSettings()
        assert ocr_tab.height_input.value() == defaults.height
        assert ocr_tab.box_width_input.value() == defaults.box_width


def test_ocr_tab_reset_all_to_defaults_cancelled(qtbot: Any, ocr_tab: OCRTab) -> None:
    """Test reset all to defaults when cancelled.

    Args:
        qtbot: PyQt test fixture
        ocr_tab: OCRTab instance
    """
    # Change some values
    ocr_tab.height_input.setValue(1080)
    original_value = 1080

    with patch(
        "foxhole_stockpiles.gui.widgets.config_tabs.ocr_tab.QMessageBox.question"
    ) as mock_msg:
        mock_msg.return_value = QMessageBox.StandardButton.No

        ocr_tab.reset_all_to_defaults()

        # Should not reset
        assert ocr_tab.height_input.value() == original_value


def test_ocr_tab_set_values_default_settings(ocr_tab: OCRTab) -> None:
    """Test setting values with default settings object.

    Args:
        ocr_tab: OCRTab instance
    """
    settings = OCRSettings()

    ocr_tab.set_values(settings)

    assert ocr_tab.height_input.value() == settings.height
    assert ocr_tab.box_width_input.value() == settings.box_width
    assert ocr_tab.box_height_input.value() == settings.box_height


def test_ocr_tab_min_height_boundary(ocr_tab: OCRTab) -> None:
    """Test height at minimum boundary.

    Args:
        ocr_tab: OCRTab instance
    """
    ocr_tab.height_input.setValue(1080)

    settings = ocr_tab.get_values()

    assert settings.height == 1080


def test_ocr_tab_max_height_boundary(ocr_tab: OCRTab) -> None:
    """Test height at maximum boundary.

    Args:
        ocr_tab: OCRTab instance
    """
    ocr_tab.height_input.setValue(4320)

    settings = ocr_tab.get_values()

    assert settings.height == 4320


def test_ocr_tab_min_box_dimensions(ocr_tab: OCRTab) -> None:
    """Test box dimensions at minimum.

    Args:
        ocr_tab: OCRTab instance
    """
    ocr_tab.box_width_input.setValue(10)
    ocr_tab.box_height_input.setValue(10)

    settings = ocr_tab.get_values()

    assert settings.box_width == 10
    assert settings.box_height == 10


def test_ocr_tab_max_box_dimensions(ocr_tab: OCRTab) -> None:
    """Test box dimensions at maximum.

    Args:
        ocr_tab: OCRTab instance
    """
    ocr_tab.box_width_input.setValue(500)
    ocr_tab.box_height_input.setValue(500)

    settings = ocr_tab.get_values()

    assert settings.box_width == 500
    assert settings.box_height == 500


def test_ocr_tab_min_gray_thresholds(ocr_tab: OCRTab) -> None:
    """Test gray thresholds at minimum.

    Args:
        ocr_tab: OCRTab instance
    """
    ocr_tab.gray_lower_input.setValue(1)
    ocr_tab.gray_upper_input.setValue(1)

    settings = ocr_tab.get_values()

    assert settings.gray_lower == 1
    assert settings.gray_upper == 1


def test_ocr_tab_max_gray_thresholds(ocr_tab: OCRTab) -> None:
    """Test gray thresholds at maximum.

    Args:
        ocr_tab: OCRTab instance
    """
    ocr_tab.gray_lower_input.setValue(255)
    ocr_tab.gray_upper_input.setValue(255)

    settings = ocr_tab.get_values()

    assert settings.gray_lower == 255
    assert settings.gray_upper == 255


def test_ocr_tab_min_offsets(ocr_tab: OCRTab) -> None:
    """Test all offsets set to minimum.

    Args:
        ocr_tab: OCRTab instance
    """
    ocr_tab.column_offset_input.setValue(1)
    ocr_tab.row_offset_input.setValue(1)
    ocr_tab.group_offset_input.setValue(1)
    ocr_tab.icon_to_quantity_offset_input.setValue(1)

    settings = ocr_tab.get_values()

    assert settings.column_offset == 1
    assert settings.row_offset == 1
    assert settings.group_offset == 1
    assert settings.icon_to_quantity_offset == 1


def test_ocr_tab_max_offsets(ocr_tab: OCRTab) -> None:
    """Test offsets at maximum values.

    Args:
        ocr_tab: OCRTab instance
    """
    ocr_tab.column_offset_input.setValue(1000)
    ocr_tab.row_offset_input.setValue(1000)
    ocr_tab.group_offset_input.setValue(1000)

    settings = ocr_tab.get_values()

    assert settings.column_offset == 1000
    assert settings.row_offset == 1000
    assert settings.group_offset == 1000


def test_ocr_tab_title_settings(ocr_tab: OCRTab) -> None:
    """Test title-related settings.

    Args:
        ocr_tab: OCRTab instance
    """
    ocr_tab.title_margin_input.setValue(20)
    ocr_tab.title_min_width_input.setValue(300)
    ocr_tab.title_height_input.setValue(60)

    settings = ocr_tab.get_values()

    assert settings.title_margin == 20
    assert settings.title_min_width == 300
    assert settings.title_height == 60


def test_ocr_tab_pixel_diff_tolerance_range(ocr_tab: OCRTab) -> None:
    """Test pixel diff tolerance has correct range.

    Args:
        ocr_tab: OCRTab instance
    """
    assert ocr_tab.pixel_diff_tolerance_input.minimum() == 0
    assert ocr_tab.pixel_diff_tolerance_input.maximum() == 50


def test_ocr_tab_all_inputs_are_spin_boxes(ocr_tab: OCRTab) -> None:
    """Test all inputs are spin boxes.

    Args:
        ocr_tab: OCRTab instance
    """
    from PySide6.QtWidgets import QSpinBox

    assert isinstance(ocr_tab.height_input, QSpinBox)
    assert isinstance(ocr_tab.box_width_input, QSpinBox)
    assert isinstance(ocr_tab.box_height_input, QSpinBox)
    assert isinstance(ocr_tab.column_offset_input, QSpinBox)
    assert isinstance(ocr_tab.row_offset_input, QSpinBox)
    assert isinstance(ocr_tab.group_offset_input, QSpinBox)

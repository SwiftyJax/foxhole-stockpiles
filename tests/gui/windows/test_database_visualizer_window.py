"""Tests for DatabaseVisualizerWindow."""

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem

from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.gui.windows.database_visualizer_window import (
    DatabaseLoader,
    DatabaseVisualizerWindow,
)
from foxhole_stockpiles.models.icon_template import IconTemplate
from foxhole_stockpiles.services.template_database import TemplateDatabase


@pytest.fixture
def mock_template() -> IconTemplate:
    """Create a mock template for testing.

    Returns:
        IconTemplate: A mock template instance.
    """
    return IconTemplate(
        code="TestItem",
        faction=ItemFaction.NEUTRAL,
        category=ItemCategory.Item,
        mod="vanilla",
        crated=False,
        resolution=SupportedResolution.R_1080,
        image=np.zeros((32, 32, 3), dtype=np.uint8),
        phash=0,
    )


@pytest.fixture
def mock_crated_template() -> IconTemplate:
    """Create a mock crated template for testing.

    Returns:
        IconTemplate: A mock crated template instance.
    """
    return IconTemplate(
        code="TestItem",
        faction=ItemFaction.COLONIALS,
        category=ItemCategory.Vehicle,
        mod="testmod",
        crated=True,
        resolution=SupportedResolution.R_1080,
        image=np.zeros((32, 32, 3), dtype=np.uint8),
        phash=0,
    )


@pytest.fixture
def mock_database(mock_template: IconTemplate, mock_crated_template: IconTemplate) -> MagicMock:
    """Create a mock template database.

    Args:
        mock_template: Mock template fixture.
        mock_crated_template: Mock crated template fixture.

    Returns:
        MagicMock: A mock database instance.
    """
    db = MagicMock(spec=TemplateDatabase)
    db.templates = [mock_template, mock_crated_template]
    return db


@pytest.fixture
def visualizer_window(qtbot: Any) -> DatabaseVisualizerWindow:
    """Create a DatabaseVisualizerWindow instance without loading.

    Args:
        qtbot: PyQt test fixture.

    Returns:
        DatabaseVisualizerWindow: Window instance.
    """
    window = DatabaseVisualizerWindow(parent=None, database_path=None)
    qtbot.addWidget(window)
    return window


class TestDatabaseLoader:
    """Tests for DatabaseLoader thread."""

    def test_initialization(self) -> None:
        """Test DatabaseLoader initialization."""
        loader = DatabaseLoader("/path/to/db.h5")
        assert loader.database_path == "/path/to/db.h5"

    def test_run_success(self, qtbot: Any) -> None:
        """Test successful database loading.

        Args:
            qtbot: PyQt test fixture.
        """
        loader = DatabaseLoader("/path/to/db.h5")

        mock_databases = {SupportedResolution.R_1080: MagicMock()}

        with patch("foxhole_stockpiles.gui.windows.database_visualizer_window.TemplateManager"):
            with patch(
                "foxhole_stockpiles.gui.windows.database_visualizer_window.asyncio.run",
                return_value=mock_databases,
            ):
                # Connect signal to capture result
                result = []
                loader.finished.connect(lambda x: result.append(x))

                loader.run()

                assert len(result) == 1
                assert result[0] == mock_databases

    def test_run_error(self, qtbot: Any) -> None:
        """Test database loading error handling.

        Args:
            qtbot: PyQt test fixture.
        """
        loader = DatabaseLoader("/path/to/db.h5")

        with patch(
            "foxhole_stockpiles.gui.windows.database_visualizer_window.TemplateManager",
            side_effect=FileNotFoundError("Database not found"),
        ):
            # Connect signal to capture error
            errors = []
            loader.error.connect(lambda x: errors.append(x))

            loader.run()

            assert len(errors) == 1
            assert "Database not found" in errors[0]


class TestDatabaseVisualizerWindowInitialization:
    """Tests for DatabaseVisualizerWindow initialization."""

    def test_initialization_without_path(self, qtbot: Any) -> None:
        """Test window initialization without database path.

        Args:
            qtbot: PyQt test fixture.
        """
        window = DatabaseVisualizerWindow(parent=None, database_path=None)
        qtbot.addWidget(window)

        assert window.database_path is None
        assert window.all_databases == {}
        assert window.current_resolution is None
        assert window.database is None
        assert window.filtered_templates == []
        assert window.all_templates == []

    def test_initialization_with_path(self, qtbot: Any) -> None:
        """Test window initialization with database path starts loading.

        Args:
            qtbot: PyQt test fixture.
        """
        with patch.object(DatabaseVisualizerWindow, "load_databases") as mock_load:
            window = DatabaseVisualizerWindow(parent=None, database_path="/path/to/db.h5")
            qtbot.addWidget(window)

            assert window.database_path == "/path/to/db.h5"
            mock_load.assert_called_once()

    def test_window_title(self, visualizer_window: DatabaseVisualizerWindow) -> None:
        """Test initial window title.

        Args:
            visualizer_window: Window fixture.
        """
        assert "Template Database Visualizer" in visualizer_window.windowTitle()

    def test_minimum_size(self, visualizer_window: DatabaseVisualizerWindow) -> None:
        """Test window minimum size.

        Args:
            visualizer_window: Window fixture.
        """
        assert visualizer_window.minimumWidth() >= 1200
        assert visualizer_window.minimumHeight() >= 700


class TestDatabaseVisualizerWindowUI:
    """Tests for DatabaseVisualizerWindow UI components."""

    def test_filter_widgets_exist(self, visualizer_window: DatabaseVisualizerWindow) -> None:
        """Test that filter widgets are created.

        Args:
            visualizer_window: Window fixture.
        """
        assert visualizer_window.resolution_filter is not None
        assert visualizer_window.code_filter is not None
        assert visualizer_window.faction_filter is not None
        assert visualizer_window.category_filter is not None
        assert visualizer_window.mod_filter is not None
        assert visualizer_window.crated_all is not None
        assert visualizer_window.crated_normal is not None
        assert visualizer_window.crated_crated is not None

    def test_image_labels_exist(self, visualizer_window: DatabaseVisualizerWindow) -> None:
        """Test that image display labels are created.

        Args:
            visualizer_window: Window fixture.
        """
        assert visualizer_window.current_image is not None
        assert visualizer_window.highest_image is not None
        assert visualizer_window.info_label is not None

    def test_progress_bar_hidden_initially(
        self, visualizer_window: DatabaseVisualizerWindow
    ) -> None:
        """Test that progress bar is hidden initially.

        Args:
            visualizer_window: Window fixture.
        """
        assert not visualizer_window.progress_bar.isVisible()

    def test_faction_filter_options(self, visualizer_window: DatabaseVisualizerWindow) -> None:
        """Test faction filter has all options.

        Args:
            visualizer_window: Window fixture.
        """
        # Should have "All" plus all factions
        assert visualizer_window.faction_filter.count() >= len(ItemFaction) + 1
        assert visualizer_window.faction_filter.itemText(0) == "All"

    def test_category_filter_options(self, visualizer_window: DatabaseVisualizerWindow) -> None:
        """Test category filter has all options.

        Args:
            visualizer_window: Window fixture.
        """
        # Should have "All" plus all categories
        assert visualizer_window.category_filter.count() >= len(ItemCategory) + 1
        assert visualizer_window.category_filter.itemText(0) == "All"

    def test_crated_all_checked_initially(
        self, visualizer_window: DatabaseVisualizerWindow
    ) -> None:
        """Test crated 'All' checkbox is checked initially.

        Args:
            visualizer_window: Window fixture.
        """
        assert visualizer_window.crated_all.isChecked()
        assert not visualizer_window.crated_normal.isChecked()
        assert not visualizer_window.crated_crated.isChecked()


class TestDatabaseVisualizerWindowFilters:
    """Tests for filter functionality."""

    def test_clear_filters(self, visualizer_window: DatabaseVisualizerWindow) -> None:
        """Test clearing all filters.

        Args:
            visualizer_window: Window fixture.
        """
        # Set some filter values
        visualizer_window.code_filter.setText("test")
        visualizer_window.faction_filter.setCurrentIndex(1)
        visualizer_window.crated_all.setChecked(False)
        visualizer_window.crated_normal.setChecked(True)

        # Clear filters
        visualizer_window._clear_filters()

        # Verify all reset
        assert visualizer_window.code_filter.text() == ""
        assert visualizer_window.faction_filter.currentIndex() == 0
        assert visualizer_window.crated_all.isChecked()
        assert not visualizer_window.crated_normal.isChecked()
        assert not visualizer_window.crated_crated.isChecked()

    def test_crated_all_toggle_unchecks_others(
        self, visualizer_window: DatabaseVisualizerWindow
    ) -> None:
        """Test that checking 'All' unchecks normal and crated.

        Args:
            visualizer_window: Window fixture.
        """
        # First uncheck All and check others
        visualizer_window.crated_all.setChecked(False)
        visualizer_window.crated_normal.setChecked(True)
        visualizer_window.crated_crated.setChecked(True)

        # Now check All
        visualizer_window.crated_all.setChecked(True)

        # Others should be unchecked
        assert not visualizer_window.crated_normal.isChecked()
        assert not visualizer_window.crated_crated.isChecked()

    def test_apply_filters_no_database(self, visualizer_window: DatabaseVisualizerWindow) -> None:
        """Test apply filters does nothing without database.

        Args:
            visualizer_window: Window fixture.
        """
        visualizer_window.database = None
        visualizer_window._apply_filters()
        # Should not raise, just return early

    def test_apply_filters_code_filter(
        self,
        visualizer_window: DatabaseVisualizerWindow,
        mock_template: IconTemplate,
        mock_crated_template: IconTemplate,
    ) -> None:
        """Test code filter functionality.

        Args:
            visualizer_window: Window fixture.
            mock_template: Mock template.
            mock_crated_template: Mock crated template.
        """
        visualizer_window.database = MagicMock()
        visualizer_window.all_templates = [(0, mock_template), (1, mock_crated_template)]

        # Filter by code
        visualizer_window.code_filter.setText("TestItem")
        visualizer_window._apply_filters()

        # Both should match
        assert len(visualizer_window.filtered_templates) == 2

        # Filter by non-existing code
        visualizer_window.code_filter.setText("NonExistent")
        visualizer_window._apply_filters()

        assert len(visualizer_window.filtered_templates) == 0

    def test_apply_filters_faction_filter(
        self,
        visualizer_window: DatabaseVisualizerWindow,
        mock_template: IconTemplate,
        mock_crated_template: IconTemplate,
    ) -> None:
        """Test faction filter functionality.

        Args:
            visualizer_window: Window fixture.
            mock_template: Mock template (NEUTRAL).
            mock_crated_template: Mock crated template (COLONIALS).
        """
        visualizer_window.database = MagicMock()
        visualizer_window.all_templates = [(0, mock_template), (1, mock_crated_template)]

        # Filter by COLONIALS
        visualizer_window.faction_filter.setCurrentIndex(
            visualizer_window.faction_filter.findData(ItemFaction.COLONIALS)
        )
        visualizer_window._apply_filters()

        # Only crated template should match
        assert len(visualizer_window.filtered_templates) == 1
        assert visualizer_window.filtered_templates[0][1].faction == ItemFaction.COLONIALS

    def test_apply_filters_crated_filter(
        self,
        visualizer_window: DatabaseVisualizerWindow,
        mock_template: IconTemplate,
        mock_crated_template: IconTemplate,
    ) -> None:
        """Test crated filter functionality.

        Args:
            visualizer_window: Window fixture.
            mock_template: Mock template (not crated).
            mock_crated_template: Mock crated template.
        """
        visualizer_window.database = MagicMock()
        visualizer_window.all_templates = [(0, mock_template), (1, mock_crated_template)]

        # Show only crated
        visualizer_window.crated_all.setChecked(False)
        visualizer_window.crated_crated.setChecked(True)
        visualizer_window._apply_filters()

        assert len(visualizer_window.filtered_templates) == 1
        assert visualizer_window.filtered_templates[0][1].crated is True

        # Show only normal
        visualizer_window.crated_crated.setChecked(False)
        visualizer_window.crated_normal.setChecked(True)
        visualizer_window._apply_filters()

        assert len(visualizer_window.filtered_templates) == 1
        assert visualizer_window.filtered_templates[0][1].crated is False


class TestDatabaseVisualizerWindowDatabaseLoading:
    """Tests for database loading functionality."""

    def test_load_databases_no_path(self, visualizer_window: DatabaseVisualizerWindow) -> None:
        """Test load_databases with no path shows message.

        Args:
            visualizer_window: Window fixture.
        """
        visualizer_window.database_path = None
        visualizer_window.load_databases()

        assert "No database path" in visualizer_window.results_label.text()

    def test_load_databases_starts_thread(
        self, visualizer_window: DatabaseVisualizerWindow
    ) -> None:
        """Test load_databases starts loader thread.

        Args:
            visualizer_window: Window fixture.
        """
        visualizer_window.database_path = "/path/to/db.h5"

        with patch.object(DatabaseLoader, "start") as mock_start:
            visualizer_window.load_databases()

            assert visualizer_window.loader_thread is not None
            # Progress bar should be visible after load_databases is called
            # (check the property was set, not visibility which requires event processing)
            assert visualizer_window.results_label.text() == "Loading all databases..."
            mock_start.assert_called_once()

    def test_on_databases_loaded(
        self,
        visualizer_window: DatabaseVisualizerWindow,
        mock_database: MagicMock,
    ) -> None:
        """Test successful database load handling.

        Args:
            visualizer_window: Window fixture.
            mock_database: Mock database.
        """
        all_databases: Any = {
            SupportedResolution.R_1080: mock_database,
            SupportedResolution.R_1440: mock_database,
        }

        visualizer_window.progress_bar.setVisible(True)
        visualizer_window._on_databases_loaded(all_databases)

        # Progress bar should be hidden
        assert not visualizer_window.progress_bar.isVisible()

        # Resolution filter should be populated
        assert visualizer_window.resolution_filter.count() == 2

        # Databases should be stored
        assert visualizer_window.all_databases == all_databases

    def test_on_database_error(self, visualizer_window: DatabaseVisualizerWindow) -> None:
        """Test database error handling.

        Args:
            visualizer_window: Window fixture.
        """
        visualizer_window.progress_bar.setVisible(True)
        visualizer_window._on_database_error("Test error message")

        assert not visualizer_window.progress_bar.isVisible()
        assert "Error" in visualizer_window.results_label.text()
        assert "Test error message" in visualizer_window.results_label.text()


class TestDatabaseVisualizerWindowResolutionChange:
    """Tests for resolution change handling."""

    def test_on_resolution_changed(
        self,
        visualizer_window: DatabaseVisualizerWindow,
        mock_database: MagicMock,
        mock_template: IconTemplate,
    ) -> None:
        """Test resolution change updates database and filters.

        Args:
            visualizer_window: Window fixture.
            mock_database: Mock database.
            mock_template: Mock template.
        """
        visualizer_window.all_databases = {SupportedResolution.R_1080: mock_database}

        # Add resolution to filter
        visualizer_window.resolution_filter.clear()
        visualizer_window.resolution_filter.addItem("1080p", SupportedResolution.R_1080)
        visualizer_window.resolution_filter.setCurrentIndex(0)

        # Trigger resolution change
        visualizer_window._on_resolution_changed()

        assert visualizer_window.current_resolution == SupportedResolution.R_1080
        assert visualizer_window.database == mock_database
        assert "1080p" in visualizer_window.windowTitle()


class TestDatabaseVisualizerWindowTemplateSelection:
    """Tests for template selection."""

    def test_update_template_list(
        self,
        visualizer_window: DatabaseVisualizerWindow,
        mock_template: IconTemplate,
        mock_crated_template: IconTemplate,
    ) -> None:
        """Test template list update.

        Args:
            visualizer_window: Window fixture.
            mock_template: Mock template.
            mock_crated_template: Mock crated template.
        """
        visualizer_window.all_templates = [(0, mock_template), (1, mock_crated_template)]
        visualizer_window.filtered_templates = [(0, mock_template), (1, mock_crated_template)]

        visualizer_window._update_template_list()

        assert visualizer_window.template_list.count() == 2
        assert "Showing 2 of 2" in visualizer_window.results_label.text()

    def test_on_template_selected(
        self,
        visualizer_window: DatabaseVisualizerWindow,
        mock_template: IconTemplate,
        mock_database: MagicMock,
    ) -> None:
        """Test template selection updates info label.

        Args:
            visualizer_window: Window fixture.
            mock_template: Mock template.
            mock_database: Mock database.
        """
        visualizer_window.all_databases = {SupportedResolution.R_1080: mock_database}

        # Create list item with template data
        item = QListWidgetItem("TestItem")
        item.setData(Qt.ItemDataRole.UserRole, (0, mock_template))

        visualizer_window._on_template_selected(item)

        # Info label should contain template details
        info_text = visualizer_window.info_label.text()
        assert "TestItem" in info_text
        assert "neutral" in info_text
        assert "vanilla" in info_text


class TestDatabaseVisualizerWindowFiltersAdvanced:
    """Additional tests for filter edge cases."""

    def test_apply_filters_category_filter(
        self,
        visualizer_window: DatabaseVisualizerWindow,
        mock_template: IconTemplate,
        mock_crated_template: IconTemplate,
    ) -> None:
        """Test category filter functionality.

        Args:
            visualizer_window: Window fixture.
            mock_template: Mock template (Item category).
            mock_crated_template: Mock crated template (Vehicle category).
        """
        visualizer_window.database = MagicMock()
        visualizer_window.all_templates = [(0, mock_template), (1, mock_crated_template)]

        # Filter by Vehicle category
        visualizer_window.category_filter.setCurrentIndex(
            visualizer_window.category_filter.findData(ItemCategory.Vehicle)
        )
        visualizer_window._apply_filters()

        # Only crated template (Vehicle) should match
        assert len(visualizer_window.filtered_templates) == 1
        assert visualizer_window.filtered_templates[0][1].category == ItemCategory.Vehicle

    def test_apply_filters_mod_filter(
        self,
        visualizer_window: DatabaseVisualizerWindow,
        mock_template: IconTemplate,
        mock_crated_template: IconTemplate,
    ) -> None:
        """Test mod filter functionality.

        Args:
            visualizer_window: Window fixture.
            mock_template: Mock template (vanilla mod).
            mock_crated_template: Mock crated template (testmod mod).
        """
        visualizer_window.database = MagicMock()
        visualizer_window.all_templates = [(0, mock_template), (1, mock_crated_template)]

        # Add mods to filter
        visualizer_window.mod_filter.clear()
        visualizer_window.mod_filter.addItem("All", "")
        visualizer_window.mod_filter.addItem("vanilla", "vanilla")
        visualizer_window.mod_filter.addItem("testmod", "testmod")

        # Filter by testmod
        visualizer_window.mod_filter.setCurrentIndex(
            visualizer_window.mod_filter.findData("testmod")
        )
        visualizer_window._apply_filters()

        # Only crated template (testmod) should match
        assert len(visualizer_window.filtered_templates) == 1
        assert visualizer_window.filtered_templates[0][1].mod == "testmod"

    def test_on_resolution_changed_restores_mod_selection(
        self,
        visualizer_window: DatabaseVisualizerWindow,
        mock_database: MagicMock,
        mock_template: IconTemplate,
    ) -> None:
        """Test resolution change restores mod selection if available.

        Args:
            visualizer_window: Window fixture.
            mock_database: Mock database.
            mock_template: Mock template.
        """
        visualizer_window.all_databases = {SupportedResolution.R_1080: mock_database}

        # Set up mod filter with a selection
        visualizer_window.mod_filter.clear()
        visualizer_window.mod_filter.addItem("All", "")
        visualizer_window.mod_filter.addItem("vanilla", "vanilla")
        visualizer_window.mod_filter.setCurrentIndex(1)  # Select "vanilla"

        # Add resolution to filter
        visualizer_window.resolution_filter.clear()
        visualizer_window.resolution_filter.addItem("1080p", SupportedResolution.R_1080)
        visualizer_window.resolution_filter.setCurrentIndex(0)

        # Trigger resolution change - should restore mod selection
        visualizer_window._on_resolution_changed()

        # Mod filter should have "vanilla" selected if it exists
        assert visualizer_window.mod_filter.currentData() == "vanilla"


class TestDatabaseVisualizerWindowTemplateSelectionAdvanced:
    """Additional tests for template selection edge cases."""

    def test_on_template_selected_highest_not_found(
        self,
        visualizer_window: DatabaseVisualizerWindow,
        mock_template: IconTemplate,
    ) -> None:
        """Test template selection when highest resolution template not found.

        Args:
            visualizer_window: Window fixture.
            mock_template: Mock template.
        """
        # Create a database with different template (won't match)
        different_template = IconTemplate(
            code="DifferentItem",
            faction=ItemFaction.WARDENS,
            category=ItemCategory.Shippable,
            mod="othermod",
            crated=True,
            resolution=SupportedResolution.R_1080,
            image=np.zeros((32, 32, 3), dtype=np.uint8),
            phash=0,
        )
        mock_db = MagicMock(spec=TemplateDatabase)
        mock_db.templates = [different_template]

        visualizer_window.all_databases = {SupportedResolution.R_1080: mock_db}

        # Create list item with template data
        item = QListWidgetItem("TestItem")
        item.setData(Qt.ItemDataRole.UserRole, (0, mock_template))

        visualizer_window._on_template_selected(item)

        # Info label should indicate highest resolution not found
        info_text = visualizer_window.info_label.text()
        assert "Not found" in info_text


class TestDatabaseVisualizerWindowImageDisplay:
    """Tests for image display functionality."""

    def test_display_comparison_images_no_template(
        self, visualizer_window: DatabaseVisualizerWindow
    ) -> None:
        """Test display does nothing with no template.

        Args:
            visualizer_window: Window fixture.
        """
        visualizer_window._display_comparison_images(None, None)
        # Should not raise

    def test_display_comparison_images_with_template(
        self,
        visualizer_window: DatabaseVisualizerWindow,
        mock_template: IconTemplate,
    ) -> None:
        """Test display with template shows image.

        Args:
            visualizer_window: Window fixture.
            mock_template: Mock template.
        """
        # Create a non-zero image for display
        mock_template.image = np.ones((32, 32, 3), dtype=np.uint8) * 128

        visualizer_window._display_comparison_images(mock_template, None)

        # Current image should have a pixmap
        assert not visualizer_window.current_image.pixmap().isNull()

        # Highest should show not found text
        assert "not found" in visualizer_window.highest_image.text().lower()

    def test_display_comparison_images_with_both(
        self,
        visualizer_window: DatabaseVisualizerWindow,
        mock_template: IconTemplate,
    ) -> None:
        """Test display with both templates shows comparison.

        Args:
            visualizer_window: Window fixture.
            mock_template: Mock template.
        """
        # Create images
        mock_template.image = np.ones((32, 32, 3), dtype=np.uint8) * 128

        highest_template = IconTemplate(
            code="TestItem",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            mod="vanilla",
            crated=False,
            resolution=SupportedResolution.R_1440,
            image=np.ones((48, 48, 3), dtype=np.uint8) * 200,
            phash=0,
        )

        visualizer_window._display_comparison_images(mock_template, highest_template)

        # Both images should have pixmaps
        assert not visualizer_window.current_image.pixmap().isNull()
        assert not visualizer_window.highest_image.pixmap().isNull()


class TestDatabaseVisualizerWindowCloseEvent:
    """Tests for window close event."""

    def test_close_event_waits_for_thread(
        self, visualizer_window: DatabaseVisualizerWindow
    ) -> None:
        """Test close event waits for loader thread.

        Args:
            visualizer_window: Window fixture.
        """
        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = True
        visualizer_window.loader_thread = mock_thread

        mock_event = MagicMock()

        visualizer_window.closeEvent(mock_event)

        mock_thread.wait.assert_called_once()
        mock_event.accept.assert_called_once()

    def test_close_event_no_thread(self, visualizer_window: DatabaseVisualizerWindow) -> None:
        """Test close event with no loader thread.

        Args:
            visualizer_window: Window fixture.
        """
        visualizer_window.loader_thread = None

        mock_event = MagicMock()

        visualizer_window.closeEvent(mock_event)

        mock_event.accept.assert_called_once()

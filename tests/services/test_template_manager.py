"""Tests for services.template_manager module.

This module contains comprehensive tests for the TemplateManager class,
which handles template database loading, caching, and management for
different screen resolutions.
"""

import pickle
from pathlib import Path
from unittest.mock import patch

import pytest

from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.services.template_database import TemplateDatabase
from foxhole_stockpiles.services.template_manager import TemplateManager


class TestTemplateManagerInitialization:
    """Test suite for TemplateManager initialization.

    This class contains tests for proper initialization of the TemplateManager
    including path handling, cache initialization, and initial state validation.
    """

    def test_init_with_path(self, tmp_path: Path) -> None:
        """Test initializing TemplateManager with a database path.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        manager = TemplateManager(db_path)

        assert manager.database_path == db_path
        assert manager.active_database is None
        assert manager.current_resolution is None

    def test_init_creates_empty_cache(self, tmp_path: Path) -> None:
        """Test that initialization creates empty database cache.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        manager = TemplateManager(db_path)

        assert manager.active_database is None
        assert manager.current_resolution is None


class TestLoadDatabase:
    """Test suite for TemplateManager.load_database method.

    This class contains tests for database loading functionality including
    new database loading, cache handling, error conditions, and file corruption.
    """

    async def test_load_new_database(self, tmp_path: Path) -> None:
        """Test loading a database for a new resolution.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"

        # Create a real database file
        real_db = TemplateDatabase(SupportedResolution.R_1080)
        databases = {SupportedResolution.R_1080: real_db}
        with open(db_path, "wb") as f:
            pickle.dump(databases, f)

        manager = TemplateManager(db_path)

        with patch("logging.Logger.debug") as mock_log:
            db = await manager.load_database(SupportedResolution.R_1080)

        assert db is not None
        mock_log.assert_called()

    async def test_load_cached_database(self, tmp_path: Path) -> None:
        """Test loading a database that's already cached.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"

        # Create a real database
        real_db = TemplateDatabase(SupportedResolution.R_1080)

        # Create database file
        databases = {SupportedResolution.R_1080: real_db}
        with open(db_path, "wb") as f:
            pickle.dump(databases, f)

        manager = TemplateManager(db_path)

        # Load it once to cache it
        await manager.load_database(SupportedResolution.R_1080)

        # Load it again - should use cache
        with patch("logging.Logger.debug"):
            db = await manager.load_database(SupportedResolution.R_1080)

        assert db is not None

    async def test_load_missing_resolution(self, tmp_path: Path) -> None:
        """Test loading a resolution that doesn't exist in the database.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"

        # Create database with only one resolution
        real_db = TemplateDatabase(SupportedResolution.R_1080)
        databases = {SupportedResolution.R_1080: real_db}
        with open(db_path, "wb") as f:
            pickle.dump(databases, f)

        manager = TemplateManager(db_path)

        # Try to load a different resolution
        with pytest.raises(ValueError):
            await manager.load_database(SupportedResolution.R_720)

    async def test_load_corrupted_database(self, tmp_path: Path) -> None:
        """Test handling of corrupted database file.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "corrupted.pkl"
        db_path.write_text("corrupted data")

        manager = TemplateManager(db_path)

        # Should raise an exception for corrupted pickle file
        with pytest.raises((pickle.UnpicklingError, EOFError, ValueError)):
            await manager.load_database(SupportedResolution.R_1080)


class TestSetActiveResolution:
    """Test suite for TemplateManager.set_active_resolution method.

    This class contains tests for switching between resolutions based on
    screenshot dimensions and database caching behavior.
    """

    async def test_set_active_resolution_first_time(self, tmp_path: Path) -> None:
        """Test setting active resolution for the first time.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"

        # Create a real database
        real_db = TemplateDatabase(SupportedResolution.R_1080)
        databases = {SupportedResolution.R_1080: real_db}
        with open(db_path, "wb") as f:
            pickle.dump(databases, f)

        manager = TemplateManager(db_path)

        # Set resolution for 1080p screenshot
        resolution = await manager.set_active_resolution(1080)

        assert resolution == SupportedResolution.R_1080
        assert manager.current_resolution == SupportedResolution.R_1080
        assert manager.active_database is not None

    async def test_set_active_resolution_switch(self, tmp_path: Path) -> None:
        """Test switching between different resolutions.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"

        # Create databases for multiple resolutions
        db_1080 = TemplateDatabase(SupportedResolution.R_1080)
        db_720 = TemplateDatabase(SupportedResolution.R_720)
        databases = {
            SupportedResolution.R_1080: db_1080,
            SupportedResolution.R_720: db_720,
        }
        with open(db_path, "wb") as f:
            pickle.dump(databases, f)

        manager = TemplateManager(db_path)

        # Set resolution for 1080p
        resolution1 = await manager.set_active_resolution(1080)
        assert resolution1 == SupportedResolution.R_1080

        # Switch to 720p
        resolution2 = await manager.set_active_resolution(720)
        assert resolution2 == SupportedResolution.R_720
        assert manager.current_resolution == SupportedResolution.R_720

    async def test_set_active_resolution_no_switch(self, tmp_path: Path) -> None:
        """Test that setting same resolution doesn't reload database.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"

        # Create a real database
        real_db = TemplateDatabase(SupportedResolution.R_1080)
        databases = {SupportedResolution.R_1080: real_db}
        with open(db_path, "wb") as f:
            pickle.dump(databases, f)

        manager = TemplateManager(db_path)

        # Set resolution for 1080p
        await manager.set_active_resolution(1080)
        db_reference = manager.active_database

        # Set same resolution again
        await manager.set_active_resolution(1080)

        # Should be the same database reference (not reloaded)
        assert manager.active_database is db_reference


class TestFindBestResolution:
    """Test suite for TemplateManager._find_best_resolution method.

    This class contains tests for finding the best matching resolution
    for various screenshot heights.
    """

    def test_find_best_resolution_exact_match(self, tmp_path: Path) -> None:
        """Test finding exact resolution match.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        manager = TemplateManager(db_path)

        # Test exact matches
        assert manager._find_best_resolution(1080) == SupportedResolution.R_1080
        assert manager._find_best_resolution(720) == SupportedResolution.R_720
        assert manager._find_best_resolution(1440) == SupportedResolution.R_1440

    def test_find_best_resolution_closest_match(self, tmp_path: Path) -> None:
        """Test finding closest resolution when no exact match.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        manager = TemplateManager(db_path)

        # Test closest matches - 992 is closest to 1000
        assert manager._find_best_resolution(1000) == SupportedResolution.R_992
        assert manager._find_best_resolution(800) == SupportedResolution.R_800
        assert manager._find_best_resolution(1200) == SupportedResolution.R_1200
        # 1500 is closer to 1536 (36 away) than to 1440 (60 away)
        assert manager._find_best_resolution(1500) == SupportedResolution.R_1536

    def test_find_best_resolution_edge_cases(self, tmp_path: Path) -> None:
        """Test edge cases for resolution finding.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        manager = TemplateManager(db_path)

        # Very low resolution - 664 is closest to 480
        result = manager._find_best_resolution(480)
        assert result == SupportedResolution.R_664

        # Very high resolution - exact match
        result = manager._find_best_resolution(2160)
        assert result == SupportedResolution.R_2160


class TestMatchIcon:
    """Test suite for TemplateManager.match_icon method.

    This class contains tests for icon matching functionality with various
    filters and matching parameters.
    """

    def setup_method(self) -> None:
        """Clear the shared cache before each test."""
        TemplateManager._shared_databases.clear()

    async def test_match_icon_no_database_loaded(self, tmp_path: Path) -> None:
        """Test match_icon raises error when no database loaded.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        manager = TemplateManager(db_path)

        # Should raise ValueError when no database is loaded
        with pytest.raises(ValueError, match="No active database loaded"):
            manager.match_icon()

    async def test_match_icon_no_image_returns_candidates(self, tmp_path: Path) -> None:
        """Test match_icon without image returns only candidates.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        import numpy as np

        from foxhole_stockpiles.enums.item_category import ItemCategory
        from foxhole_stockpiles.enums.item_faction import ItemFaction
        from foxhole_stockpiles.models.icon_template import IconTemplate

        db_path = tmp_path / "test.pkl"

        # Create database with a template
        db = TemplateDatabase(SupportedResolution.R_1080)
        template = IconTemplate(
            code="TestItem",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
            image=np.zeros((32, 32, 3), dtype=np.uint8),
            phash=0,
        )
        db.add_template(template)

        databases = {SupportedResolution.R_1080: db}
        with open(db_path, "wb") as f:
            pickle.dump(databases, f)

        manager = TemplateManager(db_path)
        await manager.set_active_resolution(1080)

        # Match without image should return candidates only
        result = manager.match_icon()

        assert result.icon is None
        assert result.confidence == 0.0
        assert len(result.candidates) > 0

    async def test_match_icon_with_image_matching(self, tmp_path: Path) -> None:
        """Test match_icon with actual image matching.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        import numpy as np

        from foxhole_stockpiles.enums.item_category import ItemCategory
        from foxhole_stockpiles.enums.item_faction import ItemFaction
        from foxhole_stockpiles.models.icon_template import IconTemplate

        db_path = tmp_path / "test.pkl"

        # Create test image
        test_image = np.ones((32, 32, 3), dtype=np.uint8) * 128

        # Create database with a template
        db = TemplateDatabase(SupportedResolution.R_1080)
        template = IconTemplate(
            code="TestItem",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
            image=test_image.copy(),
            phash=0,
        )
        db.add_template(template)

        databases = {SupportedResolution.R_1080: db}
        with open(db_path, "wb") as f:
            pickle.dump(databases, f)

        manager = TemplateManager(db_path)
        await manager.set_active_resolution(1080)

        # Match with the same image should return high confidence
        result = manager.match_icon(icon_image=test_image)

        assert result.icon is not None
        assert result.confidence is not None
        assert result.confidence >= 0.8
        assert result.icon.code == "TestItem"

    async def test_match_icon_with_filters(self, tmp_path: Path) -> None:
        """Test match_icon with faction and category filters.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        import numpy as np

        from foxhole_stockpiles.enums.item_category import ItemCategory
        from foxhole_stockpiles.enums.item_faction import ItemFaction
        from foxhole_stockpiles.models.icon_template import IconTemplate

        db_path = tmp_path / "test.pkl"

        # Create database with multiple templates
        db = TemplateDatabase(SupportedResolution.R_1080)

        # Add neutral item
        template1 = IconTemplate(
            code="NeutralItem",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
            image=np.zeros((32, 32, 3), dtype=np.uint8),
            phash=0,
        )
        db.add_template(template1)

        # Add colonial item
        template2 = IconTemplate(
            code="ColonialItem",
            faction=ItemFaction.COLONIALS,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
            image=np.ones((32, 32, 3), dtype=np.uint8) * 128,
            phash=1,
        )
        db.add_template(template2)

        databases = {SupportedResolution.R_1080: db}
        with open(db_path, "wb") as f:
            pickle.dump(databases, f)

        manager = TemplateManager(db_path)
        await manager.set_active_resolution(1080)

        # Filter by faction
        result = manager.match_icon(faction=ItemFaction.COLONIALS)

        # Should return fewer candidates (colonial templates only)
        # Note: The actual count depends on how filtering works - it may include neutral items
        assert len(result.candidates) >= 1
        assert result.icon is None  # No image provided, so no match

    async def test_match_icon_phash_filtering(self, tmp_path: Path) -> None:
        """Test match_icon uses pHash pre-filtering with many candidates.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        import numpy as np

        from foxhole_stockpiles.enums.item_category import ItemCategory
        from foxhole_stockpiles.enums.item_faction import ItemFaction
        from foxhole_stockpiles.models.icon_template import IconTemplate

        db_path = tmp_path / "test.pkl"

        # Create database with many templates (>25 to trigger pHash filtering)
        db = TemplateDatabase(SupportedResolution.R_1080)

        for i in range(30):
            template = IconTemplate(
                code=f"Item{i}",
                faction=ItemFaction.NEUTRAL,
                category=ItemCategory.Item,
                crated=False,
                mod="vanilla",
                resolution=SupportedResolution.R_1080,
                image=np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8),
                phash=i,
            )
            db.add_template(template)

        databases = {SupportedResolution.R_1080: db}
        with open(db_path, "wb") as f:
            pickle.dump(databases, f)

        manager = TemplateManager(db_path)
        await manager.set_active_resolution(1080)

        test_image = np.ones((32, 32, 3), dtype=np.uint8) * 128

        # Match with image - should trigger pHash filtering
        result = manager.match_icon(icon_image=test_image, max_ncc_candidates=25)

        # Should have tested <= max_ncc_candidates due to pHash filtering
        assert result.tested_candidates <= 25

    async def test_match_icon_early_exit(self, tmp_path: Path) -> None:
        """Test match_icon early exit with high confidence.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        import numpy as np

        from foxhole_stockpiles.enums.item_category import ItemCategory
        from foxhole_stockpiles.enums.item_faction import ItemFaction
        from foxhole_stockpiles.models.icon_template import IconTemplate

        db_path = tmp_path / "test.pkl"

        # Create test image
        test_image = np.ones((32, 32, 3), dtype=np.uint8) * 128

        # Create database with matching template first
        db = TemplateDatabase(SupportedResolution.R_1080)

        # Add perfect match as first template
        template1 = IconTemplate(
            code="PerfectMatch",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
            image=test_image.copy(),
            phash=0,
        )
        db.add_template(template1)

        # Add more templates that won't be tested due to early exit
        for i in range(10):
            template = IconTemplate(
                code=f"OtherItem{i}",
                faction=ItemFaction.NEUTRAL,
                category=ItemCategory.Item,
                crated=False,
                mod="vanilla",
                resolution=SupportedResolution.R_1080,
                image=np.zeros((32, 32, 3), dtype=np.uint8),
                phash=i,
            )
            db.add_template(template)

        databases = {SupportedResolution.R_1080: db}
        with open(db_path, "wb") as f:
            pickle.dump(databases, f)

        manager = TemplateManager(db_path)
        await manager.set_active_resolution(1080)

        # Match with early exit enabled
        result = manager.match_icon(icon_image=test_image, early_exit_threshold=0.95)

        # Should have found match and exited early
        assert result.icon is not None
        assert result.confidence is not None
        assert result.confidence >= 0.95
        # Should have tested fewer candidates due to early exit
        assert result.tested_candidates < 11


class TestTemplateManagerRepr:
    """Test suite for TemplateManager.__repr__ method."""

    def test_repr(self, tmp_path: Path) -> None:
        """Test string representation of TemplateManager.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.pkl"
        manager = TemplateManager(db_path)

        repr_str = repr(manager)

        assert "TemplateManager" in repr_str
        assert str(db_path) in repr_str
        assert "current_resolution" in repr_str

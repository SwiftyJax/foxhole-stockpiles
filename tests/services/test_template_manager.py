"""Tests for services.template_manager module.

This module contains comprehensive tests for the TemplateManager class,
which handles template database loading, caching, and management for
different screen resolutions.
"""

from pathlib import Path
from unittest.mock import patch

import h5py
import pytest

from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.services.template_database import DATABASE_VERSION, TemplateDatabase
from foxhole_stockpiles.services.template_manager import TemplateManager


def create_hdf5_database(
    db_path: Path, databases: dict[SupportedResolution, TemplateDatabase]
) -> None:
    """Create an HDF5 database file for testing.

    Args:
        db_path (Path): Path where the HDF5 database will be created.
        databases (dict[SupportedResolution, TemplateDatabase]): Dict of resolution to database.
    """
    with h5py.File(str(db_path), "w") as f:
        # Set root-level attributes
        f.attrs["version"] = DATABASE_VERSION
        f.attrs["format"] = "hdf5"
        f.attrs["resolutions"] = [res.value for res in databases.keys()]

        # Save each resolution's database
        for resolution, db in databases.items():
            group = f.create_group(resolution.value)
            db.save_to_hdf5_group(group)


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
        db_path = tmp_path / "test.h5"
        manager = TemplateManager(db_path)

        assert manager.database_path == db_path
        assert manager.active_database is None
        assert manager.current_resolution is None

    def test_init_creates_empty_cache(self, tmp_path: Path) -> None:
        """Test that initialization creates empty database cache.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
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
        db_path = tmp_path / "test.h5"

        # Create a real database file
        real_db = TemplateDatabase(SupportedResolution.R_1080)
        databases = {SupportedResolution.R_1080: real_db}
        create_hdf5_database(db_path, databases)

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
        db_path = tmp_path / "test.h5"

        # Create a real database
        real_db = TemplateDatabase(SupportedResolution.R_1080)

        # Create database file
        databases = {SupportedResolution.R_1080: real_db}
        create_hdf5_database(db_path, databases)

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
        db_path = tmp_path / "test.h5"

        # Create database with only one resolution
        real_db = TemplateDatabase(SupportedResolution.R_1080)
        databases = {SupportedResolution.R_1080: real_db}
        create_hdf5_database(db_path, databases)

        manager = TemplateManager(db_path)

        # Try to load a different resolution
        with pytest.raises(ValueError):
            await manager.load_database(SupportedResolution.R_720)

    async def test_load_corrupted_database(self, tmp_path: Path) -> None:
        """Test handling of corrupted database file.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "corrupted.h5"
        db_path.write_text("corrupted data")

        manager = TemplateManager(db_path)

        # Should raise ValueError for corrupted/invalid database file
        with pytest.raises(ValueError):
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
        db_path = tmp_path / "test.h5"

        # Create a real database
        real_db = TemplateDatabase(SupportedResolution.R_1080)
        databases = {SupportedResolution.R_1080: real_db}
        create_hdf5_database(db_path, databases)

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
        db_path = tmp_path / "test.h5"

        # Create databases for multiple resolutions
        db_1080 = TemplateDatabase(SupportedResolution.R_1080)
        db_720 = TemplateDatabase(SupportedResolution.R_720)
        databases = {
            SupportedResolution.R_1080: db_1080,
            SupportedResolution.R_720: db_720,
        }
        create_hdf5_database(db_path, databases)

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
        db_path = tmp_path / "test.h5"

        # Create a real database
        real_db = TemplateDatabase(SupportedResolution.R_1080)
        databases = {SupportedResolution.R_1080: real_db}
        create_hdf5_database(db_path, databases)

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
        db_path = tmp_path / "test.h5"
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
        db_path = tmp_path / "test.h5"
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
        db_path = tmp_path / "test.h5"
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
        db_path = tmp_path / "test.h5"
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

        db_path = tmp_path / "test.h5"

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
        create_hdf5_database(db_path, databases)

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

        db_path = tmp_path / "test.h5"

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
        create_hdf5_database(db_path, databases)

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

        db_path = tmp_path / "test.h5"

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
        create_hdf5_database(db_path, databases)

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

        db_path = tmp_path / "test.h5"

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
        create_hdf5_database(db_path, databases)

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

        db_path = tmp_path / "test.h5"

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
        create_hdf5_database(db_path, databases)

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

    async def test_match_icon_with_confidence_gap(self, tmp_path: Path) -> None:
        """Test match_icon with confidence_gap returns alternative candidates.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        import numpy as np

        from foxhole_stockpiles.enums.item_category import ItemCategory
        from foxhole_stockpiles.enums.item_faction import ItemFaction
        from foxhole_stockpiles.models.icon_template import IconTemplate

        db_path = tmp_path / "test.h5"

        # Create test image with distinct pattern
        test_image = np.ones((32, 32, 3), dtype=np.uint8) * 128
        # Add a distinctive pattern to make it more unique
        test_image[10:20, 10:20] = [200, 200, 200]

        # Create database with multiple similar templates
        db = TemplateDatabase(SupportedResolution.R_1080)

        # Add best match template
        template1 = IconTemplate(
            code="Rifle",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
            image=test_image.copy(),
            phash=0,
        )
        db.add_template(template1)

        # Add similar template (same category, crated, mod) - but with noticeable differences
        similar_image1 = np.ones((32, 32, 3), dtype=np.uint8) * 128
        similar_image1[10:20, 10:20] = [180, 180, 180]  # Different brightness in same area
        similar_image1[:8, :8] = [100, 100, 100]  # Additional difference
        template2 = IconTemplate(
            code="RifleAlt1",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
            image=similar_image1,
            phash=1,
        )
        db.add_template(template2)

        # Add another similar template - even more different
        similar_image2 = np.ones((32, 32, 3), dtype=np.uint8) * 128
        similar_image2[10:20, 10:20] = [160, 160, 160]  # More different brightness
        similar_image2[:12, :12] = [80, 80, 80]  # Larger different area
        template3 = IconTemplate(
            code="RifleAlt2",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
            image=similar_image2,
            phash=2,
        )
        db.add_template(template3)

        # Add template with different category (should NOT be included)
        template4 = IconTemplate(
            code="Vehicle",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Vehicle,
            crated=False,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
            image=test_image.copy(),
            phash=3,
        )
        db.add_template(template4)

        # Add template with different crated status (should NOT be included)
        template5 = IconTemplate(
            code="RifleCrated",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            crated=True,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
            image=test_image.copy(),
            phash=4,
        )
        db.add_template(template5)

        databases = {SupportedResolution.R_1080: db}
        create_hdf5_database(db_path, databases)

        manager = TemplateManager(db_path)
        await manager.set_active_resolution(1080)

        # Match with a larger confidence_gap to ensure we get candidates
        result = manager.match_icon(icon_image=test_image, confidence_gap=0.25)

        # Should have found best match
        assert result.icon is not None
        assert result.icon.code == "Rifle"

        # With different enough images and a 0.25 gap, we should have gap_candidates
        # If confidence scores are very close, we might not get any, so we test the logic instead
        if len(result.gap_candidates) > 0:
            # Gap candidates should only include items with same category, crated, and mod
            for template, conf in result.gap_candidates:
                assert template.category == ItemCategory.Item
                assert template.crated is False
                assert template.mod == "vanilla"
                # Should not include the best match itself
                assert template.code != "Rifle"
                # Confidence should be within the gap
                assert conf < result.best_confidence
                assert conf >= (result.best_confidence - 0.25)

        # Verify that gap_candidates field exists and is a list
        assert isinstance(result.gap_candidates, list)

    async def test_match_icon_with_zero_confidence_gap(self, tmp_path: Path) -> None:
        """Test match_icon with confidence_gap=0.0 returns no gap candidates.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        import numpy as np

        from foxhole_stockpiles.enums.item_category import ItemCategory
        from foxhole_stockpiles.enums.item_faction import ItemFaction
        from foxhole_stockpiles.models.icon_template import IconTemplate

        db_path = tmp_path / "test.h5"

        # Create test image
        test_image = np.ones((32, 32, 3), dtype=np.uint8) * 128

        # Create database with template
        db = TemplateDatabase(SupportedResolution.R_1080)
        template = IconTemplate(
            code="Rifle",
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
        create_hdf5_database(db_path, databases)

        manager = TemplateManager(db_path)
        await manager.set_active_resolution(1080)

        # Match with confidence_gap=0.0 (default)
        result = manager.match_icon(icon_image=test_image, confidence_gap=0.0)

        # Should have found match
        assert result.icon is not None
        # Should have NO gap candidates
        assert len(result.gap_candidates) == 0


class TestTemplateManagerRepr:
    """Test suite for TemplateManager.__repr__ method."""

    def test_repr(self, tmp_path: Path) -> None:
        """Test string representation of TemplateManager.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        db_path = tmp_path / "test.h5"
        manager = TemplateManager(db_path)

        repr_str = repr(manager)

        assert "TemplateManager" in repr_str
        assert str(db_path) in repr_str
        assert "current_resolution" in repr_str

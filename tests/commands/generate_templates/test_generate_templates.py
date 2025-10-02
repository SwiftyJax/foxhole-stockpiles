"""Tests for commands.generate_templates.generate_templates module.

This module contains comprehensive tests for the template generator command,
including TemplateGenerator class functionality, image processing, and
template generation for multiple resolutions.
"""

import argparse
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest
from numpy.typing import NDArray

from foxhole_stockpiles.commands.generate_templates.generate_templates import (
    TemplateGenerator,
    main,
)
from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.catalog_item import CatalogItem


class TestTemplateGeneratorInitialization:
    """Test suite for TemplateGenerator initialization.

    This class contains tests for TemplateGenerator instance creation
    with various parameter combinations and configurations.
    """

    async def test_initialization_with_valid_paths(
        self, tmp_path: Path, mock_catalog_file: Path
    ) -> None:
        """Test TemplateGenerator initialization with valid paths.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_catalog_file (Path): Mock catalog file from fixture.
        """
        assets_path = tmp_path / "assets"
        assets_path.mkdir()

        # Create mod folder
        (assets_path / "vanilla").mkdir()

        template_path = tmp_path / "templates"

        generator = TemplateGenerator(
            catalog_path=mock_catalog_file,
            assets_path=assets_path,
            template_path=template_path,
            filter_name=None,
        )

        assert generator.assets_path == assets_path
        assert generator.template_path == template_path
        assert generator.filter_name is None
        assert len(generator.catalog_data) > 0
        assert generator.template_path.exists()

    async def test_initialization_with_filter(
        self, tmp_path: Path, mock_catalog_file: Path
    ) -> None:
        """Test TemplateGenerator initialization with filter.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_catalog_file (Path): Mock catalog file from fixture.
        """
        assets_path = tmp_path / "assets"
        assets_path.mkdir()
        (assets_path / "vanilla").mkdir()

        template_path = tmp_path / "templates"

        generator = TemplateGenerator(
            catalog_path=mock_catalog_file,
            assets_path=assets_path,
            template_path=template_path,
            filter_name="Rifle",
        )

        assert generator.filter_name == "Rifle"

    async def test_initialization_catalog_not_found(self, tmp_path: Path) -> None:
        """Test TemplateGenerator initialization with missing catalog.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        catalog_path = tmp_path / "nonexistent.json"
        assets_path = tmp_path / "assets"
        assets_path.mkdir()
        template_path = tmp_path / "templates"

        with pytest.raises(FileNotFoundError, match="Catalog file not found"):
            TemplateGenerator(
                catalog_path=catalog_path,
                assets_path=assets_path,
                template_path=template_path,
            )

    async def test_initialization_assets_not_found(
        self, tmp_path: Path, mock_catalog_file: Path
    ) -> None:
        """Test TemplateGenerator initialization with missing assets.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_catalog_file (Path): Mock catalog file from fixture.
        """
        assets_path = tmp_path / "nonexistent_assets"
        template_path = tmp_path / "templates"

        with pytest.raises(FileNotFoundError, match="Assets directory not found"):
            TemplateGenerator(
                catalog_path=mock_catalog_file,
                assets_path=assets_path,
                template_path=template_path,
            )


class TestTemplateGeneratorMethods:
    """Test suite for TemplateGenerator methods.

    This class contains tests for the core functionality of TemplateGenerator
    including image loading, icon processing, and template generation.
    """

    @pytest.fixture
    def generator(self, tmp_path: Path, mock_catalog_file: Path) -> TemplateGenerator:
        """Create a TemplateGenerator instance for testing.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_catalog_file (Path): Mock catalog file from fixture.

        Returns:
            TemplateGenerator: Configured generator instance for testing.
        """
        assets_path = tmp_path / "assets"
        assets_path.mkdir()
        (assets_path / "vanilla").mkdir()

        template_path = tmp_path / "templates"

        return TemplateGenerator(
            catalog_path=mock_catalog_file,
            assets_path=assets_path,
            template_path=template_path,
        )

    async def test_discover_mods(self, tmp_path: Path, mock_catalog_file: Path) -> None:
        """Test mod discovery in assets directory.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_catalog_file (Path): Mock catalog file from fixture.
        """
        assets_path = tmp_path / "assets"
        assets_path.mkdir()

        # Create multiple mod folders
        (assets_path / "vanilla").mkdir()
        (assets_path / "mod1").mkdir()
        (assets_path / "mod2").mkdir()

        template_path = tmp_path / "templates"

        generator = TemplateGenerator(
            catalog_path=mock_catalog_file,
            assets_path=assets_path,
            template_path=template_path,
        )

        # Vanilla should be first
        assert generator.available_mods[0] == "vanilla"
        assert len(generator.available_mods) == 3

    async def test_calculate_icon_size(self, generator: TemplateGenerator, tmp_path: Path) -> None:
        """Test icon size calculation for different resolutions.

        Args:
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        size_1080 = generator._calculate_icon_size(SupportedResolution.R_1080)
        size_2160 = generator._calculate_icon_size(SupportedResolution.R_2160)

        # 1080p should be 32px, 2160p should be 64px
        assert size_1080 == 32
        assert size_2160 == 64

    @patch("cv2.imread")
    async def test_load_icon_image_success(
        self, mock_imread: Mock, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test loading icon image successfully.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Create test icon file
        icon_path = "War/Content/test_icon"
        full_path = generator.assets_path / "vanilla" / f"{icon_path}.png"
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.touch()

        # Mock image loading with BGRA image
        mock_image = np.zeros((64, 64, 4), dtype=np.uint8)
        mock_imread.return_value = mock_image

        result = await generator._load_icon_image(icon_path=icon_path, mod_name="vanilla")

        assert result is not None
        assert result.shape == (64, 64, 4)

    @patch("cv2.imread")
    async def test_load_icon_image_not_found(
        self, mock_imread: Mock, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test loading icon image when file doesn't exist.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        icon_path = "War/Content/nonexistent"

        result = await generator._load_icon_image(icon_path=icon_path, mod_name="vanilla")

        assert result is None

    async def test_filter_catalog_items_with_filter(
        self, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test filtering catalog items by name.

        Args:
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Filter for items containing "Rifle"
        filtered = generator._filter_catalog_items(filter_name="Rifle")

        # Should filter the catalog
        assert isinstance(filtered, list)
        # All filtered items should contain "Rifle" in code
        for item in filtered:
            assert "rifle" in item.code.lower()

    async def test_filter_catalog_items_no_filter(
        self, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test catalog items without filter.

        Args:
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        filtered = generator._filter_catalog_items(filter_name=None)

        # Should return all items
        assert filtered == generator.catalog_data

    async def test_apply_subicon_effects(
        self, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test applying subicon color effects.

        Args:
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Create test image
        test_image = np.ones((32, 32, 4), dtype=np.uint8) * 128

        result = generator._apply_subicon_effects(image=test_image)

        # Result should have same shape
        assert result.shape == test_image.shape
        # Result should be different from input (color tint applied)
        assert not np.array_equal(result[:, :, :3], test_image[:, :, :3])

    @patch("cv2.imread")
    async def test_load_crate_icon_success(
        self, mock_imread: Mock, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test loading crate icon successfully.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Create crate icon file
        crate_path = (
            generator.assets_path / "vanilla" / "War/Content/Textures/UI/Menus/IconFilterCrates.png"
        )
        crate_path.parent.mkdir(parents=True, exist_ok=True)
        crate_path.touch()

        # Mock image loading
        mock_image = np.ones((64, 64, 4), dtype=np.uint8)
        mock_imread.return_value = mock_image

        result = await generator._load_crate_icon()

        assert result is not None
        assert result.shape == (64, 64, 4)

    @patch("cv2.imread")
    async def test_load_crate_icon_not_found(
        self, mock_imread: Mock, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test loading crate icon when not found in any mod.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Don't create the file, so it won't be found
        mock_imread.return_value = None

        with pytest.raises(FileNotFoundError, match="Crate icon not found"):
            await generator._load_crate_icon()

    @patch("cv2.imread")
    async def test_load_icon_image_grayscale(
        self, mock_imread: Mock, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test loading grayscale icon and converting to BGRA.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        icon_path = "War/Content/test_icon"
        full_path = generator.assets_path / "vanilla" / f"{icon_path}.png"
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.touch()

        # Mock grayscale image (2D array)
        mock_image = np.zeros((64, 64), dtype=np.uint8)
        mock_imread.return_value = mock_image

        with patch("cv2.cvtColor") as mock_cvtcolor:
            mock_cvtcolor.return_value = np.zeros((64, 64, 4), dtype=np.uint8)
            result = await generator._load_icon_image(icon_path=icon_path, mod_name="vanilla")

            assert result is not None
            mock_cvtcolor.assert_called_once()

    @patch("cv2.imread")
    async def test_load_icon_image_bgr(
        self, mock_imread: Mock, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test loading BGR icon and converting to BGRA.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        icon_path = "War/Content/test_icon"
        full_path = generator.assets_path / "vanilla" / f"{icon_path}.png"
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.touch()

        # Mock BGR image (3 channels)
        mock_image = np.zeros((64, 64, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image

        with patch("cv2.cvtColor") as mock_cvtcolor:
            mock_cvtcolor.return_value = np.zeros((64, 64, 4), dtype=np.uint8)
            result = await generator._load_icon_image(icon_path=icon_path, mod_name="vanilla")

            assert result is not None
            mock_cvtcolor.assert_called_once()

    @patch("cv2.imread")
    async def test_load_icon_image_imread_returns_none(
        self, mock_imread: Mock, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test loading icon when imread returns None.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        icon_path = "War/Content/test_icon"
        full_path = generator.assets_path / "vanilla" / f"{icon_path}.png"
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.touch()

        # Mock imread returning None (corrupted file)
        mock_imread.return_value = None

        result = await generator._load_icon_image(icon_path=icon_path, mod_name="vanilla")

        assert result is None

    @patch("cv2.imread")
    async def test_load_icon_image_exception(
        self, mock_imread: Mock, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test loading icon when an exception occurs.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        icon_path = "War/Content/test_icon"
        full_path = generator.assets_path / "vanilla" / f"{icon_path}.png"
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.touch()

        # Mock imread raising exception
        mock_imread.side_effect = RuntimeError("Read error")

        result = await generator._load_icon_image(icon_path=icon_path, mod_name="vanilla")

        assert result is None

    async def test_load_subicon_cached_with_cache_hit(
        self, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test loading subicon with cache hit.

        Args:
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        subicon_path = "War/Content/test_subicon"
        mock_subicon = np.ones((32, 32, 4), dtype=np.uint8)

        # Prepopulate cache
        generator.subicon_cache["vanilla:War/Content/test_subicon"] = mock_subicon

        result = await generator._load_subicon_cached(subicon_path=subicon_path, mod_name="vanilla")

        assert result is not None
        assert np.array_equal(result, mock_subicon)

    @patch("cv2.imread")
    async def test_load_subicon_cached_vanilla_fallback(
        self, mock_imread: Mock, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test loading subicon with vanilla fallback.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Create multiple mod folders
        (generator.assets_path / "mod1").mkdir()

        subicon_path = "War/Content/test_subicon"
        vanilla_path = generator.assets_path / "vanilla" / f"{subicon_path}.png"
        vanilla_path.parent.mkdir(parents=True, exist_ok=True)
        vanilla_path.touch()

        # Mock image loading - fails for mod1, succeeds for vanilla
        def imread_side_effect(path: str, flags: int) -> NDArray[np.uint8] | None:
            if "vanilla" in str(path):
                return np.ones((32, 32, 4), dtype=np.uint8)
            return None

        mock_imread.side_effect = imread_side_effect

        result = await generator._load_subicon_cached(subicon_path=subicon_path, mod_name="mod1")

        # Should fallback to vanilla
        assert result is not None
        # Cache should have entries for both mod1 (pointing to vanilla result) and vanilla
        assert "mod1:War/Content/test_subicon" in generator.subicon_cache

    @patch("cv2.imread")
    async def test_load_subicon_cached_not_found_anywhere(
        self, mock_imread: Mock, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test loading subicon when not found anywhere.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        subicon_path = "War/Content/nonexistent"
        mock_imread.return_value = None

        result = await generator._load_subicon_cached(subicon_path=subicon_path, mod_name="vanilla")

        assert result is None
        # Should cache None result
        assert generator.subicon_cache["vanilla:War/Content/nonexistent"] is None

    async def test_add_subicon_bottom_right(
        self, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test adding subicon in bottom-right corner.

        Args:
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        main_icon = np.zeros((64, 64, 4), dtype=np.uint8)
        subicon = np.ones((32, 32, 4), dtype=np.uint8) * 255

        result = generator._add_subicon(
            main_icon=main_icon, subicon=subicon, target_size=64, top_left=False
        )

        assert result.shape == (64, 64, 4)

    async def test_create_base_icon_without_subicon(
        self, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test creating base icon without subicon.

        Args:
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        main_icon = np.ones((32, 32, 4), dtype=np.uint8) * 128

        result = generator._create_base_icon(main_icon=main_icon, subicon=None, target_size=64)

        assert result.shape == (64, 64, 4)

    @patch("cv2.imread")
    async def test_generate_templates_item_missing_code(
        self, mock_imread: Mock, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test generating templates for item with missing code.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Create item with empty code
        catalog_item = CatalogItem(
            code="",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            icon_path="War/Content/test",
            subicon_path="",
        )

        result = await generator._generate_templates_for_item_and_mod(
            item=catalog_item, mod_name="vanilla"
        )

        assert result is False

    @patch("cv2.imread")
    async def test_generate_templates_icon_not_found(
        self, mock_imread: Mock, generator: TemplateGenerator, tmp_path: Path
    ) -> None:
        """Test generating templates when icon not found.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Don't create the icon file
        mock_imread.return_value = None

        catalog_item = CatalogItem(
            code="TestItem",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            icon_path="War/Content/missing",
            subicon_path="",
        )

        result = await generator._generate_templates_for_item_and_mod(
            item=catalog_item, mod_name="vanilla"
        )

        assert result is False

    @patch("cv2.imread")
    @patch("cv2.imwrite")
    async def test_generate_templates_with_subicon(
        self,
        mock_imwrite: Mock,
        mock_imread: Mock,
        generator: TemplateGenerator,
        tmp_path: Path,
    ) -> None:
        """Test generating templates with subicon.

        Args:
            mock_imwrite (Mock): Mocked cv2.imwrite function.
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Create icon and subicon files
        icon_path = "War/Content/test_rifle"
        subicon_path = "War/Content/test_subicon"

        icon_full = generator.assets_path / "vanilla" / f"{icon_path}.png"
        subicon_full = generator.assets_path / "vanilla" / f"{subicon_path}.png"

        icon_full.parent.mkdir(parents=True, exist_ok=True)
        subicon_full.parent.mkdir(parents=True, exist_ok=True)
        icon_full.touch()
        subicon_full.touch()

        generator.crate_icon = np.ones((64, 64, 4), dtype=np.uint8)

        # Mock imread to return different images for icon and subicon
        def imread_side_effect(path: str, flags: int) -> NDArray[np.uint8]:
            if "subicon" in str(path):
                return np.ones((32, 32, 4), dtype=np.uint8) * 200
            return np.ones((64, 64, 4), dtype=np.uint8) * 128

        mock_imread.side_effect = imread_side_effect
        mock_imwrite.return_value = True

        catalog_item = CatalogItem(
            code="TestRifle",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            icon_path=icon_path,
            subicon_path=subicon_path,
        )

        result = await generator._generate_templates_for_item_and_mod(
            item=catalog_item, mod_name="vanilla"
        )

        assert result is True

    @patch("cv2.imread")
    @patch("cv2.imwrite")
    async def test_generate_templates_crate_icon_not_loaded(
        self,
        mock_imwrite: Mock,
        mock_imread: Mock,
        generator: TemplateGenerator,
        tmp_path: Path,
    ) -> None:
        """Test generating templates when crate icon is not loaded.

        Args:
            mock_imwrite (Mock): Mocked cv2.imwrite function.
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        icon_path = "War/Content/test_rifle"
        full_path = generator.assets_path / "vanilla" / f"{icon_path}.png"
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.touch()

        # Don't set crate_icon
        generator.crate_icon = None

        mock_image = np.ones((64, 64, 4), dtype=np.uint8) * 128
        mock_imread.return_value = mock_image
        mock_imwrite.return_value = True

        catalog_item = CatalogItem(
            code="TestRifle",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            icon_path=icon_path,
            subicon_path="",
        )

        result = await generator._generate_templates_for_item_and_mod(
            item=catalog_item, mod_name="vanilla"
        )

        # Should return partial success (True) since normal templates succeed
        # Only crated templates fail, so success_count > 0
        assert result is True

    @patch("cv2.imread")
    @patch("cv2.imwrite")
    async def test_generate_templates_imwrite_exception(
        self,
        mock_imwrite: Mock,
        mock_imread: Mock,
        generator: TemplateGenerator,
        tmp_path: Path,
    ) -> None:
        """Test generating templates when imwrite raises exception.

        Args:
            mock_imwrite (Mock): Mocked cv2.imwrite function.
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        icon_path = "War/Content/test_rifle"
        full_path = generator.assets_path / "vanilla" / f"{icon_path}.png"
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.touch()

        generator.crate_icon = np.ones((64, 64, 4), dtype=np.uint8)
        mock_imread.return_value = np.ones((64, 64, 4), dtype=np.uint8) * 128
        mock_imwrite.side_effect = RuntimeError("Write error")

        catalog_item = CatalogItem(
            code="TestRifle",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            icon_path=icon_path,
            subicon_path="",
        )

        result = await generator._generate_templates_for_item_and_mod(
            item=catalog_item, mod_name="vanilla"
        )

        # Should return False due to errors
        assert result is False

    @patch("cv2.imread")
    @patch("cv2.imwrite")
    async def test_generate_all_templates_success(
        self,
        mock_imwrite: Mock,
        mock_imread: Mock,
        tmp_path: Path,
        mock_catalog_file: Path,
    ) -> None:
        """Test generating all templates successfully.

        Args:
            mock_imwrite (Mock): Mocked cv2.imwrite function.
            mock_imread (Mock): Mocked cv2.imread function.
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_catalog_file (Path): Mock catalog file from fixture.
        """
        # Create a custom catalog with valid items
        import json

        catalog_data = [
            {
                "CodeName": "TestRifle",
                "FactionVariant": "EFactionId::Neutral",
                "Icon": "War/Content/test_rifle",
                "SubTypeIcon": "",
            }
        ]
        catalog_path = tmp_path / "custom_catalog.json"
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        assets_path = tmp_path / "assets"
        assets_path.mkdir()
        (assets_path / "vanilla").mkdir()

        generator = TemplateGenerator(
            catalog_path=catalog_path,
            assets_path=assets_path,
            template_path=tmp_path / "templates",
        )

        # Create necessary icon files
        crate_path = assets_path / "vanilla" / "War/Content/Textures/UI/Menus/IconFilterCrates.png"
        crate_path.parent.mkdir(parents=True, exist_ok=True)
        crate_path.touch()

        icon_path = assets_path / "vanilla" / "War/Content/test_rifle.png"
        icon_path.parent.mkdir(parents=True, exist_ok=True)
        icon_path.touch()

        mock_imread.return_value = np.ones((64, 64, 4), dtype=np.uint8)
        mock_imwrite.return_value = True

        result = await generator.generate_all_templates()

        assert result is True

    async def test_generate_all_templates_no_mods(
        self, tmp_path: Path, mock_catalog_file: Path
    ) -> None:
        """Test generating templates when no mods are found.

        Args:
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_catalog_file (Path): Mock catalog file from fixture.
        """
        assets_path = tmp_path / "empty_assets"
        assets_path.mkdir()

        template_path = tmp_path / "templates"

        generator = TemplateGenerator(
            catalog_path=mock_catalog_file,
            assets_path=assets_path,
            template_path=template_path,
        )

        result = await generator.generate_all_templates()

        assert result is False

    @patch("cv2.imread")
    async def test_generate_all_templates_no_matching_filter(
        self,
        mock_imread: Mock,
        tmp_path: Path,
        mock_catalog_file: Path,
    ) -> None:
        """Test generating templates when filter matches nothing.

        Args:
            mock_imread (Mock): Mocked cv2.imread function.
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_catalog_file (Path): Mock catalog file from fixture.
        """
        assets_path = tmp_path / "assets"
        assets_path.mkdir()
        (assets_path / "vanilla").mkdir()

        template_path = tmp_path / "templates"

        generator = TemplateGenerator(
            catalog_path=mock_catalog_file,
            assets_path=assets_path,
            template_path=template_path,
            filter_name="NonexistentItem",
        )

        # Create crate icon
        crate_path = (
            generator.assets_path / "vanilla" / "War/Content/Textures/UI/Menus/IconFilterCrates.png"
        )
        crate_path.parent.mkdir(parents=True, exist_ok=True)
        crate_path.touch()

        mock_imread.return_value = np.ones((64, 64, 4), dtype=np.uint8)

        result = await generator.generate_all_templates()

        assert result is False

    @patch("cv2.imread")
    @patch("cv2.imwrite")
    async def test_generate_templates_for_item_and_mod(
        self,
        mock_imwrite: Mock,
        mock_imread: Mock,
        generator: TemplateGenerator,
        tmp_path: Path,
    ) -> None:
        """Test generating templates for a single item from a mod.

        Args:
            mock_imwrite (Mock): Mocked cv2.imwrite function.
            mock_imread (Mock): Mocked cv2.imread function.
            generator (TemplateGenerator): TemplateGenerator instance from fixture.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        # Create test icon file
        icon_path = "War/Content/test_rifle"
        full_path = generator.assets_path / "vanilla" / f"{icon_path}.png"
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.touch()

        # Mock crate icon
        generator.crate_icon = np.ones((64, 64, 4), dtype=np.uint8)

        # Mock image loading
        mock_image = np.ones((64, 64, 4), dtype=np.uint8) * 128
        mock_imread.return_value = mock_image
        mock_imwrite.return_value = True

        # Create catalog item
        catalog_item = CatalogItem(
            code="TestRifle",
            faction=ItemFaction.NEUTRAL,
            category=ItemCategory.Item,
            icon_path=icon_path,
            subicon_path="",
        )

        result = await generator._generate_templates_for_item_and_mod(
            item=catalog_item, mod_name="vanilla"
        )

        # Should succeed
        assert result is True

        # Verify output directories were created
        assert (generator.template_path / "TestRifle").exists()
        assert (generator.template_path / "TestRifle_crated").exists()


class TestMainFunction:
    """Test suite for the main CLI function.

    This class contains tests for the main entry point of the generate
    templates command, including argument parsing and workflow execution.
    """

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.generate_templates.generate_templates.TemplateGenerator")
    @patch("foxhole_stockpiles.commands.generate_templates.generate_templates.setup_logging")
    async def test_main_with_default_args(
        self,
        mock_setup_logging: Mock,
        mock_generator_class: Mock,
        mock_args: Mock,
        tmp_path: Path,
        mock_catalog_file: Path,
    ) -> None:
        """Test main function with default arguments.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_generator_class (Mock): Mocked TemplateGenerator class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_catalog_file (Path): Mock catalog file from fixture.
        """
        assets_path = tmp_path / "assets"
        assets_path.mkdir()

        templates_path = tmp_path / "templates"

        mock_args.return_value = argparse.Namespace(
            catalog=mock_catalog_file,
            assets=assets_path,
            templates=templates_path,
            filter=None,
            verbose=False,
            quiet=False,
            log_file=None,
        )

        # Mock generator instance
        mock_generator = MagicMock()
        mock_generator.generate_all_templates = AsyncMock(return_value=True)
        mock_generator_class.return_value = mock_generator

        await main()

        # Verify TemplateGenerator was instantiated
        mock_generator_class.assert_called_once()

        # Verify generate_all_templates was called
        assert mock_generator.generate_all_templates.call_count > 0

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.generate_templates.generate_templates.TemplateGenerator")
    @patch("foxhole_stockpiles.commands.generate_templates.generate_templates.setup_logging")
    async def test_main_with_filter(
        self,
        mock_setup_logging: Mock,
        mock_generator_class: Mock,
        mock_args: Mock,
        tmp_path: Path,
        mock_catalog_file: Path,
    ) -> None:
        """Test main function with filter argument.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_generator_class (Mock): Mocked TemplateGenerator class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_catalog_file (Path): Mock catalog file from fixture.
        """
        assets_path = tmp_path / "assets"
        assets_path.mkdir()

        templates_path = tmp_path / "templates"

        mock_args.return_value = argparse.Namespace(
            catalog=mock_catalog_file,
            assets=assets_path,
            templates=templates_path,
            filter="Rifle",
            verbose=True,
            quiet=False,
            log_file=None,
        )

        # Mock generator instance
        mock_generator = MagicMock()

        async def mock_generate_all() -> bool:
            return True

        mock_generator.generate_all_templates = mock_generate_all
        mock_generator_class.return_value = mock_generator

        await main()

        # Verify TemplateGenerator was called with filter
        call_kwargs = mock_generator_class.call_args[1]
        assert call_kwargs["filter_name"] == "Rifle"

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.generate_templates.generate_templates.setup_logging")
    async def test_main_catalog_not_found(
        self, mock_setup_logging: Mock, mock_args: Mock, tmp_path: Path
    ) -> None:
        """Test main function when catalog file is not found.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
        """
        catalog_path = tmp_path / "nonexistent.json"
        assets_path = tmp_path / "assets"
        assets_path.mkdir()
        templates_path = tmp_path / "templates"

        mock_args.return_value = argparse.Namespace(
            catalog=catalog_path,
            assets=assets_path,
            templates=templates_path,
            filter=None,
            verbose=False,
            quiet=False,
            log_file=None,
        )

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.generate_templates.generate_templates.TemplateGenerator")
    @patch("foxhole_stockpiles.commands.generate_templates.generate_templates.setup_logging")
    async def test_main_generation_failure(
        self,
        mock_setup_logging: Mock,
        mock_generator_class: Mock,
        mock_args: Mock,
        tmp_path: Path,
        mock_catalog_file: Path,
    ) -> None:
        """Test main function when template generation fails.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_generator_class (Mock): Mocked TemplateGenerator class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_catalog_file (Path): Mock catalog file from fixture.
        """
        assets_path = tmp_path / "assets"
        assets_path.mkdir()

        templates_path = tmp_path / "templates"

        mock_args.return_value = argparse.Namespace(
            catalog=mock_catalog_file,
            assets=assets_path,
            templates=templates_path,
            filter=None,
            verbose=False,
            quiet=False,
            log_file=None,
        )

        # Mock generator instance to return failure
        mock_generator = MagicMock()

        async def mock_generate_all() -> bool:
            return False

        mock_generator.generate_all_templates = mock_generate_all
        mock_generator_class.return_value = mock_generator

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.generate_templates.generate_templates.setup_logging")
    async def test_main_assets_not_found(
        self, mock_setup_logging: Mock, mock_args: Mock, tmp_path: Path, mock_catalog_file: Path
    ) -> None:
        """Test main function when assets directory is not found.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_catalog_file (Path): Mock catalog file from fixture.
        """
        assets_path = tmp_path / "nonexistent_assets"
        templates_path = tmp_path / "templates"

        mock_args.return_value = argparse.Namespace(
            catalog=mock_catalog_file,
            assets=assets_path,
            templates=templates_path,
            filter=None,
            verbose=False,
            quiet=False,
            log_file=None,
        )

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.generate_templates.generate_templates.TemplateGenerator")
    @patch("foxhole_stockpiles.commands.generate_templates.generate_templates.setup_logging")
    async def test_main_with_quiet_mode(
        self,
        mock_setup_logging: Mock,
        mock_generator_class: Mock,
        mock_args: Mock,
        tmp_path: Path,
        mock_catalog_file: Path,
    ) -> None:
        """Test main function with quiet mode.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_generator_class (Mock): Mocked TemplateGenerator class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_catalog_file (Path): Mock catalog file from fixture.
        """
        assets_path = tmp_path / "assets"
        assets_path.mkdir()
        templates_path = tmp_path / "templates"

        mock_args.return_value = argparse.Namespace(
            catalog=mock_catalog_file,
            assets=assets_path,
            templates=templates_path,
            filter=None,
            verbose=False,
            quiet=True,
            log_file=None,
        )

        # Mock generator instance
        mock_generator = MagicMock()
        mock_generator.generate_all_templates = AsyncMock(return_value=True)
        mock_generator_class.return_value = mock_generator

        await main()

        # Verify setup_logging was called
        assert mock_setup_logging.call_count > 0

    @patch("argparse.ArgumentParser.parse_args")
    @patch("foxhole_stockpiles.commands.generate_templates.generate_templates.TemplateGenerator")
    @patch("foxhole_stockpiles.commands.generate_templates.generate_templates.setup_logging")
    async def test_main_with_exception(
        self,
        mock_setup_logging: Mock,
        mock_generator_class: Mock,
        mock_args: Mock,
        tmp_path: Path,
        mock_catalog_file: Path,
    ) -> None:
        """Test main function when an exception occurs during generation.

        Args:
            mock_setup_logging (Mock): Mocked setup_logging function.
            mock_generator_class (Mock): Mocked TemplateGenerator class.
            mock_args (Mock): Mocked ArgumentParser.parse_args method.
            tmp_path (Path): Temporary directory path from pytest fixture.
            mock_catalog_file (Path): Mock catalog file from fixture.
        """
        assets_path = tmp_path / "assets"
        assets_path.mkdir()
        templates_path = tmp_path / "templates"

        mock_args.return_value = argparse.Namespace(
            catalog=mock_catalog_file,
            assets=assets_path,
            templates=templates_path,
            filter=None,
            verbose=False,
            quiet=False,
            log_file=None,
        )

        # Mock generator to raise exception
        mock_generator_class.side_effect = RuntimeError("Unexpected error")

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            await main()

        assert exc_info.value.code == 1

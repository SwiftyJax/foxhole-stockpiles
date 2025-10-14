"""Tests for models.icon_template module.

This module contains comprehensive tests for the IconTemplate model,
including template creation, optimization data computation, and string representations.
"""

import numpy as np
import pytest

from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.enums.supported_resolution import SupportedResolution
from foxhole_stockpiles.models.icon_template import IconTemplate


class TestIconTemplateCreation:
    """Test suite for IconTemplate creation and initialization."""

    def test_create_template_with_valid_data(self) -> None:
        """Test creating an IconTemplate with valid data."""
        # Create a simple test image
        image = np.zeros((64, 64, 3), dtype=np.uint8)
        image[10:54, 10:54] = 255  # White square in center

        template = IconTemplate(
            image=image,
            code="TestRifle",
            crated=False,
            category=ItemCategory.Item,
            faction=ItemFaction.NEUTRAL,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        assert template.code == "TestRifle"
        assert template.crated is False
        assert template.category == ItemCategory.Item
        assert template.faction == ItemFaction.NEUTRAL
        assert template.mod == "vanilla"
        assert template.resolution == SupportedResolution.R_1080
        assert template.image.shape == (64, 64, 3)

    def test_create_template_with_crated_variant(self) -> None:
        """Test creating an IconTemplate for a crated item."""
        image = np.zeros((64, 64, 3), dtype=np.uint8)

        template = IconTemplate(
            image=image,
            code="TestRifle",
            crated=True,  # Crated variant
            category=ItemCategory.Item,
            faction=ItemFaction.NEUTRAL,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        assert template.crated is True

    def test_create_template_strips_whitespace(self) -> None:
        """Test that string fields strip whitespace."""
        image = np.zeros((64, 64, 3), dtype=np.uint8)

        template = IconTemplate(
            image=image,
            code="  TestRifle  ",  # Whitespace should be stripped
            crated=False,
            category=ItemCategory.Item,
            faction=ItemFaction.NEUTRAL,
            mod="  vanilla  ",  # Whitespace should be stripped
            resolution=SupportedResolution.R_1080,
        )

        assert template.code == "TestRifle"
        assert template.mod == "vanilla"

    def test_create_template_with_empty_code_raises_error(self) -> None:
        """Test that creating template with empty code raises validation error."""
        image = np.zeros((64, 64, 3), dtype=np.uint8)

        with pytest.raises(ValueError):
            IconTemplate(
                image=image,
                code="",  # Empty code should fail validation
                crated=False,
                category=ItemCategory.Item,
                faction=ItemFaction.NEUTRAL,
                mod="vanilla",
                resolution=SupportedResolution.R_1080,
            )


class TestIconTemplateOptimization:
    """Test suite for IconTemplate optimization data computation."""

    def test_compute_optimization_data_normal_image(self) -> None:
        """Test computing optimization data for normal image."""
        # Create image with variation
        image = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)

        template = IconTemplate(
            image=image,
            code="TestRifle",
            crated=False,
            category=ItemCategory.Item,
            faction=ItemFaction.NEUTRAL,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        # Manually compute optimization data
        template.compute_optimization_data()

        # Verify optimization data was computed
        assert template.template_mean > 0
        assert template.template_std > 0
        assert template.normalized_image.shape == (64, 64)
        assert template.phash != 0

    def test_compute_optimization_data_zero_std_deviation(self) -> None:
        """Test computing optimization data for constant image (zero std deviation)."""
        # Create completely uniform image (all same value)
        image = np.full((64, 64, 3), 128, dtype=np.uint8)

        template = IconTemplate(
            image=image,
            code="TestRifle",
            crated=False,
            category=ItemCategory.Item,
            faction=ItemFaction.NEUTRAL,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        # Manually compute optimization data
        template.compute_optimization_data()

        # Verify optimization data handles zero std deviation
        assert template.template_mean == 128.0
        assert template.template_std == 0.0
        # Normalized image should be zeros for constant image
        assert np.all(template.normalized_image == 0)
        # pHash for completely uniform image will be 0 (all pixels same)
        assert template.phash == 0

    def test_compute_optimization_data_near_zero_std_deviation(self) -> None:
        """Test computing optimization data for near-constant image."""
        # Create nearly uniform image (very small variation)
        image = np.full((64, 64, 3), 128, dtype=np.uint8)
        image[0, 0] = 129  # Single pixel slightly different

        template = IconTemplate(
            image=image,
            code="TestRifle",
            crated=False,
            category=ItemCategory.Item,
            faction=ItemFaction.NEUTRAL,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        # Manually compute optimization data
        template.compute_optimization_data()

        # Verify optimization data handles near-zero std deviation
        assert template.template_mean > 0
        # std should be very small but positive
        assert template.template_std >= 0
        assert template.normalized_image.shape == (64, 64)

    def test_compute_phash_consistency(self) -> None:
        """Test that perceptual hash is consistent for same image."""
        # Create identical images
        image1 = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
        image2 = image1.copy()

        template1 = IconTemplate(
            image=image1,
            code="TestRifle",
            crated=False,
            category=ItemCategory.Item,
            faction=ItemFaction.NEUTRAL,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        template2 = IconTemplate(
            image=image2,
            code="TestRifle",
            crated=False,
            category=ItemCategory.Item,
            faction=ItemFaction.NEUTRAL,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        # pHash should be identical for identical images
        assert template1.phash == template2.phash

    def test_manual_compute_optimization_data(self) -> None:
        """Test manually calling compute_optimization_data method."""
        image = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)

        template = IconTemplate(
            image=image,
            code="TestRifle",
            crated=False,
            category=ItemCategory.Item,
            faction=ItemFaction.NEUTRAL,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        # Compute optimization data first time
        template.compute_optimization_data()
        original_phash = template.phash
        original_mean = template.template_mean

        # Manually call compute_optimization_data again
        template.compute_optimization_data()

        # Should produce same results
        assert template.phash == original_phash
        assert template.template_mean == original_mean


class TestIconTemplateStringRepresentations:
    """Test suite for IconTemplate string representations."""

    def test_str_representation(self) -> None:
        """Test __str__ method returns human-readable representation."""
        image = np.zeros((64, 64, 3), dtype=np.uint8)

        template = IconTemplate(
            image=image,
            code="TestRifle",
            crated=False,
            category=ItemCategory.Item,
            faction=ItemFaction.NEUTRAL,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        str_repr = str(template)

        # Verify string contains key information
        assert "IconTemplate" in str_repr
        assert "TestRifle" in str_repr
        assert "crated=False" in str_repr
        assert "neutral" in str_repr
        assert "vanilla" in str_repr

    def test_str_representation_crated(self) -> None:
        """Test __str__ method for crated variant."""
        image = np.zeros((64, 64, 3), dtype=np.uint8)

        template = IconTemplate(
            image=image,
            code="TestRifle",
            crated=True,
            category=ItemCategory.Item,
            faction=ItemFaction.NEUTRAL,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        str_repr = str(template)

        assert "crated=True" in str_repr

    def test_repr_representation(self) -> None:
        """Test __repr__ method returns detailed representation."""
        image = np.zeros((64, 64, 3), dtype=np.uint8)

        template = IconTemplate(
            image=image,
            code="TestRifle",
            crated=False,
            category=ItemCategory.Item,
            faction=ItemFaction.COLONIALS,
            mod="vanilla",
            resolution=SupportedResolution.R_2160,
        )

        repr_str = repr(template)

        # Verify repr contains detailed information
        assert "IconTemplate" in repr_str
        assert "code='TestRifle'" in repr_str
        assert "crated=False" in repr_str
        assert "mod='vanilla'" in repr_str
        assert "resolution='2160'" in repr_str
        assert "faction='Colonials'" in repr_str  # Capitalized
        assert "image_shape=(64, 64, 3)" in repr_str

    def test_repr_representation_with_hasattr_check(self) -> None:
        """Test __repr__ method checks for shape attribute."""
        image = np.zeros((64, 64, 3), dtype=np.uint8)

        template = IconTemplate(
            image=image,
            code="TestRifle",
            crated=False,
            category=ItemCategory.Item,
            faction=ItemFaction.NEUTRAL,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        # Test normal case - image has shape
        repr_str = repr(template)
        assert "image_shape=(64, 64, 3)" in repr_str


class TestIconTemplateEdgeCases:
    """Test suite for IconTemplate edge cases and boundary conditions."""

    def test_different_resolutions(self) -> None:
        """Test creating templates for different resolutions."""
        image = np.zeros((64, 64, 3), dtype=np.uint8)

        for resolution in SupportedResolution:
            template = IconTemplate(
                image=image,
                code="TestRifle",
                crated=False,
                category=ItemCategory.Item,
                faction=ItemFaction.NEUTRAL,
                mod="vanilla",
                resolution=resolution,
            )

            assert template.resolution == resolution

    def test_different_factions(self) -> None:
        """Test creating templates for different factions."""
        image = np.zeros((64, 64, 3), dtype=np.uint8)

        for faction in ItemFaction:
            template = IconTemplate(
                image=image,
                code="TestRifle",
                crated=False,
                category=ItemCategory.Item,
                faction=faction,
                mod="vanilla",
                resolution=SupportedResolution.R_1080,
            )

            assert template.faction == faction

    def test_different_categories(self) -> None:
        """Test creating templates for different categories."""
        image = np.zeros((64, 64, 3), dtype=np.uint8)

        for category in ItemCategory:
            template = IconTemplate(
                image=image,
                code="TestRifle",
                crated=False,
                category=category,
                faction=ItemFaction.NEUTRAL,
                mod="vanilla",
                resolution=SupportedResolution.R_1080,
            )

            assert template.category == category

    def test_large_image(self) -> None:
        """Test creating template with larger image."""
        # Create larger image
        image = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)

        template = IconTemplate(
            image=image,
            code="TestRifle",
            crated=False,
            category=ItemCategory.Item,
            faction=ItemFaction.NEUTRAL,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        # Manually compute optimization data
        template.compute_optimization_data()

        assert template.image.shape == (256, 256, 3)
        assert template.normalized_image.shape == (256, 256)
        assert template.phash != 0

    def test_small_image(self) -> None:
        """Test creating template with small image."""
        # Create small image
        image = np.random.randint(0, 255, (16, 16, 3), dtype=np.uint8)

        template = IconTemplate(
            image=image,
            code="TestRifle",
            crated=False,
            category=ItemCategory.Item,
            faction=ItemFaction.NEUTRAL,
            mod="vanilla",
            resolution=SupportedResolution.R_1080,
        )

        # Manually compute optimization data
        template.compute_optimization_data()

        assert template.image.shape == (16, 16, 3)
        assert template.normalized_image.shape == (16, 16)
        assert template.phash != 0

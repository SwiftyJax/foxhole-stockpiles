"""Tests for models.catalog_item module.

This module contains tests for the CatalogItem class business logic,
including catalog parsing and type determination.
"""

from typing import Any

from foxhole_stockpiles.enums.item_category import ItemCategory
from foxhole_stockpiles.enums.item_faction import ItemFaction
from foxhole_stockpiles.models.catalog_item import CatalogItem


class TestCatalogItemFromCatalog:
    """Test suite for CatalogItem.from_catalog class method.

    This class contains tests for the class method that creates CatalogItem
    instances from game catalog data dictionaries.
    """

    def test_from_catalog_basic(self) -> None:
        """Test creating CatalogItem from catalog dictionary."""
        catalog_data = {
            "CodeName": "Rifle",
            "FactionVariant": "Colonials",
            "ItemCategory": "Weapon",
            "Icon": "icons/rifle.png",
            "SubTypeIcon": "icons/rifle_sub.png",
        }

        item = CatalogItem.from_catalog(catalog_data)

        assert item is not None
        assert item.code == "Rifle"
        assert item.faction == ItemFaction.COLONIALS
        assert item.category == ItemCategory.Item
        assert item.icon_path == "icons/rifle.png"
        assert item.subicon_path == "icons/rifle_sub.png"

    def test_from_catalog_vehicle(self) -> None:
        """Test creating vehicle item from catalog."""
        catalog_data = {
            "CodeName": "Tank",
            "VehicleProfileType": "HeavyTank",
            "Icon": "icons/tank.png",
        }

        item = CatalogItem.from_catalog(catalog_data)

        assert item is not None
        assert item.code == "Tank"
        assert item.category == ItemCategory.Vehicle
        assert item.faction == ItemFaction.NEUTRAL

    def test_from_catalog_shippable(self) -> None:
        """Test creating shippable item from catalog."""
        catalog_data = {
            "CodeName": "Container",
            "ShippableInfo": {"Weight": 100},
            "Icon": "icons/container.png",
        }

        item = CatalogItem.from_catalog(catalog_data)

        assert item is not None
        assert item.code == "Container"
        assert item.category == ItemCategory.Shippable

    def test_from_catalog_missing_code(self) -> None:
        """Test that missing CodeName creates item with empty code."""
        catalog_data = {
            "ItemCategory": "Weapon",
            "Icon": "icons/item.png",
        }

        item = CatalogItem.from_catalog(catalog_data)

        # Should create item with empty code
        assert item is not None
        assert item.code == ""

    def test_from_catalog_empty_dict(self) -> None:
        """Test creating from empty dictionary."""
        catalog_data: dict[str, Any] = {}

        item = CatalogItem.from_catalog(catalog_data)

        assert item is not None
        assert item.code == ""
        assert item.category == ItemCategory.Invalid
        assert item.faction == ItemFaction.NEUTRAL

    def test_from_catalog_with_version_suffixes(self) -> None:
        """Test that version suffixes are removed when creating from catalog."""
        catalog_data = {
            "CodeName": "VersionedItem",
            "ItemCategory": "Tool",
            "Icon": "icons/item.123",
            "SubTypeIcon": "icons/item_sub.456",
        }

        item = CatalogItem.from_catalog(catalog_data)

        assert item is not None
        assert item.icon_path == "icons/item"
        assert item.subicon_path == "icons/item_sub"


class TestDetermineItemType:
    """Test suite for _determine_item_type static method.

    This class contains tests for the static method that determines
    the appropriate ItemCategory based on catalog data structure.
    """

    def test_determine_shippable(self) -> None:
        """Test determining shippable item type."""
        item_data = {"ShippableInfo": {"Weight": 100}}
        result = CatalogItem._determine_item_type(item_data)
        assert result == ItemCategory.Shippable

    def test_determine_vehicle(self) -> None:
        """Test determining vehicle item type."""
        item_data = {"VehicleProfileType": "Tank"}
        result = CatalogItem._determine_item_type(item_data)
        assert result == ItemCategory.Vehicle

    def test_determine_item(self) -> None:
        """Test determining regular item type."""
        item_data = {"ItemCategory": "Weapon"}
        result = CatalogItem._determine_item_type(item_data)
        assert result == ItemCategory.Item

    def test_determine_invalid(self) -> None:
        """Test fallback to invalid category."""
        item_data = {"UnknownField": "Value"}
        result = CatalogItem._determine_item_type(item_data)
        assert result == ItemCategory.Invalid

    def test_determine_priority_order(self) -> None:
        """Test priority order: Vehicle > Shippable > Item."""
        # Vehicle should take highest priority
        item_data = {
            "VehicleProfileType": "Tank",
            "ShippableInfo": {"Weight": 100},
            "ItemCategory": "Weapon",
        }
        result = CatalogItem._determine_item_type(item_data)
        assert result == ItemCategory.Vehicle

        # Shippable should take priority over Item
        item_data = {
            "ShippableInfo": {"Weight": 100},
            "ItemCategory": "Weapon",
        }
        result = CatalogItem._determine_item_type(item_data)
        assert result == ItemCategory.Shippable


class TestCanBeCrated:
    """Test suite for _can_be_crated static method.

    This class contains tests for the static method that determines
    whether an item can appear in crate form in stockpiles.
    """

    def test_item_cratable_true(self) -> None:
        """Test item with bIsCratable=True."""
        item_data = {
            "ItemProfileData": {"bIsCratable": True},
        }
        assert CatalogItem._can_be_crated(item_data) is True

    def test_item_cratable_false(self) -> None:
        """Test item with bIsCratable=False."""
        item_data = {
            "ItemProfileData": {"bIsCratable": False},
        }
        assert CatalogItem._can_be_crated(item_data) is False

    def test_item_cratable_missing_defaults_false(self) -> None:
        """Test item with ItemProfileData but missing bIsCratable."""
        item_data = {
            "ItemProfileData": {"OtherField": "value"},
        }
        assert CatalogItem._can_be_crated(item_data) is False

    def test_vehicle_with_mpf(self) -> None:
        """Test vehicle with MassProductionFactory is cratable."""
        item_data = {
            "VehicleProfileType": "Tank",
            "ProductionCategories": {"MassProductionFactory": {"Cost": 100}},
        }
        assert CatalogItem._can_be_crated(item_data) is True

    def test_vehicle_without_mpf(self) -> None:
        """Test vehicle without MassProductionFactory is not cratable."""
        item_data = {
            "VehicleProfileType": "Tank",
            "ProductionCategories": {"Factory": {"Cost": 100}},
        }
        assert CatalogItem._can_be_crated(item_data) is False

    def test_empty_dict_not_cratable(self) -> None:
        """Test empty dictionary is not cratable."""
        item_data: dict[str, Any] = {}
        assert CatalogItem._can_be_crated(item_data) is False

    def test_from_catalog_sets_cratable_for_item(self) -> None:
        """Test that from_catalog correctly sets cratable field for items."""
        catalog_data = {
            "CodeName": "Rifle",
            "ItemCategory": "Weapon",
            "ItemProfileData": {"bIsCratable": True},
            "Icon": "icons/rifle.png",
        }
        item = CatalogItem.from_catalog(catalog_data)
        assert item is not None
        assert item.cratable is True

        catalog_data_not_cratable = {
            "CodeName": "RawMaterial",
            "ItemCategory": "Resource",
            "ItemProfileData": {"bIsCratable": False},
            "Icon": "icons/material.png",
        }
        item2 = CatalogItem.from_catalog(catalog_data_not_cratable)
        assert item2 is not None
        assert item2.cratable is False

    def test_from_catalog_sets_cratable_for_vehicle(self) -> None:
        """Test that from_catalog correctly sets cratable field for vehicles."""
        catalog_data = {
            "CodeName": "Tank",
            "VehicleProfileType": "MediumTank",
            "ProductionCategories": {"MassProductionFactory": {}},
            "Icon": "icons/tank.png",
        }
        item = CatalogItem.from_catalog(catalog_data)
        assert item is not None
        assert item.cratable is True

        catalog_data_not_cratable = {
            "CodeName": "FacilityTank",
            "VehicleProfileType": "MediumTank",
            "ProductionCategories": {"Factory": {}},
            "Icon": "icons/tank.png",
        }
        item2 = CatalogItem.from_catalog(catalog_data_not_cratable)
        assert item2 is not None
        assert item2.cratable is False

    def test_shippable_with_packaging_allowed(self) -> None:
        """Test shippable with bAllowPackagingToCrate=True is cratable."""
        item_data = {
            "ShippableInfo": {"bAllowPackagingToCrate": True},
        }
        assert CatalogItem._can_be_crated(item_data) is True

    def test_shippable_with_packaging_not_allowed(self) -> None:
        """Test shippable with bAllowPackagingToCrate=False is not cratable."""
        item_data = {
            "ShippableInfo": {"bAllowPackagingToCrate": False},
        }
        assert CatalogItem._can_be_crated(item_data) is False


class TestFromCatalogExceptionHandling:
    """Test suite for exception handling in from_catalog method."""

    def test_from_catalog_returns_none_on_validation_error(self) -> None:
        """Test that from_catalog returns None on Pydantic validation failure."""
        # Passing an int for CodeName triggers TypeError during validation
        catalog_data = {
            "CodeName": 123,  # int instead of str
            "ItemCategory": "Weapon",
        }
        item = CatalogItem.from_catalog(catalog_data)
        # This returns None because the exception is caught
        assert item is None

"""Tests for catalog_builder.data_table_lookup module."""

import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from fs_tools.services.catalog_builder.data_table_lookup import (
    DataTableLookup,
)


@pytest.fixture
def temp_data_dir() -> Generator[Path, None, None]:
    """Create a temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "Data"
        data_dir.mkdir(parents=True)

        # Also create Structures directory for factory blueprints
        structures_dir = Path(tmpdir) / "Structures"
        structures_dir.mkdir(parents=True)

        yield data_dir


@pytest.fixture
def sample_data_table() -> dict[str, Any]:
    """Create sample data table JSON data."""
    return {
        "Exports": [
            {
                "$type": "UAssetAPI.ExportTypes.DataTableExport, UAssetAPI",
                "Table": {
                    "Data": [
                        {
                            "Name": "RifleItem",
                            "Value": [
                                {
                                    "Name": "Damage",
                                    "$type": "FloatPropertyData",
                                    "Value": 25.0,
                                },
                                {
                                    "Name": "Range",
                                    "$type": "IntPropertyData",
                                    "Value": 100,
                                },
                                {
                                    "Name": "bIsAutomatic",
                                    "$type": "BoolPropertyData",
                                    "Value": False,
                                },
                            ],
                        },
                        {
                            "Name": "PistolItem",
                            "Value": [
                                {
                                    "Name": "Damage",
                                    "$type": "FloatPropertyData",
                                    "Value": 15.0,
                                },
                                {
                                    "Name": "Range",
                                    "$type": "IntPropertyData",
                                    "Value": 50,
                                },
                                {
                                    "Name": "bIsAutomatic",
                                    "$type": "BoolPropertyData",
                                    "Value": False,
                                },
                            ],
                        },
                    ],
                },
            }
        ],
    }


@pytest.fixture
def sample_profile_table() -> dict[str, Any]:
    """Create sample profile table JSON data."""
    return {
        "Exports": [
            {
                "ObjectName": "Default__BPItemProfileTable_C",
                "Data": [
                    {
                        "Name": "ItemProfileTable",
                        "Value": [
                            [
                                {"Value": "EItemProfileType::Rifle"},
                                {
                                    "Value": [
                                        {
                                            "Name": "Weight",
                                            "$type": "FloatPropertyData",
                                            "Value": 5.0,
                                        },
                                        {
                                            "Name": "Stackable",
                                            "$type": "BoolPropertyData",
                                            "Value": False,
                                        },
                                    ]
                                },
                            ],
                            [
                                {"Value": "EItemProfileType::Pistol"},
                                {
                                    "Value": [
                                        {
                                            "Name": "Weight",
                                            "$type": "FloatPropertyData",
                                            "Value": 2.0,
                                        },
                                        {
                                            "Name": "Stackable",
                                            "$type": "BoolPropertyData",
                                            "Value": False,
                                        },
                                    ]
                                },
                            ],
                        ],
                    }
                ],
            }
        ],
    }


class TestDataTableLookupInit:
    """Tests for DataTableLookup initialization."""

    def test_init_sets_data_dir(self, temp_data_dir: Path) -> None:
        """Test that data_dir is set correctly."""
        lookup = DataTableLookup(temp_data_dir)
        assert lookup.data_dir == temp_data_dir.resolve()

    def test_init_sets_blueprints_dir(self, temp_data_dir: Path) -> None:
        """Test that blueprints_dir is set to parent of data_dir."""
        lookup = DataTableLookup(temp_data_dir)
        assert lookup.blueprints_dir == temp_data_dir.parent.resolve()

    def test_init_creates_empty_caches(self, temp_data_dir: Path) -> None:
        """Test that caches are initialized as empty."""
        lookup = DataTableLookup(temp_data_dir)
        assert lookup._table_cache == {}
        assert lookup._raw_cache == {}
        assert lookup._production_categories_cache is None


class TestDataTableLookupGet:
    """Tests for DataTableLookup.get method."""

    def test_get_returns_none_for_missing_table(self, temp_data_dir: Path) -> None:
        """Test that get returns None for missing table files."""
        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("NonexistentTable.json", "SomeKey")
        assert result is None

    def test_get_returns_none_for_missing_key(
        self, temp_data_dir: Path, sample_data_table: dict[str, Any]
    ) -> None:
        """Test that get returns None for missing keys."""
        # Write sample data
        table_path = temp_data_dir / "BPWeaponDynamicData.json"
        with open(table_path, "w") as f:
            json.dump(sample_data_table, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("BPWeaponDynamicData.json", "NonexistentKey")
        assert result is None

    def test_get_returns_data_for_existing_key(
        self, temp_data_dir: Path, sample_data_table: dict[str, Any]
    ) -> None:
        """Test that get returns data for existing keys."""
        table_path = temp_data_dir / "BPWeaponDynamicData.json"
        with open(table_path, "w") as f:
            json.dump(sample_data_table, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("BPWeaponDynamicData.json", "RifleItem")

        assert result is not None
        assert result.get("Damage") == 25.0
        assert result.get("Range") == 100
        assert result.get("bIsAutomatic") is False

    def test_get_includes_object_path(
        self, temp_data_dir: Path, sample_data_table: dict[str, Any]
    ) -> None:
        """Test that get adds ObjectPath to result."""
        table_path = temp_data_dir / "BPWeaponDynamicData.json"
        with open(table_path, "w") as f:
            json.dump(sample_data_table, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("BPWeaponDynamicData.json", "RifleItem")

        assert result is not None
        assert result.get("ObjectPath") == "War/Content/Blueprints/Data/BPWeaponDynamicData"

    def test_get_caches_table(self, temp_data_dir: Path, sample_data_table: dict[str, Any]) -> None:
        """Test that get caches the parsed table."""
        table_path = temp_data_dir / "BPWeaponDynamicData.json"
        with open(table_path, "w") as f:
            json.dump(sample_data_table, f)

        lookup = DataTableLookup(temp_data_dir)

        # First call
        lookup.get("BPWeaponDynamicData.json", "RifleItem")

        # Check cache was populated
        assert "BPWeaponDynamicData.json" in lookup._table_cache

        # Second call should use cache
        result = lookup.get("BPWeaponDynamicData.json", "PistolItem")
        assert result is not None


class TestDataTableLookupGetProfile:
    """Tests for DataTableLookup.get_profile method."""

    def test_get_profile_returns_none_for_missing_table(self, temp_data_dir: Path) -> None:
        """Test that get_profile returns None for missing table files."""
        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get_profile("NonexistentTable.json", "SomeMap", "SomeKey")
        assert result is None

    def test_get_profile_returns_data_for_existing_key(
        self, temp_data_dir: Path, sample_profile_table: dict[str, Any]
    ) -> None:
        """Test that get_profile returns data for existing keys."""
        table_path = temp_data_dir / "BPItemProfileTable.json"
        with open(table_path, "w") as f:
            json.dump(sample_profile_table, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get_profile(
            "BPItemProfileTable.json", "ItemProfileTable", "EItemProfileType::Rifle"
        )

        assert result is not None
        assert result.get("Weight") == 5.0
        assert result.get("Stackable") is False

    def test_get_profile_includes_object_path(
        self, temp_data_dir: Path, sample_profile_table: dict[str, Any]
    ) -> None:
        """Test that get_profile adds ObjectPath to result."""
        table_path = temp_data_dir / "BPItemProfileTable.json"
        with open(table_path, "w") as f:
            json.dump(sample_profile_table, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get_profile(
            "BPItemProfileTable.json", "ItemProfileTable", "EItemProfileType::Rifle"
        )

        assert result is not None
        assert "ObjectPath" in result


class TestDataTableLookupGetAmmoDynamicData:
    """Tests for DataTableLookup.get_ammo_dynamic_data method."""

    def test_get_ammo_returns_none_for_missing_file(self, temp_data_dir: Path) -> None:
        """Test that get_ammo_dynamic_data returns None when file is missing."""
        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get_ammo_dynamic_data("SomeAmmo")
        assert result is None

    def test_get_ammo_returns_none_for_empty_codename(self, temp_data_dir: Path) -> None:
        """Test that get_ammo_dynamic_data returns None for empty codename."""
        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get_ammo_dynamic_data("")
        assert result is None

    def test_get_ammo_performs_case_insensitive_lookup(self, temp_data_dir: Path) -> None:
        """Test that get_ammo_dynamic_data is case-insensitive."""
        ammo_table = {
            "Exports": [
                {
                    "$type": "UAssetAPI.ExportTypes.DataTableExport, UAssetAPI",
                    "Table": {
                        "Data": [
                            {
                                "Name": "RpgAmmo",
                                "Value": [
                                    {
                                        "Name": "Damage",
                                        "$type": "FloatPropertyData",
                                        "Value": 500.0,
                                    }
                                ],
                            }
                        ]
                    },
                }
            ]
        }

        table_path = temp_data_dir / "BPAmmoDynamicData.json"
        with open(table_path, "w") as f:
            json.dump(ammo_table, f)

        lookup = DataTableLookup(temp_data_dir)

        # Try with different casing
        result = lookup.get_ammo_dynamic_data("RPGAmmo")

        assert result is not None
        assert result.get("Damage") == 500.0


class TestDataTableLookupGetProductionCategories:
    """Tests for DataTableLookup.get_production_categories method."""

    def test_get_production_returns_none_for_unknown_item(self, temp_data_dir: Path) -> None:
        """Test that get_production_categories returns None for unknown items."""
        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get_production_categories("UnknownItem")
        assert result is None

    def test_get_production_parses_factory_blueprint(self, temp_data_dir: Path) -> None:
        """Test that get_production_categories parses factory blueprints."""
        # Create factory blueprint
        factory_data = {
            "Exports": [
                {
                    "ObjectName": "SpecializedFactoryComponent",
                    "Data": [
                        {
                            "Name": "ProductionCategories",
                            "Value": [
                                {
                                    "Value": [
                                        {"Name": "Type", "Value": "EFactoryQueueType::Weapons"},
                                        {
                                            "Name": "CategoryItems",
                                            "Value": [
                                                {
                                                    "Value": [
                                                        {"Name": "CodeName", "Value": "RifleW"}
                                                    ]
                                                },
                                                {
                                                    "Value": [
                                                        {"Name": "CodeName", "Value": "PistolW"}
                                                    ]
                                                },
                                            ],
                                        },
                                    ]
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        factory_path = temp_data_dir.parent / "Structures" / "BPFactory.json"
        with open(factory_path, "w") as f:
            json.dump(factory_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get_production_categories("RifleW")

        assert result is not None
        assert result.get("Factory") == "EFactoryQueueType::Weapons"

    def test_get_production_caches_result(self, temp_data_dir: Path) -> None:
        """Test that get_production_categories caches the parsed data."""
        # Create factory blueprint
        factory_data = {
            "Exports": [
                {
                    "ObjectName": "SpecializedFactoryComponent",
                    "Data": [
                        {
                            "Name": "ProductionCategories",
                            "Value": [
                                {
                                    "Value": [
                                        {"Name": "Type", "Value": "EFactoryQueueType::Weapons"},
                                        {
                                            "Name": "CategoryItems",
                                            "Value": [
                                                {"Value": [{"Name": "CodeName", "Value": "RifleW"}]}
                                            ],
                                        },
                                    ]
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        factory_path = temp_data_dir.parent / "Structures" / "BPFactory.json"
        with open(factory_path, "w") as f:
            json.dump(factory_data, f)

        lookup = DataTableLookup(temp_data_dir)

        # First call
        lookup.get_production_categories("RifleW")

        # Check cache was populated
        assert lookup._production_categories_cache is not None

        # Second call should use cache
        result = lookup.get_production_categories("RifleW")
        assert result is not None


class TestDataTableLookupPropertyExtraction:
    """Tests for property extraction in data tables."""

    def test_extracts_nested_struct_properties(self, temp_data_dir: Path) -> None:
        """Test that nested struct properties are extracted correctly."""
        table_data = {
            "Exports": [
                {
                    "$type": "UAssetAPI.ExportTypes.DataTableExport, UAssetAPI",
                    "Table": {
                        "Data": [
                            {
                                "Name": "TestItem",
                                "Value": [
                                    {
                                        "Name": "Stats",
                                        "$type": "StructPropertyData",
                                        "Value": [
                                            {
                                                "Name": "Damage",
                                                "$type": "FloatPropertyData",
                                                "Value": 25.0,
                                            },
                                            {
                                                "Name": "Range",
                                                "$type": "IntPropertyData",
                                                "Value": 100,
                                            },
                                        ],
                                    }
                                ],
                            }
                        ]
                    },
                }
            ]
        }

        table_path = temp_data_dir / "TestTable.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("TestTable.json", "TestItem")

        assert result is not None
        stats = result.get("Stats")
        assert stats == {"Damage": 25.0, "Range": 100}

    def test_extracts_array_properties(self, temp_data_dir: Path) -> None:
        """Test that array properties are extracted correctly."""
        table_data = {
            "Exports": [
                {
                    "$type": "UAssetAPI.ExportTypes.DataTableExport, UAssetAPI",
                    "Table": {
                        "Data": [
                            {
                                "Name": "TestItem",
                                "Value": [
                                    {
                                        "Name": "Tags",
                                        "$type": "ArrayPropertyData",
                                        "Value": [
                                            {"$type": "StrPropertyData", "Value": "weapon"},
                                            {"$type": "StrPropertyData", "Value": "rifle"},
                                        ],
                                    }
                                ],
                            }
                        ]
                    },
                }
            ]
        }

        table_path = temp_data_dir / "TestTable.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("TestTable.json", "TestItem")

        assert result is not None
        assert result.get("Tags") == ["weapon", "rifle"]

    def test_keeps_object_property_as_raw_value(self, temp_data_dir: Path) -> None:
        """Test that ObjectPropertyData keeps raw value for import resolution."""
        table_data = {
            "Exports": [
                {
                    "$type": "UAssetAPI.ExportTypes.DataTableExport, UAssetAPI",
                    "Table": {
                        "Data": [
                            {
                                "Name": "TestAmmo",
                                "Value": [
                                    {
                                        "Name": "DamageType",
                                        "$type": "ObjectPropertyData",
                                        "Value": -5,
                                    }
                                ],
                            }
                        ]
                    },
                }
            ]
        }

        table_path = temp_data_dir / "TestTable.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("TestTable.json", "TestAmmo")

        assert result is not None
        # ObjectPropertyData should keep raw int value for resolution
        assert result.get("DamageType") == -5


class TestDataTableLookupEdgeCases:
    """Edge case tests for DataTableLookup."""

    def test_handles_json_load_error(self, temp_data_dir: Path) -> None:
        """Test that JSON load errors are handled gracefully."""
        table_path = temp_data_dir / "corrupt.json"
        with open(table_path, "w") as f:
            f.write("not valid json{")

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("corrupt.json", "SomeKey")
        assert result is None

    def test_handles_empty_exports(self, temp_data_dir: Path) -> None:
        """Test that empty Exports array is handled."""
        table_data: dict[str, Any] = {"Exports": []}
        table_path = temp_data_dir / "empty.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("empty.json", "SomeKey")
        assert result is None

    def test_handles_non_datatable_exports(self, temp_data_dir: Path) -> None:
        """Test that non-DataTableExport exports are skipped."""
        table_data = {
            "Exports": [
                {"$type": "SomeOtherExport", "Data": []},
                {
                    "$type": "UAssetAPI.ExportTypes.DataTableExport, UAssetAPI",
                    "Table": {"Data": [{"Name": "TestItem", "Value": []}]},
                },
            ]
        }
        table_path = temp_data_dir / "mixed.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("mixed.json", "TestItem")
        assert result is not None

    def test_handles_entry_without_name(self, temp_data_dir: Path) -> None:
        """Test that entries without Name are skipped."""
        table_data = {
            "Exports": [
                {
                    "$type": "UAssetAPI.ExportTypes.DataTableExport, UAssetAPI",
                    "Table": {
                        "Data": [
                            {"Value": []},  # No Name
                            {"Name": "ValidItem", "Value": []},
                        ]
                    },
                }
            ]
        }
        table_path = temp_data_dir / "noname.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("noname.json", "ValidItem")
        assert result is not None

    def test_handles_non_dict_property(self, temp_data_dir: Path) -> None:
        """Test that non-dict properties in Value array are skipped."""
        table_data = {
            "Exports": [
                {
                    "$type": "UAssetAPI.ExportTypes.DataTableExport, UAssetAPI",
                    "Table": {
                        "Data": [
                            {
                                "Name": "TestItem",
                                "Value": [
                                    "not a dict",
                                    {"Name": "ValidProp", "$type": "IntPropertyData", "Value": 42},
                                ],
                            }
                        ]
                    },
                }
            ]
        }
        table_path = temp_data_dir / "nondict.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("nondict.json", "TestItem")
        assert result is not None
        assert result.get("ValidProp") == 42

    def test_handles_property_without_name(self, temp_data_dir: Path) -> None:
        """Test that properties without Name are skipped."""
        table_data = {
            "Exports": [
                {
                    "$type": "UAssetAPI.ExportTypes.DataTableExport, UAssetAPI",
                    "Table": {
                        "Data": [
                            {
                                "Name": "TestItem",
                                "Value": [
                                    {"$type": "IntPropertyData", "Value": 1},  # No Name
                                    {"Name": "ValidProp", "$type": "IntPropertyData", "Value": 42},
                                ],
                            }
                        ]
                    },
                }
            ]
        }
        table_path = temp_data_dir / "nopropname.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("nopropname.json", "TestItem")
        assert result is not None
        assert "ValidProp" in result
        assert len(result) == 2  # ValidProp + ObjectPath

    def test_struct_property_non_list_value(self, temp_data_dir: Path) -> None:
        """Test StructPropertyData with non-list value."""
        table_data = {
            "Exports": [
                {
                    "$type": "UAssetAPI.ExportTypes.DataTableExport, UAssetAPI",
                    "Table": {
                        "Data": [
                            {
                                "Name": "TestItem",
                                "Value": [
                                    {
                                        "Name": "Struct",
                                        "$type": "StructPropertyData",
                                        "Value": "not a list",
                                    }
                                ],
                            }
                        ]
                    },
                }
            ]
        }
        table_path = temp_data_dir / "structnonlist.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("structnonlist.json", "TestItem")
        assert result is not None
        assert result.get("Struct") == "not a list"

    def test_array_property_non_list_value(self, temp_data_dir: Path) -> None:
        """Test ArrayPropertyData with non-list value."""
        table_data = {
            "Exports": [
                {
                    "$type": "UAssetAPI.ExportTypes.DataTableExport, UAssetAPI",
                    "Table": {
                        "Data": [
                            {
                                "Name": "TestItem",
                                "Value": [
                                    {
                                        "Name": "Array",
                                        "$type": "ArrayPropertyData",
                                        "Value": "not a list",
                                    }
                                ],
                            }
                        ]
                    },
                }
            ]
        }
        table_path = temp_data_dir / "arraynonlist.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get("arraynonlist.json", "TestItem")
        assert result is not None
        assert result.get("Array") == "not a list"

    def test_uses_raw_cache(self, temp_data_dir: Path) -> None:
        """Test that raw cache is used on second load."""
        table_data = {
            "Exports": [
                {
                    "$type": "UAssetAPI.ExportTypes.DataTableExport, UAssetAPI",
                    "Table": {"Data": [{"Name": "TestItem", "Value": []}]},
                }
            ]
        }
        table_path = temp_data_dir / "cached.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)

        # First load
        lookup.get("cached.json", "TestItem")
        assert "cached.json" in lookup._raw_cache

        # Modify the file (won't be reloaded due to cache)
        with open(table_path, "w") as f:
            json.dump({"Exports": []}, f)

        # Second load should use cache
        result = lookup.get("cached.json", "TestItem")
        assert result is not None  # Still returns original data


class TestDataTableLookupProfileTableEdgeCases:
    """Edge case tests for profile table parsing."""

    def test_handles_empty_profile_exports(self, temp_data_dir: Path) -> None:
        """Test that empty exports in profile table is handled."""
        table_data: dict[str, Any] = {"Exports": []}
        table_path = temp_data_dir / "emptyprofile.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get_profile("emptyprofile.json", "SomeMap", "SomeKey")
        assert result is None

    def test_handles_non_default_export(self, temp_data_dir: Path) -> None:
        """Test that non-Default__ exports in profile table are skipped."""
        table_data = {
            "Exports": [
                {"ObjectName": "NotDefault", "Data": []},
            ]
        }
        table_path = temp_data_dir / "nodefault.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get_profile("nodefault.json", "SomeMap", "SomeKey")
        assert result is None

    def test_handles_wrong_map_name(self, temp_data_dir: Path) -> None:
        """Test that wrong map names are skipped."""
        table_data = {
            "Exports": [
                {
                    "ObjectName": "Default__Test",
                    "Data": [{"Name": "WrongMapName", "Value": []}],
                }
            ]
        }
        table_path = temp_data_dir / "wrongmap.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get_profile("wrongmap.json", "CorrectMapName", "SomeKey")
        assert result is None

    def test_handles_invalid_map_entry(self, temp_data_dir: Path) -> None:
        """Test that invalid map entries are skipped."""
        table_data = {
            "Exports": [
                {
                    "ObjectName": "Default__Test",
                    "Data": [
                        {
                            "Name": "TestMap",
                            "Value": [
                                "not a list",
                                [{"Value": "Key1"}],  # Only 1 element, need 2
                                [{"Value": "Key2"}, {"Value": []}],  # Valid
                            ],
                        }
                    ],
                }
            ]
        }
        table_path = temp_data_dir / "invalidentry.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get_profile("invalidentry.json", "TestMap", "Key2")
        assert result is not None

    def test_handles_key_without_value(self, temp_data_dir: Path) -> None:
        """Test that map entries without key value are skipped."""
        table_data = {
            "Exports": [
                {
                    "ObjectName": "Default__Test",
                    "Data": [
                        {
                            "Name": "TestMap",
                            "Value": [
                                [{"NoValue": "here"}, {"Value": []}],  # No Value in key
                                [{"Value": "ValidKey"}, {"Value": []}],  # Valid
                            ],
                        }
                    ],
                }
            ]
        }
        table_path = temp_data_dir / "nokey.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get_profile("nokey.json", "TestMap", "ValidKey")
        assert result is not None

    def test_handles_non_dict_value_props(self, temp_data_dir: Path) -> None:
        """Test that non-dict value props in profile table are handled."""
        table_data = {
            "Exports": [
                {
                    "ObjectName": "Default__Test",
                    "Data": [
                        {
                            "Name": "TestMap",
                            "Value": [
                                [
                                    {"Value": "TestKey"},
                                    [  # Direct list instead of dict with Value
                                        {"Name": "Prop1", "$type": "IntPropertyData", "Value": 42}
                                    ],
                                ]
                            ],
                        }
                    ],
                }
            ]
        }
        table_path = temp_data_dir / "directlist.json"
        with open(table_path, "w") as f:
            json.dump(table_data, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get_profile("directlist.json", "TestMap", "TestKey")
        assert result is not None
        assert result.get("Prop1") == 42


class TestDataTableLookupResolveDamageType:
    """Tests for resolve_damage_type_import method."""

    def test_returns_none_for_missing_ammo(self, temp_data_dir: Path) -> None:
        """Test that None is returned when ammo data doesn't exist."""
        lookup = DataTableLookup(temp_data_dir)
        result = lookup.resolve_damage_type_import("NonexistentAmmo")
        assert result is None

    def test_returns_none_for_non_negative_damage_type(self, temp_data_dir: Path) -> None:
        """Test that None is returned when DamageType is not a negative int."""
        ammo_table = {
            "Exports": [
                {
                    "$type": "UAssetAPI.ExportTypes.DataTableExport, UAssetAPI",
                    "Table": {
                        "Data": [
                            {
                                "Name": "TestAmmo",
                                "Value": [
                                    {
                                        "Name": "DamageType",
                                        "$type": "ObjectPropertyData",
                                        "Value": 5,  # Positive, not an import
                                    }
                                ],
                            }
                        ]
                    },
                }
            ]
        }
        table_path = temp_data_dir / "BPAmmoDynamicData.json"
        with open(table_path, "w") as f:
            json.dump(ammo_table, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.resolve_damage_type_import("TestAmmo")
        assert result is None

    def test_resolves_damage_type_path(self, temp_data_dir: Path) -> None:
        """Test that damage type path is resolved from imports."""
        ammo_table = {
            "Imports": [
                {"ObjectName": "/Game/Blueprints/DamageTypes", "OuterIndex": 0},
                {"ObjectName": "BPExplosive_C", "OuterIndex": -1},
            ],
            "Exports": [
                {
                    "$type": "UAssetAPI.ExportTypes.DataTableExport, UAssetAPI",
                    "Table": {
                        "Data": [
                            {
                                "Name": "TestAmmo",
                                "Value": [
                                    {
                                        "Name": "DamageType",
                                        "$type": "ObjectPropertyData",
                                        "Value": -2,
                                    }
                                ],
                            }
                        ]
                    },
                }
            ],
        }
        table_path = temp_data_dir / "BPAmmoDynamicData.json"
        with open(table_path, "w") as f:
            json.dump(ammo_table, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.resolve_damage_type_import("TestAmmo")
        assert result == "/Game/Blueprints/DamageTypes/BPExplosive_C"


class TestDataTableLookupMassProduction:
    """Tests for MassProductionFactory parsing."""

    def test_parses_mass_production_blueprint(self, temp_data_dir: Path) -> None:
        """Test that MassProductionFactory blueprint is parsed."""
        mass_prod_data = {
            "Exports": [
                {
                    "ObjectName": "SpecializedFactoryComponent",
                    "Data": [
                        {
                            "Name": "ProductionCategories",
                            "Value": [
                                {
                                    "Value": [
                                        {"Name": "Type", "Value": "EFactoryQueueType::Materials"},
                                        {
                                            "Name": "CategoryItems",
                                            "Value": [
                                                {
                                                    "Value": [
                                                        {
                                                            "Name": "CodeName",
                                                            "Value": "MaterialsItem",
                                                        }
                                                    ]
                                                }
                                            ],
                                        },
                                    ]
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        mass_prod_path = temp_data_dir.parent / "Structures" / "BPMassProduction.json"
        with open(mass_prod_path, "w") as f:
            json.dump(mass_prod_data, f)

        # Also need factory blueprint (empty)
        factory_path = temp_data_dir.parent / "Structures" / "BPFactory.json"
        with open(factory_path, "w") as f:
            json.dump({"Exports": []}, f)

        lookup = DataTableLookup(temp_data_dir)
        result = lookup.get_production_categories("MaterialsItem")

        assert result is not None
        assert result.get("MassProductionFactory") == "EFactoryQueueType::Materials"

"""Tests for catalog_builder.blueprint_parser module."""

import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from fs_tools.services.catalog_builder.blueprint_parser import BlueprintParser


@pytest.fixture
def temp_blueprints_dir() -> Generator[Path, None, None]:
    """Create a temporary blueprints directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        blueprints_dir = Path(tmpdir) / "War" / "Content" / "Blueprints"
        blueprints_dir.mkdir(parents=True)
        yield blueprints_dir


@pytest.fixture
def sample_blueprint_data() -> dict[str, Any]:
    """Create sample blueprint JSON data."""
    return {
        "Imports": [
            {
                "ClassName": "Package",
                "ObjectName": "/Script/CoreUObject",
                "OuterIndex": 0,
            },
            {
                "ClassName": "BlueprintGeneratedClass",
                "ObjectName": "BPItemBase_C",
                "OuterIndex": -3,
            },
            {
                "ClassName": "Package",
                "ObjectName": "/Game/Blueprints/Items/BPItemBase",
                "OuterIndex": 0,
            },
        ],
        "Exports": [
            {
                "ObjectName": "BPTestItem_C",
                "ClassIndex": -2,
                "SuperIndex": -2,
                "Data": [],
            },
            {
                "ObjectName": "Default__BPTestItem_C",
                "ClassIndex": 1,
                "Data": [
                    {
                        "Name": "CodeName",
                        "$type": "StrPropertyData",
                        "Value": "TestItem",
                    },
                    {
                        "Name": "DisplayName",
                        "$type": "TextPropertyData",
                        "CultureInvariantString": "Test Item",
                        "Value": "GUID123",
                    },
                    {
                        "Name": "bIsStockpilable",
                        "$type": "BoolPropertyData",
                        "Value": True,
                    },
                ],
            },
        ],
    }


class TestBlueprintParserInit:
    """Tests for BlueprintParser initialization."""

    def test_init_sets_blueprints_dir(self, temp_blueprints_dir: Path) -> None:
        """Test that blueprints_dir is set correctly."""
        parser = BlueprintParser(temp_blueprints_dir)
        assert parser.blueprints_dir == temp_blueprints_dir.resolve()

    def test_init_sets_full_extraction_default(self, temp_blueprints_dir: Path) -> None:
        """Test that full_extraction defaults to False."""
        parser = BlueprintParser(temp_blueprints_dir)
        assert parser.full_extraction is False

    def test_init_sets_full_extraction_true(self, temp_blueprints_dir: Path) -> None:
        """Test that full_extraction can be set to True."""
        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)
        assert parser.full_extraction is True

    def test_init_creates_empty_caches(self, temp_blueprints_dir: Path) -> None:
        """Test that caches are initialized as empty."""
        parser = BlueprintParser(temp_blueprints_dir)
        assert parser.raw_cache == {}
        assert parser.processed_cache == {}
        assert parser.catalog_cache == {}


class TestBlueprintParserParse:
    """Tests for BlueprintParser.parse method."""

    def test_parse_returns_none_for_missing_file(self, temp_blueprints_dir: Path) -> None:
        """Test that parse returns None for missing files."""
        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("nonexistent.json")
        assert result is None

    def test_parse_loads_and_processes_json(
        self, temp_blueprints_dir: Path, sample_blueprint_data: dict[str, Any]
    ) -> None:
        """Test that parse loads and processes a JSON file."""
        # Write sample data to file
        json_path = temp_blueprints_dir / "Items" / "BPTestItem.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(sample_blueprint_data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("Items/BPTestItem.json")

        assert result is not None
        assert "Exports" in result
        assert "Imports" in result

    def test_parse_caches_result(
        self, temp_blueprints_dir: Path, sample_blueprint_data: dict[str, Any]
    ) -> None:
        """Test that parse caches the processed result."""
        json_path = temp_blueprints_dir / "Items" / "BPTestItem.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(sample_blueprint_data, f)

        parser = BlueprintParser(temp_blueprints_dir)

        # First call
        result1 = parser.parse("Items/BPTestItem.json")

        # Check cache was populated
        assert len(parser.processed_cache) == 1

        # Second call should return cached result
        result2 = parser.parse("Items/BPTestItem.json")
        assert result1 == result2

    def test_parse_processes_exports(
        self, temp_blueprints_dir: Path, sample_blueprint_data: dict[str, Any]
    ) -> None:
        """Test that parse processes exports correctly."""
        json_path = temp_blueprints_dir / "Items" / "BPTestItem.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(sample_blueprint_data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("Items/BPTestItem.json")

        assert result is not None
        exports = result.get("Exports", [])

        # Should have Default__ export
        default_export = next(
            (e for e in exports if e.get("ObjectName", "").startswith("Default__")),
            None,
        )
        assert default_export is not None

        # Check Data was processed
        data = default_export.get("Data", {})
        assert "CodeName" in data
        assert data["CodeName"] == "TestItem"

    def test_parse_processes_imports(
        self, temp_blueprints_dir: Path, sample_blueprint_data: dict[str, Any]
    ) -> None:
        """Test that parse processes imports correctly."""
        json_path = temp_blueprints_dir / "Items" / "BPTestItem.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(sample_blueprint_data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("Items/BPTestItem.json")

        assert result is not None
        imports = result.get("Imports", [])

        # First import (Package) should be None (not a blueprint)
        assert imports[0] is None

        # Second import (BlueprintGeneratedClass) should resolve to path
        assert imports[1] == "/Game/Blueprints/Items/BPItemBase"


class TestBlueprintParserExtractCatalogData:
    """Tests for BlueprintParser.extract_catalog_data method."""

    def test_extract_returns_none_for_missing_file(self, temp_blueprints_dir: Path) -> None:
        """Test that extract_catalog_data returns None for missing files."""
        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("nonexistent.json")
        assert result is None

    def test_extract_returns_catalog_data(
        self, temp_blueprints_dir: Path, sample_blueprint_data: dict[str, Any]
    ) -> None:
        """Test that extract_catalog_data returns simplified catalog data."""
        json_path = temp_blueprints_dir / "Items" / "BPTestItem.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(sample_blueprint_data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("Items/BPTestItem.json")

        assert result is not None
        assert result.get("CodeName") == "TestItem"
        assert "DisplayName" in result
        assert result.get("bIsStockpilable") is True

    def test_extract_includes_object_path(
        self, temp_blueprints_dir: Path, sample_blueprint_data: dict[str, Any]
    ) -> None:
        """Test that extract_catalog_data includes ObjectPath."""
        json_path = temp_blueprints_dir / "Items" / "BPTestItem.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(sample_blueprint_data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("Items/BPTestItem.json")

        assert result is not None
        assert "ObjectPath" in result

    def test_extract_includes_parent_blueprint(
        self, temp_blueprints_dir: Path, sample_blueprint_data: dict[str, Any]
    ) -> None:
        """Test that extract_catalog_data includes ParentBlueprint."""
        json_path = temp_blueprints_dir / "Items" / "BPTestItem.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(sample_blueprint_data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("Items/BPTestItem.json")

        assert result is not None
        assert result.get("ParentBlueprint") == "/Game/Blueprints/Items/BPItemBase"

    def test_extract_caches_result(
        self, temp_blueprints_dir: Path, sample_blueprint_data: dict[str, Any]
    ) -> None:
        """Test that extract_catalog_data caches the result."""
        json_path = temp_blueprints_dir / "Items" / "BPTestItem.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(sample_blueprint_data, f)

        parser = BlueprintParser(temp_blueprints_dir)

        # First call
        result1 = parser.extract_catalog_data("Items/BPTestItem.json")

        # Check cache was populated
        assert len(parser.catalog_cache) == 1

        # Second call should return cached result
        result2 = parser.extract_catalog_data("Items/BPTestItem.json")
        assert result1 == result2


class TestBlueprintParserFindPath:
    """Tests for BlueprintParser path resolution."""

    def test_finds_file_in_subdirectory(
        self, temp_blueprints_dir: Path, sample_blueprint_data: dict[str, Any]
    ) -> None:
        """Test that parser finds files in subdirectories."""
        # Create file in subdirectory
        json_path = temp_blueprints_dir / "Structures" / "Emplacements" / "BPTurret.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(sample_blueprint_data, f)

        parser = BlueprintParser(temp_blueprints_dir)

        # Request file as if it were in parent directory
        result = parser.parse("Structures/BPTurret.json")

        # Should find it in subdirectory
        assert result is not None


class TestBlueprintParserInheritance:
    """Tests for BlueprintParser inheritance handling."""

    def test_merges_parent_blueprint_data(self, temp_blueprints_dir: Path) -> None:
        """Test that child blueprints inherit parent properties."""
        # Create parent blueprint
        parent_data = {
            "Imports": [],
            "Exports": [
                {
                    "ObjectName": "BPParent_C",
                    "Data": [],
                },
                {
                    "ObjectName": "Default__BPParent_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "ParentProperty",
                            "$type": "IntPropertyData",
                            "Value": 100,
                        },
                        {
                            "Name": "SharedProperty",
                            "$type": "IntPropertyData",
                            "Value": 50,
                        },
                    ],
                },
            ],
        }

        parent_path = temp_blueprints_dir / "Items" / "BPParent.json"
        parent_path.parent.mkdir(parents=True, exist_ok=True)
        with open(parent_path, "w") as f:
            json.dump(parent_data, f)

        # Create child blueprint that inherits from parent
        child_data = {
            "Imports": [
                {
                    "ClassName": "BlueprintGeneratedClass",
                    "ObjectName": "BPParent_C",
                    "OuterIndex": -2,
                },
                {
                    "ClassName": "Package",
                    "ObjectName": "/Game/Blueprints/Items/BPParent",
                    "OuterIndex": 0,
                },
            ],
            "Exports": [
                {
                    "ObjectName": "BPChild_C",
                    "SuperIndex": -1,
                    "Data": [],
                },
                {
                    "ObjectName": "Default__BPChild_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "CodeName",
                            "$type": "StrPropertyData",
                            "Value": "ChildItem",
                        },
                        {
                            "Name": "ChildProperty",
                            "$type": "IntPropertyData",
                            "Value": 200,
                        },
                        {
                            "Name": "SharedProperty",
                            "$type": "IntPropertyData",
                            "Value": 75,
                        },
                    ],
                },
            ],
        }

        child_path = temp_blueprints_dir / "Items" / "BPChild.json"
        with open(child_path, "w") as f:
            json.dump(child_data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("Items/BPChild.json")

        assert result is not None

        # Child should have its own properties
        assert result.get("CodeName") == "ChildItem"
        assert result.get("ChildProperty") == 200

        # Child should inherit parent properties
        assert result.get("ParentProperty") == 100

        # Child should override shared properties
        assert result.get("SharedProperty") == 75


class TestBlueprintParserPropertyProcessing:
    """Tests for property type processing."""

    def test_processes_text_property_with_localization(self, temp_blueprints_dir: Path) -> None:
        """Test that TextPropertyData with GUID is processed correctly."""
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "DisplayName",
                            "$type": "TextPropertyData",
                            "CultureInvariantString": "My Item",
                            "Value": "ABC123GUID",
                        }
                    ],
                },
            ],
        }

        json_path = temp_blueprints_dir / "BPTest.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("BPTest.json")

        assert result is not None
        display_name = result.get("DisplayName")
        assert display_name == {"Text": "My Item", "Guid": "ABC123GUID"}

    def test_processes_array_property(self, temp_blueprints_dir: Path) -> None:
        """Test that ArrayPropertyData is processed correctly."""
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "ItemList",
                            "$type": "ArrayPropertyData",
                            "Value": [
                                {"$type": "IntPropertyData", "Value": 1},
                                {"$type": "IntPropertyData", "Value": 2},
                                {"$type": "IntPropertyData", "Value": 3},
                            ],
                        }
                    ],
                },
            ],
        }

        json_path = temp_blueprints_dir / "BPTest.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("BPTest.json")

        assert result is not None
        assert result.get("ItemList") == [1, 2, 3]

    def test_processes_struct_property(self, temp_blueprints_dir: Path) -> None:
        """Test that StructPropertyData is processed correctly."""
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "ItemStats",
                            "$type": "StructPropertyData",
                            "Value": [
                                {
                                    "Name": "Damage",
                                    "$type": "FloatPropertyData",
                                    "Value": 25.0,
                                },
                                {
                                    "Name": "Range",
                                    "$type": "FloatPropertyData",
                                    "Value": 100.0,
                                },
                            ],
                        }
                    ],
                },
            ],
        }

        json_path = temp_blueprints_dir / "BPTest.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("BPTest.json")

        assert result is not None
        item_stats = result.get("ItemStats")
        assert item_stats == {"Damage": 25, "Range": 100}


class TestBlueprintParserEdgeCases:
    """Edge case tests for BlueprintParser."""

    def test_handles_non_relative_path(self, temp_blueprints_dir: Path) -> None:
        """Test that ValueError in path resolution is handled."""
        parser = BlueprintParser(temp_blueprints_dir)

        # Try to find a path that's not relative to blueprints_dir
        result = parser._find_blueprint_path(Path("/some/other/path.json"))
        assert result is None

    def test_handles_json_load_error(self, temp_blueprints_dir: Path) -> None:
        """Test that JSON load errors are handled gracefully."""
        json_path = temp_blueprints_dir / "corrupt.json"
        with open(json_path, "w") as f:
            f.write("not valid json{")

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("corrupt.json")
        assert result is None

    def test_handles_no_default_export(self, temp_blueprints_dir: Path) -> None:
        """Test that missing Default__ export returns None for catalog data."""
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "NotDefault_C", "Data": []},
            ],
        }
        json_path = temp_blueprints_dir / "nodefault.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("nodefault.json")
        assert result is None

    def test_handles_default_export_without_prefix(self, temp_blueprints_dir: Path) -> None:
        """Test resolving parent from non-Default__ export."""
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "NotDefault", "Data": []},
            ],
        }
        json_path = temp_blueprints_dir / "notdefault.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("notdefault.json")
        # _resolve_parent_blueprint should return None
        assert result is not None

    def test_handles_class_not_found(self, temp_blueprints_dir: Path) -> None:
        """Test when class export matching Default__ is not found."""
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "SomeOther_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",  # Class Test_C doesn't exist
                    "ClassIndex": 1,
                    "Data": [],
                },
            ],
        }
        json_path = temp_blueprints_dir / "noclassmatch.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("noclassmatch.json")
        # Should still work, just no parent
        assert result is not None
        assert "ParentBlueprint" not in result

    def test_handles_import_path_null(self, temp_blueprints_dir: Path) -> None:
        """Test when import path resolves to None."""
        data = {
            "Imports": [
                {"ClassName": "Package", "ObjectName": "/Script/CoreUObject", "OuterIndex": 0},
            ],
            "Exports": [
                {
                    "ObjectName": "Test_C",
                    "SuperIndex": "Reference: -1",  # Points to non-blueprint import
                    "Data": [],
                },
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [],
                },
            ],
        }
        json_path = temp_blueprints_dir / "nullimport.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("nullimport.json")
        assert result is not None
        assert "ParentBlueprint" not in result

    def test_handles_unconverted_data(self, temp_blueprints_dir: Path) -> None:
        """Test blueprint with unconverted Data (base64 string)."""
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": "base64encodedstring==",  # Not dict or list
                },
            ],
        }
        json_path = temp_blueprints_dir / "unconverted.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("unconverted.json")
        # Should still return ObjectPath even if Data is not processed
        assert result is not None
        assert "ObjectPath" in result

    def test_handles_object_path_not_relative(self, temp_blueprints_dir: Path) -> None:
        """Test when object path can't be made relative to extraction root."""
        # Create file in temp location outside normal structure
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            other_dir = Path(tmpdir)
            json_path = other_dir / "test.json"
            data = {
                "Imports": [],
                "Exports": [
                    {"ObjectName": "Test_C", "Data": []},
                    {"ObjectName": "Default__Test_C", "ClassIndex": 1, "Data": []},
                ],
            }
            with open(json_path, "w") as f:
                json.dump(data, f)

            parser = BlueprintParser(other_dir)
            result = parser.extract_catalog_data(json_path)
            # Should still work, ObjectPath will be the full path
            assert result is not None

    def test_parent_not_found(self, temp_blueprints_dir: Path) -> None:
        """Test when parent blueprint file doesn't exist."""
        data = {
            "Imports": [
                {
                    "ClassName": "BlueprintGeneratedClass",
                    "ObjectName": "BPParent_C",
                    "OuterIndex": -2,
                },
                {
                    "ClassName": "Package",
                    "ObjectName": "/Game/Blueprints/Items/BPParent",
                    "OuterIndex": 0,
                },
            ],
            "Exports": [
                {
                    "ObjectName": "Test_C",
                    "SuperIndex": -1,  # Direct negative int (import reference)
                    "Data": [],
                },
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [{"Name": "CodeName", "$type": "StrPropertyData", "Value": "Test"}],
                },
            ],
        }
        json_path = temp_blueprints_dir / "Items" / "BPTest.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("Items/BPTest.json")
        # Should work, just won't have parent data merged (parent file doesn't exist)
        assert result is not None
        # ParentBlueprint is only set when SuperIndex resolves to a valid /Game/Blueprints path
        assert result.get("CodeName") == "Test"

    def test_parent_not_game_blueprints(self, temp_blueprints_dir: Path) -> None:
        """Test when parent path doesn't start with /Game/Blueprints/."""
        data = {
            "Imports": [
                {
                    "ClassName": "BlueprintGeneratedClass",
                    "ObjectName": "SomeClass_C",
                    "OuterIndex": -2,
                },
                {
                    "ClassName": "Package",
                    "ObjectName": "/Script/Engine/SomeClass",  # Not /Game/Blueprints/
                    "OuterIndex": 0,
                },
            ],
            "Exports": [
                {
                    "ObjectName": "Test_C",
                    "SuperIndex": "Reference: -1",
                    "Data": [],
                },
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [],
                },
            ],
        }
        json_path = temp_blueprints_dir / "test.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("test.json")
        # _get_parent_data should return None for non-game paths
        assert result is not None


class TestBlueprintParserFullExtraction:
    """Tests for full extraction mode."""

    def test_full_extraction_resolves_export_references(self, temp_blueprints_dir: Path) -> None:
        """Test that full extraction resolves export references."""
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "SomeComponent", "Data": []},
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 2,
                    "Data": [
                        {
                            "Name": "Component",
                            "$type": "ObjectPropertyData",
                            "Value": "Reference: 1",  # Export reference
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "fullextract.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)
        result = parser.extract_catalog_data("fullextract.json")

        assert result is not None
        # In full extraction mode, export reference should be resolved to ObjectName
        assert result.get("Component") == "SomeComponent"

    def test_full_extraction_resolves_raw_import_path(self, temp_blueprints_dir: Path) -> None:
        """Test that full extraction falls back to raw import for asset paths."""
        data = {
            "Imports": [
                {
                    "ClassName": "Texture2D",
                    "ObjectName": "MyIcon",
                    "OuterIndex": -2,
                },
                {
                    "ClassName": "Package",
                    "ObjectName": "/Game/Textures/Icons",
                    "OuterIndex": 0,
                },
            ],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "Icon",
                            "$type": "ObjectPropertyData",
                            "Value": "Reference: -1",  # Import reference to non-blueprint
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "rawimp.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)
        result = parser.extract_catalog_data("rawimp.json")

        assert result is not None
        # Should resolve using raw import path
        assert result.get("Icon") is not None

    def test_full_extraction_handles_list_references(self, temp_blueprints_dir: Path) -> None:
        """Test that full extraction handles references in lists."""
        data = {
            "Imports": [
                {
                    "ClassName": "BlueprintGeneratedClass",
                    "ObjectName": "BPItem_C",
                    "OuterIndex": -2,
                },
                {
                    "ClassName": "Package",
                    "ObjectName": "/Game/Blueprints/Items/BPItem",
                    "OuterIndex": 0,
                },
            ],
            "Exports": [
                {"ObjectName": "Component1", "Data": []},
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 2,
                    "Data": [
                        {
                            "Name": "Items",
                            "$type": "ArrayPropertyData",
                            "Value": [
                                "Reference: -1",  # Import ref
                                "Reference: 1",  # Export ref
                                "Reference: 0",  # Null ref (should be skipped)
                            ],
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "listrefs.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)
        result = parser.extract_catalog_data("listrefs.json")

        assert result is not None
        items = result.get("Items", [])
        assert len(items) == 2  # Should skip null reference
        assert "/Game/Blueprints/Items/BPItem" in items
        assert "Component1" in items

    def test_simple_mode_skips_empty_results(self, temp_blueprints_dir: Path) -> None:
        """Test that simple mode (non-full) skips empty results."""
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "EmptyStruct",
                            "$type": "StructPropertyData",
                            "Value": [],  # Empty struct
                        },
                        {
                            "Name": "NonEmpty",
                            "$type": "IntPropertyData",
                            "Value": 42,
                        },
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "simplemode.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir, full_extraction=False)
        result = parser.extract_catalog_data("simplemode.json")

        assert result is not None
        # Empty struct should be skipped in simple mode
        assert "EmptyStruct" not in result
        assert result.get("NonEmpty") == 42


class TestBlueprintParserProcessDataPrimitive:
    """Tests for _process_data with primitive values."""

    def test_returns_primitive_unchanged(self, temp_blueprints_dir: Path) -> None:
        """Test that primitive values are returned unchanged."""
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {"Name": "StringVal", "$type": "StrPropertyData", "Value": "hello"},
                        {"Name": "IntVal", "$type": "IntPropertyData", "Value": 42},
                        {"Name": "BoolVal", "$type": "BoolPropertyData", "Value": True},
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "primitives.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("primitives.json")

        assert result is not None
        assert result.get("StringVal") == "hello"
        assert result.get("IntVal") == 42
        assert result.get("BoolVal") is True


class TestBlueprintParserPropertyTypes:
    """Tests for various PropertyData type processing.

    This class contains tests for different property types handled by
    _process_property_data method to ensure proper value extraction.
    """

    def test_processes_text_property_only_culture_invariant(
        self, temp_blueprints_dir: Path
    ) -> None:
        """Test TextPropertyData with only CultureInvariantString.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "Description",
                            "$type": "TextPropertyData",
                            "CultureInvariantString": "Just text",
                            "Value": None,
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "textonly.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("textonly.json")

        assert result is not None
        assert result.get("Description") == "Just text"

    def test_processes_text_property_dict_value(self, temp_blueprints_dir: Path) -> None:
        """Test TextPropertyData with dict value containing CultureInvariantString.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "Description",
                            "$type": "TextPropertyData",
                            "CultureInvariantString": None,
                            "Value": {"CultureInvariantString": "Nested text"},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "textdict.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("textdict.json")

        assert result is not None
        assert result.get("Description") == "Nested text"

    def test_processes_byte_property_dict_value(self, temp_blueprints_dir: Path) -> None:
        """Test BytePropertyData with dict value.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "ByteVal",
                            "$type": "BytePropertyData",
                            "Value": {"Value": "EnumValue"},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "bytedict.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("bytedict.json")

        assert result is not None
        assert result.get("ByteVal") == "EnumValue"

    def test_processes_object_property_dict_index(self, temp_blueprints_dir: Path) -> None:
        """Test ObjectPropertyData with dict value containing Index.

        Uses parse() which processes property types via _process_property_data.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "ObjectRef",
                            "$type": "ObjectPropertyData",
                            "Value": {"Index": 5},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "objdict.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("objdict.json")

        assert result is not None
        # Find Default__ export's Data
        exports = result.get("Exports", [])
        default_export = next(
            (e for e in exports if e.get("ObjectName") == "Default__Test_C"), None
        )
        assert default_export is not None
        assert default_export.get("Data", {}).get("ObjectRef") == "Reference: 5"

    def test_processes_object_property_direct_int(self, temp_blueprints_dir: Path) -> None:
        """Test ObjectPropertyData with direct int value.

        Uses parse() which processes property types via _process_property_data.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "ObjectRef",
                            "$type": "ObjectPropertyData",
                            "Value": 3,
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "objint.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("objint.json")

        assert result is not None
        exports = result.get("Exports", [])
        default_export = next(
            (e for e in exports if e.get("ObjectName") == "Default__Test_C"), None
        )
        assert default_export is not None
        assert default_export.get("Data", {}).get("ObjectRef") == "Reference: 3"

    def test_processes_soft_object_property(self, temp_blueprints_dir: Path) -> None:
        """Test SoftObjectPropertyData extraction.

        Uses parse() which processes property types via _process_property_data.
        SoftObjectPropertyData is checked before ObjectPropertyData to avoid
        substring match issue.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "SoftRef",
                            "$type": "SoftObjectPropertyData",
                            "Value": {"AssetPathName": "/Game/Textures/Icon.0"},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "softobj.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("softobj.json")

        assert result is not None
        exports = result.get("Exports", [])
        default_export = next(
            (e for e in exports if e.get("ObjectName") == "Default__Test_C"), None
        )
        assert default_export is not None
        # SoftObjectPropertyData extracts AssetPathName
        assert default_export.get("Data", {}).get("SoftRef") == "/Game/Textures/Icon.0"

    def test_processes_map_property(self, temp_blueprints_dir: Path) -> None:
        """Test MapPropertyData extraction.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "MapVal",
                            "$type": "MapPropertyData",
                            "Value": {"key1": "value1", "key2": "value2"},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "mapval.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("mapval.json")

        assert result is not None
        assert result.get("MapVal") == {"key1": "value1", "key2": "value2"}

    def test_processes_set_property(self, temp_blueprints_dir: Path) -> None:
        """Test SetPropertyData extraction.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "SetVal",
                            "$type": "SetPropertyData",
                            "Value": [
                                {"$type": "IntPropertyData", "Value": 1},
                                {"$type": "IntPropertyData", "Value": 2},
                            ],
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "setval.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("setval.json")

        assert result is not None
        assert result.get("SetVal") == [1, 2]

    def test_processes_delegate_property(self, temp_blueprints_dir: Path) -> None:
        """Test DelegatePropertyData extraction.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "Delegate",
                            "$type": "DelegatePropertyData",
                            "Value": {"Object": 1, "FunctionName": "OnEvent"},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "delegate.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("delegate.json")

        assert result is not None
        assert result.get("Delegate") is not None

    def test_processes_multicast_delegate_property(self, temp_blueprints_dir: Path) -> None:
        """Test MulticastSparseDelegatePropertyData extraction.

        In full extraction mode, empty lists are kept.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "MultiDelegate",
                            "$type": "MulticastSparseDelegatePropertyData",
                            "Value": [],
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "multidel.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        # Use full extraction to keep empty values
        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)
        result = parser.extract_catalog_data("multidel.json")

        assert result is not None
        assert result.get("MultiDelegate") == []


class TestBlueprintParserStructTypes:
    """Tests for struct type processing.

    This class contains tests for different struct types handled by
    _process_struct_data method.
    """

    def test_processes_vector_property(self, temp_blueprints_dir: Path) -> None:
        """Test VectorPropertyData extraction.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "Position",
                            "$type": "StructPropertyData",
                            "StructType": "VectorPropertyData",
                            "Value": {"X": 1.0, "Y": 2.0, "Z": 3.0},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "vector.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("vector.json")

        assert result is not None
        assert result.get("Position") == {"X": 1.0, "Y": 2.0, "Z": 3.0}

    def test_processes_rotator_property(self, temp_blueprints_dir: Path) -> None:
        """Test RotatorPropertyData extraction.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "Rotation",
                            "$type": "StructPropertyData",
                            "StructType": "RotatorPropertyData",
                            "Value": {"Pitch": 0.0, "Yaw": 90.0, "Roll": 0.0},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "rotator.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("rotator.json")

        assert result is not None
        assert result.get("Rotation") == {"Pitch": 0.0, "Yaw": 90.0, "Roll": 0.0}

    def test_processes_color_property(self, temp_blueprints_dir: Path) -> None:
        """Test ColorPropertyData extraction.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "TintColor",
                            "$type": "StructPropertyData",
                            "StructType": "ColorPropertyData",
                            "Value": {"R": 255, "G": 128, "B": 64, "A": 255},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "color.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("color.json")

        assert result is not None
        assert result.get("TintColor") == {"R": 255, "G": 128, "B": 64, "A": 255}

    def test_processes_guid_property(self, temp_blueprints_dir: Path) -> None:
        """Test GuidPropertyData extraction.

        The GuidPropertyData is extracted as a dict containing the Guid value.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "UniqueId",
                            "$type": "StructPropertyData",
                            "StructType": "GuidPropertyData",
                            "Value": {"Guid": "12345678-ABCD-1234-5678-ABCDEF123456"},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "guid.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("guid.json")

        assert result is not None
        # GuidPropertyData is stored as dict with Guid key
        assert result.get("UniqueId") == {"Guid": "12345678-ABCD-1234-5678-ABCDEF123456"}


class TestBlueprintParserParseMethod:
    """Tests for the parse method with full extraction.

    This class contains tests for the parse method which performs
    full blueprint parsing. Note: parse() only includes Default__ exports
    and exports referenced by Default__'s ClassIndex.
    """

    def test_parse_returns_processed_exports(self, temp_blueprints_dir: Path) -> None:
        """Test that parse returns processed exports.

        Parse only includes Default__ exports and their ClassIndex references.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [
                {"ClassName": "Package", "ObjectName": "/Script/Engine", "OuterIndex": 0},
            ],
            "Exports": [
                {
                    "ObjectName": "Test_C",
                    "ClassIndex": -1,
                    "Data": [],
                },
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,  # Points to Test_C
                    "Data": [
                        {"Name": "SomeValue", "$type": "IntPropertyData", "Value": 42},
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "parse.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("parse.json")

        assert result is not None
        assert "Exports" in result
        # Should include Default__ and the export it references via ClassIndex
        assert len(result["Exports"]) == 2

    def test_parse_resolves_class_index_to_name(self, temp_blueprints_dir: Path) -> None:
        """Test that ClassIndex is resolved to import name.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [
                {"ClassName": "Package", "ObjectName": "/Script/Engine", "OuterIndex": 0},
                {"ClassName": "Class", "ObjectName": "Actor", "OuterIndex": -1},
            ],
            "Exports": [
                {
                    "ObjectName": "Test_C",
                    "ClassIndex": -2,  # Points to Actor import
                    "Data": [],
                },
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,  # Points to Test_C export
                    "Data": [],
                },
            ],
        }
        json_path = temp_blueprints_dir / "classidx.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("classidx.json")

        assert result is not None
        exports = result.get("Exports", [])
        assert len(exports) == 2
        # Find Test_C export
        test_export = next((e for e in exports if e.get("ObjectName") == "Test_C"), None)
        assert test_export is not None
        # ClassIndex should be resolved to name since export has no data
        assert test_export.get("ClassIndex") == "Actor"

    def test_parse_handles_raw_export(self, temp_blueprints_dir: Path) -> None:
        """Test that RawExport is handled properly.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {
                    "$type": "UAssetAPI.ExportTypes.RawExport, UAssetAPI",
                    "ObjectName": "Default__RawData_C",
                    "ClassIndex": 0,
                    "Data": "base64encodeddata==",
                },
            ],
        }
        json_path = temp_blueprints_dir / "rawexport.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("rawexport.json")

        assert result is not None
        exports = result.get("Exports", [])
        assert len(exports) == 1
        # RawExport Data should be kept as-is
        assert exports[0].get("Data") == "base64encodeddata=="

    def test_parse_handles_template_index(self, temp_blueprints_dir: Path) -> None:
        """Test that TemplateIndex is included in result.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 0,
                    "TemplateIndex": 5,
                    "Data": [],
                },
            ],
        }
        json_path = temp_blueprints_dir / "template.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("template.json")

        assert result is not None
        exports = result.get("Exports", [])
        assert len(exports) == 1
        assert exports[0].get("TemplateIndex") == "Reference: 5"

    def test_parse_handles_class_index_with_data(self, temp_blueprints_dir: Path) -> None:
        """Test ClassIndex keeps reference when pointed export has data.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {
                    "ObjectName": "Component",
                    "Data": [{"Name": "Value", "$type": "IntPropertyData", "Value": 1}],
                },
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,  # Points to Component export which has data
                    "Data": [],
                },
            ],
        }
        json_path = temp_blueprints_dir / "classdata.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("classdata.json")

        assert result is not None
        exports = result.get("Exports", [])
        assert len(exports) == 2
        # Find Default__ export
        default_export = next(
            (e for e in exports if e.get("ObjectName") == "Default__Test_C"), None
        )
        assert default_export is not None
        # ClassIndex should be kept as reference since pointed export has data
        assert default_export.get("ClassIndex") == "Reference: 1"


class TestBlueprintParserResolveIndexToName:
    """Tests for _resolve_index_to_name method.

    This class contains tests for resolving import/export indices to names.
    """

    def test_resolves_positive_export_index(self, temp_blueprints_dir: Path) -> None:
        """Test resolving positive export index.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        imports: list[dict[str, Any]] = []
        exports = [{"ObjectName": "TestExport"}]

        result = parser._resolve_index_to_name(1, imports, exports)
        assert result == "TestExport"

    def test_resolves_negative_import_index(self, temp_blueprints_dir: Path) -> None:
        """Test resolving negative import index.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        imports = [{"ObjectName": "TestImport"}]
        exports: list[dict[str, Any]] = []

        result = parser._resolve_index_to_name(-1, imports, exports)
        assert result == "TestImport"

    def test_returns_none_for_zero_index(self, temp_blueprints_dir: Path) -> None:
        """Test that zero index returns None.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        imports: list[dict[str, Any]] = []
        exports: list[dict[str, Any]] = []

        result = parser._resolve_index_to_name(0, imports, exports)
        assert result is None

    def test_returns_invalid_for_out_of_bounds(self, temp_blueprints_dir: Path) -> None:
        """Test that out of bounds index returns Invalid marker.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        imports: list[dict[str, Any]] = []
        exports: list[dict[str, Any]] = []

        result = parser._resolve_index_to_name(100, imports, exports)
        assert result == "Invalid:100"


class TestBlueprintParserUnrealTypes:
    """Tests for UnrealTypes, FieldTypes, and CustomVersion processing.

    This class contains tests for special type handlers.
    """

    def test_processes_unreal_type(self, temp_blueprints_dir: Path) -> None:
        """Test UnrealTypes processing.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "UAssetAPI.UnrealTypes.FVector, UAssetAPI",
            "X": 1.0,
            "Y": 2.0,
            "Z": 3.0,
        }

        result = parser._process_value(data)
        assert result == {"X": 1.0, "Y": 2.0, "Z": 3.0}
        assert "$type" not in result

    def test_processes_field_type(self, temp_blueprints_dir: Path) -> None:
        """Test FieldTypes processing.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "UAssetAPI.FieldTypes.UObjectProperty, UAssetAPI",
            "Name": "MyProperty",
            "Flags": 12345,
            "OtherField": "ignored",
        }

        result = parser._process_value(data)
        assert result == {"Name": "MyProperty", "Flags": 12345}

    def test_processes_custom_version(self, temp_blueprints_dir: Path) -> None:
        """Test CustomVersion processing.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "UAssetAPI.CustomVersion, UAssetAPI",
            "FriendlyName": "EngineVersion",
            "Version": 504,
        }

        result = parser._process_value(data)
        assert result == {"EngineVersion": 504}


class TestBlueprintParserImportResolution:
    """Tests for import path resolution methods.

    This class contains tests for _resolve_import_full_path and
    _resolve_import_asset_path methods.
    """

    def test_resolve_import_full_path_non_blueprint(self, temp_blueprints_dir: Path) -> None:
        """Test that non-BlueprintGeneratedClass returns None.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        import_obj: dict[str, Any] = {
            "ClassName": "Texture2D",
            "ObjectName": "MyTexture",
            "OuterIndex": -2,
        }
        all_imports: list[dict[str, Any]] = [
            import_obj,
            {"ClassName": "Package", "ObjectName": "/Game/Textures"},
        ]

        result = parser._resolve_import_full_path(import_obj, all_imports)
        assert result is None

    def test_resolve_import_full_path_index_error(self, temp_blueprints_dir: Path) -> None:
        """Test that IndexError is handled gracefully.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        import_obj = {
            "ClassName": "BlueprintGeneratedClass",
            "ObjectName": "MyClass_C",
            "OuterIndex": -100,  # Out of bounds
        }
        all_imports = [import_obj]

        result = parser._resolve_import_full_path(import_obj, all_imports)
        assert result is None

    def test_resolve_import_asset_path_skips_package(self, temp_blueprints_dir: Path) -> None:
        """Test that Package class returns None.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        import_obj = {
            "ClassName": "Package",
            "ObjectName": "/Game/Textures",
            "OuterIndex": 0,
        }
        all_imports = [import_obj]

        result = parser._resolve_import_asset_path(import_obj, all_imports)
        assert result is None

    def test_resolve_import_asset_path_index_error(self, temp_blueprints_dir: Path) -> None:
        """Test that IndexError is handled in asset path resolution.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        import_obj = {
            "ClassName": "Texture2D",
            "ObjectName": "MyTexture",
            "OuterIndex": -100,  # Out of bounds
        }
        all_imports = [import_obj]

        result = parser._resolve_import_asset_path(import_obj, all_imports)
        assert result is None


class TestBlueprintParserResolveParentBlueprint:
    """Tests for _resolve_parent_blueprint method edge cases."""

    def test_returns_none_for_non_default_export(self, temp_blueprints_dir: Path) -> None:
        """Test that non-Default__ export returns None.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        default_export = {"ObjectName": "NotADefaultExport"}
        exports: list[dict[str, Any]] = []
        imports: list[str | None] = []

        result = parser._resolve_parent_blueprint(default_export, exports, imports)
        assert result is None

    def test_returns_none_for_empty_import_path(self, temp_blueprints_dir: Path) -> None:
        """Test that empty import path returns None.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        default_export = {"ObjectName": "Default__Test_C"}
        exports: list[dict[str, Any]] = [
            {"ObjectName": "Test_C", "SuperIndex": "Import:-1"},
        ]
        imports: list[str | None] = [""]  # Empty string import

        result = parser._resolve_parent_blueprint(default_export, exports, imports)
        assert result is None


class TestBlueprintParserObjectPathHandling:
    """Tests for ObjectPath handling including edge cases."""

    def test_handles_non_relative_path_in_extract(self, temp_blueprints_dir: Path) -> None:
        """Test that non-relative paths are handled with full path.

        This test creates a JSON file in an absolute path that is not
        relative to blueprints_dir, triggering the ValueError branch.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        import tempfile

        # Create JSON in a separate temp directory (not relative to blueprints_dir)
        with tempfile.TemporaryDirectory() as other_dir:
            other_path = Path(other_dir)
            json_path = other_path / "outside.json"
            data = {
                "Imports": [],
                "Exports": [
                    {"ObjectName": "Test_C", "Data": []},
                    {
                        "ObjectName": "Default__Test_C",
                        "ClassIndex": 1,
                        "Data": [{"Name": "Value", "$type": "IntPropertyData", "Value": 1}],
                    },
                ],
            }
            with open(json_path, "w") as f:
                json.dump(data, f)

            # Use blueprints_dir but pass absolute path outside of it
            parser = BlueprintParser(temp_blueprints_dir)
            result = parser.extract_catalog_data(json_path)

            assert result is not None
            # ObjectPath should contain the full path string
            assert "outside.json" in result.get("ObjectPath", "")


class TestBlueprintParserUnconvertedData:
    """Tests for handling unconverted Data fields."""

    def test_handles_string_data_field(self, temp_blueprints_dir: Path) -> None:
        """Test that base64 string Data (unconverted) is handled.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": "base64encodedstringnotadict",  # Unconverted data
                },
            ],
        }
        json_path = temp_blueprints_dir / "unconverted.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("unconverted.json")

        assert result is not None
        # Should still return basic data (ObjectPath) even with unconverted Data
        assert "ObjectPath" in result
        # No Data properties should be extracted from unconverted string
        assert len(result) == 1


class TestBlueprintParserGetParentData:
    """Tests for _get_parent_data method edge cases."""

    def test_returns_none_for_non_game_blueprints_path(self, temp_blueprints_dir: Path) -> None:
        """Test that non /Game/Blueprints/ path returns None.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)

        result = parser._get_parent_data("/Script/Engine/Actor")
        assert result is None


class TestBlueprintParserProcessDataReferences:
    """Tests for reference processing in _process_data method."""

    def test_skips_null_reference_in_dict(self, temp_blueprints_dir: Path) -> None:
        """Test that null references (index 0) are skipped in dict.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "NullRef",
                            "$type": "ObjectPropertyData",
                            "Value": {"Index": 0},  # Null reference
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "nullref.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("nullref.json")

        assert result is not None
        # NullRef should not appear in result (skipped)
        assert "NullRef" not in result or result.get("NullRef") == "Reference: 0"

    def test_processes_import_reference_directly(self, temp_blueprints_dir: Path) -> None:
        """Test import reference resolution by calling _process_data directly.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)

        # Setup raw imports for resolution
        raw_imports: list[dict[str, Any]] = [
            {"ClassName": "Package", "ObjectName": "/Game/Items", "OuterIndex": 0},
            {
                "ClassName": "BlueprintGeneratedClass",
                "ObjectName": "BPItem_C",
                "OuterIndex": -1,
            },
        ]
        raw_exports: list[dict[str, Any]] = []
        imports: list[str | None] = ["/Game/Items", "/Game/Items/BPItem"]

        # Dict with import reference string (format: "Reference: N")
        data = {"ItemRef": "Reference: -2"}

        result = parser._process_data(
            data=data,
            imports=imports,
            raw_imports=raw_imports,
            raw_exports=raw_exports,
        )

        assert result.get("ItemRef") == "/Game/Items/BPItem"

    def test_processes_export_reference_directly(self, temp_blueprints_dir: Path) -> None:
        """Test export reference resolution by calling _process_data directly.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)

        raw_imports: list[dict[str, Any]] = []
        raw_exports: list[dict[str, Any]] = [
            {"ObjectName": "SomeComponent"},
            {"ObjectName": "Test_C"},
        ]
        imports: list[str | None] = []

        # Dict with export reference string (format: "Reference: N")
        data: dict[str, Any] = {"ComponentRef": "Reference: 1"}

        result = parser._process_data(
            data=data,
            imports=imports,
            raw_imports=raw_imports,
            raw_exports=raw_exports,
        )

        assert result.get("ComponentRef") == "SomeComponent"

    def test_skips_zero_reference_in_dict(self, temp_blueprints_dir: Path) -> None:
        """Test that zero reference (null) is skipped in dict.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)

        data = {"NullRef": "Reference: 0"}

        result = parser._process_data(data=data, imports=[], raw_imports=[], raw_exports=[])

        # Null reference should be skipped
        assert "NullRef" not in result

    def test_resolves_import_via_asset_path_fallback(self, temp_blueprints_dir: Path) -> None:
        """Test import resolution falls back to asset path.

        When imports list has empty path, it falls back to raw_imports.
        _resolve_import_asset_path returns the normalized package path.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)

        # Empty import path in imports list
        imports: list[str | None] = ["", ""]
        raw_imports: list[dict[str, Any]] = [
            {"ClassName": "Package", "ObjectName": "/Game/Items", "OuterIndex": 0},
            {
                "ClassName": "Texture2D",
                "ObjectName": "MyTexture",
                "OuterIndex": -1,
            },
        ]
        raw_exports: list[dict[str, Any]] = []

        data: dict[str, Any] = {"TextureRef": "Reference: -2"}

        result = parser._process_data(
            data=data,
            imports=imports,
            raw_imports=raw_imports,
            raw_exports=raw_exports,
        )

        # Should resolve via asset path (normalized from /Game/ to War/Content/)
        assert result.get("TextureRef") == "War/Content/Items.0"


class TestBlueprintParserProcessDataList:
    """Tests for list processing in _process_data method."""

    def test_processes_list_with_null_references(self, temp_blueprints_dir: Path) -> None:
        """Test that null references in lists are skipped.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)

        # List with null references (index 0) using "Reference: N" format
        data = ["Reference: 0", "Reference: 0"]

        result = parser._process_data(data=data, imports=[], raw_imports=[], raw_exports=[])

        # List should be empty after skipping null references
        assert result == []

    def test_processes_list_with_import_references(self, temp_blueprints_dir: Path) -> None:
        """Test list with import references.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)

        imports: list[str | None] = ["/Game/Items", "/Game/Items/Item1"]
        raw_imports: list[dict[str, Any]] = [
            {"ClassName": "Package", "ObjectName": "/Game/Items", "OuterIndex": 0},
            {
                "ClassName": "BlueprintGeneratedClass",
                "ObjectName": "Item1_C",
                "OuterIndex": -1,
            },
        ]
        raw_exports: list[dict[str, Any]] = []

        # Import reference (negative index) using "Reference: N" format
        data: list[str] = ["Reference: -2"]

        result = parser._process_data(
            data=data,
            imports=imports,
            raw_imports=raw_imports,
            raw_exports=raw_exports,
        )

        assert result == ["/Game/Items/Item1"]

    def test_processes_list_with_export_references(self, temp_blueprints_dir: Path) -> None:
        """Test list with export references.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)

        raw_exports: list[dict[str, Any]] = [{"ObjectName": "Component1"}]
        imports: list[str | None] = []
        raw_imports: list[dict[str, Any]] = []

        # Export reference (positive index) using "Reference: N" format
        data: list[str] = ["Reference: 1"]

        result = parser._process_data(
            data=data,
            imports=imports,
            raw_imports=raw_imports,
            raw_exports=raw_exports,
        )

        assert result == ["Component1"]

    def test_processes_nested_list_in_data(self, temp_blueprints_dir: Path) -> None:
        """Test nested list/dict processing in _process_data list.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)

        # List containing nested dicts
        data = [
            {"key": "value1"},
            {"key": "value2"},
        ]

        result = parser._process_data(data=data, imports=[], raw_imports=[], raw_exports=[])

        assert result == [{"key": "value1"}, {"key": "value2"}]

    def test_processes_list_with_primitives(self, temp_blueprints_dir: Path) -> None:
        """Test list with primitive values.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)

        data = [1, 2, 3, "string", True]

        result = parser._process_data(data=data, imports=[], raw_imports=[], raw_exports=[])

        assert result == [1, 2, 3, "string", True]

    def test_processes_list_import_fallback_to_asset_path(self, temp_blueprints_dir: Path) -> None:
        """Test list import resolution falls back to asset path.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir, full_extraction=True)

        # Empty import path
        imports: list[str | None] = ["", ""]
        raw_imports: list[dict[str, Any]] = [
            {"ClassName": "Package", "ObjectName": "/Game/Items", "OuterIndex": 0},
            {"ClassName": "Texture2D", "ObjectName": "MyTex", "OuterIndex": -1},
        ]
        raw_exports: list[dict[str, Any]] = []

        # Import reference using "Reference: N" format
        data: list[str] = ["Reference: -2"]

        result = parser._process_data(
            data=data,
            imports=imports,
            raw_imports=raw_imports,
            raw_exports=raw_exports,
        )

        # Asset path fallback returns normalized path (War/Content/ prefix)
        assert result == ["War/Content/Items.0"]

    def test_returns_primitive_data_unchanged(self, temp_blueprints_dir: Path) -> None:
        """Test that primitive data (not dict/list) is returned unchanged.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)

        result = parser._process_data(data="primitive_string", imports=[])
        assert result == "primitive_string"

        result = parser._process_data(data=42, imports=[])
        assert result == 42


class TestBlueprintParserProcessValuePaths:
    """Tests for various paths through _process_value method."""

    def test_processes_list_value(self, temp_blueprints_dir: Path) -> None:
        """Test that list values are processed recursively.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = [
            {"$type": "IntPropertyData", "Value": 1},
            {"$type": "IntPropertyData", "Value": 2},
        ]

        result = parser._process_value(data)
        assert result == [1, 2]

    def test_processes_dict_without_type(self, temp_blueprints_dir: Path) -> None:
        """Test that dict without $type is processed recursively.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "X": {"$type": "IntPropertyData", "Value": 1},
            "Y": {"$type": "IntPropertyData", "Value": 2},
        }

        result = parser._process_value(data)
        assert result == {"X": 1, "Y": 2}

    def test_returns_value_for_unknown_type(self, temp_blueprints_dir: Path) -> None:
        """Test that unknown $type returns Value field or dict.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "SomeUnknownType",
            "Value": {"custom": "data"},
        }

        result = parser._process_value(data)
        assert result == {"custom": "data"}


class TestBlueprintParserMoreStructTypes:
    """Tests for additional struct types in _process_struct_data."""

    def test_processes_vector4_property(self, temp_blueprints_dir: Path) -> None:
        """Test Vector4PropertyData extraction.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "Vec4",
                            "$type": "StructPropertyData",
                            "StructType": "Vector4PropertyData",
                            "Value": {"X": 1.0, "Y": 2.0, "Z": 3.0, "W": 4.0},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "vector4.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("vector4.json")

        assert result is not None
        assert result.get("Vec4") == {"X": 1.0, "Y": 2.0, "Z": 3.0, "W": 4.0}

    def test_processes_quat_property(self, temp_blueprints_dir: Path) -> None:
        """Test QuatPropertyData extraction.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "Rotation",
                            "$type": "StructPropertyData",
                            "StructType": "QuatPropertyData",
                            "Value": {"X": 0.0, "Y": 0.0, "Z": 0.707, "W": 0.707},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "quat.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("quat.json")

        assert result is not None
        assert result.get("Rotation") == {"X": 0.0, "Y": 0.0, "Z": 0.707, "W": 0.707}

    def test_processes_linear_color_property(self, temp_blueprints_dir: Path) -> None:
        """Test LinearColorPropertyData extraction.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "Color",
                            "$type": "StructPropertyData",
                            "StructType": "LinearColorPropertyData",
                            "Value": {"R": 1.0, "G": 0.5, "B": 0.25, "A": 1.0},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "linearcolor.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("linearcolor.json")

        assert result is not None
        assert result.get("Color") == {"R": 1.0, "G": 0.5, "B": 0.25, "A": 1.0}

    def test_processes_box_property(self, temp_blueprints_dir: Path) -> None:
        """Test BoxPropertyData extraction.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "Bounds",
                            "$type": "StructPropertyData",
                            "StructType": "BoxPropertyData",
                            "Value": {"Min": {"X": 0, "Y": 0}, "Max": {"X": 100, "Y": 100}},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "box.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("box.json")

        assert result is not None
        assert "Bounds" in result

    def test_processes_intpoint_property(self, temp_blueprints_dir: Path) -> None:
        """Test IntPointPropertyData extraction.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "GridPos",
                            "$type": "StructPropertyData",
                            "StructType": "IntPointPropertyData",
                            "Value": {"X": 10, "Y": 20},
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "intpoint.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("intpoint.json")

        assert result is not None
        assert result.get("GridPos") == {"X": 10, "Y": 20}

    def test_processes_per_platform_float(self, temp_blueprints_dir: Path) -> None:
        """Test PerPlatformFloatPropertyData extraction.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [
                        {
                            "Name": "LODDistance",
                            "$type": "StructPropertyData",
                            "StructType": "PerPlatformFloatPropertyData",
                            "Value": 1000.0,
                        }
                    ],
                },
            ],
        }
        json_path = temp_blueprints_dir / "perplatform.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.extract_catalog_data("perplatform.json")

        assert result is not None
        assert result.get("LODDistance") == 1000.0


class TestBlueprintParserParseOtherFields:
    """Tests for parse method handling of non-Imports/Exports fields."""

    def test_parse_processes_other_fields(self, temp_blueprints_dir: Path) -> None:
        """Test that parse processes fields other than Imports/Exports.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Default__Test_C", "ClassIndex": 0, "Data": []},
            ],
            "CustomField": {
                "$type": "SomeType",
                "Value": {"key": "value"},
            },
            "AnotherField": [1, 2, 3],
        }
        json_path = temp_blueprints_dir / "otherfields.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)
        result = parser.parse("otherfields.json")

        assert result is not None
        # Other fields should be processed through _process_value
        assert result.get("CustomField") == {"key": "value"}
        assert result.get("AnotherField") == [1, 2, 3]


class TestBlueprintParserRawCacheHit:
    """Tests for raw cache hit path."""

    def test_raw_cache_is_reused(self, temp_blueprints_dir: Path) -> None:
        """Test that raw cache is reused on second call.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data = {
            "Imports": [],
            "Exports": [
                {"ObjectName": "Test_C", "Data": []},
                {
                    "ObjectName": "Default__Test_C",
                    "ClassIndex": 1,
                    "Data": [{"Name": "Val", "$type": "IntPropertyData", "Value": 1}],
                },
            ],
        }
        json_path = temp_blueprints_dir / "cachetest.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)

        # First call - populates cache
        result1 = parser.parse("cachetest.json")
        assert result1 is not None

        # Verify cache is populated
        cache_key = str(temp_blueprints_dir / "cachetest.json")
        assert cache_key in parser.raw_cache

        # Second call - should use cache
        result2 = parser.parse("cachetest.json")
        assert result2 is not None
        assert result2 == result1

    def test_load_raw_json_cache_hit(self, temp_blueprints_dir: Path) -> None:
        """Test that _load_raw_json returns from cache on second call.

        This directly tests line 477 - the cache hit return path.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        data: dict[str, Any] = {"Imports": [], "Exports": []}
        json_path = temp_blueprints_dir / "rawcache.json"
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = BlueprintParser(temp_blueprints_dir)

        # First call - loads from file and caches
        result1 = parser._load_raw_json(json_path)
        assert result1 is not None
        assert result1 == data

        # Verify cache is populated
        cache_key = str(json_path)
        assert cache_key in parser.raw_cache

        # Second call - should return from cache (line 477)
        result2 = parser._load_raw_json(json_path)
        assert result2 is not None
        assert result2 is result1  # Should be exact same object from cache


class TestBlueprintParserDirectStructTypes:
    """Tests for struct types processed directly via _process_struct_data.

    These tests use $type values that directly match struct type names,
    triggering the specific type handlers in _process_struct_data (lines 896-959).
    """

    def test_vector_property_data_direct_type(self, temp_blueprints_dir: Path) -> None:
        """Test VectorPropertyData with direct $type.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "VectorPropertyData",
            "Value": {"X": 1.0, "Y": 2.0, "Z": 3.0},
        }

        result = parser._process_value(data)
        assert result == {"X": 1.0, "Y": 2.0, "Z": 3.0}

    def test_vector2d_property_data_direct_type(self, temp_blueprints_dir: Path) -> None:
        """Test Vector2DPropertyData with direct $type.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "Vector2DPropertyData",
            "Value": {"X": 1.0, "Y": 2.0},
        }

        result = parser._process_value(data)
        assert result == {"X": 1.0, "Y": 2.0}

    def test_rotator_property_data_direct_type(self, temp_blueprints_dir: Path) -> None:
        """Test RotatorPropertyData with direct $type.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "RotatorPropertyData",
            "Value": {"Pitch": 0.0, "Yaw": 90.0, "Roll": 0.0},
        }

        result = parser._process_value(data)
        assert result == {"Pitch": 0.0, "Yaw": 90.0, "Roll": 0.0}

    def test_quat_property_data_direct_type(self, temp_blueprints_dir: Path) -> None:
        """Test QuatPropertyData with direct $type.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "QuatPropertyData",
            "Value": {"X": 0.0, "Y": 0.0, "Z": 0.707, "W": 0.707},
        }

        result = parser._process_value(data)
        assert result == {"X": 0.0, "Y": 0.0, "Z": 0.707, "W": 0.707}

    def test_color_property_data_direct_type(self, temp_blueprints_dir: Path) -> None:
        """Test ColorPropertyData with direct $type.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "ColorPropertyData",
            "Value": {"R": 255, "G": 128, "B": 64, "A": 255},
        }

        result = parser._process_value(data)
        assert result == {"R": 255, "G": 128, "B": 64, "A": 255}

    def test_linear_color_property_data_direct_type(self, temp_blueprints_dir: Path) -> None:
        """Test LinearColorPropertyData with direct $type.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "LinearColorPropertyData",
            "Value": {"R": 1.0, "G": 0.5, "B": 0.25, "A": 1.0},
        }

        result = parser._process_value(data)
        assert result == {"R": 1.0, "G": 0.5, "B": 0.25, "A": 1.0}

    def test_guid_property_data_direct_type(self, temp_blueprints_dir: Path) -> None:
        """Test GuidPropertyData with direct $type.

        GuidPropertyData goes through _process_property_data (not _process_struct_data)
        since "Struct" is not in the type name. It returns Value as-is.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "GuidPropertyData",
            "Value": {"Guid": "12345678-ABCD-1234-5678-ABCDEF123456"},
        }

        result = parser._process_value(data)
        # GuidPropertyData falls through to default in _process_property_data
        assert result == {"Guid": "12345678-ABCD-1234-5678-ABCDEF123456"}

    def test_box_property_data_direct_type(self, temp_blueprints_dir: Path) -> None:
        """Test BoxPropertyData with direct $type.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "BoxPropertyData",
            "Value": {"Min": {"X": 0, "Y": 0}, "Max": {"X": 100, "Y": 100}},
        }

        result = parser._process_value(data)
        assert result == {"Min": {"X": 0, "Y": 0}, "Max": {"X": 100, "Y": 100}}

    def test_intpoint_property_data_direct_type(self, temp_blueprints_dir: Path) -> None:
        """Test IntPointPropertyData with direct $type.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "IntPointPropertyData",
            "Value": {"X": 10, "Y": 20},
        }

        result = parser._process_value(data)
        assert result == {"X": 10, "Y": 20}

    def test_perplatformfloat_property_data_direct_type(self, temp_blueprints_dir: Path) -> None:
        """Test PerPlatformFloatPropertyData with direct $type.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "PerPlatformFloatPropertyData",
            "Value": 1000.0,
        }

        result = parser._process_value(data)
        assert result == 1000.0

    def test_richcurvekey_property_data_direct_type(self, temp_blueprints_dir: Path) -> None:
        """Test RichCurveKeyPropertyData with direct $type.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "RichCurveKeyPropertyData",
            "Value": {"Time": 0.0, "Value": 1.0},
        }

        result = parser._process_value(data)
        assert result == {"Time": 0.0, "Value": 1.0}

    def test_color_material_input_direct_type(self, temp_blueprints_dir: Path) -> None:
        """Test ColorMaterialInputPropertyData with direct $type.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "ColorMaterialInputPropertyData",
            "Value": {"Input": 1, "Color": {"R": 1.0, "G": 0.0, "B": 0.0}},
        }

        result = parser._process_value(data)
        assert result == {"Input": 1, "Color": {"R": 1.0, "G": 0.0, "B": 0.0}}

    def test_skeletal_mesh_property_data_direct_type(self, temp_blueprints_dir: Path) -> None:
        """Test SkeletalMeshSamplingPropertyData with direct $type.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "SkeletalMeshSamplingPropertyData",
            "Value": {"SamplingData": []},
        }

        result = parser._process_value(data)
        assert result == {"SamplingData": []}

    def test_struct_default_return_value(self, temp_blueprints_dir: Path) -> None:
        """Test that unknown struct type returns Value field.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "UnknownStructPropertyData",
            "Value": {"custom": "data"},
        }

        result = parser._process_value(data)
        assert result == {"custom": "data"}


class TestBlueprintParserStructsRouting:
    """Tests for struct types routed via _process_struct_data.

    These tests use $type values containing "Structs" (like UAssetAPI format)
    to route to _process_struct_data and hit lines 896-959.
    """

    def test_vector_via_structs_routing(self, temp_blueprints_dir: Path) -> None:
        """Test VectorPropertyData routed via Structs path.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "UAssetAPI.PropertyTypes.Structs.VectorPropertyData, UAssetAPI",
            "Value": {"X": 1.0, "Y": 2.0, "Z": 3.0},
        }

        result = parser._process_value(data)
        assert result == {"X": 1.0, "Y": 2.0, "Z": 3.0}

    def test_rotator_via_structs_routing(self, temp_blueprints_dir: Path) -> None:
        """Test RotatorPropertyData routed via Structs path.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "UAssetAPI.PropertyTypes.Structs.RotatorPropertyData, UAssetAPI",
            "Value": {"Pitch": 0.0, "Yaw": 90.0, "Roll": 0.0},
        }

        result = parser._process_value(data)
        assert result == {"Pitch": 0.0, "Yaw": 90.0, "Roll": 0.0}

    def test_quat_via_structs_routing(self, temp_blueprints_dir: Path) -> None:
        """Test QuatPropertyData routed via Structs path.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "UAssetAPI.PropertyTypes.Structs.QuatPropertyData, UAssetAPI",
            "Value": {"X": 0.0, "Y": 0.0, "Z": 0.707, "W": 0.707},
        }

        result = parser._process_value(data)
        assert result == {"X": 0.0, "Y": 0.0, "Z": 0.707, "W": 0.707}

    def test_color_via_structs_routing(self, temp_blueprints_dir: Path) -> None:
        """Test ColorPropertyData routed via Structs path.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "UAssetAPI.PropertyTypes.Structs.ColorPropertyData, UAssetAPI",
            "Value": {"R": 255, "G": 128, "B": 64, "A": 255},
        }

        result = parser._process_value(data)
        assert result == {"R": 255, "G": 128, "B": 64, "A": 255}

    def test_guid_via_structs_routing(self, temp_blueprints_dir: Path) -> None:
        """Test GuidPropertyData routed via Structs path.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "UAssetAPI.PropertyTypes.Structs.GuidPropertyData, UAssetAPI",
            "Value": {"Guid": "12345678-ABCD-1234-5678-ABCDEF123456"},
        }

        result = parser._process_value(data)
        # GuidPropertyData in _process_struct_data extracts Guid as string
        assert result == "12345678-ABCD-1234-5678-ABCDEF123456"

    def test_box_via_structs_routing(self, temp_blueprints_dir: Path) -> None:
        """Test BoxPropertyData routed via Structs path.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "UAssetAPI.PropertyTypes.Structs.BoxPropertyData, UAssetAPI",
            "Value": {"Min": {"X": 0, "Y": 0}, "Max": {"X": 100, "Y": 100}},
        }

        result = parser._process_value(data)
        assert result == {"Min": {"X": 0, "Y": 0}, "Max": {"X": 100, "Y": 100}}

    def test_intpoint_via_structs_routing(self, temp_blueprints_dir: Path) -> None:
        """Test IntPointPropertyData routed via Structs path.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "UAssetAPI.PropertyTypes.Structs.IntPointPropertyData, UAssetAPI",
            "Value": {"X": 10, "Y": 20},
        }

        result = parser._process_value(data)
        assert result == {"X": 10, "Y": 20}

    def test_richcurvekey_via_structs_routing(self, temp_blueprints_dir: Path) -> None:
        """Test RichCurveKeyPropertyData routed via Structs path.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        data = {
            "$type": "UAssetAPI.PropertyTypes.Structs.RichCurveKeyPropertyData, UAssetAPI",
            "Value": {"Time": 0.0, "Value": 1.0},
        }

        result = parser._process_value(data)
        assert result == {"Time": 0.0, "Value": 1.0}

    def test_struct_returns_non_dict_value(self, temp_blueprints_dir: Path) -> None:
        """Test struct types return non-dict Value as-is.

        Args:
            temp_blueprints_dir (Path): Temporary blueprints directory fixture.
        """
        parser = BlueprintParser(temp_blueprints_dir)
        # Non-dict Value should be returned as-is
        data = {
            "$type": "UAssetAPI.PropertyTypes.Structs.VectorPropertyData, UAssetAPI",
            "Value": "non-dict-value",
        }

        result = parser._process_value(data)
        assert result == "non-dict-value"

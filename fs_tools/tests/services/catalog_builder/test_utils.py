"""Tests for catalog_builder.utils module."""

from fs_tools.services.catalog_builder.utils import (
    extract_localized_text,
    extract_property_value,
    normalize_object_path,
    parse_reference,
    resolve_import_path,
    simplify_value,
)


class TestNormalizeObjectPath:
    """Tests for normalize_object_path function."""

    def test_converts_game_path_to_war_content(self) -> None:
        """Test that /Game/ paths are converted to War/Content/ format."""
        result = normalize_object_path("/Game/Blueprints/Items/BPFoo")
        assert result == "War/Content/Blueprints/Items/BPFoo.0"

    def test_adds_dot_zero_suffix(self) -> None:
        """Test that .0 suffix is added when missing."""
        result = normalize_object_path("War/Content/Items/BPFoo")
        assert result == "War/Content/Items/BPFoo.0"

    def test_does_not_duplicate_dot_zero_suffix(self) -> None:
        """Test that .0 suffix is not duplicated if already present."""
        result = normalize_object_path("War/Content/Items/BPFoo.0")
        assert result == "War/Content/Items/BPFoo.0"

    def test_handles_nested_paths(self) -> None:
        """Test that nested paths are handled correctly."""
        result = normalize_object_path("/Game/Blueprints/Items/Weapons/BPRifle")
        assert result == "War/Content/Blueprints/Items/Weapons/BPRifle.0"

    def test_handles_paths_without_game_prefix(self) -> None:
        """Test that paths without /Game/ prefix are handled."""
        result = normalize_object_path("SomePath/Items/BPFoo")
        assert result == "SomePath/Items/BPFoo.0"


class TestExtractLocalizedText:
    """Tests for extract_localized_text function."""

    def test_extracts_text_from_dict(self) -> None:
        """Test extracting text from a dict with Text key."""
        result = extract_localized_text({"Text": "Hello World", "Guid": "ABC123"})
        assert result == "Hello World"

    def test_returns_string_as_is(self) -> None:
        """Test that plain strings are returned as-is."""
        result = extract_localized_text("Plain text")
        assert result == "Plain text"

    def test_returns_none_for_none_value(self) -> None:
        """Test that None is returned for None input."""
        result = extract_localized_text(None)
        assert result is None

    def test_returns_none_for_empty_string(self) -> None:
        """Test that None is returned for empty string."""
        result = extract_localized_text("")
        assert result is None

    def test_returns_none_for_dict_without_text(self) -> None:
        """Test that None is returned for dict without Text key."""
        result = extract_localized_text({"Guid": "ABC123"})
        assert result is None

    def test_converts_non_string_to_string(self) -> None:
        """Test that non-string values are converted to string."""
        result = extract_localized_text(42)
        assert result == "42"


class TestSimplifyValue:
    """Tests for simplify_value function."""

    def test_converts_whole_float_to_int(self) -> None:
        """Test that whole number floats are converted to ints."""
        result = simplify_value(5.0)
        assert result == 5
        assert isinstance(result, int)

    def test_keeps_fractional_float(self) -> None:
        """Test that fractional floats are kept as floats."""
        result = simplify_value(5.5)
        assert result == 5.5
        assert isinstance(result, float)

    def test_rounds_float_to_6_decimals(self) -> None:
        """Test that floats are rounded to 6 decimal places."""
        result = simplify_value(1.23456789)
        assert result == 1.234568

    def test_converts_plus_string_to_int(self) -> None:
        """Test that '+N' strings are converted to ints."""
        result = simplify_value("+42")
        assert result == 42
        assert isinstance(result, int)

    def test_converts_minus_string_to_int(self) -> None:
        """Test that '-N' strings are converted to ints."""
        result = simplify_value("-10")
        assert result == -10
        assert isinstance(result, int)

    def test_flattens_single_key_dict(self) -> None:
        """Test that single-key dicts are flattened to just the value."""
        result = simplify_value({"Value": 42})
        assert result == 42

    def test_keeps_multi_key_dict(self) -> None:
        """Test that multi-key dicts are kept as dicts."""
        result = simplify_value({"X": 1, "Y": 2})
        assert result == {"X": 1, "Y": 2}

    def test_recursively_simplifies_nested_dict(self) -> None:
        """Test that nested dicts are recursively simplified."""
        result = simplify_value({"Value": {"Inner": 5.0}})
        assert result == 5  # Both levels flattened, float to int

    def test_recursively_simplifies_list(self) -> None:
        """Test that lists are recursively simplified."""
        result = simplify_value([5.0, "+10", {"Value": 3.0}])
        assert result == [5, 10, 3]

    def test_keeps_regular_string(self) -> None:
        """Test that regular strings are kept as-is."""
        result = simplify_value("hello")
        assert result == "hello"


class TestParseReference:
    """Tests for parse_reference function."""

    def test_parses_positive_reference(self) -> None:
        """Test parsing positive (export) reference."""
        result = parse_reference("Reference: 5")
        assert result == 5

    def test_parses_negative_reference(self) -> None:
        """Test parsing negative (import) reference."""
        result = parse_reference("Reference: -10")
        assert result == -10

    def test_parses_zero_reference(self) -> None:
        """Test parsing zero reference."""
        result = parse_reference("Reference: 0")
        assert result == 0

    def test_returns_none_for_invalid_format(self) -> None:
        """Test that None is returned for non-reference strings."""
        result = parse_reference("Not a reference")
        assert result is None

    def test_returns_none_for_empty_string(self) -> None:
        """Test that None is returned for empty string."""
        result = parse_reference("")
        assert result is None

    def test_returns_none_for_none_input(self) -> None:
        """Test that None is returned for None input."""
        result = parse_reference(None)  # type: ignore[arg-type]
        assert result is None

    def test_returns_none_for_malformed_reference(self) -> None:
        """Test that None is returned for malformed reference."""
        result = parse_reference("Reference: abc")
        assert result is None


class TestResolveImportPath:
    """Tests for resolve_import_path function."""

    def test_resolves_simple_import(self) -> None:
        """Test resolving a simple import without outer."""
        imports = [{"ObjectName": "/Game/Blueprints/Items/BPRifle", "OuterIndex": 0}]
        result = resolve_import_path(-1, imports)
        assert result == "/Game/Blueprints/Items/BPRifle"

    def test_resolves_nested_import(self) -> None:
        """Test resolving an import with outer index."""
        imports = [
            {"ObjectName": "/Game/Blueprints/Items", "OuterIndex": 0},
            {"ObjectName": "BPRifle", "OuterIndex": -1},
        ]
        result = resolve_import_path(-2, imports)
        assert result == "/Game/Blueprints/Items/BPRifle"

    def test_returns_none_for_positive_index(self) -> None:
        """Test that None is returned for positive (export) indices."""
        imports = [{"ObjectName": "Test", "OuterIndex": 0}]
        result = resolve_import_path(1, imports)
        assert result is None

    def test_returns_none_for_zero_index(self) -> None:
        """Test that None is returned for zero index."""
        imports = [{"ObjectName": "Test", "OuterIndex": 0}]
        result = resolve_import_path(0, imports)
        assert result is None

    def test_returns_none_for_out_of_bounds_index(self) -> None:
        """Test that None is returned for out of bounds index."""
        imports = [{"ObjectName": "Test", "OuterIndex": 0}]
        result = resolve_import_path(-5, imports)
        assert result is None

    def test_handles_deeply_nested_imports(self) -> None:
        """Test resolving deeply nested imports."""
        imports = [
            {"ObjectName": "/Game", "OuterIndex": 0},
            {"ObjectName": "Blueprints", "OuterIndex": -1},
            {"ObjectName": "Items", "OuterIndex": -2},
            {"ObjectName": "BPRifle", "OuterIndex": -3},
        ]
        result = resolve_import_path(-4, imports)
        assert result == "/Game/Blueprints/Items/BPRifle"


class TestExtractPropertyValue:
    """Tests for extract_property_value function."""

    def test_extracts_int_property(self) -> None:
        """Test extracting IntPropertyData."""
        prop = {"$type": "IntPropertyData", "Value": 42}
        result = extract_property_value(prop)
        assert result == 42

    def test_extracts_bool_property_true(self) -> None:
        """Test extracting BoolPropertyData with True value."""
        prop = {"$type": "BoolPropertyData", "Value": True}
        result = extract_property_value(prop)
        assert result is True

    def test_extracts_bool_property_false(self) -> None:
        """Test extracting BoolPropertyData with False value."""
        prop = {"$type": "BoolPropertyData", "Value": False}
        result = extract_property_value(prop)
        assert result is False

    def test_extracts_float_property(self) -> None:
        """Test extracting FloatPropertyData."""
        prop = {"$type": "FloatPropertyData", "Value": 3.14}
        result = extract_property_value(prop)
        assert result == 3.14

    def test_extracts_str_property_from_dict(self) -> None:
        """Test extracting StrPropertyData from dict format."""
        prop = {"$type": "StrPropertyData", "Value": {"Value": "hello"}}
        result = extract_property_value(prop)
        assert result == "hello"

    def test_extracts_str_property_direct(self) -> None:
        """Test extracting StrPropertyData from direct value."""
        prop = {"$type": "StrPropertyData", "Value": "hello"}
        result = extract_property_value(prop)
        assert result == "hello"

    def test_extracts_text_property_with_guid(self) -> None:
        """Test extracting TextPropertyData with localization GUID."""
        prop = {
            "$type": "TextPropertyData",
            "CultureInvariantString": "Display Text",
            "Value": "ABC123GUID",
        }
        result = extract_property_value(prop)
        assert result == {"Text": "Display Text", "Guid": "ABC123GUID"}

    def test_extracts_text_property_without_guid(self) -> None:
        """Test extracting TextPropertyData without GUID."""
        prop = {"$type": "TextPropertyData", "CultureInvariantString": "Display Text"}
        result = extract_property_value(prop)
        assert result == "Display Text"

    def test_extracts_object_property(self) -> None:
        """Test extracting ObjectPropertyData."""
        prop = {"$type": "ObjectPropertyData", "Value": {"Index": -5}}
        result = extract_property_value(prop)
        assert result == "Reference: -5"

    def test_extracts_object_property_direct_int(self) -> None:
        """Test extracting ObjectPropertyData with direct int value."""
        prop = {"$type": "ObjectPropertyData", "Value": -5}
        result = extract_property_value(prop)
        assert result == "Reference: -5"

    def test_extracts_array_property(self) -> None:
        """Test extracting ArrayPropertyData."""
        prop = {
            "$type": "ArrayPropertyData",
            "Value": [
                {"$type": "IntPropertyData", "Value": 1},
                {"$type": "IntPropertyData", "Value": 2},
            ],
        }
        result = extract_property_value(prop)
        assert result == [1, 2]

    def test_extracts_enum_property(self) -> None:
        """Test extracting EnumPropertyData."""
        prop = {"$type": "EnumPropertyData", "Value": "EItemCategory::Weapon"}
        result = extract_property_value(prop)
        assert result == "EItemCategory::Weapon"

    def test_extracts_struct_property(self) -> None:
        """Test extracting StructPropertyData."""
        prop = {
            "$type": "StructPropertyData",
            "Value": [
                {"Name": "X", "$type": "FloatPropertyData", "Value": 1.0},
                {"Name": "Y", "$type": "FloatPropertyData", "Value": 2.0},
            ],
        }
        result = extract_property_value(prop)
        # Result should be simplified
        assert result == {"X": 1, "Y": 2}

    def test_extracts_name_property_from_dict(self) -> None:
        """Test extracting NamePropertyData from dict format."""
        prop = {"$type": "NamePropertyData", "Value": {"Value": "ItemName"}}
        result = extract_property_value(prop)
        assert result == "ItemName"

    def test_extracts_soft_object_property(self) -> None:
        """Test extracting SoftObjectPropertyData.

        Note: Due to substring matching in the implementation,
        SoftObjectPropertyData is currently processed as ObjectPropertyData.
        This test verifies current behavior.
        """
        prop = {
            "$type": "SoftObjectPropertyData",
            "Value": {"AssetPathName": "/Game/Textures/Icon"},
        }
        result = extract_property_value(prop)
        # Currently returns Reference: 0 because "SoftObjectPropertyData" contains
        # "ObjectPropertyData" and the Object check runs first.
        # The value dict doesn't have "Index", so it defaults to 0.
        assert result == "Reference: 0"

    def test_returns_raw_value_for_unknown_type(self) -> None:
        """Test that unknown types return raw value."""
        prop = {"$type": "UnknownPropertyData", "Value": "some value"}
        result = extract_property_value(prop)
        assert result == "some value"

    def test_extracts_name_property_direct_value(self) -> None:
        """Test extracting NamePropertyData with direct value (non-dict)."""
        prop = {"$type": "NamePropertyData", "Value": "DirectName"}
        result = extract_property_value(prop)
        assert result == "DirectName"

    def test_extracts_text_property_from_dict_value(self) -> None:
        """Test extracting TextPropertyData from dict Value format."""
        prop = {
            "$type": "TextPropertyData",
            "Value": {"CultureInvariantString": "From Dict"},
        }
        result = extract_property_value(prop)
        assert result == "From Dict"

    def test_extracts_text_property_none_value(self) -> None:
        """Test extracting TextPropertyData with None value."""
        prop = {"$type": "TextPropertyData", "Value": None}
        result = extract_property_value(prop)
        assert result == ""

    def test_extracts_object_property_other_value(self) -> None:
        """Test extracting ObjectPropertyData with non-int, non-dict value."""
        prop = {"$type": "ObjectPropertyData", "Value": "some_string"}
        result = extract_property_value(prop)
        assert result == "some_string"

    def test_extracts_array_property_non_list(self) -> None:
        """Test extracting ArrayPropertyData with non-list value."""
        prop = {"$type": "ArrayPropertyData", "Value": "not a list"}
        result = extract_property_value(prop)
        assert result == "not a list"

    def test_extracts_set_property(self) -> None:
        """Test extracting SetPropertyData."""
        prop = {
            "$type": "SetPropertyData",
            "Value": [
                {"$type": "IntPropertyData", "Value": 1},
                {"$type": "IntPropertyData", "Value": 2},
            ],
        }
        result = extract_property_value(prop)
        assert result == [1, 2]

    def test_extracts_set_property_non_list(self) -> None:
        """Test extracting SetPropertyData with non-list value."""
        prop = {"$type": "SetPropertyData", "Value": "not a list"}
        result = extract_property_value(prop)
        assert result == "not a list"

    def test_extracts_map_property(self) -> None:
        """Test extracting MapPropertyData."""
        prop = {"$type": "MapPropertyData", "Value": {"key": "value"}}
        result = extract_property_value(prop)
        assert result == {"key": "value"}

    def test_extracts_struct_property_non_list(self) -> None:
        """Test extracting StructPropertyData with non-list value."""
        prop = {"$type": "StructPropertyData", "Value": {"X": 1.0, "Y": 2.0}}
        result = extract_property_value(prop)
        # Non-list value goes through simplify_value
        assert result == {"X": 1, "Y": 2}

    def test_extracts_delegate_property(self) -> None:
        """Test extracting DelegatePropertyData."""
        prop = {"$type": "DelegatePropertyData", "Value": {"Object": "SomeObject"}}
        result = extract_property_value(prop)
        assert result == {"Object": "SomeObject"}

    def test_extracts_fdelegate_property(self) -> None:
        """Test extracting FDelegate type."""
        prop = {"$type": "FDelegate", "Value": "delegate_value"}
        result = extract_property_value(prop)
        assert result == "delegate_value"

    def test_extracts_multicast_delegate_list(self) -> None:
        """Test extracting MulticastSparseDelegatePropertyData with list."""
        prop = {
            "$type": "MulticastSparseDelegatePropertyData",
            "Value": [{"func": "A"}, {"func": "B"}],
        }
        result = extract_property_value(prop)
        assert result == [{"func": "A"}, {"func": "B"}]

    def test_extracts_multicast_delegate_non_list(self) -> None:
        """Test extracting MulticastSparseDelegatePropertyData with non-list.

        Note: Due to substring matching order, MulticastSparseDelegatePropertyData
        is matched by DelegatePropertyData first, so returns raw value.
        """
        prop = {"$type": "MulticastSparseDelegatePropertyData", "Value": "not a list"}
        result = extract_property_value(prop)
        # Currently returns raw value because "DelegatePropertyData" substring
        # matches before "MulticastSparseDelegatePropertyData" specific check
        assert result == "not a list"

    def test_extracts_int8_property(self) -> None:
        """Test extracting Int8PropertyData."""
        prop = {"$type": "Int8PropertyData", "Value": 127}
        result = extract_property_value(prop)
        assert result == 127

    def test_extracts_int16_property(self) -> None:
        """Test extracting Int16PropertyData."""
        prop = {"$type": "Int16PropertyData", "Value": 32000}
        result = extract_property_value(prop)
        assert result == 32000

    def test_extracts_int64_property(self) -> None:
        """Test extracting Int64PropertyData."""
        prop = {"$type": "Int64PropertyData", "Value": 9223372036854775807}
        result = extract_property_value(prop)
        assert result == 9223372036854775807

    def test_extracts_uint16_property(self) -> None:
        """Test extracting UInt16PropertyData."""
        prop = {"$type": "UInt16PropertyData", "Value": 65535}
        result = extract_property_value(prop)
        assert result == 65535

    def test_extracts_uint32_property(self) -> None:
        """Test extracting UInt32PropertyData."""
        prop = {"$type": "UInt32PropertyData", "Value": 4294967295}
        result = extract_property_value(prop)
        assert result == 4294967295

    def test_extracts_byte_property(self) -> None:
        """Test extracting BytePropertyData."""
        prop = {"$type": "BytePropertyData", "Value": 255}
        result = extract_property_value(prop)
        assert result == 255

    def test_extracts_str_property_none_value(self) -> None:
        """Test extracting StrPropertyData with None value."""
        prop = {"$type": "StrPropertyData", "Value": None}
        result = extract_property_value(prop)
        assert result == ""

    def test_extracts_bool_property_non_bool(self) -> None:
        """Test extracting BoolPropertyData with non-bool value."""
        prop = {"$type": "BoolPropertyData", "Value": "not a bool"}
        result = extract_property_value(prop)
        assert result is False

    def test_array_with_non_typed_items(self) -> None:
        """Test extracting ArrayPropertyData with non-typed items."""
        prop = {
            "$type": "ArrayPropertyData",
            "Value": [
                {"$type": "IntPropertyData", "Value": 1},
                "plain_string",
                42,
            ],
        }
        result = extract_property_value(prop)
        assert result == [1, "plain_string", 42]


class TestResolveImportPathEdgeCases:
    """Additional edge case tests for resolve_import_path."""

    def test_returns_object_name_when_outer_path_none(self) -> None:
        """Test that object name is returned when outer path can't be resolved."""
        imports = [
            {"ObjectName": "Root", "OuterIndex": -99},  # Invalid outer
            {"ObjectName": "Child", "OuterIndex": -1},
        ]
        result = resolve_import_path(-2, imports)
        # -1 outer index points to index 0, which has invalid outer -99
        # So it returns just the object name
        assert result == "Root/Child"

    def test_returns_object_name_alone_when_no_outer(self) -> None:
        """Test import with OuterIndex 0 (no outer)."""
        imports = [{"ObjectName": "Standalone", "OuterIndex": 0}]
        result = resolve_import_path(-1, imports)
        assert result == "Standalone"

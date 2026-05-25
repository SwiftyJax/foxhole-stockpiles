"""Shared utilities for catalog builder services."""

from typing import Any


def normalize_object_path(path: str) -> str:
    """Normalize an object path to War/Content format.

    Converts /Game/ paths to War/Content/ format and ensures .0 suffix.

    Args:
        path: Object path (e.g., "/Game/Blueprints/Items/BPFoo").

    Returns:
        Normalized path (e.g., "War/Content/Blueprints/Items/BPFoo.0").
    """
    result = path
    if result.startswith("/Game/"):
        result = "War/Content/" + result[6:]
    if not result.endswith(".0"):
        result = result + ".0"
    return result


def extract_localized_text(value: Any) -> str | None:
    """Extract text from a localized value.

    Handles both dict format {"Text": "...", "Guid": "..."} and plain strings.

    Args:
        value: Localized value (dict with Text/Guid, string, or other).

    Returns:
        Extracted text string, or None if value is None/empty.
    """
    if value is None:
        return None
    if isinstance(value, dict):
        text = value.get("Text")
        if text is not None:
            return str(text)
        return None
    if isinstance(value, str):
        return value if value else None
    return str(value)


def extract_property_value(prop: dict[str, Any]) -> Any:
    """Extract the value from a UAsset property dict.

    Centralized extraction for common UAsset property types.

    Args:
        prop: Property dict with $type and Value fields.

    Returns:
        Extracted value (simplified).
    """
    prop_type = prop.get("$type", "")
    value = prop.get("Value")

    # Integer types
    if any(
        t in prop_type
        for t in [
            "IntPropertyData",
            "Int8PropertyData",
            "Int16PropertyData",
            "Int32PropertyData",
            "Int64PropertyData",
            "UInt16PropertyData",
            "UInt32PropertyData",
        ]
    ):
        return simplify_value(value)

    # Float
    if "FloatPropertyData" in prop_type:
        return simplify_value(value)

    # Boolean
    if "BoolPropertyData" in prop_type:
        return value if isinstance(value, bool) else False

    # Byte/Enum
    if "BytePropertyData" in prop_type or "EnumPropertyData" in prop_type:
        return value

    # Name property
    if "NamePropertyData" in prop_type:
        if isinstance(value, dict):
            return value.get("Value", "")
        return value

    # String property
    if "StrPropertyData" in prop_type:
        if isinstance(value, dict):
            return value.get("Value", "")
        return str(value) if value is not None else ""

    # Text property - returns {"Text": ..., "Guid": ...} for localization support
    if "TextPropertyData" in prop_type:
        culture_invariant = prop.get("CultureInvariantString")
        if culture_invariant and value and isinstance(value, str):
            return {"Text": culture_invariant, "Guid": value}
        if culture_invariant:
            return culture_invariant
        if isinstance(value, dict):
            return value.get("CultureInvariantString", "")
        return str(value) if value is not None else ""

    # Object property (import/export reference)
    if "ObjectPropertyData" in prop_type:
        if isinstance(value, dict):
            index = value.get("Index", 0)
        elif isinstance(value, int):
            index = value
        else:
            return value
        return f"Reference: {index}"

    # SoftObject property
    if "SoftObjectPropertyData" in prop_type:
        if isinstance(value, dict):
            return value.get("AssetPathName", "")
        return value

    # Array property
    if "ArrayPropertyData" in prop_type:
        if isinstance(value, list):
            return [
                extract_property_value(item) if isinstance(item, dict) and "$type" in item else item
                for item in value
            ]
        return value

    # Set property
    if "SetPropertyData" in prop_type:
        if isinstance(value, list):
            return [
                extract_property_value(item) if isinstance(item, dict) and "$type" in item else item
                for item in value
            ]
        return value

    # Map property
    if "MapPropertyData" in prop_type:
        return value

    # Struct property - recursively extract
    if "StructPropertyData" in prop_type:
        if isinstance(value, list):
            result = {}
            for inner_prop in value:
                if isinstance(inner_prop, dict) and "Name" in inner_prop:
                    inner_name = inner_prop.get("Name")
                    inner_value = extract_property_value(inner_prop)
                    result[inner_name] = inner_value
            return simplify_value(result)
        return simplify_value(value)

    # Delegate types
    if "DelegatePropertyData" in prop_type or "FDelegate" in prop_type:
        return value

    # MulticastDelegate
    if "MulticastSparseDelegatePropertyData" in prop_type:
        return value if isinstance(value, list) else []

    # Default: return raw value
    return value


def simplify_value(value: Any) -> Any:
    """Simplify extracted values.

    - Convert floats to ints if they're whole numbers
    - Convert '+N' strings to ints (game format for numbers)
    - Flatten single-key dicts to just the value
    - Recursively simplify nested structures

    Args:
        value: Value to simplify.

    Returns:
        Simplified value.
    """
    # Round floats to 6 decimals, convert to int if whole number
    if isinstance(value, float):
        rounded = round(value, 6)
        if rounded == int(rounded):
            return int(rounded)
        return rounded

    # Convert '+N' or '-N' strings to ints (game format)
    if isinstance(value, str) and value and value[0] in "+-" and value[1:].isdigit():
        return int(value)

    # Recursively simplify dicts
    if isinstance(value, dict):
        simplified = {k: simplify_value(v) for k, v in value.items()}
        # Flatten single-key dicts to just the value
        if len(simplified) == 1:
            return next(iter(simplified.values()))
        return simplified

    # Recursively simplify lists
    if isinstance(value, list):
        return [simplify_value(item) for item in value]

    return value


def parse_reference(ref_string: str) -> int | None:
    """Parse a reference string like 'Reference: -5' to extract the index.

    Args:
        ref_string: Reference string in format "Reference: N".

    Returns:
        The reference index (negative for imports, positive for exports),
        or None if parsing fails.
    """
    if not ref_string or not ref_string.startswith("Reference:"):
        return None
    try:
        return int(ref_string.split(":")[1].strip())
    except (IndexError, ValueError):
        return None


def resolve_import_path(import_index: int, imports: list[dict[str, Any]]) -> str | None:
    """Resolve an import index to its full object path.

    Follows OuterIndex chain to build complete path.

    Args:
        import_index: Negative import index.
        imports: Raw imports array from JSON.

    Returns:
        Resolved path string or None.
    """
    if import_index >= 0:
        return None

    index = abs(import_index) - 1
    if index >= len(imports):
        return None

    import_obj = imports[index]
    object_name: str = import_obj.get("ObjectName", "")
    outer_index = import_obj.get("OuterIndex", 0)

    # Recursively resolve outer
    if outer_index < 0:
        outer_path = resolve_import_path(outer_index, imports)
        if outer_path:
            return f"{outer_path}/{object_name}"
        return object_name

    return object_name

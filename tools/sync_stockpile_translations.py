#!/usr/bin/env python3
"""Sync stockpile type translations from game files.

This script extracts stockpile type names and their translations from the game's
JSON blueprints and .locres localization files, then compares them with the
constants defined in foxhole_stockpiles/constants/stockpile_texts.py.

It can also auto-discover new stockpile types by scanning for specific patterns
in the game files that indicate player-accessible stockpiles.

Usage:
    python tools/sync_stockpile_translations.py [--war-dir PATH] [--update]

Options:
    --war-dir PATH  Path to extracted game files (default: ./war/War/Content)
    --update        Update the constants file with official translations
    --show-guids    Show GUIDs for each stockpile type
    --discover      Auto-discover potential new stockpile types from game files
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from foxhole_stockpiles.constants import STOCKPILE_TYPE_TEXTS  # noqa: E402
from foxhole_stockpiles.enums.stockpile_type import StockpileType  # noqa: E402
from foxhole_stockpiles.services.catalog_builder.localization_lookup import (  # noqa: E402
    SUPPORTED_LANGUAGES,
    LocalizationLookup,
)

# Mapping of StockpileType to blueprint search patterns and English display names
STOCKPILE_BLUEPRINTS = {
    StockpileType.SEAPORT: {
        "patterns": ["BPSeaport.json"],
        "english": "Seaport",
    },
    StockpileType.STORAGE_DEPOT: {
        "patterns": ["BPStorageFacility.json", "BPStorageDepot.json"],
        "english": "Storage Depot",
    },
    StockpileType.ENCAMPMENT: {
        "patterns": ["BPForwardBase1.json"],
        "english": "Encampment",
    },
    StockpileType.KEEP: {
        "patterns": ["BPKeep.json"],
        "english": "Keep",
    },
    StockpileType.SAFE_HOUSE: {
        "patterns": ["TownWLargeGS1.json", "BPSafeHouse*.json"],
        "english": "Safe House",
    },
    StockpileType.RELIC_BASE: {
        "patterns": ["BPRelicBase.json"],
        "english": "Relic Base",
    },
    StockpileType.BUNKER_BASE_1: {
        "patterns": [
            "BPFortBaseT1.json",
            "BPFortBaseT2.json",
            "BPFortBaseT3.json",
            "BPDestroyedFortForwardBaseT1.json",
            "BPDestroyedFortForwardBaseT2.json",
            "BPDestroyedFortForwardBaseT3.json",
        ],
        "english": "Bunker Base",
    },
    StockpileType.BORDER_BASE: {
        "patterns": ["BPBorderBase.json"],
        "english": "Border Base",
    },
    StockpileType.TOWN_BASE_1: {
        "patterns": ["BPTownBase1.json", "BPTownBase2.json", "BPTownBase3.json"],
        "english": "Town Base",
    },
    StockpileType.AIRCRAFT_DEPOT: {
        "patterns": ["BPAircraftDepot.json"],
        "english": "Aircraft Depot",
    },
    StockpileType.UNDERGROUND_FORTRESS: {
        "patterns": ["BPFortGarrisonStation.json"],
        "english": "Underground Fortress",
    },
    StockpileType.BMS_LONGHOOK: {
        "patterns": ["BPLargeShipBaseShip.json"],
        "english": "BMS - Longhook",
    },
}

# Patterns that indicate player-accessible stockpile structures
STOCKPILE_INDICATORS = {
    "storage_facility": "ESimScreen::StorageFacility",
    "base_stockpile": "spawn and stockpile",
    "item_stockpile": "GenericItemStockpileComponent",
    "generic_stockpile": "GenericStockpileComponent",
    "static_base": "ESpawnPointCategory::StaticBase",
}

# Patterns to exclude from discovery (not player-accessible stockpiles)
EXCLUDE_PATTERNS = [
    "Transfer",  # Transfer stations
    "Destroyed",  # Destroyed versions
    "BuildSite",  # Build sites
    "Factory",  # Factories (internal stockpiles)
    "Mine",  # Mines (internal stockpiles)
    "Refinery",  # Refineries (internal stockpiles)
    "Harvester",  # Harvesters (internal stockpiles)
    "Room",  # Bunker rooms (internal stockpiles)
    "Engine",  # Engine rooms
    "Hospital",  # Hospitals
    "Container",  # Containers
    "Pallet",  # Pallets
    "Platform",  # Platforms
    "Tunnel",  # Tunnels
    "Mixer",  # Concrete mixer
    "Equipment",  # Construction equipment
    "Power",  # Power plants
    "Pump",  # Water pumps
    "Well",  # Oil wells
    "Offshore",  # Offshore platforms
    "Dock",  # Dry dock
    "Assembly",  # Assembly stations
    "Modification",  # Modification center
    "Trailer",  # Trailers
]

# Known English names of stockpile types (for comparison)
KNOWN_STOCKPILE_NAMES = {config["english"] for config in STOCKPILE_BLUEPRINTS.values()}


def find_display_name_guid(json_path: Path) -> tuple[str | None, str | None]:
    """Extract DisplayName GUID and CultureInvariantString from a blueprint JSON.

    Args:
        json_path: Path to the blueprint JSON file.

    Returns:
        Tuple of (guid, english_text) or (None, None) if not found.
    """
    try:
        with open(json_path) as f:
            data = json.load(f)

        for export in data.get("Exports", []):
            for item in export.get("Data", []):
                if isinstance(item, dict) and item.get("Name") == "DisplayName":
                    guid = item.get("Value")
                    text = item.get("CultureInvariantString")
                    return guid, text
    except Exception:
        pass

    return None, None


def discover_stockpile_structures(war_dir: Path) -> list[dict[str, Any]]:
    """Scan game files to discover potential stockpile structures.

    Uses multiple indicators to identify structures that may be player-accessible
    stockpiles. This helps detect new stockpile types when game updates are released.

    Args:
        war_dir: Path to War/Content directory.

    Returns:
        List of discovered structures with their details.
    """
    discovered = {}

    for json_file in war_dir.rglob("*.json"):
        # Skip excluded patterns
        if any(ex in json_file.name for ex in EXCLUDE_PATTERNS):
            continue

        try:
            content = json_file.read_text()

            # Check which indicators are present
            indicators_found = []
            for key, pattern in STOCKPILE_INDICATORS.items():
                if pattern in content:
                    indicators_found.append(key)

            # Must have at least one strong indicator
            # Storage facilities or bases with stockpiles
            is_storage = "storage_facility" in indicators_found
            has_stockpile = (
                "item_stockpile" in indicators_found or "generic_stockpile" in indicators_found
            )
            is_base = ("base_stockpile" in indicators_found and has_stockpile) or (
                "static_base" in indicators_found and has_stockpile
            )

            if not (is_storage or is_base):
                continue

            # Get DisplayName
            data = json.loads(content)
            display_name = None
            guid = None
            for export in data.get("Exports", []):
                for item in export.get("Data", []):
                    if isinstance(item, dict) and item.get("Name") == "DisplayName":
                        display_name = item.get("CultureInvariantString")
                        guid = item.get("Value")
                        break

            if display_name and display_name not in discovered:
                discovered[display_name] = {
                    "name": display_name,
                    "file": json_file.name,
                    "guid": guid,
                    "indicators": indicators_found,
                    "type": "storage_facility" if is_storage else "base",
                }
        except Exception:
            pass

    return list(discovered.values())


def print_discovered_structures(
    structures: list[dict[str, Any]],
    lookup: LocalizationLookup | None = None,
) -> None:
    """Print discovered stockpile structures.

    Args:
        structures: List of discovered structures.
        lookup: Optional localization lookup for fetching translations.
    """
    known = []
    new = []

    for struct in structures:
        if struct["name"] in KNOWN_STOCKPILE_NAMES:
            known.append(struct)
        else:
            new.append(struct)

    print("=" * 60)
    print("Auto-Discovery Results")
    print("=" * 60)

    if new:
        print("\n*** NEW STOCKPILE TYPES DETECTED ***\n")
        for struct in sorted(new, key=lambda x: x["name"]):
            print(f"  {struct['name']}")
            print(f"    File: {struct['file']}")
            print(f"    GUID: {struct['guid']}")
            print(f"    Type: {struct['type']}")
            print(f"    Indicators: {struct['indicators']}")
            # Print translations if lookup is available
            if lookup and struct["guid"]:
                translations = {}
                for lang in SUPPORTED_LANGUAGES:
                    trans = lookup.get(struct["guid"], language=lang)
                    if trans:
                        translations[lang] = trans
                if translations:
                    print("    Translations:")
                    for lang, trans in translations.items():
                        print(f"      {lang}: {trans}")
                else:
                    print("    Translations: (none available)")
            print()
    else:
        print("\nNo new stockpile types detected.")

    print(f"\nKnown stockpile types found: {len(known)}")
    for struct in sorted(known, key=lambda x: x["name"]):
        print(f"  - {struct['name']} ({struct['type']})")


def extract_official_translations(
    war_dir: Path,
) -> tuple[dict[StockpileType, dict[str, list[str]]], dict[StockpileType, list[str]]]:
    """Extract official translations from game files.

    Args:
        war_dir: Path to War/Content directory.

    Returns:
        Tuple of (translations_dict, guids_dict) where translations_dict maps
        StockpileType to {language: [translations]} and guids_dict maps
        StockpileType to list of GUIDs found.
    """
    localization_dir = war_dir / "Localization"
    if not localization_dir.exists():
        print(f"Error: Localization directory not found: {localization_dir}")
        sys.exit(1)

    lookup = LocalizationLookup(localization_dir)
    results: dict[StockpileType, dict[str, list[str]]] = {}
    guids_found: dict[StockpileType, list[str]] = {}

    for stockpile_type, config in STOCKPILE_BLUEPRINTS.items():
        results[stockpile_type] = {lang: [] for lang in SUPPORTED_LANGUAGES}
        guids_found[stockpile_type] = []

        for pattern in config["patterns"]:
            # Handle glob patterns
            if "*" in pattern:
                files = list(war_dir.rglob(pattern))
            else:
                files = list(war_dir.rglob(pattern))

            for json_file in files:
                guid, english_text = find_display_name_guid(json_file)

                if guid and english_text == config["english"]:
                    guids_found[stockpile_type].append(guid)

                    # Always include the English name from the blueprint
                    if english_text and english_text not in results[stockpile_type]["en"]:
                        results[stockpile_type]["en"].append(english_text)

                    # Get translations for all languages from localization files
                    for lang in SUPPORTED_LANGUAGES:
                        trans = lookup.get(guid, language=lang)
                        if trans and trans not in results[stockpile_type][lang]:
                            results[stockpile_type][lang].append(trans)

    return results, guids_found


def compare_translations(
    official: dict[StockpileType, dict[str, list[str]]],
) -> dict[StockpileType, dict[str, set[str] | bool]]:
    """Compare official translations with current constants.

    Args:
        official: Official translations from game files.

    Returns:
        Dict with 'missing', 'extra', and 'no_game_translations' for each stockpile type.
    """
    differences: dict[StockpileType, dict[str, set[str] | bool]] = {}

    for stockpile_type, lang_translations in official.items():
        our_texts = set(STOCKPILE_TYPE_TEXTS.get(stockpile_type, []))
        official_texts = set()
        for translations in lang_translations.values():
            official_texts.update(translations)

        # Check if game has no translations at all for this type
        no_game_translations = len(official_texts) == 0 and len(our_texts) > 0

        missing = official_texts - our_texts
        extra = our_texts - official_texts if not no_game_translations else set()

        if missing or extra or no_game_translations:
            differences[stockpile_type] = {
                "missing": missing,
                "extra": extra,
                "no_game_translations": no_game_translations,
            }

    return differences


def print_translations(
    official: dict[StockpileType, dict[str, list[str]]],
    guids: dict[StockpileType, list[str]],
    show_guids: bool = False,
) -> None:
    """Print extracted translations.

    Args:
        official: Official translations from game files.
        guids: GUIDs found for each stockpile type.
        show_guids: Whether to show GUIDs.
    """
    print("=" * 60)
    print("Official Stockpile Type Translations from Game Files")
    print("=" * 60)

    for stockpile_type, lang_translations in official.items():
        print(f"\n{stockpile_type.name}:")
        if show_guids and guids.get(stockpile_type):
            print(f"  GUIDs: {guids[stockpile_type]}")
        for lang, translations in lang_translations.items():
            if translations:
                print(f"  {lang}: {translations}")


def print_differences(differences: dict[StockpileType, dict[str, set[str] | bool]]) -> None:
    """Print differences between official and current translations.

    Args:
        differences: Dict with missing and extra translations.
    """
    if not differences:
        print("\n✓ All translations match official game files!")
        return

    print("\n" + "=" * 60)
    print("Differences Found")
    print("=" * 60)

    for stockpile_type, diff in differences.items():
        print(f"\n{stockpile_type.name}:")
        if diff.get("no_game_translations"):
            print("  No translations in game files yet (manually added)")
        elif diff["missing"]:
            print(f"  MISSING (in game, not in constants): {diff['missing']}")
        if diff["extra"]:
            print(f"  EXTRA (in constants, not in game): {diff['extra']}")


def generate_updated_constants(
    official: dict[StockpileType, dict[str, list[str]]],
) -> str:
    """Generate updated constants file content.

    Args:
        official: Official translations from game files.

    Returns:
        Updated Python code for the constants file.
    """
    lines = [
        '"""Stockpile type text constants.',
        "",
        "This module contains the valid texts for each stockpile type, including",
        "translations for all supported languages. These are the canonical texts",
        "that appear in the game UI.",
        "",
        "Generated/verified by: tools/sync_stockpile_translations.py",
        '"""',
        "",
        "from foxhole_stockpiles.enums.stockpile_type import StockpileType",
        "",
        "STOCKPILE_TYPE_TEXTS: dict[StockpileType, list[str]] = {",
    ]

    # Order: use the order from StockpileType enum
    for stockpile_type in StockpileType:
        if stockpile_type == StockpileType.UNDEFINED:
            # Handle UNDEFINED separately
            lines.append(f"    StockpileType.{stockpile_type.name}: [")
            lines.append('        "Undefined",')
            lines.append("    ],")
            continue

        if stockpile_type not in official:
            continue

        lang_translations = official[stockpile_type]

        # Collect all unique translations, English first
        all_translations = []
        if lang_translations.get("en"):
            all_translations.extend(lang_translations["en"])

        for lang in ["de", "fr", "pt", "ru", "zh"]:
            for trans in lang_translations.get(lang, []):
                if trans not in all_translations:
                    all_translations.append(trans)

        lines.append(f"    StockpileType.{stockpile_type.name}: [")
        for trans in all_translations:
            lines.append(f'        "{trans}",')
        lines.append("    ],")

    lines.append("}")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sync stockpile type translations from game files."
    )
    parser.add_argument(
        "--war-dir",
        type=Path,
        default=PROJECT_ROOT / "war" / "War" / "Content",
        help="Path to extracted game War/Content directory",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update the constants file with official translations",
    )
    parser.add_argument(
        "--show-guids",
        action="store_true",
        help="Show GUIDs for each stockpile type",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Auto-discover potential new stockpile types from game files",
    )

    args = parser.parse_args()

    if not args.war_dir.exists():
        print(f"Error: War directory not found: {args.war_dir}")
        print("Make sure game files are extracted to the war/ folder.")
        sys.exit(1)

    print(f"Using game files from: {args.war_dir}")

    # Auto-discover mode
    if args.discover:
        print("\nScanning for stockpile structures...")
        discovered = discover_stockpile_structures(args.war_dir)
        # Create localization lookup for translations
        localization_dir = args.war_dir / "Localization"
        lookup = None
        if localization_dir.exists():
            lookup = LocalizationLookup(localization_dir)
        print_discovered_structures(discovered, lookup)
        return

    print("\nExtracting translations...")
    official, guids = extract_official_translations(args.war_dir)
    print_translations(official, guids, show_guids=args.show_guids)

    differences = compare_translations(official)
    print_differences(differences)

    if args.update:
        constants_path = PROJECT_ROOT / "foxhole_stockpiles" / "constants" / "stockpile_texts.py"
        updated_content = generate_updated_constants(official)

        print(f"\nUpdating {constants_path}...")
        with open(constants_path, "w") as f:
            f.write(updated_content)
        print("✓ Constants file updated!")
    elif differences:
        print("\nRun with --update to update the constants file.")


if __name__ == "__main__":
    main()

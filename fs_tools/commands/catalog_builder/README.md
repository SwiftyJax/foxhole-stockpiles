# Catalog Builder

Builds catalog.json from Foxhole PAK files by extracting game blueprints, converting them to JSON, and parsing item definitions. This tool generates the complete item catalog without requiring manual data entry.

## Prerequisites

### External Tools
- **repak.exe**: Modern Rust-based PAK extraction tool
- **UAssetGUI.exe**: For converting .uasset blueprint files to .json format

### Tool Locations
- **repak.exe**: Download from https://github.com/trumank/repak/releases
- **UAssetGUI.exe**: Download from https://github.com/atenfyr/UAssetGUI/releases

### Default Tool Paths
- `C:\repak\repak.exe`
- `C:\UAssetGUI\UAssetGUI.exe`

### Required Files
- **Foxhole PAK file**: War-WindowsNoEditor.pak from game installation

## Usage

### Primary Interface

The catalog builder is available through the unified Foxhole Stockpiles CLI:

```bash
fs catalog-builder --pak /path/to/War-WindowsNoEditor.pak
fs catalog --pak /path/to/War-WindowsNoEditor.pak    # Short alias
```

### Development Interface

For development and testing, you can also run the catalog builder module directly:

```bash
python -m foxhole_stockpiles.commands.catalog_builder.catalog_builder --pak /path/to/War-WindowsNoEditor.pak
```

**Note**: The recommended way to use this tool is through the unified `fs` command.

### Basic Usage

#### Generate Catalog from PAK

```bash
# Generate catalog.json from PAK file
fs catalog-builder --pak "C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks\War-WindowsNoEditor.pak"

# Custom output location
fs catalog-builder --pak /path/to/War-WindowsNoEditor.pak --output data/catalog.json
```

#### Custom Tool Paths

```bash
# Specify custom tool locations
fs catalog-builder --pak /path/to/War-WindowsNoEditor.pak \
  --extractor /mnt/c/Jorge/apps/repak/repak.exe \
  --converter /mnt/c/Users/username/Downloads/UAssetGUI.exe
```

## Command-Line Options

```bash
fs catalog-builder [OPTIONS]

Optional:
  --pak PATH                  Path to War-WindowsNoEditor.pak file (default: C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks\War-WindowsNoEditor.pak)
  --extractor PATH            Path to repak.exe (default: C:\repak\repak.exe)
  --converter PATH            Path to UAssetGUI.exe (default: C:\UAssetGUI\UAssetGUI.exe)
  --output PATH               Output path for catalog JSON (default: catalog.json)
  --workers N                 Number of parallel conversions (default: 4)
  --keep-temp                 Keep temporary extraction directory (uses temp dir instead of war/)
  --force-extract             Force re-extraction from PAK even if JSON files exist
  --extract-dir PATH          Use existing extraction directory instead of extracting from PAK
  --log-file PATH             Path to log file (default: console only)
  --verbose                   Enable verbose logging (debug level)
  --quiet                     Suppress all output except errors
```

## Performance Options

### Parallel Processing

```bash
# Use 16 parallel workers for faster conversion
fs catalog-builder --pak /path/to/War-WindowsNoEditor.pak --workers 16

# Use fewer workers for limited CPU
fs catalog-builder --pak /path/to/War-WindowsNoEditor.pak --workers 4
```

### Logging

```bash
# Log to file for debugging
fs catalog-builder --pak /path/to/War-WindowsNoEditor.pak --log-file catalog_build.log

# Verbose logging
fs catalog-builder --pak /path/to/War-WindowsNoEditor.pak --verbose --log-file catalog_build.log

# Quiet mode (only errors)
fs catalog-builder --pak /path/to/War-WindowsNoEditor.pak --quiet
```

### Keep Temporary Files

The `--keep-temp` flag extracts to a **separate temporary directory** with a unique name, useful for debugging or inspection:

```bash
# Extract to /tmp/catalog_builder_xyz123/ instead of war/
fs catalog-builder --pak /path/to/War-WindowsNoEditor.pak --keep-temp
```

**Note**: Using `--keep-temp` disables automatic caching since each run creates a new directory. Use the default behavior (no flag) for caching.

### Extraction Caching

**By default**, the catalog builder extracts files to the `war/` directory in your current working directory. This enables automatic caching:

```bash
# First run: Extracts to war/ and builds catalog
fs catalog-builder --pak /path/to/War-WindowsNoEditor.pak

# Second run: Uses existing war/ files, skips extraction/conversion
fs catalog-builder --pak /path/to/War-WindowsNoEditor.pak

# Force re-extraction (e.g., after game update)
fs catalog-builder --pak /path/to/War-WindowsNoEditor.pak --force-extract
```

**Extraction locations:**
- **Default**: `war/` directory (kept for caching)
- **With `--keep-temp`**: Temporary directory with unique name (e.g., `/tmp/catalog_builder_xyz123/`)

This significantly speeds up catalog rebuilds when iterating on catalog generation logic or cleanup rules.

To completely remove cached files:
```bash
rm -rf war/
```

### Using an Existing Extraction Directory

If you already have extracted and converted JSON files (e.g., from a previous run or manual extraction), you can skip the PAK extraction entirely:

```bash
# Use existing extraction directory (skips PAK extraction and conversion)
fs catalog-builder --extract-dir ./war

# Use a custom extraction location
fs catalog-builder --extract-dir /path/to/extracted/files
```

**Note**: When using `--extract-dir`, the `--pak`, `--extractor`, and `--converter` options are ignored since no extraction is performed.

## Pipeline Stages

The catalog builder executes a complete 7-stage pipeline:

### Stage 1: PAK Extraction
- Extracts blueprint directories from PAK using repak
- Directories: ItemPickups, Vehicles, Structures, Data
- Only extracts files needed for catalog generation (~2,100 files)

### Stage 2: .uasset → .json Conversion
- Converts .uasset blueprint files to JSON using UAssetGUI
- Parallel processing for faster conversion
- Skips already-converted files (resume support)

### Stage 3: Data Table Parsing
- Parses ItemDynamicData and VehicleDynamicData tables
- Identifies stockpilable items (405 total CodeNames)
- Extracts item stats and properties

### Stage 4: Blueprint Parsing
- Parses blueprint JSON files
- Extracts item properties: CodeName, DisplayName, Description, Icon
- Detects stockpilable items by data table membership
- Handles RawExport items (logs and skips unparseable blueprints)

### Stage 5: Stats Merging
- Merges data table stats into catalog entries
- Adds QuantityPerCrate, CrateProductionTime, MaxHealth, etc.
- 100% merge rate for all extracted items

### Stage 6: Cleanup
- Removes empty ChassisName fields
- Removes ResearchLevel fields when value is 0
- Flattens CostPerCrate and ResourceAmounts struct arrays to simple array of objects
- Flattens AltResourceAmounts and UpgradeResourceAmounts with validation:
  - Skips entries with CodeName="None"
  - Skips entries with empty OtherResources array
  - Recursively flattens nested OtherResources structures
- Normalizes numeric values:
  - Removes .0 from whole numbers (100.0 → 100)
  - Rounds most decimals to 2 places (3.14159 → 3.14)
  - Special precision for FuelConsumptionPerSecond and MinorDamagePercent: 4 decimal places
- Converts "+0" strings to numeric 0

### Stage 7: Output
- Sorts entries by CodeName
- Writes catalog.json
- Cleans up temporary directory (unless --keep-temp)

## Output Structure

Generates a catalog.json file with this structure:

```json
[
  {
    "ObjectPath": "War/Content/Blueprints/ItemPickups/BPAluminumPickup",
    "CodeName": "Aluminum",
    "CrateProductionTime": 50.0,
    "Description": "Processed from Bauxite...",
    "DisplayName": "Aluminum Alloy",
    "Icon": "War/Content/Textures/UI/ItemIcons/AluminumIcon",
    "ItemCategory": "EItemCategory::RawResource",
    "ItemProfileType": "EItemProfileType::RawResource",
    "QuantityPerCrate": 100,
    "SingleRetrieveTime": 7.0
  },
  ...
]
```

## Expected Results

### Success Metrics
- **~367 stockpilable items** extracted from blueprints
- **100% data table merge rate** (all items have stats)
- **4 RawExport items** skipped and logged (LargeShips)
- **0 errors** for parseable blueprints

### RawExport Items (Skipped)
The following items cannot be extracted due to UAssetGUI limitations:
- `LargeShipDestroyerC`
- `LargeShipDestroyerW`
- `LargeShipSubmarineC`
- `LargeShipSubmarineW`

These complex blueprints are logged but not included in the catalog. They can be manually added if needed.

## Example: Complete Catalog Generation

```bash
# Windows (PowerShell)
fs catalog-builder `
  --pak "C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks\War-WindowsNoEditor.pak" `
  --extractor "C:\Jorge\apps\repak\repak.exe" `
  --converter "C:\Users\username\Downloads\UAssetGUI.exe" `
  --output "data/catalog.json" `
  --workers 16 `
  --verbose

# Linux (WSL)
fs catalog-builder \
  --pak /mnt/c/Program\ Files\ \(x86\)/Steam/steamapps/common/Foxhole/War/Content/Paks/War-WindowsNoEditor.pak \
  --extractor /mnt/c/Jorge/apps/repak/repak.exe \
  --converter /mnt/c/Users/username/Downloads/UAssetGUI.exe \
  --output data/catalog.json \
  --workers 16 \
  --verbose
```

## Integration

This command is part of the Foxhole Stockpiles CLI tool suite. The catalog it generates is used by other tools:

```bash
# 1. Build catalog (this tool)
fs catalog-builder --pak /path/to/War-WindowsNoEditor.pak --output catalog.json

# 2. Extract assets using the catalog
fs extract-assets --catalog catalog.json --pak /path/to/War-WindowsNoEditor.pak --output raw_assets/

# 3. Generate templates
fs generate-templates --catalog catalog.json --assets raw_assets/ --templates processed_templates/

# 4. Build database
fs database-builder --catalog catalog.json --templates processed_templates/ --database templates.h5

# 5. Scan stockpiles
fs scanner --database templates.h5 --image screenshot.png
```

For more help:
```bash
fs catalog-builder --help
fs --help  # See all available commands
```

## Troubleshooting

### File Not Found Errors
- Verify PAK file path is correct
- Ensure repak.exe and UAssetGUI.exe paths are valid
- Use `--verbose` to see detailed extraction logs

### Conversion Failures
- Some blueprints may fail to convert (this is normal)
- Check that UAssetGUI version supports UE 4.27
- Use `--engine-version VER_UE4_27` explicitly if needed

### Incomplete Catalog
- Generated catalog may have more items than old catalog (game updates)
- Missing items may be deprecated or non-stockpilable
- Use `--verbose` to see which items are skipped and why

### Performance Issues
- Increase `--workers` for faster conversion (16+ recommended)
- Extraction takes ~5-10 minutes depending on hardware
- Use `--keep-temp` to avoid re-extraction during testing

## Related Tools

- [`fs extract-assets`](../uasset_extractor/README.md) - Uses the catalog generated by this tool
- [`fs generate-templates`](../generate_templates/README.md) - Uses the catalog for template generation
- [`fs database-builder`](../database_builder/README.md) - Uses the catalog for database building
- [`fs scanner`](../stockpile_scanner/README.md) - Final tool that uses the complete pipeline

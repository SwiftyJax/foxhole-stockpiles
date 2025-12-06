# Asset Extractor

Extracts item icons and assets from Foxhole PAK files and converts them to PNG format for use in the recognition system.

## Prerequisites

### External Tools
- **repak.exe**: Modern Rust-based PAK extraction tool
- **UModel.exe**: For converting .uasset files to .png format

### Tool Locations
- **repak.exe**: Download from https://github.com/trumank/repak/releases
- **UModel.exe**: Download from https://www.gildor.org/en/projects/umodel

### Default Tool Paths
- `C:\repak\repak.exe`
- `C:\UModel\umodel.exe`

### Required Files
- **catalog.json**: Item definitions
- **Foxhole PAK files**: Game installation or mod files

## Usage

### Primary Interface

The asset extractor is available through the unified Foxhole Stockpiles CLI:

```bash
fs extract-assets --catalog catalog.json
fs extract --catalog catalog.json    # Short alias
```

### Development Interface

For development and testing, you can also run the asset extractor module directly:

```bash
python -m foxhole_stockpiles.commands.uasset_extractor.uasset_extractor --catalog catalog.json
```

**Note**: The recommended way to use this tool is through the unified `fs` command.

### Basic Usage

### Vanilla Game Extraction

```bash
# Extract from default Foxhole installation using repak
fs extract-assets --catalog catalog.json

# Custom PAK file location
fs extract-assets --catalog catalog.json \
  --pak "C:\Games\Foxhole\War\Content\Paks\War-WindowsNoEditor.pak"
```

### Custom Output Directory

```bash
fs extract-assets --catalog catalog.json --output "extracted_assets/"
```

## Mod Support

The extractor handles multiple PAK files for comprehensive mod support:

### Multi-PAK Extraction

```bash
# Extract from multiple PAK files (vanilla + mods)
fs extract-assets --catalog catalog.json \
  --pak "C:\Path\To\War-WindowsNoEditor.pak" \
  --pak "C:\Path\To\ModPak1.pak" \
  --pak "C:\Path\To\ModPak2.pak"
```

### How Multi-PAK Works

1. **Individual File Extraction**: Uses repak's `--include` feature to extract only catalog files
2. **Sequential Search**: Tries each PAK file in order until the specific file is found
3. **Fast File Discovery**: Quickly determines if a file exists in each PAK
4. **Mod Priority**: Process PAKs in order (vanilla first, then mods for override behavior)

### Common Mod Scenarios

**Single Mod with Split Assets**:
```bash
fs extract-assets --catalog catalog.json \
  --pak vanilla.pak --pak mod_part1.pak --pak mod_part2.pak
```

**Multiple Independent Mods**:
```bash
fs extract-assets --catalog catalog.json \
  --pak vanilla.pak --pak weapon_mod.pak --pak vehicle_mod.pak
```

## Command-Line Options

```bash
fs extract-assets [OPTIONS]

Required:
  --catalog PATH              Path to catalog.json file

Optional:
  --pak PATH                  PAK file path (can be specified multiple times)
  --extractor-tool PATH       Path to repak.exe (default: C:\repak\repak.exe)
  --converter-tool PATH       Path to umodel.exe (default: C:\UModel\umodel.exe)
  --output PATH               Output directory (default: output)
  --workers N                 Number of parallel workers (default: CPU count)
  --log-file PATH             Path to log file (default: console only)
  --verbose                   Enable verbose logging (debug level)
  --quiet                     Suppress all output except errors and warnings
```

## Performance Options

### Parallel Processing

```bash
# Use 8 parallel workers
fs extract-assets --catalog catalog.json --workers 8

# Use all CPU cores (default)
fs extract-assets --catalog catalog.json
```

### Logging

```bash
# Log to file for debugging
fs extract-assets --catalog catalog.json --log-file extraction.log

# Verbose logging
fs extract-assets --catalog catalog.json --verbose --log-file extraction.log

# Quiet mode (only errors)
fs extract-assets --catalog catalog.json --quiet
```

## Output Structure

Creates PNG files matching the catalog.json structure:

```
output/
├── War/Content/Textures/Items/
│   ├── BasicMaterials.png
│   ├── RefinedMaterials.png
│   └── ...
├── War/Content/Textures/UI/Menus/
│   └── IconFilterCrates.png
└── ...
```

## Recommended output
Example extracting vanilla icons with custom tools path

```bash
fs extract-assets --catalog catalog.json --extractor-tool ./repak/repak.exe \
  --converter-tool ./umodel/umodel.exe \
  --pak 'C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks\War-WindowsNoEditor.pak' \
  --output ./extracted_images/vanilla/
```

Example extracting [UI Label Icons mods](https://sentsu.itch.io/foxhole-ui-label-icons)

```bash
fs extract-assets --catalog catalog.json --extractor-tool ./repak/repak.exe \
  --converter-tool ./umodel/umodel.exe \
  --pak 'C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks\War-WindowsNoEditor_UI_Label_Items_v6.0.pak' \
  --pak 'C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks\War-WindowsNoEditor_UI_Label_Vehicles_v6.0.pak' \
  --pak 'C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks\War-WindowsNoEditor_UI_Label_Materials_v5.0.pak' \
  --output ./extracted_images/ui-label/
```

The output folder should look like:
```
extracted_images/
├── vanilla/
├── ui-label/
└── ...
```

## Integration

This command is part of the Foxhole Stockpiles CLI tool suite. For complete pipeline usage:

```bash
# 1. Extract assets (this tool)
fs extract-assets --catalog catalog.json --pak game.pak --output raw_assets/

# 2. Generate templates
fs generate-templates --catalog catalog.json --assets raw_assets/ --templates processed_templates/

# 3. Build database
fs database-builder --catalog catalog.json --templates processed_templates/ --database templates.h5

# 4. Scan stockpiles
fs scanner --database templates.h5 --image screenshot.png
```

For more help:
```bash
fs extract-assets --help
fs --help  # See all available commands
```

### Why Some Files May Fail
- **Missing Assets**: Some catalog entries may reference files not present in your PAK collection like subicons.
- **Subicons from Vanilla**: Other tools need the subicons making it mandatory to extract them from vanilla, even if you plan to use moded icons only the subicons should be extracted from vanilla and then moved to the appropriate location in the mod. This ONLY applies if you plan to remove vanilla icons.

## Related Tools

- [`fs generate-templates`](../generate_templates/README.md) - Uses the assets extracted by this tool
- [`fs database-builder`](../database_builder/README.md) - Uses templates generated from these assets
- [`fs scanner`](../stockpile_scanner/README.md) - Final tool that uses the complete pipeline
- [`fs inspect`](../candidate_inspector/README.md) - Debug tool for inspecting results

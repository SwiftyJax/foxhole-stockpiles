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

## Basic Usage

### Vanilla Game Extraction

```bash
# Extract from default Foxhole installation using repak
python uasset_extractor.py --catalog catalog.json

# Custom PAK file location
python uasset_extractor.py \
    --catalog catalog.json \
    --pak "C:\Games\Foxhole\War\Content\Paks\War-WindowsNoEditor.pak"
```

### Custom Output Directory

```bash
python uasset_extractor.py \
    --catalog catalog.json \
    --output "extracted_assets/"
```

## Mod Support

The extractor handles multiple PAK files for comprehensive mod support:

### Multi-PAK Extraction

```bash
# Extract from multiple PAK files (vanilla + mods)
python uasset_extractor.py \
    --catalog catalog.json \
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
python uasset_extractor.py \
    --catalog catalog.json \
    --pak vanilla.pak \
    --pak mod_part1.pak \
    --pak mod_part2.pak
```

**Multiple Independent Mods**:
```bash
python uasset_extractor.py \
    --catalog catalog.json \
    --pak vanilla.pak \
    --pak weapon_mod.pak \
    --pak vehicle_mod.pak
```

## Command-Line Options

```bash
python uasset_extractor.py [OPTIONS]

Required:
  --catalog PATH              Path to catalog.json file

Optional:
  --pak PATH                  PAK file path (can be specified multiple times)
  --extractor-tool PATH       Path to repak.exe (default: C:\repak\repak.exe)
  --converter-tool PATH       Path to umodel.exe (default: C:\UModel\umodel.exe)
  --output PATH               Output directory (default: ./output)
  --workers N                 Number of parallel workers (default: CPU count)
  --logfile PATH              Log file path (default: console only)
```

## Performance Options

### Parallel Processing

```bash
# Use 8 parallel workers
python uasset_extractor.py --catalog catalog.json --workers 8

# Use all CPU cores (default)
python uasset_extractor.py --catalog catalog.json
```

### Logging

```bash
# Log to file for debugging
python uasset_extractor.py \
    --catalog catalog.json \
    --logfile extraction.log
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
python -m foxhole_stockpiles.commands.uasset_extractor.uasset_extractor --catalog catalog.json --extractor-tool ./repak/repak.exe --converter-tool ./umodel/umodel.exe --pak 'C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks\War-WindowsNoEditor.pak' --output .\extracted_images\vanilla\
```

Example extracting [UI Label Icons mods](https://sentsu.itch.io/foxhole-ui-label-icons)

```bash
python -m foxhole_stockpiles.commands.uasset_extractor.uasset_extractor --catalog catalog.json --extractor-tool ./repak/repak.exe --converter-tool ./umodel/umodel.exe --pak 'C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks\War-WindowsNoEditor_UI_Label_Items_v6.0.pak' --pak 'C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks\War-WindowsNoEditor_UI_Label_Vehicles_v6.0.pak' --pak 'C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks\War-WindowsNoEditor_UI_Label_Materials_v5.0.pak' --output .\extracted_images\vanilla\
```

The output folder should look like:
```
extracted_images/
├── vanilla/
├── ui-label/
└── ...
```

### Why Some Files May Fail
- **Missing Assets**: Some catalog entries may reference files not present in your PAK collection like subicons.
- **Subicons from Vanilla**: Other tools need the subicons making it mandatory to extract them from vanilla, even if you plan to use moded icons only the subicons should be extracted from vanilla and then moved to the appropriate location in the mod. This ONLY applies if you plan to remove vanilla icons.

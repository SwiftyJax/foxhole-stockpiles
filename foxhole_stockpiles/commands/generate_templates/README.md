# Template Generator

This directory contains the tool for generating icon templates from extracted game assets for Foxhole stockpile recognition.

## Overview

The `generate_templates.py` tool processes PNG files extracted from Foxhole PAK files and creates template images at multiple resolutions. It generates both normal and crated variants of each icon, preparing them for template matching in the recognition system.

## Purpose

This tool is **Step 2** in the database building pipeline:

1. **PAK Extraction** (`uasset_extractor.py`) - Extracts PNG files from game PAK files
2. **Template Generation** (`generate_templates.py`) - **THIS TOOL** - Creates resolution-specific templates
3. **Database Building** (`database_builder.py`) - Builds optimized binary database

## What It Does

### Icon Template Generation
- **Multi-Resolution**: Creates templates for 16 different resolutions (664p to 2160p)
- **Scaling Algorithm**: Uses 64px@2160p as base scale, proportionally scales for other resolutions
- **Crate Variants**: Generates both normal and crated versions using IconFilterCrates overlay
- **Mod Support**: Handles vanilla and mod variants of the same items

### Visual Processing
- **Subicon Overlays**: Applies category icons (weapons, vehicles, etc.) to top-left corners
- **Brown Effect**: Applies visual tinting to subicons for game accuracy
- **Alpha Blending**: Proper transparency handling for overlay effects
- **Crate Overlay**: Adds semi-transparent crate icon to bottom-right for crated variants

### Output Organization
- **Item-Based Folders**: Creates separate directories for each item code name
- **Crated Separation**: Normal and crated variants in separate folders
- **Naming Convention**: `{mod_name}_{code_name}_{size}.png` format

## Usage

### Command Line Interface

```bash
python generate_templates.py --catalog CATALOG --assets INPUT --templates TEMPLATES [--logfile LOGFILE]
```

### Arguments

- `--catalog` (required): Path to catalog.json file containing item definitions
- `--assets` (required): Path to directory containing extracted PNG assets
- `--templates` (required): Path where template images will be saved
- `--logfile` (optional): Path to log file for detailed output

### Examples

**Basic usage:**
```bash
python generate_templates.py \
    --catalog catalog.json \
    --assets extracted_assets \
    --templates template_images
```

**With logging:**
```bash
python generate_templates.py \
    --catalog catalog.json \
    --assets extracted_assets \
    --templates template_images
    --logfile generation.log
```

## Input Requirements

### Directory Structure
The input directory should contain extracted PNG files organized as:

```
extracted_assets/
├── vanilla/                         # Base game assets
│   └── War/Content/Textures/...     # PNG files from PAK extraction
└── mod_name/                        # Mod assets (if any)
    └── War/Content/Textures/...     # Mod-specific PNG files
```

### Catalog File
A JSON file containing item definitions:

```json
[
  {
    "CodeName": "ItemCodeName",
    "Icon": "War/Content/Textures/UI/Icons/ItemIcon.0",
    "SubTypeIcon": "War/Content/Textures/UI/Icons/CategoryIcon.0"
  }
]
```

## Output Structure

The tool creates organized templates:

```
templates_images/
├── ItemCodeName/                    # Normal variants
│   ├── vanilla_ItemCodeName_19.png  # 664p resolution
│   ├── vanilla_ItemCodeName_21.png  # 720p resolution
│   ├── ...
│   └── vanilla_ItemCodeName_64.png  # 2160p resolution
└── ItemCodeName_crated/             # Crated variants
    ├── vanilla_ItemCodeName_19_crated.png
    ├── vanilla_ItemCodeName_21_crated.png
    ├── ...
    └── vanilla_ItemCodeName_64_crated.png
```

### Multi-Mod Processing
**Understanding Success Rates**: When processing multiple mods, the tool attempts to generate templates for every item-mod combination. For example:
- 359 catalog items × 2 mods = 718 total combinations
- Some items may not exist in all mods (e.g., vanilla-only or mod-specific items)
- Success rate of 95-99% is normal and expected as some mods might not include all the icons
- The tool ensures every catalog item has templates from at least one mod

**Example Output**:
```
=== GENERATION SUMMARY ===
Total catalog items: 359
Available mods: 2 (ui-label, vanilla)
Expected combinations: 718 (items × mods)
Successfully processed: 713
Skipped (mod unavailable): 5
Success rate: 99.3%
Unique items with templates: 359/359
```

### Output Size
- **Per item**: ~32 templates (16 resolutions × 2 variants)
- **File size**: ~50-200KB per template depending on resolution
- **Total output**: ~10-50MB for typical game catalog

## Features

### Error Handling
- **Missing Files**: Skips items with missing source images
- **Invalid Images**: Handles corrupted or unreadable files gracefully
- **Progress Tracking**: Shows processing progress every 50 items
- **Comprehensive Logging**: Debug, info, warning, and error levels

### Quality Assurance
- **Catalog Validation**: Verifies all catalog items have required fields
- **File Existence**: Checks for source PNG files before processing
- **Success Metrics**: Reports successful vs failed item processing
- **Visual Validation**: Ensures proper overlay positioning and effects

## Integration

### Pipeline Position
This tool bridges PAK extraction and database building:

```
PAK Files → uasset_extractor.py → PNG Files → generate_templates.py → Templates → database_builder.py → Binary DB
```

### Next Steps
The generated templates are consumed by `database_builder.py` to create the final optimized database for the recognition system.

### Supported Resolutions
Based on common game resolutions, scaled proportionally:
- 664p, 720p, 768p, 800p, 864p, 900p, 960p, 992p
- 1024p, 1050p, 1080p, 1200p, 1440p, 1536p, 1600p, 2160p

## Troubleshooting

### Common Issues

**Question: "Why does it show 713/718 successful? Are 5 items missing?"**
- This is normal for multi-mod setups
- The numbers represent item-mod combinations, not unique items
- Some items exist in vanilla but not in mods
- Check the summary: "Unique items with templates: 359/359" - this is the important number
- As long as all catalog items have templates from at least one mod, everything is working correctly

**Error: "Invalid catalog file"**
- Check JSON syntax in catalog file
- Ensure file exists and is readable

**Warning: "File does not exist"**
- Verify input directory contains extracted PNG files
- Check that PAK extraction completed successfully

**Error: "Failed to save image"**
- Ensure output directory is writable
- Check available disk space

### Debug Tips
- Use `--logfile` to capture detailed processing information
- Check logs for specific items that fail processing
- Verify catalog item names match extracted file paths
- Ensure proper directory permissions for input and output

## Dependencies

- **OpenCV (cv2)**: Image processing and manipulation
- **NumPy**: Efficient array operations
- **Python 3.12+**: Modern Python features and type annotations

See `pyproject.toml` for exact version requirements.

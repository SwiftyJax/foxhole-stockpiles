# Stockpile Scanner

This directory contains the main tool for detecting and identifying items in Foxhole stockpile screenshots using computer vision and template matching.

## Overview

The `stockpile_scanner.py` tool analyzes screenshots of Foxhole stockpiles and automatically identifies the items and their quantities. It combines region detection, icon extraction, and template matching to provide accurate stockpile inventory analysis.

## Purpose

This is the **primary recognition tool** in the Foxhole Stockpiles system. It consumes the databases created by the database building pipeline and applies them to real game screenshots for automated stockpile analysis.

## What It Does

### Screenshot Analysis
- **Region Detection**: Automatically detects quantity boxes and icon regions
- **Scale Detection**: Identifies resolution scale factors for accurate recognition
- **Icon Extraction**: Extracts individual item icons from detected regions
- **Group Analysis**: Organizes icons into logical groups for processing

### Template Matching
- **Database Loading**: Loads optimized binary databases for fast template matching
- **Multi-Stage Filtering**: Uses pre-computed features for efficient candidate filtering
- **Match Scoring**: Provides match confidence scores for all detected items
- **Faction Filtering**: Supports filtering by Colonial/Warden faction when specified

### Results Processing
- **Item Identification**: Converts matched templates to item codes
- **Quantity Detection**: Associates detected quantities with identified items
- **Category Classification**: Determines item categories (weapons, supplies, vehicles, etc.)
- **Crate Detection**: Identifies crated vs normal item variants

## Usage

### Primary Interface

The scanner is available through the unified Foxhole Stockpiles CLI:

```bash
fs scanner --database DATABASE --image IMAGE [OPTIONS]
fs scan --database DATABASE --image IMAGE [OPTIONS]    # Short alias
```

### Development Interface

For development and testing, you can also run the scanner module directly:

```bash
python -m foxhole_stockpiles.commands.stockpile_scanner --database DATABASE --image IMAGE [OPTIONS]
```

**Note**: The recommended way to use this tool is through the unified `fs` command.

### Command Line Interface

### Arguments

#### Database
- `--database`: Path to the template database file (.pkl format). If not provided, uses the value from configuration file

#### Optional
- `--image`: Path to the input screenshot image file
- `--faction`: Faction filter (Colonial: 'c'/'colonials', Warden: 'w'/'wardens')
- `--mod`: Mod filter to limit detection to specific mod items
- `--language`: Language for text detection (en, pt, fr, de, ru, zh). If not specified, uses all supported languages
- `--early_exit`: Early exit threshold for icon matching (0.0 = disabled, test all candidates)
- `--debug_image`: Save debug image showing detected regions and matches
- `--verbose`: Enable verbose logging (debug level)
- `--quiet`: Suppress output except errors and warnings
- `--log-file`: Path to log file (default: console only)
- `--output-format`: Output format for results (console, file, json, webhook)
- `--config`: Path to configuration file
- `--token`: Override the webhook token from the configuration file

### Examples

**Basic stockpile scanning:**
```bash
fs scanner --database database/db.pkl --image screenshot.png
```

**With faction filtering and debug output:**
```bash
fs scanner --database database/db.pkl --image stockpile_screenshot.png \
  --faction colonial --debug_image --verbose
```

**With logging:**
```bash
fs scanner --database database/db.pkl --image stockpile.png \
  --log-file scan_results.log
```

**Webhook output:**
```bash
fs scanner --database database/db.pkl --image stockpile.png \
  --output-format webhook --config config.json
```

**JSON output to file:**
```bash
fs scanner --database database/db.pkl --image stockpile.png \
  --output-format json
```

**With mod filtering:**
```bash
fs scanner --database database/db.pkl --image stockpile.png \
  --mod custom_mod_name
```

**With specific language for text detection:**
```bash
# French stockpile
fs scanner --database database/db.pkl --image stockpile.png \
  --language fr

# Portuguese stockpile
fs scanner --database database/db.pkl --image stockpile.png \
  --language pt
```

## Input Requirements

### Screenshot Format
- **Supported formats**: PNG, JPG, BMP
- **Resolution support**: 664p to 2160p vertical resolution
- **Content**: Full or partial Foxhole stockpile interface screenshots
- **Quality**: Clear, unobstructed view of stockpile items

### Database File
- **Format**: Binary database file (.pkl) created by `fs database-builder`
- **Content**: Pre-computed templates and lookup tables for target resolution
- **Size**: Typically 35-75MB for full game item databases

### Supported Resolutions
The scanner automatically detects and supports:
- 664p, 720p, 768p, 800p, 864p, 900p, 960p, 992p
- 1024p, 1050p, 1080p, 1200p, 1440p, 1536p, 1600p, 2160p

## Output

### Detection Summary
The tool provides comprehensive analysis results:

```
Detection Summary:
- Resolution scale factor: 1.000
- Detected 24 quantity boxes
- Detected 6 icon groups

Loaded database for resolution 1080 with 15,247 templates

Group 0: Icon at index 0 matched with template 'BasicMaterials' (confidence: 0.92)
Group 0: Icon at index 1 matched with template 'RefinedMaterials' (confidence: 0.99)
Group 1: Icon at index 2 matched with template 'Rifle' (confidence: 0.95)
...
```

### Scanned Stockpile Data
The tool builds a structured data object containing:

```python
{
    "items": ["BasicMaterials", "RefinedMaterials", "Rifle", ...],
    "quantities": [150, 75, 12, ...],
    "type": "Seaport",
    "name": "Port Base",
    "shard": "Able",
    "timestamp": "2024-01-15T14:30:00Z"
}
```

### Debug Output
When using `--debug_image`, creates a visual debugging image showing:
- Detected quantity boxes (green rectangles)
- Identified icon regions (blue rectangles)
- Group boundaries and classifications
- Match confidence scores and item labels

## Features

### Advanced Recognition
- **Multi-Resolution Support**: Automatically adapts to different screenshot resolutions
- **Adaptive Scaling**: Handles various UI scale settings and aspect ratios
- **Group Intelligence**: Uses contextual information to improve accuracy
- **Crate Detection**: Distinguishes between normal and crated item variants

### Quality Assurance
- **Match Confidence**: Returns confidence scores for all matches for downstream filtering
- **Faction Validation**: Cross-references matches against expected factions
- **Category Consistency**: Validates item categories within groups
- **Progressive Learning**: Improves accuracy using group context

### Performance Optimization
- **Fast Database Loading**: 1-2 second initialization for large databases
- **Efficient Filtering**: Multi-stage candidate reduction (12,000 → 20-30 candidates)
- **Quick Recognition**: 1-4ms per icon recognition after filtering
- **Memory Efficient**: Processes large screenshots without excessive memory usage
- **Configurable Performance**: Tunable parameters for speed vs accuracy trade-offs

### Template Matching Controls
- **Early Exit Threshold**: Stop searching when a match exceeds this confidence (speeds up processing)
- **NCC Candidate Limit**: Maximum number of candidates to evaluate (controls processing time)
- **pHash Filtering**: Pre-filter candidates using perceptual hash distance (improves accuracy)

## Integration

### Pipeline Position
This is the final consumer tool in the processing pipeline:

```
PAK Files → fs extract-assets → fs generate-templates → fs database-builder → fs scanner
```

### Data Flow
```
Screenshot Input → Region Detection → Icon Extraction → Database Lookup → Template Match → Structured Output
```

## Performance

### Recognition Speed
- **Total processing**: 1-2 seconds for stockpile screenshots with 80-120 items. It varies depending on the max_ncc_candidates used

## Troubleshooting

### Common Issues

**Error: "File 'screenshot.png' does not exist"**
- Verify the image file path is correct
- Check file permissions and accessibility

**Error: "Invalid resolution"**
- Ensure screenshot resolution is supported (664p-2160p)
- Check that the screenshot shows the full stockpile interface

**Warning: "No match found for icon"**
- Check the returned confidence score to see how close the best match was
- Increase max NCC candidates in config (max_ncc_candidates = 50)
- Adjust pHash threshold (--phash_threshold 15)
- Enable debug output to see what was detected
- Verify database contains templates for the target resolution

**Low detection accuracy**
- Ensure screenshot quality is good (no blur, compression artifacts)
- Try using faction filtering to reduce search space
- Check that database matches the game version/mods

### Debug Tips
- Use `--debug_image` to visualize detection regions
- Enable `--verbose` logging for detailed processing information
- Check confidence scores in output to understand match quality
- Test with different resolution screenshots to find optimal settings
- Verify database loading succeeds and reports expected template count

## Dependencies

- **OpenCV (cv2)**: Image processing and computer vision operations
- **NumPy**: Efficient array operations and mathematical computations

See `pyproject.toml` for exact version requirements.

## Integration

This command is part of the Foxhole Stockpiles CLI tool suite. For complete pipeline usage:

```bash
# 1. Extract assets
fs extract-assets --catalog catalog.json --pak game.pak --output raw_assets/

# 2. Generate templates
fs generate-templates --catalog catalog.json --assets raw_assets/ --templates processed_templates/

# 3. Build database
fs database-builder --catalog catalog.json --templates processed_templates/ --database templates.pkl

# 4. Scan stockpiles
fs scanner --database templates.pkl --image screenshot.png
```

For more help:
```bash
fs scanner --help
fs --help  # See all available commands
```

## Related Tools

- [`fs database-builder`](../database_builder/README.md) - Creates the template databases used by this scanner
- [`fs generate-templates`](../generate_templates/README.md) - Generates the templates from game assets
- [`fs inspect`](../candidate_inspector/README.md) - Debugging tool for template matching issues
- [`fs extract-assets`](../uasset_extractor/README.md) - Extracts game assets for template generation

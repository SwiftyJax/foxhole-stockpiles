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
- **Confidence Scoring**: Provides match confidence levels for quality assurance
- **Faction Filtering**: Supports filtering by Colonial/Warden faction when specified

### Results Processing
- **Item Identification**: Converts matched templates to item codes
- **Quantity Detection**: Associates detected quantities with identified items
- **Category Classification**: Determines item categories (weapons, supplies, vehicles, etc.)
- **Crate Detection**: Identifies crated vs normal item variants

## Usage

### Command Line Interface

```bash
python stockpile_scanner.py --database DATABASE --image IMAGE [OPTIONS]
```

### Arguments

#### Required
- `--database`: Path to the template database file (.pkl format)
- `--image`: Path to the input screenshot image file

#### Optional Filtering
- `--faction`: Faction filter (Colonial: 'c'/'colonial', Warden: 'w'/'warden')
- `--confidence`: Minimum confidence threshold for icon matching (default: 0.8, range: 0.0-1.0)

#### Output Control
- `--debug_image`: Save debug image showing detected regions and matches
- `--verbose`: Enable verbose logging (debug level)
- `--quiet`: Suppress output except errors and warnings
- `--log-file`: Path to log file (default: console only)

### Examples

**Basic stockpile scanning:**
```bash
python stockpile_scanner.py \
    --database database/db.pkl \
    --image screenshot.png
```

**With faction filtering and debug output:**
```bash
python stockpile_scanner.py \
    --database database/db.pkl \
    --image stockpile_screenshot.png \
    --faction colonial \
    --debug_image \
    --verbose
```

**High confidence matching with logging:**
```bash
python stockpile_scanner.py \
    --database database/db.pkl \
    --image stockpile.png \
    --confidence 0.9 \
    --log-file scan_results.log
```

## Input Requirements

### Screenshot Format
- **Supported formats**: PNG, JPG, BMP
- **Resolution support**: 664p to 2160p vertical resolution
- **Content**: Full or partial Foxhole stockpile interface screenshots
- **Quality**: Clear, unobstructed view of stockpile items

### Database File
- **Format**: Binary database file (.pkl) created by `database_builder.py`
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
Group 0: Icon at index 1 matched with template 'RefinedMaterials' (confidence: 0.89)
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
    "hex_name": "Deadlands",
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
- **Confidence Thresholds**: Configurable minimum confidence for reliable matches
- **Faction Validation**: Cross-references matches against expected factions
- **Category Consistency**: Validates item categories within groups
- **Progressive Learning**: Improves accuracy using group context

### Performance Optimization
- **Fast Database Loading**: 1-2 second initialization for large databases
- **Efficient Filtering**: Multi-stage candidate reduction (12,000 → 20-30 candidates)
- **Quick Recognition**: 1-4ms per icon recognition after filtering
- **Memory Efficient**: Processes large screenshots without excessive memory usage

## Integration

### Pipeline Position
This is the final consumer tool in the processing pipeline:

```
PAK Files → uasset_extractor → generate_templates → database_builder → stockpile_scanner
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
- Try lowering confidence threshold (--confidence 0.7)
- Enable debug output to see what was detected
- Verify database contains templates for the target resolution

**Low detection accuracy**
- Ensure screenshot quality is good (no blur, compression artifacts)
- Try using faction filtering to reduce search space
- Check that database matches the game version/mods

### Debug Tips
- Use `--debug_image` to visualize detection regions
- Enable `--verbose` logging for detailed processing information
- Start with lower confidence thresholds and increase gradually
- Test with different resolution screenshots to find optimal settings
- Verify database loading succeeds and reports expected template count

## Dependencies

- **OpenCV (cv2)**: Image processing and computer vision operations
- **NumPy**: Efficient array operations and mathematical computations

See `pyproject.toml` for exact version requirements.

## Related Tools

- **Database Builder**: Creates the template databases used by this scanner
- **Template Generator**: Generates the templates from game assets
- **Candidate Inspector**: Debugging tool for template matching issues
- **PAK Extractor**: Extracts game assets for template generation

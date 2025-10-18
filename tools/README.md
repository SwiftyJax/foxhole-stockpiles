# Developer Tools

This directory contains utilities for developers working on the foxhole-stockpiles project.

## Database Visualizer

**File:** `database_visualizer.py`

A tool to visualize the icons in the database. It displays the selected resolution and upscales
the icon to compare it with the highest resolution available.

It allows filtering by faction, category, mod, crated status, and partial code matching.

### Requirements

This tool requires the development dependencies to be installed:

```bash
pip install -e ".[dev]"
```

### Usage

```bash
python tools/database_visualizer.py
```

The tool will load the template database and provide a GUI for browsing and inspecting icon templates.

## Crate Overlay Calibrator

**File:** `crate_overlay_calibrator.py`

An interactive GUI tool for calibrating the color transformation formula applied to crate overlays
on item icons. This tool helps match the appearance of crated items in the game by allowing you to:

- Load a base icon and crate overlay image
- Adjust RGB multipliers and offsets for each color channel
- Control alpha blending strength
- Manually select sample points in light and dark areas
- Auto-calculate optimal transformation parameters to match target colors
- Preview the result in real-time

The goal is to tune the transformation formula so that the composited result matches how crated items
appear in actual in-game screenshots.

### Requirements

This tool requires the development dependencies to be installed:

```bash
pip install -e ".[dev]"
```

### Usage

```bash
# Basic usage with GUI file pickers
python tools/crate_overlay_calibrator.py

# Load images directly from command line
python tools/crate_overlay_calibrator.py --icon path/to/icon.png --crate path/to/crate.png

# Specify custom icon size
python tools/crate_overlay_calibrator.py --size 35
```

### How It Works

1. **Load Images**: Load a base item icon and a crate overlay image
2. **Manual Sampling**: Click on the preview to select light and dark sample points
3. **Manual Tuning**: Use sliders to adjust RGB multipliers, offsets, and alpha
4. **Auto-Calculate**: Click "Auto Calculate" to automatically compute optimal transformation parameters
5. **Verify**: Check that the preview matches the target colors (Light: R:182, G:179, B:170 / Dark: R:75, G:73, B:69)

The tool displays the transformation formula as: `crate_color = original × multiplier + offset`

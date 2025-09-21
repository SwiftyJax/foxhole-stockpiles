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

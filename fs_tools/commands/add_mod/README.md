# Add Mod

This directory contains the tool for adding a complete mod to existing template databases by running the full import pipeline.

## Overview

The `fs add-mod` tool allows you to add all icons from a mod's PAK file(s) to your template database in a single command. It orchestrates the complete pipeline: extracting assets, generating templates, and building/merging the database.

## Purpose

This tool is designed for **mod integration** into your template databases:

- Add all icons from a mod PAK file in one command
- Automatically extract assets using repak and umodel
- Generate templates for all configured resolutions
- Merge new templates into existing database without rebuilding
- Skip items that already exist in the database (unless overwrite is enabled)

## What It Does

### Complete Pipeline
Runs the full import pipeline automatically:

1. **Catalog Check**: Loads catalog and checks which items already exist in database
2. **Asset Extraction**: Extracts icons from mod PAK files using external tools
3. **Template Generation**: Creates resolution-specific templates with crate overlays
4. **Database Building**: Merges new templates into existing database

### Smart Merging
- **Skip existing**: By default, only adds items not already in database
- **Overwrite mode**: Optionally replace all templates for the mod
- **Vanilla dependencies**: Can extract shared resources (crate icons) from vanilla PAK

## Usage

### Primary Interface

The add mod tool is available through the unified Foxhole Stockpiles CLI:

```bash
fs add-mod --pak MOD.pak --name "Mod Name" [OPTIONS]
fs mod --pak MOD.pak --name "Mod Name" [OPTIONS]    # Short alias
```

### Development Interface

For development and testing, you can also run the module directly:

```bash
python -m foxhole_stockpiles.commands.add_mod.add_mod --pak MOD.pak --name "Mod Name" [OPTIONS]
```

**Note**: The recommended way to use this tool is through the unified `fs` command.

### Command Line Interface

### Required Arguments

- `--pak`: Path to mod PAK file (can be specified multiple times for multi-PAK mods)
- `--name`: Name of the mod (alphanumeric, spaces, underscores, hyphens only)

### Optional Arguments

- `--vanilla`: Path to vanilla PAK file for shared dependencies (crate icons, subicons)
- `--catalog`: Path to catalog.json (default: from database_builder.catalog_file setting)
- `--database`: Path to output database (default: from scanner.database_path setting)
- `--extractor`: Path to repak.exe (default: from database_builder.extractor_tool setting)
- `--converter`: Path to umodel.exe (default: from database_builder.converter_tool setting)
- `--overwrite`: Overwrite existing templates for this mod (default: merge/skip existing)
- `--resolution`: Target resolution (can be specified multiple times, default: all configured)
- `--workers`: Number of worker processes for database building (default: from database_builder.workers setting or CPU count)
- `--verbose`: Enable verbose logging (debug level)
- `--quiet`: Suppress all output except errors
- `--log-file`: Path to log file for detailed output

### Examples

**Add a mod to the database (using settings for tools and paths):**
```bash
fs add-mod --pak /path/to/mod.pak --name "My Mod"
```

**Add a mod with vanilla dependencies (for shared icons like crates):**
```bash
fs add-mod --pak /path/to/mod.pak --name "My Mod" --vanilla /path/to/War.pak
```

**Overwrite existing templates for this mod:**
```bash
fs add-mod --pak /path/to/mod.pak --name "My Mod" --overwrite
```

**Add multiple PAK files for the same mod:**
```bash
fs add-mod --pak mod_part1.pak --pak mod_part2.pak --name "My Mod"
```

**Specify custom paths for all required files:**
```bash
fs add-mod --pak mod.pak --name "My Mod" \
  --catalog /path/to/catalog.json \
  --database /path/to/templates.h5 \
  --extractor /path/to/repak.exe \
  --converter /path/to/umodel.exe
```

**Add mod for specific resolutions only:**
```bash
fs add-mod --pak mod.pak --name "My Mod" \
  --resolution 1080 --resolution 1440 --resolution 2160
```

**Use single-threaded mode (avoids multiprocessing issues):**
```bash
fs add-mod --pak mod.pak --name "My Mod" --workers 1
```

## Prerequisites

Before using this command, you need:

1. **repak.exe** - PAK file extractor
   - Download from: https://github.com/trumank/repak

2. **umodel.exe** - UAsset to PNG converter
   - Download from: https://www.gildor.org/en/projects/umodel

3. **catalog.json** - Item definitions file
   - Included in repository at `data/catalog.json`

Configure these in your `.fs_config` settings file or pass as command arguments.

## Input Requirements

### Mod PAK Files
One or more PAK files containing the mod's custom icons:

- **Format**: Unreal Engine PAK files
- **Source**: Downloaded or installed mod files
- **Multiple files**: Use `--pak` multiple times for multi-part mods

### Vanilla PAK File (Optional)
The base game PAK file for shared dependencies:

- **Purpose**: Provides crate overlay icons and subicons
- **Location**: Usually at `Steam/steamapps/common/Foxhole/War/Content/Paks/War-WindowsNoEditor.pak`
- **When needed**: If mod doesn't include its own crate overlays

### Mod Name
Identifier for the mod in the database:

- **Characters allowed**: Alphanumeric, spaces, underscores, hyphens
- **Max length**: 100 characters
- **Security**: Path traversal attempts are blocked

## Output

### Database Updates
The tool merges templates into the existing database:

- **Non-destructive**: By default, only adds new items
- **Overwrite mode**: Replaces all templates for the mod if `--overwrite` is used
- **Atomic**: Uses temporary files to prevent corruption

### Console Output

**Successful import:**
```
[0/4] Checking catalog: Loading catalog and checking database...
[1/4] Extracting assets: Extracting 150 items from PAK files...
[2/4] Generating templates: Creating templates from assets...
[3/4] Building database: Adding templates to database...
[4/4] Successfully imported 150 templates

Successfully imported mod 'My Mod'
  Templates added: 150
  Templates skipped (already in database): 0
```

**With existing items skipped:**
```
Successfully imported mod 'My Mod'
  Templates added: 50
  Templates skipped (already in database): 100
```

## Configuration

### Settings File (.fs_config)

Configure default paths in your settings file:

```json
{
  "database_builder": {
    "extractor_tool": "/path/to/repak.exe",
    "converter_tool": "/path/to/umodel.exe",
    "catalog_file": "/path/to/catalog.json",
    "target_resolutions": ["1080", "1440", "2160"],
    "workers": null
  },
  "scanner": {
    "database_path": "/path/to/templates.h5"
  }
}
```

**Note**: `workers` can be set to:
- `null` - Auto-detect (uses CPU count)
- `1` - Disable multiprocessing (single-threaded)
- `2-N` - Use specified number of worker processes

### Environment Variables

```bash
FS_DATABASE_BUILDER__EXTRACTOR_TOOL=/path/to/repak.exe
FS_DATABASE_BUILDER__CONVERTER_TOOL=/path/to/umodel.exe
FS_DATABASE_BUILDER__CATALOG_FILE=/path/to/catalog.json
FS_DATABASE_BUILDER__WORKERS=4
FS_SCANNER__DATABASE_PATH=/path/to/templates.h5
```

## Performance

### Typical Timings
- **Small mod (10-50 items)**: 30 seconds - 2 minutes
- **Medium mod (50-200 items)**: 2-5 minutes
- **Large mod (200+ items)**: 5-15 minutes

### Factors Affecting Speed
- **PAK file size**: Larger files take longer to extract
- **Number of items**: More items = more template generation
- **Number of resolutions**: Each resolution multiplies template work
- **Disk speed**: SSD significantly faster than HDD

## Troubleshooting

### Common Issues

**Error: "Extractor tool not configured"**
- Configure `database_builder.extractor_tool` in settings
- Or pass `--extractor /path/to/repak.exe`

**Error: "Converter tool not configured"**
- Configure `database_builder.converter_tool` in settings
- Or pass `--converter /path/to/umodel.exe`

**Error: "PAK file not found"**
- Verify the PAK file path is correct
- Check file permissions

**Error: "Mod name can only contain alphanumeric..."**
- Use only letters, numbers, spaces, underscores, and hyphens
- Avoid special characters and path separators

**Warning: "No items extracted from PAK files"**
- The mod may not contain items defined in catalog.json
- Check that the mod includes custom icons

### Debug Tips
- Use `--verbose` for detailed logging
- Use `--log-file` to capture full output
- Check temporary directory for extracted files (before cleanup)
- Verify external tools work independently first

## Integration

### Workflow Integration

The add-mod command fits into the database management workflow:

```bash
# 1. Build initial database from vanilla game
fs database-builder --catalog catalog.json --templates vanilla_templates/ --database templates.h5

# 2. Add mods as needed
fs add-mod --pak mod1.pak --name "Mod 1" --vanilla War.pak
fs add-mod --pak mod2.pak --name "Mod 2" --vanilla War.pak

# 3. Update mods when new versions release
fs add-mod --pak mod1_v2.pak --name "Mod 1" --overwrite

# 4. Use database for scanning
fs scanner --database templates.h5 --image screenshot.png --mod "Mod 1"
```

### Use Cases

**Adding a new mod:**
```bash
# First time adding a mod
fs add-mod --pak awesome_mod.pak --name "Awesome Mod" --vanilla War.pak
```

**Updating an existing mod:**
```bash
# Mod released new version, replace all templates
fs add-mod --pak awesome_mod_v2.pak --name "Awesome Mod" --overwrite
```

**Adding multiple mods:**
```bash
# Add several mods to the same database
fs add-mod --pak mod_a.pak --name "Mod A"
fs add-mod --pak mod_b.pak --name "Mod B"
fs add-mod --pak mod_c.pak --name "Mod C"
```

## Comparison with Other Tools

### When to use `fs add-mod`:
- Adding all icons from a mod in one command
- Automated mod integration
- Building database from multiple mods

### When to use `fs add-icon`:
- Adding individual icons
- Quick fixes to existing database
- Icons not in PAK file format

### When to use `fs database-builder`:
- Initial database creation from templates
- Rebuilding entire database
- Full control over template sources

## Dependencies

- **repak.exe**: PAK file extraction (external tool)
- **umodel.exe**: UAsset conversion (external tool)
- **OpenCV (cv2)**: Image processing
- **NumPy**: Array operations
- **Python 3.12+**: Modern Python features

See `pyproject.toml` for exact version requirements.

## Related Tools

- [`fs add-icon`](../add_icon/README.md) - Add individual icons to databases
- [`fs database-builder`](../database_builder/README.md) - Build databases from templates
- [`fs extract-assets`](../uasset_extractor/README.md) - Extract assets from PAK files
- [`fs generate-templates`](../generate_templates/README.md) - Generate templates from assets
- [`fs scanner`](../stockpile_scanner/README.md) - Scan stockpiles using database

For more help:
```bash
fs add-mod --help
fs --help  # See all available commands
```

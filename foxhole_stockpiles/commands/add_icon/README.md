# Add Icon

This directory contains the tool for manually adding individual icons to existing template databases.

## Overview

The `fs add-icon` tool allows you to add custom icons to your template database without having to rebuild the entire database. This is useful when you need to add new items, fix incorrect icons, or add mod-specific icons that weren't included in the original database build.

## Purpose

This tool is designed for **manual icon management** in your template databases:

- Add new item icons discovered after initial database build
- Add mod-specific icons without rebuilding from PAK files
- Fix or replace individual icons in the database
- Add custom resolution-specific icons
- Support multi-resolution icon additions in a single command

## What It Does

### Icon Addition
Adds individual icons to existing template databases:

- **Resolution targeting**: Add icons for specific resolutions
- **Multi-resolution support**: Add the same icon to multiple resolutions in one command
- **Complete metadata**: Specify faction, category, mod, and crated variant information
- **Automatic optimization**: Computes optimization data via `compute_optimization_data()`
- **Safe operations**: Creates backup before modifying database

### Database Management
- **Backup creation**: Automatically backs up database before modifications
- **Atomic updates**: Restores backup if save fails
- **Validation**: Ensures icon files and resolutions exist before adding
- **Statistics**: Reports total templates and database size after updates

## Usage

### Primary Interface

The add icon tool is available through the unified Foxhole Stockpiles CLI:

```bash
fs add-icon --database DATABASE --icon ICON --code CODE --faction FACTION --category CATEGORY --mod MOD --resolution RESOLUTION [OPTIONS]
fs add --database DATABASE --icon ICON --code CODE --faction FACTION --category CATEGORY --mod MOD --resolution RESOLUTION [OPTIONS]    # Short alias
```

### Development Interface

For development and testing, you can also run the add icon module directly:

```bash
python -m foxhole_stockpiles.commands.add_icon.add_icon --database DATABASE --icon ICON --code CODE --faction FACTION --category CATEGORY --mod MOD --resolution RESOLUTION [OPTIONS]
```

**Note**: The recommended way to use this tool is through the unified `fs` command.

### Command Line Interface

### Required Arguments

- `--database`: Path to existing template database (.pkl file)
- `--icon`: Path to icon image file (PNG format recommended)
- `--code`: Item code name (e.g., Rifle, LightTank, Medkit)
- `--faction`: Item faction - Valid inputs: 'c', 'colonials' for Colonials; 'w', 'wardens' for Wardens; 'n', 'neutral' for Neutral
- `--category`: Item category (choices: item, vehicle, shippable)
- `--mod`: Mod name (e.g., vanilla, custom_mod)
- `--resolution`: Target resolution (can be specified multiple times)

### Optional Arguments

- `--crated`: Mark this icon as a crated variant (flag, default: False)
- `--replace`: Replace existing icon if one already exists with same metadata (flag, default: False)
- `--verbose`: Enable verbose logging (debug level)
- `--quiet`: Suppress all output except errors and warnings
- `--log-file`: Path to log file for detailed output (default: console only)

### Examples

**Add a normal Colonial rifle icon at 1080p:**
```bash
fs add-icon --database data/templates.pkl --icon rifle.png \
  --code Rifle --faction c --category item \
  --mod vanilla --resolution 1080
```

**Add a crated Warden shippable icon at 2160p:**
```bash
fs add-icon --database data/templates.pkl --icon crate_crated.png \
  --code ShippableCrate --faction w --category shippable \
  --crated --mod vanilla --resolution 2160
```

**Add a neutral item at multiple resolutions:**
```bash
fs add-icon --database data/templates.pkl --icon medkit.png \
  --code Medkit --faction n --category item \
  --mod vanilla --resolution 1080 --resolution 1440 --resolution 2160
```

**Add a custom mod icon with verbose logging:**
```bash
fs add-icon --database data/templates.pkl --icon custom_item.png \
  --code CustomItem --faction n --category item \
  --mod my_custom_mod --resolution 1080 --verbose
```

## Input Requirements

### Database File
An existing template database file created by `fs database-builder`:

```
data/
└── templates.pkl    # Existing database with resolution-specific templates
```

### Icon File
A PNG image file containing the icon to add:

- **Format**: PNG (recommended) or any format supported by OpenCV
- **Size**: MUST match the exact size required for the target resolution (see table below)
- **Quality**: Must be properly sized - no resizing is performed
- **Naming**: Filename doesn't matter, metadata is specified via CLI arguments
- **Important**: Icons with incorrect dimensions will be rejected

### Resolution Information

The tool automatically calculates the correct icon size based on the target resolution:

- 664p → 19px icons
- 720p → 21px icons
- 768p → 23px icons
- 900p → 27px icons
- 1024p → 30px icons
- 1050p → 31px icons
- 1080p → 32px icons
- 1200p → 36px icons
- 1440p → 43px icons
- 1536p → 45px icons
- 1600p → 47px icons
- 1920p → 57px icons
- 2160p → 64px icons

## Output

### Database Updates
The tool updates the existing database file in place:

- **Backup**: Original database is backed up to `{database}.backup`
- **Atomic**: Backup is restored if save operation fails
- **Verification**: Reports total templates and file size after save

### Console Output

**Successful addition:**
```
INFO: Added icon for 'Rifle' to resolution 1080 (crated=False, faction=Colonials, category=item, mod=vanilla)
INFO: Database saved: 7 resolutions, 1523 total templates, 45.2 MB
```

**Error cases:**
```
ERROR: Icon file not found: rifle.png
ERROR: Resolution 1080 not found in database. Available resolutions: ['664', '720', '1440']
ERROR: Failed to load icon image: corrupt.png
```

## Features

### Icon Processing

**Image Handling:**
- Loads icon images using OpenCV
- Automatically resizes to resolution-specific sizes
- Converts to numpy arrays for storage

**Metadata Management:**
- Associates icon with item code
- Tracks faction, category, and mod information
- Supports crated variant flagging

**Optimization:**
- Computes NCC normalization data
- Calculates perceptual hash for fast filtering
- Pre-computes template statistics

### Safety Features

**Data Protection:**
- Automatic backup creation before modifications
- Atomic operations with rollback on failure
- Validation of inputs before processing

**Error Handling:**
- Validates icon file existence
- Checks resolution availability in database
- Verifies icon can be loaded before adding

## Performance

### Operation Speed
- **Icon addition**: < 100ms per icon (including resize and optimization)
- **Database save**: 1-3 seconds for typical databases (50-100MB)
- **Multi-resolution**: Linear scaling with number of resolutions

### Memory Usage
- **Peak memory**: ~2x database size during save operation
- **Typical**: 100-200MB for standard game databases

## Technical Details

### Icon Size Calculation
Icons are sized based on resolution using the same formula as database builder:
```python
icon_scaling_factor = 64 / 2160  # 64px at 2160p
icon_size = int(icon_scaling_factor * resolution_height)
```

### Database Format
The tool maintains compatibility with the database format created by `fs database-builder`:
```
Pickle format (HIGHEST_PROTOCOL):
- Dictionary mapping SupportedResolution → TemplateDatabase
- Each TemplateDatabase contains:
  - Resolution metadata
  - List of IconTemplate objects with:
    - Image data (numpy arrays)
    - Item metadata (code, faction, category, mod)
    - Crated variant flag
    - Optimization data (computed features)
```

### Backup Strategy
- Creates `.backup` file before modifying database
- Restores backup automatically on save failure
- Removes backup only after successful save

## Integration

### Workflow Integration
The add-icon command fits into the database management workflow:

```bash
# 1. Build initial database
fs database-builder --catalog catalog.json --templates processed_templates/ --database templates.pkl

# 2. Add custom/new icons as needed
fs add-icon --database templates.pkl --icon new_item.png \
  --code NewItem --faction n --category item --mod vanilla --resolution 1080

# 3. Continue adding more icons
fs add-icon --database templates.pkl --icon another_item.png \
  --code AnotherItem --faction c --category shippable --mod vanilla --resolution 1080

# 4. Use updated database for scanning
fs scanner --database templates.pkl --image screenshot.png
```

### Use Cases

**Adding new game items:**
```bash
# New item added in game update
fs add-icon --database templates.pkl --icon new_weapon.png \
  --code NewWeapon --faction n --category item \
  --mod vanilla --resolution 1080 --resolution 1440 --resolution 2160
```

**Adding mod-specific icons:**
```bash
# Custom mod items
fs add-icon --database templates.pkl --icon mod_tank.png \
  --code CustomTank --faction w --category vehicle \
  --mod awesome_vehicles_mod --resolution 1080
```

**Fixing incorrect icons:**
```bash
# Replace existing icon by adding with same metadata and --replace flag
fs add-icon --database templates.pkl --icon corrected_icon.png \
  --code ExistingItem --faction n --category item \
  --mod vanilla --resolution 1080 --replace
```

**Adding crated variants:**
```bash
# Add crated version of existing item
fs add-icon --database templates.pkl --icon item_crated.png \
  --code ItemName --faction n --category item \
  --crated --mod vanilla --resolution 1080
```

## Troubleshooting

### Common Issues

**Error: "Database file not found"**
- Verify the database path is correct
- Ensure database was created by `fs database-builder`
- Check file permissions

**Error: "Icon file not found"**
- Verify the icon path is correct
- Check file exists and is readable
- Use absolute paths if relative paths fail

**Error: "Resolution X not found in database"**
- Check which resolutions exist in your database
- Use `fs inspect --database templates.pkl` to see available resolutions
- Rebuild database with target resolution if needed

**Error: "Failed to load icon image"**
- Verify image file is not corrupted
- Ensure image is in a supported format (PNG, JPG, etc.)
- Try opening the image in an image viewer first

**Error: "Icon has incorrect dimensions"**
- The icon size must exactly match the required size for the target resolution
- Check the resolution-to-size mapping table in this README
- Resize your icon to the correct dimensions before adding
- Example: For 1080p, icon must be exactly 32x32 pixels

**Error: "Icon already exists"**
- An icon with the same code, faction, category, crated status, and mod already exists
- Use `--replace` flag if you want to replace the existing icon
- Or change the metadata if this is actually a different icon
- Check existing templates with: `fs inspect --database templates.pkl --code ItemName`

**Warning: "Database saved" but no changes visible**
- Verify templates were added with `fs inspect`
- Check the total template count increased

### Debug Tips
- Use `--verbose` to enable debug-level logging
- Enable logging with `--log-file` for detailed processing information
- Check `.backup` file was created (indicates modification started)
- Verify icon file can be opened in an image viewer before adding
- Check icon dimensions match expected size: `identify -format "%wx%h" icon.png`
- Use `fs inspect` to examine database contents before and after

### Performance Tips
- **Batch operations**: Add multiple resolutions in one command instead of separate commands
- **Image preparation**: Pre-resize icons to all target resolutions before running commands
- **SSD storage**: Faster database save/load times compared to HDD

## Dependencies

- **OpenCV (cv2)**: Image loading and resizing
- **NumPy**: Efficient array operations for image data
- **Python 3.12+**: Modern Python features including async/await
- **Pickle**: Database serialization (standard library)

See `pyproject.toml` for exact version requirements.

## Related Tools

- [`fs database-builder`](../database_builder/README.md) - Creates initial template databases
- [`fs scanner`](../stockpile_scanner/README.md) - Uses databases for stockpile recognition
- [`fs inspect`](../candidate_inspector/README.md) - Debugging tool for inspecting databases
- [`fs generate-templates`](../generate_templates/README.md) - Generates templates from extracted assets

## Comparison with Database Builder

### When to use `fs add-icon`:
- Adding individual icons
- Quick fixes to existing database
- Custom mod icons
- New items without full PAK extraction

### When to use `fs database-builder`:
- Initial database creation
- Rebuilding entire database
- Bulk processing of extracted assets
- Major game updates with many new items

## Examples by Use Case

### Game Update Workflow
```bash
# Game added 3 new items, extract their icons manually
# Then add them to existing database
fs add-icon --database templates.pkl --icon new_item1.png \
  --code NewItem1 --faction n --category item \
  --mod vanilla --resolution 1080 --resolution 1440

fs add-icon --database templates.pkl --icon new_item2.png \
  --code NewItem2 --faction c --category vehicle \
  --mod vanilla --resolution 1080 --resolution 1440

fs add-icon --database templates.pkl --icon new_item3.png \
  --code NewItem3 --faction w --category shippable \
  --mod vanilla --resolution 1080 --resolution 1440
```

### Mod Development Workflow
```bash
# Adding custom mod items to database
fs add-icon --database templates.pkl --icon mod_icon1.png \
  --code ModItem1 --faction n --category item \
  --mod my_awesome_mod --resolution 1080

fs add-icon --database templates.pkl --icon mod_icon2.png \
  --code ModItem2 --faction n --category vehicle \
  --crated --mod my_awesome_mod --resolution 1080
```

### Testing Workflow
```bash
# Add test icons with verbose logging for debugging
fs add-icon --database test_db.pkl --icon test_icon.png \
  --code TestItem --faction n --category item \
  --mod test --resolution 1080 --verbose --log-file add_icon.log
```

## Limitations

### Current Limitations
- **No removal**: Cannot remove icons (use database rebuild instead)
- **No bulk operations**: Must add icons one at a time
- **Duplicate prevention**: Icons with identical metadata are rejected unless --replace is used

### Future Enhancements

**Planned Features:**
- **Icon removal**: Remove specific icons by code/metadata
- **Icon replacement**: Replace existing icons in-place
- **Bulk addition**: Add multiple icons from a directory
- **Database merging**: Merge multiple databases
- **Duplicate detection**: Warn or skip duplicate icons
- **Icon listing**: List all icons for a specific item code

For more help:
```bash
fs add-icon --help
fs --help  # See all available commands
```

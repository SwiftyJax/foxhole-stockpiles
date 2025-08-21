# Candidate Inspector Tool

The Candidate Inspector is a debugging and testing tool for Foxhole Stockpiles that helps developers and users analyze template matching behavior, inspect database contents, and test icon recognition capabilities.

## Overview

This tool provides two main functionalities:
1. **Candidate Filtering**: Search and filter templates in the database based on various criteria
2. **Icon Matching**: Test icon recognition against filtered candidates to debug template matching issues

## Installation

The tool is part of the Foxhole Stockpiles package and can be run as a Python module:

```bash
python -m foxhole_stockpiles.commands.candidate_inspector.candidate_inspector
```

## Basic Usage

### Required Arguments

- `--database`: Path to the template database file (`.pkl` format)
- `--resolution`: Target resolution (e.g., '1080', '2160')

### Optional Filtering Arguments

- `--code`: Item code to search for (supports partial matching)
- `--faction`: Faction filter (`c` for Colonial, `w` for Warden)
- `--category`: Item category filter (see available categories below)
- `--crated`: Filter by crated status (`true` for crated only, `false` for normal only)
- `--mod`: Mod filter (specify mod name)

### Icon Matching Arguments

- `--icon`: Path to icon image file for template matching
- `--confidence`: Minimum confidence threshold for matches (default: 0.85, range: 0.0-1.0)

### Output Control Arguments

- `--print`: Show detailed list of matching candidates
- `--verbose`: Enable debug-level logging
- `--log-file`: Path to log file (default: console only)

## Examples

### 1. Basic Candidate Listing

List all templates for a specific resolution:

```bash
python -m foxhole_stockpiles.commands.candidate_inspector.candidate_inspector \
  --database templates.pkl \
  --resolution 1080
```

### 2. Filter by Item Code

Search for items containing "Rifle" in their code:

```bash
python -m foxhole_stockpiles.commands.candidate_inspector.candidate_inspector \
  --database templates.pkl \
  --code Rifle \
  --resolution 1080 \
  --print
```

### 3. Filter by Faction and Category

Find all Colonial items:

```bash
python -m foxhole_stockpiles.commands.candidate_inspector.candidate_inspector \
  --database templates.pkl \
  --faction c \
  --category item \
  --resolution 1080 \
  --print
```

### 4. Filter Crated Items Only

Show only crated items for debugging:

```bash
python -m foxhole_stockpiles.commands.candidate_inspector.candidate_inspector \
  --database templates.pkl \
  --crated true \
  --resolution 1080 \
  --print
```

### 5. Test Icon Matching

Test icon recognition against all candidates:

```bash
python -m foxhole_stockpiles.commands.candidate_inspector.candidate_inspector \
  --database templates.pkl \
  --resolution 1080 \
  --icon screenshot_icon.png \
  --confidence 0.8
```

### 6. Test Icon Matching with Filters

Test icon matching against specific faction and category:

```bash
python -m foxhole_stockpiles.commands.candidate_inspector.candidate_inspector \
  --database templates.pkl \
  --faction c \
  --category item \
  --resolution 1080 \
  --icon unknown_item.png \
  --confidence 0.75 \
  --verbose
```

### 7. Comprehensive Debugging Session

Full debugging with all filters and verbose output:

```bash
python -m foxhole_stockpiles.commands.candidate_inspector.candidate_inspector \
  --database templates.pkl \
  --code "7.92mm" \
  --faction w \
  --crated false \
  --resolution 2160 \
  --icon ammo_icon.png \
  --confidence 0.9 \
  --verbose \
  --log-file debug.log
```

## Available Categories

The tool supports filtering by the following item categories:
- `item` - Regular items (weapons, supplies, ammunition, etc.)
- `vehicle` - All vehicle types
- `shippable` - Items that can be shipped

Use the exact category name as shown above with the `--category` parameter.

## Supported Resolutions

The tool supports the following vertical resolutions:
- `664` - 664px height
- `720` - 720px height (HD)
- `768` - 768px height
- `800` - 800px height
- `864` - 864px height
- `900` - 900px height
- `960` - 960px height
- `992` - 992px height
- `1024` - 1024px height
- `1050` - 1050px height
- `1080` - 1080px height (Full HD)
- `1200` - 1200px height
- `1440` - 1440px height (2K)
- `1536` - 1536px height
- `1600` - 1600px height
- `2160` - 2160px height (4K)

Use the numeric value (e.g., '1080', '2160') with the `--resolution` parameter.

## Output Explanation

### Candidate Listing Mode (without --icon)

When run without the `--icon` parameter, the tool shows:

1. **Summary**: Total number of matching candidates
2. **Detailed List** (with `--print`): Table showing:
   - Item code
   - Faction
   - Category
   - Mod
   - Resolution
   - Crated status (if applicable)
3. **Statistics Breakdown**: Counts by faction, mod, category, and type

Example output:
```
Total: 45 candidates

Filtered candidates:
====================
Code                      | Faction    | Category     | Mod             | Resolution
------------------------------------------------------------------------------------------
BasicMaterials            | Colonial   | item         | base            | 1080px
BasicMaterials            | Colonial   | item         | base            | 1080px (crated)
Rifle                     | Colonial   | item         | base            | 1080px

Statistics breakdown:
=====================
Factions: {'Colonial': 30, 'Warden': 15}
Mods: {'base': 40, 'mod1': 5}
Categories: {'item': 40, 'vehicle': 5}
Types: {'normal': 35, 'crated': 10}
```

### Icon Matching Mode (with --icon)

When an icon file is provided, the tool attempts to match it against filtered candidates and shows:

1. **Match Results**:
   - ✓ Success: Shows matched item details and confidence score
   - ✗ Failure: Shows search statistics
2. **Match Details**: Item code, confidence, faction, category, mod, resolution
3. **Candidate Count**: Number of candidates searched

Example output:
```
Icon matching results:
======================
✓ Match found: Rifle
  Confidence: 0.8523
  Threshold: 0.8
  Faction: Colonial
  Category: item
  Mod: base
  Resolution: 1080px

Found 45 matching candidates
```

## Troubleshooting

### Common Issues

1. **"Database file not found"**
   - Verify the database path exists
   - Ensure you have the correct `.pkl` file

2. **"Invalid resolution"**
   - Check available resolutions in your database
   - Valid values: '664', '720', '768', '800', '864', '900', '960', '992', '1024', '1050', '1080', '1200', '1440', '1536', '1600', '2160'

3. **"Failed to load icon image"**
   - Verify image file exists and is readable
   - Supported formats: PNG, JPG, BMP
   - Ensure image is not corrupted

4. **"No candidates found"**
   - Try removing some filters to broaden search
   - Check filter values are correct (e.g., faction: 'c' or 'w')
   - Verify database contains templates for specified resolution

### Debug Tips

1. **Use `--verbose` flag** for detailed logging
2. **Start with broad filters** then narrow down
3. **Use `--print` flag** to see what candidates are found
4. **Test without `--icon` first** to verify candidate filtering works
5. **Lower `--confidence` threshold** if icon matching fails
6. **Check log files** for detailed error information

## Performance Notes

- Candidate filtering is fast (milliseconds)
- Icon matching can take 1-5 seconds depending on candidate count
- Large databases (>1000 templates) may take longer to load
- Use specific filters to reduce search space for better performance

## Integration with Development Workflow

This tool is particularly useful for:

1. **Template Database Validation**: Verify database contents and structure
2. **Icon Recognition Debugging**: Test why certain icons aren't being recognized
3. **Filter Logic Testing**: Ensure filtering works correctly for different criteria
4. **Performance Analysis**: Measure matching performance with different candidate sets
5. **Database Content Exploration**: Understand what templates are available

## Related Tools

- **Database Builder**: Creates the template databases used by this tool
- **Stockpile Scanner**: Main application that uses these templates for recognition
- **Template Manager**: Core component that handles template matching logic

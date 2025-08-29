# Candidate Inspector Tool

The Candidate Inspector is a debugging and testing tool for Foxhole Stockpiles that helps developers and users analyze template matching behavior, inspect database contents, and test icon recognition capabilities.

## Overview

This tool provides two main functionalities:
1. **Candidate Filtering**: Search and filter templates in the database based on various criteria
2. **Icon Matching**: Test icon recognition against filtered candidates to debug template matching issues

## Usage

### Primary Interface

The inspector is available through the unified Foxhole Stockpiles CLI:

```bash
fs inspect --database templates.pkl --resolution 1080
fs debug --database templates.pkl --resolution 1080    # Short alias
```

### Development Interface

For development and testing, you can also run the inspector module directly:

```bash
python -m foxhole_stockpiles.commands.candidate_inspector.candidate_inspector
```

**Note**: The recommended way to use this tool is through the unified `fs` command.

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
fs inspect --database templates.pkl --resolution 1080
```

### 2. Filter by Item Code

Search for items containing "Rifle" in their code:

```bash
fs inspect --database templates.pkl --code Rifle --resolution 1080 --print
```

### 3. Filter by Faction and Category

Find all Colonial items:

```bash
fs inspect --database templates.pkl --faction c --category item --resolution 1080 --print
```

### 4. Filter Crated Items Only

Show only crated items for debugging:

```bash
fs inspect --database templates.pkl --crated true --resolution 1080 --print
```

### 5. Test Icon Matching

Test icon recognition against all candidates:

```bash
fs inspect --database templates.pkl --resolution 1080 --icon screenshot_icon.png --confidence 0.8
```

### 6. Test Icon Matching with Filters

Test icon matching against specific faction and category:

```bash
fs inspect --database templates.pkl --faction c --category item --resolution 1080 \
  --icon unknown_item.png --confidence 0.75 --verbose
```

### 7. Comprehensive Debugging Session

Full debugging with all filters and verbose output:

```bash
fs inspect --database templates.pkl --code "7.92mm" --faction w --crated false \
  --resolution 2160 --icon ammo_icon.png --confidence 0.9 --verbose --log-file debug.log
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

## Common Debugging Workflows

### Database Validation
```bash
# Check if database loaded correctly
fs inspect --database templates.pkl --resolution 1080

# Verify specific item exists
fs inspect --database templates.pkl --code "BasicMaterials" --resolution 1080 --print

# Check faction distribution
fs inspect --database templates.pkl --faction c --resolution 1080
fs inspect --database templates.pkl --faction w --resolution 1080
```

### Icon Recognition Issues
```bash
# Test problematic icon
fs inspect --database templates.pkl --resolution 1080 --icon failing_icon.png --verbose

# Try with lower confidence
fs inspect --database templates.pkl --resolution 1080 --icon failing_icon.png --confidence 0.6

# Check similar items
fs inspect --database templates.pkl --code "Rifle" --resolution 1080 --print
```

### Template Database Analysis
```bash
# List all crated variants
fs inspect --database templates.pkl --crated true --resolution 1080 --print

# Find items in specific mod
fs inspect --database templates.pkl --mod vanilla --resolution 1080 --print

# Category breakdown
fs inspect --database templates.pkl --category item --resolution 1080
fs inspect --database templates.pkl --category vehicle --resolution 1080
```

## Integration

This command is part of the Foxhole Stockpiles CLI tool suite. It's typically used during database development and troubleshooting:

```bash
# 1. Build database
fs database-builder --catalog catalog.json --templates templates/ --database test.pkl

# 2. Inspect database contents
fs inspect --database test.pkl --resolution 1080 --print

# 3. Test specific icon recognition
fs inspect --database test.pkl --resolution 1080 --icon problem_icon.png --verbose

# 4. Debug faction-specific issues
fs inspect --database test.pkl --faction warden --category vehicle --resolution 1080
```

For more help:
```bash
fs inspect --help
fs --help  # See all available commands
```

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

**Error: "Database not found"**
- Verify the database file path is correct
- Ensure the database was built successfully with `fs database-builder`

**Error: "Invalid resolution"**
- Check that the resolution exists in the database
- Use `fs inspect --database db.pkl --resolution 1080` without other args to list available data

**No candidates found**
- Try broader search criteria
- Check if the item code exists in the catalog
- Verify faction and category filters aren't too restrictive

**Icon matching returns no results**
- Lower the confidence threshold with `--confidence 0.5`
- Enable verbose logging to see matching details
- Verify the icon file format and quality

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

## Related Tools

- [`fs database-builder`](../database_builder/README.md) - Creates the template databases used by this tool
- [`fs scanner`](../stockpile_scanner/README.md) - Uses these databases for stockpile recognition
- [`fs generate-templates`](../generate_templates/README.md) - Generates the templates stored in databases
- [`fs extract-assets`](../uasset_extractor/README.md) - Extracts assets for template generation

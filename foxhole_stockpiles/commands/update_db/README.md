# Update Database

This directory contains the tool for migrating template databases to the latest format version.

## Overview

The `fs update-db` tool automatically migrates your template database to the latest format version, ensuring compatibility with new releases of Foxhole Stockpiles. Migrations are applied sequentially (v1→v2→v3) to bring databases from any older version to the current version.

## Purpose

This tool is designed for **database migration** when upgrading Foxhole Stockpiles:

- Automatically update database files to the latest version
- Preview changes before applying them (dry-run mode)
- Create automatic backups before making changes
- Handle multi-version migration chains (e.g., v1→v2→v3)
- Convert legacy formats to current format

## What It Does

### Database Migration
Migrates template databases through version updates:

- **Automatic detection**: Identifies current database version
- **Sequential migration**: Applies migrations in correct order (v1→v2, v2→v3, etc.)
- **Format conversion**: Converts pickle format to HDF5 format
- **Safe operations**: Creates backup before modifying database
- **Dry-run preview**: See what will happen before applying changes

### Version Management
- **Version detection**: Automatically detects current database version
- **Sequential application**: Applies only necessary migrations
- **Latest version tracking**: Always updates to the most current format

## Usage

### Primary Interface

The update-db tool is available through the unified Foxhole Stockpiles CLI:

```bash
fs update-db [OPTIONS]
fs migrate-db [OPTIONS]    # Alias
```

### Development Interface

For development and testing, you can also run the update-db module directly:

```bash
python -m foxhole_stockpiles.commands.update_db.update_db [OPTIONS]
```

**Note**: The recommended way to use this tool is through the unified `fs` command.

### Command Line Interface

### Optional Arguments

- `--database-path PATH`: Path to database file (default: from config)
- `--output PATH`: Output path for migrated database (default: auto-generated)
- `--dry-run`: Preview migrations without applying them
- `--backup`: Create backup of database before migrating
- `--backup-path PATH`: Custom backup path (default: `<database>.backup`)
- `--verbose`: Enable verbose logging (debug level)
- `--quiet`: Suppress all output except errors and warnings
- `--log-file PATH`: Path to log file for detailed output

### Examples

**Check if migration is needed:**
```bash
fs update-db --dry-run
```

**Apply migration with backup:**
```bash
fs update-db --backup
```

**Specify custom paths:**
```bash
fs update-db --database-path templates.pkl --output templates.h5
```

**With logging:**
```bash
fs update-db --verbose --log-file migration.log
```

## Input Requirements

### Database File
An existing template database file created by `fs database-builder`:

**Supported formats:**
- V1 database (pickle format)
- V2 database (HDF5 format)
- Future versions (will warn if newer than current tool)

**File format:**
- Pickle: `.pkl` files
- HDF5: `.h5` or custom extension files
- Must be readable by the tool

## Output

### Migrated Database
The tool creates a new migrated database file:

- **Backup**: Optional backup of original database
- **New file**: Migrated database written to output path
- **Version metadata**: Database includes version information
- **Format**: HDF5 format for v2 and later

### Console Output

**Already at latest version:**
```
Checking database migrations for: /path/to/templates.h5
Database is already at current version (2)!
No migrations needed.
```

**Successful migration (v1→v2):**
```
Checking database migrations for: /path/to/templates.pkl
Migration needed: Convert pickle database (v1) to HDF5 format (v2)
Output: /path/to/templates.h5

Applying migrations from version 1 to version 2...
Applying migration: v1 → v2
Migrating pickle database to HDF5: templates.pkl -> templates.h5
Converting 3 resolution(s)...

Converted 3 resolution(s):
  - 1080: 234 templates
  - 1440: 234 templates
  - 2160: 234 templates

File size: 328.5 MB -> 164.2 MB (-50.0% size change)

======================================================================
Migration completed successfully!
======================================================================

Next steps:
  1. Update your configuration to use the new HDF5 database:
     scanner.database_path: /path/to/templates.h5
  2. Restart the server to use the new HDF5 format
  3. Verify everything works correctly
  4. (Optional) Remove the old pickle file:
     rm /path/to/templates.pkl
```

**Error cases:**
```
Database file not found: /path/to/templates.pkl

Database file is corrupted or in an unrecognized format

Database version 3 does not match expected version 2.
Please migrate your database using:
  fs update-db --database-path /path/to/templates.h5
```

## Features

### Migration System

**Version Detection:**
- Checks file format (HDF5 vs pickle)
- Reads version metadata from HDF5 files
- Assumes v1 for pickle files (no version metadata)

**Sequential Migration:**
- Applies migrations one at a time in order
- Each migration transforms to next version
- Handles multi-hop migrations automatically (v1→v2→v3)

**Safety Features:**
- Optional backup creation before migration
- Atomic operations with error handling
- Dry-run preview mode
- Clear error messages

## Version History

### Version 2 (Current)
**Format:** HDF5 with resolution-based groups

**Changes from v1:**
- HDF5 format instead of pickle
- Resolution groups (`/1080/`, `/1440/`, `/2160/`)
- Lazy loading (load only needed resolution)
- Compression on image data
- Version metadata in file

**Migration from v1:**
- Reads pickle database
- Converts to HDF5 structure
- Applies compression to images
- Adds version metadata

### Version 1 (Legacy)
**Format:** Pickle format

**Structure:**
- Python pickle file
- Dictionary of resolution → TemplateDatabase
- All resolutions loaded at once
- No version metadata

## Integration

### Workflow Integration
The update-db command fits into the database management workflow:

```bash
# 1. Build initial database (creates v2 HDF5 format)
fs database-builder --catalog catalog.json --templates templates/ --database templates.h5

# 2. If you have old pickle database, migrate it
fs update-db --database-path old_templates.pkl --output new_templates.h5 --backup

# 3. Use the migrated database
fs scanner --database new_templates.h5 --image screenshot.png
```

### Use Cases

**After upgrading Foxhole Stockpiles:**
```bash
# Upgrade the software
pip install --upgrade foxhole-stockpiles

# Check if database needs migration
fs update-db --dry-run

# Migrate if needed
fs update-db --backup
```

**Migrating old databases:**
```bash
# Convert pickle to HDF5
fs update-db --database-path old_db.pkl --output new_db.h5

# Update config to use new database
# Edit ~/.fs_config: scanner.database_path = "new_db.h5"
```

## Troubleshooting

### Common Issues

**Error: "Database file not found"**
- Verify the database path is correct
- Check file exists: `ls -lh /path/to/database`
- Use `--database-path` to specify location

**Error: "Database file is corrupted or in an unrecognized format"**
- File may be corrupted
- File may not be a valid database
- Try using the original database source

**Error: "Database version X does not match expected version Y"**
- Your database is from a newer version of the software
- Upgrade Foxhole Stockpiles: `pip install --upgrade foxhole-stockpiles`
- Or run migration: `fs update-db --database-path database.h5`

**Warning: "Old pickle format (version 1)"**
- This is expected for old databases
- Run migration to convert: `fs update-db --backup`

### Debug Tips
- Use `--dry-run` first to preview changes
- Use `--verbose` for detailed logging
- Use `--log-file` to save logs for debugging
- Check backup file if migration fails
- Verify output file exists after migration

## Technical Details

### Migration Process

**Step-by-step:**
1. Check if database file exists
2. Detect database version (pickle vs HDF5, version number)
3. Compare to current version constant
4. Apply migrations sequentially (v1→v2, v2→v3, etc.)
5. Create backup if requested
6. Write migrated database to output path
7. Report success/failure

### Sequential Migration Chain

Migrations are applied one at a time:

```
v1 database → _migrate_v1_to_v2() → v2 database
v2 database → _migrate_v2_to_v3() → v3 database (future)
v3 database → _migrate_v3_to_v4() → v4 database (future)
```

**Benefits:**
- Only need to implement consecutive migrations
- No combinatorial explosion of migration paths
- Easy to add new versions

### Extensibility

**Adding New Versions:**
1. Increment `DATABASE_VERSION` constant
2. Add `_migrate_vN_to_vN+1()` method to TemplateManager
3. Update `migrate_database()` to call new migration
4. Update this README with version changes

### File Formats

**Pickle Format (v1):**
```python
{
    SupportedResolution.R_1080: TemplateDatabase(...),
    SupportedResolution.R_1440: TemplateDatabase(...),
    SupportedResolution.R_2160: TemplateDatabase(...),
}
```

**HDF5 Format (v2):**
```
/
├── @version: 2
├── @format: "hdf5"
├── @resolutions: ["1080", "1440", "2160"]
├── /1080/
│   ├── @resolution: "1080"
│   ├── @template_count: 234
│   ├── images: (234, 32, 32, 3) uint8 [compressed]
│   ├── codes: (234,) string
│   ├── mods: (234,) string
│   ├── crated: (234,) bool
│   ├── faction: (234,) uint8
│   ├── category: (234,) uint8
│   └── phash: (234,) uint64
├── /1440/
│   └── ...
└── /2160/
    └── ...
```

## Dependencies

- **Python 3.12+**: Modern Python features
- **h5py**: HDF5 file format support
- **NumPy**: Array operations
- **Standard library**: pickle, pathlib, logging, argparse, asyncio

See `pyproject.toml` for exact version requirements.

## Related Documentation

- [Template Manager](../../services/template_manager.py) - Database loading and migration logic
- [Template Database](../../services/template_database.py) - Database format and structure
- [Database Builder Command](../database_builder/README.md) - Creates new databases

## Limitations

### Current Limitations
- **No downgrade**: Cannot downgrade from newer to older versions
- **Sequential only**: Must apply migrations in order
- **Single file**: Processes one database at a time

### Future Enhancements

**Possible Features:**
- Additional HDF5 optimizations (v2→v3)
- Batch migration of multiple databases
- Migration progress reporting for large databases
- Database validation after migration

For more help:
```bash
fs update-db --help
fs --help  # See all available commands
```

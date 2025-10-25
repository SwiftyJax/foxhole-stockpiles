# Update Config

This directory contains the tool for updating `.fs_config` files to the latest configuration format version.

## Overview

The `fs update-config` tool automatically migrates your configuration file to the latest format version, ensuring compatibility with new releases of Foxhole Stockpiles. This tool reads your existing config, applies all necessary migrations, and writes the updated version back to disk.

## Purpose

This tool is designed for **configuration migration** when upgrading Foxhole Stockpiles:

- Automatically update config files to the latest version
- Preview changes before applying them (dry-run mode)
- Preserve all your custom settings during migration
- Create automatic backups before making changes
- Handle multi-version migration chains (e.g., v1→v2→v3)

## What It Does

### Configuration Migration
Updates configuration files through version migrations:

- **Automatic detection**: Identifies current config version
- **Smart migration**: Applies only necessary migrations to reach latest version
- **File-only updates**: Migrates only the config file, not environment variables
- **Safe operations**: Creates backup before modifying config
- **Dry-run preview**: See changes before applying them

### Version Management
- **Version detection**: Automatically detects current config version
- **Sequential migration**: Applies migrations in correct order (v1→v2, v2→v3, etc.)
- **Latest version tracking**: Always updates to the most current format
- **Future compatibility**: Detects and warns about configs from newer versions

## Usage

### Primary Interface

The update-config tool is available through the unified Foxhole Stockpiles CLI:

```bash
fs update-config [OPTIONS]
fs update [OPTIONS]    # Short alias
```

### Development Interface

For development and testing, you can also run the update-config module directly:

```bash
python -m foxhole_stockpiles.commands.update_config.update_config [OPTIONS]
```

**Note**: The recommended way to use this tool is through the unified `fs` command.

### Command Line Interface

### Optional Arguments

- `--config PATH`: Path to config file (default: `~/.fs_config`)
- `--dry-run`: Preview update without making changes
- `--backup-path PATH`: Custom backup path (default: `<config>.backup`)

### Examples

**Update default config to latest version:**
```bash
fs update-config
```

**Preview changes without applying them:**
```bash
fs update-config --dry-run
```

**Update specific config file:**
```bash
fs update-config --config /path/to/custom_config.json
```

**Use custom backup location:**
```bash
fs update-config --backup-path /backup/my_config.backup
```

## Input Requirements

### Configuration File
An existing Foxhole Stockpiles configuration file:

```
~/.fs_config    # Default location
```

**Supported formats:**
- V1 config (flat output_format structure)
- V2 config (nested output structure)
- Future versions (will warn if newer than current tool)

**File format:**
- JSON format with proper structure
- Must be readable by the tool
- Will be validated before migration

## Output

### Updated Configuration
The tool updates the configuration file in place:

- **Backup**: Original config is backed up to `{config}.backup`
- **Atomic**: Backup is restored if save operation fails
- **Verification**: Reports config version after update
- **Preservation**: All custom settings are preserved during migration

### Console Output

**Already at latest version:**
```
Loading config from /home/user/.fs_config...
✅ Config is already at the latest version (2).
No update needed.
```

**Successful update:**
```
Loading config from /home/user/.fs_config...
Current config version: 1
Latest config version: 2
Updating config...
Creating backup at /home/user/.fs_config.backup...
Writing updated config to /home/user/.fs_config...

✅ Update complete!
   - Old config backed up to: /home/user/.fs_config.backup
   - Updated config written to: /home/user/.fs_config
   - Config version: 2

📝 Note: Environment variables will continue to override file settings.
```

**Dry-run preview:**
```
Loading config from /home/user/.fs_config...
Current config version: 1
Latest config version: 2
Updating config...

📋 DRY RUN - Preview of updated config:
============================================================
{
  "output": {
    "format": "json",
    "destination": "webhook",
    "file": {
      "path": "output.json"
    },
    "webhook": {
      "url": "https://example.com/webhook",
      "auth_type": "bearer",
      "token": "secret_token"
    }
  },
  "config_version": 2
}
============================================================

✅ Dry run complete. To apply update, run without --dry-run
```

**Error cases:**
```
❌ No config file found at /home/user/.fs_config
Nothing to update.

❌ Error: Config file is not valid JSON: Expecting value: line 1 column 1 (char 0)

⚠️  Warning: Config version 3 is newer than expected.
This tool supports up to version 2.
Your config may be from a newer version of the software.
```

## Features

### Migration System

**Version Detection:**
- Automatically detects current config version
- Compares against latest known version
- Warns about unknown/future versions

**Sequential Migration:**
- Applies migrations in correct order
- Handles multi-hop migrations (v1→v2→v3)
- Extensible for future versions

**Safety Features:**
- File-only migration (no env var contamination)
- Automatic backup creation
- Rollback on errors
- Dry-run preview mode

### Configuration Preservation

**What Gets Preserved:**
- All custom settings and values
- Logging configuration
- OCR settings
- Scanner settings
- Stockpile type definitions

**What Gets Updated:**
- Configuration structure/format
- Field names (if changed between versions)
- Nested organization
- Version number

### Environment Variable Handling

**Critical Feature**: The tool ONLY migrates the configuration file itself. Environment variables are NOT included in the migration.

**Why This Matters:**
```bash
# Config file has:
"webhook": {"url": "https://file.com"}

# Environment variable:
FS_OUTPUT__WEBHOOK__URL=https://env.com

# After migration:
# - File still has: "https://file.com"
# - Env var still wins: "https://env.com"
```

This preserves the proper separation of concerns where environment variables override file settings.

## Version History

### Version 2 (Current)
**Changes:**
- Nested output configuration structure
- Separate subsections for each output handler
- Simplified field names (removed `webhook_` prefix)
- Pre-configuration of all output destinations

**Migration from v1:**
- `output_format` → `output`
- `output_format.output_format` → `output.format`
- `output_format.output_destination` → `output.destination`
- `output_format.file_path` → `output.file.path`
- `output_format.webhook_url` → `output.webhook.url`
- `output_format.webhook_auth_type` → `output.webhook.auth_type`
- `output_format.webhook_token` → `output.webhook.token`
- `output_format.webhook_client_auth_header` → `output.webhook.client_auth_header`

### Version 1 (Legacy)
**Structure:**
- Flat `output_format` configuration
- All output settings in single section
- Field names prefixed with `webhook_`

## Integration

### Workflow Integration
The update-config command fits into the upgrade workflow:

```bash
# 1. Backup your config (optional, tool does this automatically)
cp ~/.fs_config ~/.fs_config.manual_backup

# 2. Preview what will change
fs update-config --dry-run

# 3. Apply the update
fs update-config

# 4. Verify the update
cat ~/.fs_config | head -20

# 5. Continue using Foxhole Stockpiles normally
fs scanner --database db.pkl --image screenshot.png
```

### Use Cases

**After upgrading Foxhole Stockpiles:**
```bash
# Upgrade the software
pip install --upgrade foxhole-stockpiles

# Update your config to match
fs update-config
```

**Before first use of new version:**
```bash
# Clone new version
git pull origin main

# Update config to new format
fs update-config

# Start using new features
fs scanner --help  # New options may be available
```

**Testing configuration changes:**
```bash
# Preview changes first
fs update-config --dry-run

# Review the output, then apply if satisfied
fs update-config
```

**Multiple configs:**
```bash
# Update development config
fs update-config --config ~/.fs_config.dev

# Update production config
fs update-config --config ~/.fs_config.prod
```

## Troubleshooting

### Common Issues

**Error: "No config file found"**
- Default location is `~/.fs_config`
- Create config manually or use `--config` to specify location
- See [Configuration Documentation](../../docs/configuration.md)

**Error: "Config file is not valid JSON"**
- Verify config file syntax with: `python -m json.tool ~/.fs_config`
- Check for trailing commas, missing quotes, etc.
- Restore from backup if corrupted

**Warning: "Config version X is newer than expected"**
- Your config is from a newer version of the software
- Downgrade Foxhole Stockpiles or keep config as-is
- Tool won't modify configs from future versions

**Error: "Error during migration"**
- Check error message for specific issue
- Ensure config has required fields for migration
- Original config is preserved (check backup)

**Info: "Config is already at the latest version"**
- No update needed, config is current
- This is not an error - tool does nothing when config is up-to-date

### Debug Tips
- Use `--dry-run` first to preview changes
- Check backup file: `cat ~/.fs_config.backup`
- Validate JSON: `python -m json.tool ~/.fs_config`
- Compare before/after: `diff ~/.fs_config.backup ~/.fs_config`
- Test with copy: `cp ~/.fs_config test.json && fs update-config --config test.json`

### Manual Migration

If automatic migration fails, you can manually migrate:

1. Check current structure: `cat ~/.fs_config`
2. Reference new structure: See [Configuration Documentation](../../docs/configuration.md)
3. Edit manually following examples
4. Validate JSON syntax
5. Test with your application

## Technical Details

### Migration Process

**Step-by-step:**
1. Read config file directly (not through Pydantic)
2. Detect current version (`config_version` field or assume v1)
3. Compare to `LATEST_CONFIG_VERSION` constant
4. Apply migrations sequentially through validator chain
5. Create backup of original file
6. Write updated config to original location
7. Report success/failure

### File Handling

**Read Strategy:**
- Direct JSON parsing (not through settings loader)
- Avoids merging with environment variables
- Preserves only file-based configuration

**Write Strategy:**
- Atomic write operation
- Backup created before modification
- Rollback on write failure

### Migration Chain

Future versions will chain migrations:
```
v1 config → _migrate_v1_to_v2() → v2 config
v2 config → _migrate_v2_to_v3() → v3 config
v3 config → _migrate_v3_to_v4() → v4 config
...
```

The `migrate_config` validator automatically applies all necessary migrations.

### Extensibility

**Adding New Versions:**
1. Increment `LATEST_CONFIG_VERSION` constant
2. Add `_migrate_vN_to_vN+1()` static method to `AppSettings`
3. Update `migrate_config()` validator to call new migration
4. Update this README with version changes

## Performance

### Operation Speed
- **Config read**: < 10ms for typical config files
- **Migration**: < 50ms for simple migrations
- **Backup creation**: < 10ms (file copy)
- **Config write**: < 20ms
- **Total**: < 100ms for complete update

### File Sizes
- **Typical config**: 1-5 KB
- **Large config**: < 50 KB
- **Backup overhead**: Identical to config size

## Dependencies

- **Python 3.12+**: Modern Python features including async/await
- **Standard library only**: json, shutil, pathlib, argparse, asyncio
- **Pydantic**: For migration logic (from main application)

See `pyproject.toml` for exact version requirements.

## Related Documentation

- [Configuration Guide](../../docs/configuration.md) - Complete configuration reference
- [Settings Module](../../core/settings.py) - Configuration data models
- [Migration Tests](../../tests/core/test_settings.py) - Migration test suite

## Examples by Use Case

### First-Time Update
```bash
# You've just upgraded Foxhole Stockpiles
# Check what will change
fs update-config --dry-run

# Apply the update
fs update-config

# Output:
# ✅ Update complete!
#    - Old config backed up to: /home/user/.fs_config.backup
#    - Updated config written to: /home/user/.fs_config
#    - Config version: 2
```

### CI/CD Pipeline
```bash
# Update config as part of deployment
#!/bin/bash
set -e

# Backup original
cp ~/.fs_config ~/.fs_config.pre_deploy

# Update to latest version
fs update-config

# Verify update succeeded
if ! grep -q '"config_version": 2' ~/.fs_config; then
    echo "Config update failed"
    cp ~/.fs_config.pre_deploy ~/.fs_config
    exit 1
fi

echo "Config updated successfully"
```

### Development Testing
```bash
# Test migration on a copy
cp ~/.fs_config test_config.json

# Modify to older version for testing
# (manually edit test_config.json to have "config_version": 1)

# Test migration
fs update-config --config test_config.json

# Verify results
diff ~/.fs_config test_config.json
```

## Limitations

### Current Limitations
- **No downgrade**: Cannot downgrade from newer to older versions
- **JSON only**: Requires JSON format (no YAML, TOML, etc.)
- **Single file**: Updates one config file at a time
- **No auto-update**: Manual command execution required

### Future Enhancements

**Planned Features:**
- **Automatic update prompts**: Warn when config is outdated
- **Batch updates**: Update multiple config files at once
- **Format conversion**: Support YAML/TOML input formats
- **Validation**: Verify config works after migration
- **Migration reports**: Detailed change log

## Safety Guarantees

### What This Tool Guarantees

✅ **No data loss**: Original config backed up before changes
✅ **Atomic operations**: All-or-nothing updates (rollback on failure)
✅ **Environment preservation**: Env vars unaffected by migration
✅ **Custom settings preserved**: Your values maintained through migration
✅ **Idempotent**: Running multiple times is safe (no-op if current)

### What This Tool Does NOT Do

❌ **No automatic updates**: Won't run automatically on app start
❌ **No validation**: Doesn't verify config works with application
❌ **No optimization**: Doesn't reorganize or clean up config
❌ **No merging**: Doesn't merge configs from multiple sources

For more help:
```bash
fs update-config --help
fs --help  # See all available commands
```

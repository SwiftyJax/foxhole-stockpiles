# Foxhole Stockpiles Commands

This directory contains command-line tools for building and maintaining the Foxhole Stockpiles recognition system. These tools handle everything from extracting game assets to building template databases used by the main recognition API.

## Overview

The Foxhole Stockpiles toolset follows a sequential workflow to build template databases from game assets. Each command has a specific role in the pipeline and must be executed in the correct order for optimal results.

## Available Commands

### 1. `fs-uasset-extractor` - Asset Extraction
**Purpose**: Extract icon assets from Foxhole PAK files and convert them to PNG format.

**Usage**:
```bash
# As console script
fs-uasset-extractor --catalog catalog.json --pak "path/to/War-WindowsNoEditor.pak" --output raw_assets/

# As module
python -m foxhole_stockpiles.commands.uasset_extractor
```

**Input**: PAK files from Foxhole game directory, catalog.json
**Output**: Raw PNG icon files organized by mod

[📖 Detailed Documentation](uasset_extractor/README.md)

---

### 2. `fs-generate-templates` - Template Generation
**Purpose**: Generate resolution-specific template variants from extracted assets with proper scaling and crate overlays.

**Usage**:
```bash
# As console script
fs-generate-templates --catalog catalog.json --assets raw_assets/ --templates processed_templates/

# As module
python -m foxhole_stockpiles.commands.generate_templates
```

**Input**: Raw PNG assets from uasset-extractor, catalog.json
**Output**: Resolution-specific templates (664px to 2160px) with normal and crated variants

[📖 Detailed Documentation](generate_templates/README.md)

---

### 3. `fs-database-builder` - Database Compilation
**Purpose**: Compile processed templates into optimized binary databases for fast runtime loading.

**Usage**:
```bash
# As console script
fs-database-builder --catalog catalog.json --templates processed_templates/ --database foxhole_templates.pkl

# As module
python -m foxhole_stockpiles.commands.database_builder
```

**Input**: Processed templates from generate-templates, catalog.json
**Output**: Binary database file (.pkl) containing all templates and metadata

[📖 Detailed Documentation](database_builder/README.md)

---

### 4. `fs-candidate-inspector` - Debugging & Testing
**Purpose**: Debug template matching, inspect database contents, and test icon recognition.

**Usage**:
```bash
# As console script
fs-candidate-inspector --database foxhole_templates.pkl --resolution 1080 --print

# As module
python -m foxhole_stockpiles.commands.candidate_inspector
```

**Input**: Built database from database-builder, optional test images
**Output**: Candidate listings, matching results, and debugging information

[📖 Detailed Documentation](candidate_inspector/README.md)

## Recommended Workflow

### Complete Pipeline (Production)

Execute commands in this exact order for building a complete database:

```bash
# Step 1: Extract assets from game PAK files
fs-uasset-extractor \
  --catalog catalog.json \
  --pak "C:/Program Files (x86)/Steam/steamapps/common/Foxhole/War/Content/Paks/War-WindowsNoEditor.pak" \
  --output raw_assets/

# Step 2: Generate resolution-specific templates
fs-generate-templates \
  --catalog catalog.json \
  --assets raw_assets/ \
  --templates processed_templates/

# Step 3: Build optimized binary database
fs-database-builder \
  --catalog catalog.json \
  --templates processed_templates/ \
  --database foxhole_templates.pkl \
  --validate

# Step 4: Test and validate the database
fs-candidate-inspector \
  --database foxhole_templates.pkl \
  --resolution 1080 \
  --print
```

### Development Workflow (Iterative)

For development and testing, you can work with subsets:

```bash
# Generate templates for specific items only
fs-generate-templates \
  --catalog catalog.json \
  --assets raw_assets/ \
  --templates test_templates/ \
  --filter Rifle

# Build database for specific resolutions
fs-database-builder \
  --catalog catalog.json \
  --templates test_templates/ \
  --database test_db.pkl \
  --resolution 1080 \
  --resolution 2160

# Test specific scenarios
fs-candidate-inspector \
  --database test_db.pkl \
  --resolution 1080 \
  --faction c \
  --category item \
  --icon test_icon.png
```

## Installation & Setup

### Prerequisites

1. **External Tools** (for uasset-extractor):
   - `repak.exe` - For PAK file extraction
   - `umodel.exe` - For asset conversion
   - Foxhole game files and `catalog.json`

2. **Python Package** (editable install for development):
   ```bash
   pip install -e .
   ```

### Making Commands Available

After installation, commands are available in two ways:

**Console Scripts** (recommended):
```bash
fs-uasset-extractor --help
fs-generate-templates --help
fs-database-builder --help
fs-candidate-inspector --help
```

**Python Modules** (alternative):
```bash
python -m foxhole_stockpiles.commands.uasset_extractor --help
python -m foxhole_stockpiles.commands.generate_templates --help
python -m foxhole_stockpiles.commands.database_builder --help
python -m foxhole_stockpiles.commands.candidate_inspector --help
```

## Key Dependencies

- **Image Processing**: OpenCV (cv2), NumPy, Pillow
- **Data Handling**: Pydantic v2 for validation, Pickle for serialization
- **External Tools**: repak.exe, umodel.exe (Windows-specific)
- **Concurrency**: ThreadPoolExecutor for parallel processing

## Output Files

The complete pipeline produces these important files:

- **`raw_assets/`** - Extracted PNG files organized by mod
- **`processed_templates/`** - Resolution-specific templates with variants
- **`foxhole_templates.pkl`** - Final binary database (30-100MB)
- **Log files** - Detailed processing logs for debugging

## Performance Notes

- **Asset Extraction**: 5-15 minutes (depends on PAK file size)
- **Template Generation**: 2-5 minutes (depends on item count)
- **Database Building**: 30 seconds - 2 minutes (depends on template count)
- **Memory Usage**: Peak ~2-4GB during database building

## Troubleshooting

### Common Issues

1. **Missing External Tools**
   - Ensure `repak.exe` and `umodel.exe` are installed and accessible
   - Check tool paths in command arguments

2. **PAK File Access**
   - Verify Foxhole installation path
   - Ensure PAK files are not in use by the game

3. **Permission Issues**
   - Run command prompt as administrator if needed
   - Check write permissions for output directories

4. **Memory Issues**
   - Reduce concurrent workers with `--workers` parameter
   - Process fewer resolutions at once

### Debug Tips

1. **Use `--verbose` flags** for detailed logging
2. **Check log files** for specific error messages
3. **Use filters** to process subsets during development
4. **Validate databases** with `fs-candidate-inspector`
5. **Start with small datasets** before full pipeline runs

## Integration with Main Application

The binary database produced by this pipeline is used by:

- **FastAPI Recognition Service** - Loads database for real-time stockpile scanning
- **Template Manager** - Handles template matching and candidate filtering
- **Icon Recognition Engine** - Performs template matching against screenshots

The database contains all necessary data for production recognition without requiring any of these command-line tools at runtime.

## Related Documentation

- [Main Project README](../../README.md) - Overall project documentation
- [API Documentation](../../docs/) - REST API usage and endpoints
- [Development Guide](../../docs/development.md) - Contributing and development setup

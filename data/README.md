# Data Files

This directory contains the item catalog file used by Foxhole Stockpiles.

## catalog.json

**Source:** This file is directly copied from the [FIR (Foxhole Item Recognition)](https://github.com/GICodeWarrior/fir) project.

The catalog maps Foxhole item codes to their icon paths within the game's asset files. It is essential for:
- Extracting icons from PAK files
- Generating templates for the scanner
- Identifying items in stockpile screenshots

### Credits

All credit for the catalog.json file goes to the FIR project maintainers:
- **Project:** [FIR (Foxhole Item Recognition)](https://github.com/GICodeWarrior/fir)
- **Maintainer:** GICodeWarrior and contributors

### Future Plans

This project is developing its own catalog builder tool. Once complete, this catalog may be replaced with an independently maintained version. For now, we use the FIR catalog with full attribution to the original authors.

### Usage

The catalog is used by several Foxhole Stockpiles commands:
```bash
# Extract assets from PAK files
fs extract-assets --catalog data/catalog.json --pak game.pak --output assets/

# Generate templates
fs generate-templates --catalog data/catalog.json --assets assets/ --templates templates/

# Build database
fs database-builder --catalog data/catalog.json --templates templates/ --database database.h5
```

### License

The catalog.json file is derived from the FIR project. Please refer to the [FIR repository](https://github.com/GICodeWarrior/fir) for licensing information.

Game data is property of [Siege Camp](https://www.siegecamp.com/). Use of game assets is subject to their terms of service.

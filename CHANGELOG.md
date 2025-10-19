# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2025-10-19

### Added
- **New Command**: `fs add-icon` command for manual icon database management
- Added `extract_icons` option in scanner settings to save extracted icons from screenshots for debugging
- Added `--top` option to inspector command to show confidence of top N items in database (default: 5)
- Added average confidence to scan summary log messages
- Added low-confidence match reporting to error messages
- Added adaptive grey threshold detection based on darkest quantity box grey values
- Added option to save screenshots to a folder before processing (`screenshots_folder` setting)
- Added `exclude_codes` parameter to `get_candidates` method for better icon redetection
- Improved test coverage significantly across multiple modules

### Changed
- Replaced OpenCV with PIL for image loading and resizing in template generation
- Scanner now redetects icons when there is a conflict to improve accuracy
- Corrected image format handling to consistently use BGR format
- Made name detection coordinates larger to avoid cutting names in edge cases
- Adjusted name box detection coordinates to reduce empty gap to left of name
- Moved webhook response logging to debug level
- Reduced scanner verbosity - most logs moved to debug, leaving scan summary at info level
- Item confidence now displays with 3 decimal places for better precision

### Fixed
- Fixed stockpile type and name location detection with empty stockpiles
- Fixed subprocess handling in uasset_extractor to prevent resource leaks
- Fixed individual logger level configuration from settings not being applied
- Removed default value for early exit parameter in CLI to prevent overwriting configured value in `~/.fs_config`
- Fixed uasset tests after template refactoring
- Fixed test image handling by adding via Git LFS for complete CI test coverage
- Standardized CI to Python 3.12 for consistent coverage reporting
- Used `Resampling.LANCZOS` instead of deprecated `Image.LANCZOS` to fix mypy warnings

### Development
- Updated dependencies to latest versions
- Upgraded development tools from PyQt5 to PyQt6
- Added crate overlay calibrator tool for visualizing crate icon positioning
- Updated Codevoc configuration and improved test reporting
- Updated CLI documentation to match current usage

## [0.1.1] - 2025-10-05

### Fixed
- **Critical**: Fixed contour sorting and column tracking for accurate quantity detection in stockpile screenshots
- **Critical**: Fixed UTF-8 encoding when reading JSON config files on Windows (supports Russian/Chinese characters)
- Fixed webhook authentication header forwarding (requires `"webhook_auth_type": "forward"`)
- Fixed reading settings from `.fs_config` file
- Fixed test suite after authentication changes

### Changed
- Changed OCR to use per-call `--tessdata-dir` parameter instead of global `TESSDATA_PREFIX` environment variable
- Renamed custom OCR model from "custom" to "renner_numbers" for clarity
- Custom model now used only for quantity detection; standard Tesseract models used for text

### Added
- Added fuzzy matching for common OCR errors in stockpile type detection ("Seapon" → "Seaport")
- Added case-insensitive matching for stockpile type classification

### Documentation
- Updated configuration documentation with all available options
- Clarified that `renner_numbers` model is bundled and required for quantity detection
- Added platform-specific instructions for installing optional language packs (Russian, Chinese, Portuguese, French, German)
- Documented multilingual OCR support

## [0.1.0] - 2025-10-03

Initial beta release.

### Features
- **Asset Extraction**: Extract icon assets from Foxhole PAK files
- **Template Generation**: Create resolution-specific templates with crate overlays
- **Database Building**: Compile optimized binary template databases
- **Stockpile Scanner**: Analyze screenshots to detect items and quantities
- **API Server**: FastAPI-based HTTP API for screenshot processing
- **Docker Support**: Production-ready containerization
- **OCR Integration**: Custom-trained Tesseract model for quantity detection
- **Authentication**: Bearer token authentication for API endpoints
- **Webhooks**: Push results to external services
- **CLI Tools**: Comprehensive command-line interface

### Documentation
- User guides for all CLI tools
- API usage documentation
- Docker deployment guide
- Architecture documentation
- Configuration guide
- Troubleshooting guide
- Webhook integration guide

### Testing
- Unit tests for core services
- Integration tests for API endpoints
- Test coverage >80%
- CI/CD with GitHub Actions

[Unreleased]: https://github.com/xurxogr/foxhole-stockpiles/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/xurxogr/foxhole-stockpiles/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/xurxogr/foxhole-stockpiles/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/xurxogr/foxhole-stockpiles/releases/tag/v0.1.0

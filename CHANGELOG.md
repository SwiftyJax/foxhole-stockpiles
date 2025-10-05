# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/xurxogr/foxhole-stockpiles/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/xurxogr/foxhole-stockpiles/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/xurxogr/foxhole-stockpiles/releases/tag/v0.1.0

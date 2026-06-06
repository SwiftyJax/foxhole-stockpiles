<!-- Generated: 2026-06-06 | Branch: refactor/01-pyside6 | Source files: ~253 (.py) | Token estimate: ~900 -->

# Foxhole Stockpiles — Codemap Index

**Last Updated:** 2026-06-06
**Version:** 0.4.0 | **Config schema:** v8 | **Python:** 3.12+

## What it is

Computer-vision + OCR system that extracts structured item data from Foxhole
screenshots, and (new) parses Foxhole `.sav` world files. Screenshot pipeline:
detect stockpile UI → match icons (OpenCV template matching) → read quantities
(Tesseract) → format output (JSON/CSV/TSV) → route to sinks.

## Three packages, three apps

```
┌──────────────────────┬───────────────────────┬──────────────────────┐
│ foxhole_stockpiles   │ fs_ocr                │ fs_tools             │
│ (runtime app)        │ (OCR engine pkg)      │ (asset/db tooling)   │
├──────────────────────┼───────────────────────┼──────────────────────┤
│ CLI `fs`, API server │ OCRScanner public API │ CLI `fs-tools`,      │
│ web UI, PySide6 GUI, │ + _impl/ pipeline     │ tools GUI, catalog/  │
│ SAV processing,      │ (detector, matcher,   │ db/template builders,│
│ output routing       │ extractor, classifier)│ uasset extraction    │
│ ~131 .py             │ ~22 .py               │ ~100 .py             │
└──────────────────────┴───────────────────────┴──────────────────────┘
```

`fs_ocr` is being aligned to a Rust replacement (`../fs-ocr`); the public
`OCRScanner` surface (`ScannerInfo.implementation: "python" | "rust"`) is the
stable seam. `_impl/` is the current pure-Python implementation.

## Entry points (`pyproject.toml [project.scripts]`)

| Command | Target | Purpose |
|---|---|---|
| `fs` | `foxhole_stockpiles.cli.app:main` | Typer CLI — `scan`, `serve`, `gui`, `sav` |
| `fs-ocr` | `fs_ocr.cli:main` | Direct OCR engine CLI |
| `fs-tools` | `fs_tools.cli:main` | Asset/database tooling CLI |
| `fs-gui` | `foxhole_stockpiles.gui.app:launch_gui` | PySide6 desktop app |
| `fs-tools-gui` | `fs_tools.gui:run_gui` | PySide6 tooling app |

## foxhole_stockpiles modules

- **cli/** — Typer app (`app.py`); commands `scan`, `serve`, `gui`, `sav`; `_settings.py` loads `AppSettings`, `_console.py` Rich output.
- **api/** — FastAPI `server.py`, `auth.py` (None/Bearer/API-Key), `scan_limiter.py` (slowapi), `memory_middleware.py`, `web/` (Jinja HTML upload UI).
- **services/** — `output_coordinator.py` (sink routing), `catalog_service.py`, `notification_service.py`, `memory_monitor.py`, `sav_parser.py`, `savefile_processor.py`. (OCR services now live in `fs_ocr/_impl/`.)
- **core/** — `settings/` (Pydantic `AppSettings` v8 + `config_migrator.py` + nested `sections/`), `events/bus.py` (EventBus), `logging.py`, `utils.py`, `version.py`.
- **models/** — Pydantic v2: `stockpile.py`, `stockpile_item.py`, `catalog_item.py`, `match_result.py`, `scan_result.py`, SAV/mod-import models, memory-stat models.
- **handlers/** — output sinks: `console.py`, `file.py`, `webhook.py`, `response.py` (`base_handler.py` interface).
- **notifiers/** — `discord.py` (+ `base.py`).
- **enums/** — StrEnums: stockpile_type, item_faction, item_category, supported_language, supported_resolution, output_format/destination/handler_type, auth_type, event_type, config_level, notifier_type.
- **gui/** — PySide6 desktop app (widgets, config tabs).
- **connectors/**, **constants/**, **i18n/** — tool interaction, stockpile-text tables, translations.

## See also

- `architecture.md` — package boundaries, scan & SAV data flow, patterns
- `backend.md` — API routes, middleware, CLI command flow
- `data.md` — config schema (v8), Pydantic models, HDF5 template DB
- `dependencies.md` — libraries, external tools, Rust sibling packages

## Five files to read first

1. `fs_ocr/api.py` — `OCRScanner` / `ScannerConfig` public surface
2. `fs_ocr/_impl/coordinator.py` — OCR pipeline orchestrator
3. `foxhole_stockpiles/cli/commands/scan.py` — wires scanner → output
4. `foxhole_stockpiles/api/server.py` — REST entry point
5. `foxhole_stockpiles/core/settings/app_settings.py` — configuration root

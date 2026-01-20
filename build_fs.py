"""Build script for creating fs executable (unified CLI and GUI)."""

import subprocess
import sys
from pathlib import Path


def get_hidden_imports() -> list[str]:
    """Get all hidden imports for the unified build."""
    return [
        # Core dependencies
        "cv2",
        "numpy",
        "numpy.core._methods",
        "numpy.lib.format",
        "pydantic",
        "pydantic.json_schema",
        "pydantic_settings",
        "pytesseract",
        # Core package modules
        "foxhole_stockpiles",
        "foxhole_stockpiles.core",
        "foxhole_stockpiles.core.logging",
        "foxhole_stockpiles.core.utils",
        "foxhole_stockpiles.enums",
        "foxhole_stockpiles.enums.item_faction",
        "foxhole_stockpiles.enums.item_category",
        "foxhole_stockpiles.enums.supported_resolution",
        "foxhole_stockpiles.models",
        "foxhole_stockpiles.services",
        # API Server dependencies
        "fastapi",
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "starlette",
        "starlette.routing",
        "starlette.middleware",
        "multipart",
        # API modules
        "foxhole_stockpiles.api",
        "foxhole_stockpiles.api.server",
        "foxhole_stockpiles.api.auth",
        # All command modules
        "foxhole_stockpiles.commands.stockpile_scanner.stockpile_scanner",
        "foxhole_stockpiles.commands.database_builder.database_builder",
        "foxhole_stockpiles.commands.generate_templates.generate_templates",
        "foxhole_stockpiles.commands.uasset_extractor.uasset_extractor",
        "foxhole_stockpiles.commands.candidate_inspector.candidate_inspector",
        "foxhole_stockpiles.commands.api_server.api_server",
        "foxhole_stockpiles.commands.gui.gui",
        "foxhole_stockpiles.commands.add_icon.add_icon",
        "foxhole_stockpiles.commands.add_mod.add_mod",
        "foxhole_stockpiles.commands.update_db.update_db",
        "foxhole_stockpiles.commands.update_config.update_config",
        # PyQt6 dependencies (for GUI)
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.sip",
        # GUI modules
        "foxhole_stockpiles.gui",
        "foxhole_stockpiles.gui.app",
        "foxhole_stockpiles.gui.windows",
        "foxhole_stockpiles.gui.windows.main_window",
        "foxhole_stockpiles.gui.windows.config_window",
        "foxhole_stockpiles.gui.windows.icon_import_window",
        "foxhole_stockpiles.gui.windows.database_info_window",
        "foxhole_stockpiles.gui.windows.database_builder_settings_dialog",
        "foxhole_stockpiles.gui.widgets",
        "foxhole_stockpiles.gui.widgets.server_control_panel",
        "foxhole_stockpiles.gui.widgets.config_tabs",
        "foxhole_stockpiles.gui.widgets.config_tabs.basic_config_tab",
        "foxhole_stockpiles.gui.widgets.config_tabs.scanner_tab",
        "foxhole_stockpiles.gui.widgets.config_tabs.output_tab",
        "foxhole_stockpiles.gui.widgets.config_tabs.template_tab",
        "foxhole_stockpiles.gui.widgets.config_tabs.ocr_tab",
        "foxhole_stockpiles.gui.widgets.config_tabs.api_auth_tab",
        "foxhole_stockpiles.gui.widgets.config_tabs.api_server_tab",
        "foxhole_stockpiles.gui.widgets.config_tabs.database_builder_tab",
        "foxhole_stockpiles.gui.widgets.config_tabs.logging_tab",
        "foxhole_stockpiles.gui.utils",
        "foxhole_stockpiles.gui.utils.qt_log_handler",
        "foxhole_stockpiles.gui.utils.config_manager",
        "foxhole_stockpiles.gui.utils.scan_worker",
        "foxhole_stockpiles.gui.utils.scanner_client",
        "foxhole_stockpiles.gui.utils.server_thread",
        "foxhole_stockpiles.gui.utils.icon_import_worker",
        "foxhole_stockpiles.gui.utils.pak_validation_worker",
        "foxhole_stockpiles.gui.utils.advanced_setting_widget",
    ]


def build_executable(project_root: Path) -> bool:
    """Build the unified executable (fs.exe).

    Args:
        project_root: Path to project root directory

    Returns:
        True if build successful, False otherwise
    """
    print("=" * 50)
    print("Building Unified Executable (fs.exe)")
    print("=" * 50)
    print()
    print("This executable provides:")
    print("  - GUI mode: Run 'fs' with no arguments")
    print("  - CLI mode: Run 'fs <command>' for CLI commands")
    print()

    hidden_imports = get_hidden_imports()

    # Build PyInstaller command
    # Use --windowed so no console appears on double-click
    # CLI commands attach to parent console or allocate one when needed
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name",
        "fs",
        "--windowed",
    ]

    # Add all hidden imports
    for import_name in hidden_imports:
        cmd.extend(["--hidden-import", import_name])

    # Exclude development dependencies
    exclude_modules = ["pytest", "mypy", "ruff", "pre_commit"]
    for module in exclude_modules:
        cmd.extend(["--exclude-module", module])

    # Add the main script
    cmd.append("foxhole_stockpiles/commands/fs/fs.py")

    print(f"Building with {len(hidden_imports)} hidden imports...")

    try:
        subprocess.run(cmd, cwd=project_root, check=True)

        # Check result
        exe_path = project_root / "dist" / "fs.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n[OK] Build successful!")
            print(f"  Executable: {exe_path}")
            print(f"  Size: {size_mb:.1f} MB")

            # Test the executable
            print("\n  Testing executable...")

            # Test help
            result = subprocess.run([str(exe_path), "--help"], capture_output=True, text=True)
            if result.returncode == 0:
                print("  [OK] Help command works")
            else:
                print("  [FAIL] Help command failed")
                return False

            # Test subcommand help
            result = subprocess.run(
                [str(exe_path), "scanner", "--help"], capture_output=True, text=True
            )
            if result.returncode == 0:
                print("  [OK] Scanner subcommand works")
            else:
                print("  [FAIL] Scanner subcommand failed")
                return False

            print("\n  Usage:")
            print("    fs          - Launch GUI (console window hidden)")
            print("    fs gui      - Launch GUI explicitly")
            print("    fs <cmd>    - Run CLI command")
            return True

        else:
            print("[FAIL] Executable not found after build")
            return False

    except subprocess.CalledProcessError as e:
        print(f"[FAIL] Build failed: {e}")
        return False


def main() -> None:
    """Build the unified executable."""
    project_root = Path(__file__).parent

    print("Building Foxhole Stockpiles Executable")
    print("=" * 50)
    print()

    try:
        success = build_executable(project_root)

        print("\n" + "=" * 50)
        print("Build Summary")
        print("=" * 50)
        print(f"fs.exe: {'[OK] Success' if success else '[FAIL] Failed'}")

        if success:
            print("\nBuild completed successfully!")
            print("\nExecutable in dist/:")
            print("  - fs.exe: Unified CLI/GUI tool")
            print("            Run without args for GUI, with command for CLI")
        else:
            print("\nBuild failed. Check output above for details.")
            sys.exit(1)

    except FileNotFoundError:
        print("[FAIL] PyInstaller not found. Install with: pip install pyinstaller")
        sys.exit(1)


if __name__ == "__main__":
    main()

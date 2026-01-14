"""Build script for creating fs executables (CLI and GUI)."""

import subprocess
import sys
from pathlib import Path


def get_common_hidden_imports() -> list[str]:
    """Get hidden imports common to both CLI and GUI builds."""
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
    ]


def build_cli_executable(project_root: Path) -> bool:
    """Build the CLI executable (fs.exe).

    Args:
        project_root: Path to project root directory

    Returns:
        True if build successful, False otherwise
    """
    print("\n" + "=" * 50)
    print("Building CLI Executable (fs.exe)")
    print("=" * 50)

    hidden_imports = get_common_hidden_imports() + [
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
    ]

    # Build PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name",
        "fs",
        "--console",
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
            print("\n[OK] CLI Build successful!")
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

            print("\n  fs.exe ready! Use: fs <command> [options]")
            return True

        else:
            print("[FAIL] Executable not found after build")
            return False

    except subprocess.CalledProcessError as e:
        print(f"[FAIL] Build failed: {e}")
        return False


def build_gui_executable(project_root: Path) -> bool:
    """Build the GUI executable (fs-gui.exe).

    Args:
        project_root: Path to project root directory

    Returns:
        True if build successful, False otherwise
    """
    print("\n" + "=" * 50)
    print("Building GUI Executable (fs-gui.exe)")
    print("=" * 50)

    hidden_imports = get_common_hidden_imports() + [
        # PyQt6 dependencies
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
        "foxhole_stockpiles.gui.windows.about_window",
        "foxhole_stockpiles.gui.windows.import_icons_window",
        "foxhole_stockpiles.gui.widgets",
        "foxhole_stockpiles.gui.widgets.log_widget",
        "foxhole_stockpiles.gui.handlers",
        "foxhole_stockpiles.gui.handlers.qt_log_handler",
        # API Server (needed for server control in GUI)
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
        "foxhole_stockpiles.api",
        "foxhole_stockpiles.api.server",
        "foxhole_stockpiles.api.auth",
    ]

    # Build PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name",
        "fs-gui",
        "--windowed",  # No console for GUI
    ]

    # Add all hidden imports
    for import_name in hidden_imports:
        cmd.extend(["--hidden-import", import_name])

    # Exclude development dependencies
    exclude_modules = ["pytest", "mypy", "ruff", "pre_commit"]
    for module in exclude_modules:
        cmd.extend(["--exclude-module", module])

    # Add the main script
    cmd.append("foxhole_stockpiles/gui/app.py")

    print(f"Building with {len(hidden_imports)} hidden imports...")

    try:
        subprocess.run(cmd, cwd=project_root, check=True)

        # Check result
        exe_path = project_root / "dist" / "fs-gui.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n[OK] GUI Build successful!")
            print(f"  Executable: {exe_path}")
            print(f"  Size: {size_mb:.1f} MB")
            print("\n  fs-gui.exe ready! Double-click to launch GUI (no console)")
            return True

        else:
            print("[FAIL] Executable not found after build")
            return False

    except subprocess.CalledProcessError as e:
        print(f"[FAIL] Build failed: {e}")
        return False


def main() -> None:
    """Build both CLI and GUI executables."""
    project_root = Path(__file__).parent

    print("Building Foxhole Stockpiles Executables")
    print("=" * 50)
    print("This will create:")
    print("  1. fs.exe - CLI tool (with console)")
    print("  2. fs-gui.exe - GUI tool (no console)")
    print()

    try:
        # Build CLI executable
        cli_success = build_cli_executable(project_root)

        # Build GUI executable
        gui_success = build_gui_executable(project_root)

        # Summary
        print("\n" + "=" * 50)
        print("Build Summary")
        print("=" * 50)
        print(f"CLI (fs.exe):      {'[OK] Success' if cli_success else '[FAIL] Failed'}")
        print(f"GUI (fs-gui.exe):  {'[OK] Success' if gui_success else '[FAIL] Failed'}")

        if cli_success and gui_success:
            print("\nAll builds completed successfully!")
            print("\nExecutables in dist/:")
            print("  - fs.exe: CLI tool with all commands")
            print("  - fs-gui.exe: GUI application (no console)")
        else:
            print("\nSome builds failed. Check output above for details.")
            sys.exit(1)

    except FileNotFoundError:
        print("[FAIL] PyInstaller not found. Install with: pip install pyinstaller")
        sys.exit(1)


if __name__ == "__main__":
    main()

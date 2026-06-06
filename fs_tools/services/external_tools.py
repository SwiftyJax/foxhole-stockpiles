"""Centralized invocation of external tools (repak, umodel, uassetgui).

Every place that shells out to an external tool needs the same cross-cutting
concerns handled consistently:

- detecting whether a tool is a Windows executable (so paths must be converted
  when running under WSL),
- converting WSL paths to Windows paths for those executables,
- locating a Windows-accessible temp directory when Windows tools run in WSL,
- launching the process with the correct subprocess options
  (``get_subprocess_kwargs`` hides the console window on Windows) and turning a
  non-zero exit into a single, catchable error type.

Consolidating these here keeps the WSL/Windows interop logic in one place
instead of being re-implemented (and drifting) at each call site.
"""

import asyncio
import logging
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

from foxhole_stockpiles.core.utils import get_subprocess_kwargs

logger = logging.getLogger(__name__)

_WSL_SUBPROCESS_TIMEOUT = 5


class ExternalToolError(RuntimeError):
    """Raised when an external tool exits with a non-zero status."""


def is_wsl() -> bool:
    """Check whether the current process is running under WSL.

    Returns:
        bool: True if running on Windows Subsystem for Linux, False otherwise.
    """
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        # File doesn't exist or can't be read - not running on Linux/WSL.
        return False


def tool_is_windows(tool_path: str | Path) -> bool:
    """Detect whether an external tool is a Windows executable.

    Windows tools (``.exe`` or living under ``/mnt/``) need their path arguments
    converted to Windows form when invoked from WSL.

    Args:
        tool_path (str | Path): Path to the external tool.

    Returns:
        bool: True if the tool looks like a Windows executable.
    """
    text = str(tool_path).lower()
    return text.endswith(".exe") or text.startswith("/mnt/")


def get_wsl_temp_dir() -> str | None:
    """Get a Windows-accessible temp directory when running under WSL.

    Windows tools cannot write to a Linux-only temp directory, so when Windows
    executables are used from WSL their scratch files must live somewhere both
    sides can reach. Resolves Windows ``%TEMP%`` via PowerShell and maps it back
    to a WSL path with ``wslpath``.

    Returns:
        str | None: A writable WSL path to the Windows temp directory, or None
            if not running under WSL or the lookup failed.
    """
    if not is_wsl():
        logger.debug("Not running in WSL, using default temp directory")
        return None

    logger.info("Detected WSL environment, using Windows temp directory for compatibility")

    try:
        result = subprocess.run(
            ["powershell.exe", "-Command", "Write-Host $env:TEMP"],
            capture_output=True,
            text=True,
            check=True,
            timeout=_WSL_SUBPROCESS_TIMEOUT,
        )
        windows_temp = result.stdout.strip()
        if not windows_temp:
            logger.warning("Empty TEMP path from PowerShell")
            return None

        result = subprocess.run(
            ["wslpath", "-u", windows_temp],
            capture_output=True,
            text=True,
            check=True,
            timeout=_WSL_SUBPROCESS_TIMEOUT,
        )
        wsl_temp_path = result.stdout.strip()

        if os.path.exists(wsl_temp_path) and os.access(wsl_temp_path, os.W_OK):
            logger.info("Using Windows temp directory: %s", wsl_temp_path)
            return wsl_temp_path
        logger.warning("Windows temp path not accessible: %s", wsl_temp_path)
    except (subprocess.SubprocessError, OSError, ValueError) as e:
        # PowerShell/wslpath can fail in many ways across environments; treat any
        # expected failure as "no Windows temp dir available" and fall back to
        # the default.
        logger.warning("Failed to get Windows temp directory: %s", e)

    return None


def convert_wsl_path_to_windows(path: str | Path) -> str:
    """Convert a WSL path to a Windows path for Windows executables.

    ``/mnt/<drive>/...`` paths are mapped directly; other paths fall back to
    ``wslpath -w``. Outside WSL the path is returned unchanged.

    Args:
        path (str | Path): Path to convert (may already be a Windows path).

    Returns:
        str: A Windows-compatible path.
    """
    path_str = str(path)

    if not is_wsl():
        return path_str

    if path_str.startswith("/mnt/"):
        parts = path_str[5:].split("/", 1)
        if parts and parts[0]:
            drive_letter = parts[0].upper()
            rest_of_path = parts[1] if len(parts) > 1 else ""
            return f"{drive_letter}:\\" + rest_of_path.replace("/", "\\")

    try:
        result = subprocess.run(
            ["wslpath", "-w", path_str],
            capture_output=True,
            text=True,
            check=True,
            timeout=_WSL_SUBPROCESS_TIMEOUT,
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        # wslpath failed or is unavailable - return the path unchanged.
        return path_str


async def run_tool(command: Sequence[str], *, check: bool = False) -> tuple[int, str, str]:
    """Run an external tool asynchronously and capture its output.

    Applies ``get_subprocess_kwargs`` so the console window is suppressed on
    Windows, and decodes stdout/stderr to text.

    Args:
        command (Sequence[str]): The full command line (tool path plus args).
        check (bool): If True, raise ``ExternalToolError`` on a non-zero exit.
            Defaults to False.

    Returns:
        tuple[int, str, str]: The (returncode, stdout, stderr) of the process.

    Raises:
        ExternalToolError: If check is True and the tool exits non-zero.
    """
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **get_subprocess_kwargs(),
    )
    stdout_bytes, stderr_bytes = await process.communicate()
    returncode = process.returncode if process.returncode is not None else -1
    stdout = stdout_bytes.decode(errors="replace")
    stderr = stderr_bytes.decode(errors="replace")

    if check and returncode != 0:
        raise ExternalToolError(f"{command[0]} failed (exit {returncode}): {stderr.strip()}")

    return returncode, stdout, stderr

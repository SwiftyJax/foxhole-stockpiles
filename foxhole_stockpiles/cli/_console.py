"""Windows console attachment for windowed (PyInstaller) executables.

When the ``fs`` binary is built as a windowed executable, CLI subcommands still
need a console to write to. This module attaches to the parent console (when run
from ``cmd``) or allocates a new one (when double-clicked). On non-Windows
platforms every function here is a no-op.
"""

import ctypes
import os
import sys


def attach_console() -> None:
    """Attach to a parent console or allocate a new one on Windows.

    Used when running CLI commands from a windowed executable:
    - When run from cmd: attaches to the parent console.
    - When double-clicked: allocates a new console for output.

    On non-Windows platforms this returns immediately.
    """
    if sys.platform != "win32":
        return

    # Import msvcrt here since it's only available on Windows.
    import msvcrt

    try:
        kernel32 = ctypes.windll.kernel32
        # Try to attach to parent console (e.g., when run from cmd).
        attach_parent_process = -1
        if not kernel32.AttachConsole(attach_parent_process):
            # No parent console, allocate a new one.
            kernel32.AllocConsole()

        # Get console handles.
        std_output_handle = -11
        std_error_handle = -12

        stdout_handle = kernel32.GetStdHandle(std_output_handle)
        stderr_handle = kernel32.GetStdHandle(std_error_handle)

        if stdout_handle and stdout_handle != -1:
            stdout_fd = msvcrt.open_osfhandle(stdout_handle, os.O_WRONLY | os.O_TEXT)
            sys.stdout = open(stdout_fd, "w", encoding="utf-8", buffering=1)

        if stderr_handle and stderr_handle != -1:
            stderr_fd = msvcrt.open_osfhandle(stderr_handle, os.O_WRONLY | os.O_TEXT)
            sys.stderr = open(stderr_fd, "w", encoding="utf-8", buffering=1)

    except (OSError, ValueError, AttributeError):
        # Silently ignore errors - output may not work but won't crash.
        # OSError: console/file descriptor issues
        # ValueError: invalid file descriptor
        # AttributeError: missing windll attributes on non-Windows
        pass

"""Windows console attachment for windowed (PyInstaller) executables.

When the ``fs`` binary is built as a windowed executable, CLI subcommands still
need a console to write to. This module attaches to the parent console (when run
from ``cmd``) or allocates a new one (when double-clicked). On non-Windows
platforms every function here is a no-op.
"""

import ctypes
import os
import sys
from typing import TextIO

# Win32 constants (see GetStdHandle / AttachConsole docs).
_ATTACH_PARENT_PROCESS = -1
_STD_OUTPUT_HANDLE = -11
_STD_ERROR_HANDLE = -12
_INVALID_HANDLE_VALUE = -1


def _replace_stream(old: TextIO | None, fd: int) -> TextIO:
    """Open a text stream on a file descriptor and close the previous one.

    Args:
        old (TextIO | None): The stream being replaced (may be None on windowed
            builds where stdout/stderr are not attached).
        fd (int): File descriptor to wrap in a new text stream.

    Returns:
        TextIO: The newly opened text stream.
    """
    new_stream = open(fd, "w", encoding="utf-8", buffering=1)
    if old is not None:
        try:
            old.close()
        except (OSError, ValueError):
            pass
    return new_stream


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
        if not kernel32.AttachConsole(_ATTACH_PARENT_PROCESS):
            # No parent console, allocate a new one.
            kernel32.AllocConsole()

        stdout_handle = kernel32.GetStdHandle(_STD_OUTPUT_HANDLE)
        stderr_handle = kernel32.GetStdHandle(_STD_ERROR_HANDLE)

        if stdout_handle and stdout_handle != _INVALID_HANDLE_VALUE:
            stdout_fd = msvcrt.open_osfhandle(stdout_handle, os.O_WRONLY | os.O_TEXT)
            sys.stdout = _replace_stream(sys.stdout, stdout_fd)

        if stderr_handle and stderr_handle != _INVALID_HANDLE_VALUE:
            stderr_fd = msvcrt.open_osfhandle(stderr_handle, os.O_WRONLY | os.O_TEXT)
            sys.stderr = _replace_stream(sys.stderr, stderr_fd)

    except (OSError, ValueError, AttributeError):
        # Silently ignore errors - output may not work but won't crash.
        # OSError: console/file descriptor issues
        # ValueError: invalid file descriptor
        # AttributeError: missing windll attributes on non-Windows
        pass

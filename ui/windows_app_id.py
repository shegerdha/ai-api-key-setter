"""Windows taskbar icon + AppUserModelID."""

from __future__ import annotations

import sys


def configure_windows_taskbar_icon() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        app_id = "ai-api-key-setter.portable.1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except OSError:
        pass

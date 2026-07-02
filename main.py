"""ai-api-key-setter entry point."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ui.app_icon import apply_window_icon, load_app_icon
from ui.main_window import MainWindow
from ui.theme import apply_app_style
from ui.windows_app_id import configure_windows_taskbar_icon


def main() -> int:
    configure_windows_taskbar_icon()
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except OSError:
            pass
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("ai-api-key-setter")
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    apply_app_style(app)

    app_icon = load_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    window = MainWindow()
    apply_window_icon(window)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

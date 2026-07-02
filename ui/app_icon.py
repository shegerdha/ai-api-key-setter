"""Application icon helpers."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def icon_png_path() -> Path:
    return _resource_root() / "assets" / "icons" / "app-icon.png"


def icon_ico_path() -> Path:
    return _resource_root() / "assets" / "icons" / "app-icon.ico"


def load_app_icon() -> QIcon:
    ico = icon_ico_path()
    if ico.exists():
        return QIcon(str(ico))
    png = icon_png_path()
    if png.exists():
        return QIcon(str(png))
    return QIcon()


def load_app_pixmap(size: int = 96) -> QPixmap:
    png = icon_png_path()
    if not png.exists():
        return QPixmap()
    pixmap = QPixmap(str(png))
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def apply_window_icon(window) -> None:
    icon = load_app_icon()
    if not icon.isNull():
        window.setWindowIcon(icon)

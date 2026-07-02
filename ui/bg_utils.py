"""Shared light background helper."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QWidget

LIGHT_BG = "#ffffff"


def apply_light_background(widget: QWidget) -> None:
    widget.setAutoFillBackground(True)
    palette = widget.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(LIGHT_BG))
    palette.setColor(QPalette.ColorRole.Base, QColor(LIGHT_BG))
    widget.setPalette(palette)

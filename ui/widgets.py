"""Reusable UI widgets."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPolygonF
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

_ARROW_COLOR = QColor("#4b5563")
_ARROW_COLOR_DISABLED = QColor("#9ca3af")
_ARROW_ZONE_WIDTH = 24


class ArrowComboBox(QComboBox):
    """QComboBox with a reliably visible painted chevron on Windows."""

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = _ARROW_COLOR_DISABLED if not self.isEnabled() else _ARROW_COLOR
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)

        cx = self.width() - _ARROW_ZONE_WIDTH // 2 - 1
        cy = self.height() // 2 + 1
        half_w = 5
        half_h = 3
        triangle = QPolygonF(
            [
                QPointF(cx - half_w, cy - half_h),
                QPointF(cx + half_w, cy - half_h),
                QPointF(cx, cy + half_h + 1),
            ]
        )
        painter.drawPolygon(triangle)
        painter.end()


class MaskedTokenEdit(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("maskedTokenEdit")
        self._visible = False

        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.EchoMode.Password)
        self.input.setPlaceholderText("sk-...")
        self.input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self.toggle_btn = QPushButton("نمایش")
        self.toggle_btn.setFixedWidth(72)
        self.toggle_btn.clicked.connect(self._toggle_visibility)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.input, 1)
        layout.addWidget(self.toggle_btn)

        self.setMinimumHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _toggle_visibility(self) -> None:
        self._visible = not self._visible
        if self._visible:
            self.input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setText("مخفی")
        else:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setText("نمایش")

    def text(self) -> str:
        return self.input.text().strip()

    def setText(self, value: str) -> None:
        self.input.setText(value)

    def setPlaceholderText(self, text: str) -> None:
        self.input.setPlaceholderText(text)

    def clear(self) -> None:
        self.input.clear()

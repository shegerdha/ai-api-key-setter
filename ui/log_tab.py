"""Application log tab."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextBlockFormat, QTextCursor, QTextOption
from PySide6.QtWidgets import QFrame, QPlainTextEdit, QSizePolicy, QVBoxLayout, QWidget

from ui.log_hub import register, unregister


class LogTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setObjectName("logTab")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.log = QPlainTextEdit()
        self.log.setObjectName("logView")
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("گزارش عملیات اینجا نمایش داده می‌شود...")
        self.log.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.log.setFrameShape(QFrame.Shape.NoFrame)
        self.log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.log.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.log.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.log.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.log.setTabStopDistance(28)
        self.log.document().setDocumentMargin(8)

        text_option = QTextOption()
        text_option.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
        )
        text_option.setTextDirection(Qt.LayoutDirection.RightToLeft)
        self.log.document().setDefaultTextOption(text_option)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.log, 1)

        register(self.append)

    def append(self, text: str) -> None:
        scrollbar = self.log.verticalScrollBar()
        stick_to_bottom = scrollbar.maximum() > 0 and scrollbar.value() >= scrollbar.maximum() - 8

        cursor = self.log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        block_format = QTextBlockFormat()
        block_format.setAlignment(Qt.AlignmentFlag.AlignRight)
        block_format.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        cursor.setBlockFormat(block_format)
        cursor.insertText(text)
        cursor.insertBlock(block_format)

        if stick_to_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event) -> None:
        unregister(self.append)
        super().closeEvent(event)

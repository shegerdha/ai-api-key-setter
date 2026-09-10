"""Main application window."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget

from ui.about_tab import AboutTab
from ui.claude_tab import ClaudeTab
from ui.codex_tab import CodexTab
from ui.cursor_tab import CursorTab
from ui.help_tab import HelpTab
from ui.log_tab import LogTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ai-api-key-setter")
        self.setMinimumSize(680, 560)
        self.resize(700, 640)

        shell = QWidget()
        shell.setObjectName("appShell")
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        tabs.setUsesScrollButtons(True)
        log_tab = LogTab()
        claude_tab = ClaudeTab()
        tabs.addTab(claude_tab, "Claude Code")
        tabs.addTab(CodexTab(), "Codex")
        tabs.addTab(CursorTab(), "Cursor")
        tabs.addTab(log_tab, "گزارش")
        tabs.addTab(HelpTab(), "راهنما")
        tabs.addTab(AboutTab(), "درباره")
        layout.addWidget(tabs, 1)

        self.setCentralWidget(shell)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

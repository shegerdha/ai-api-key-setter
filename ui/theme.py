"""IranYekanX font + application stylesheet."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def load_app_font(size: int = 9) -> QFont:
    candidates = [
        _resource_root() / "assets" / "fonts" / "IRANYekanX-Regular.ttf",
        _resource_root() / "assets" / "fonts" / "IRANYekanX-Medium.ttf",
    ]
    for path in candidates:
        if path.exists():
            font_id = QFontDatabase.addApplicationFont(str(path))
            if font_id >= 0:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    font = QFont(families[0], size)
                    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
                    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
                    return font

    for family in ("IRANYekanX", "Iran Yekan X", "IRANYekan", "Tahoma"):
        if family in QFontDatabase.families():
            font = QFont(family, size)
            font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return font

    font = QFont("Segoe UI", size)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


APP_STYLESHEET = """
* {
    outline: none;
}
QMainWindow, QWidget#appShell, QTabWidget, QTabWidget::tab-bar {
    background-color: #f8f9fb;
}
QTabWidget::pane {
    border: 1px solid #e2e6ed;
    border-top: none;
    border-radius: 0 0 8px 8px;
    background-color: #ffffff;
    top: 0px;
    margin-top: 0px;
    padding: 0px;
}
QTabWidget::tab-bar {
    alignment: right;
}
QTabWidget::left-corner,
QTabWidget::right-corner {
    background-color: #f8f9fb;
    width: 0px;
    height: 0px;
}
QTabBar {
    background-color: #f8f9fb;
    qproperty-drawBase: 0;
}
QTabBar::tab {
    background-color: #eef1f5;
    color: #5b6472;
    border: 1px solid #e2e6ed;
    border-bottom: none;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    padding: 6px 14px;
    margin-left: 2px;
    min-height: 18px;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #111827;
    font-weight: 600;
    border-bottom: 2px solid #2563eb;
}
QWidget#claudeTab, QWidget#cursorTab {
    background-color: #ffffff;
}
QWidget#logTab, QWidget#aboutPanel, QWidget#codexTab, QWidget#codexPanel, QWidget#helpTab,
QWidget#claudeTabScroll, QWidget#cursorTabScroll, QWidget#helpContent, QWidget#aboutContent,
QWidget#guideDocument {
    background-color: #ffffff;
}
QScrollArea#appScroll {
    background-color: #ffffff;
    border: none;
}
QScrollArea#appScroll QScrollBar:vertical,
QPlainTextEdit#logView QScrollBar:vertical {
    width: 10px;
    margin: 2px;
    background: transparent;
}
QScrollArea#appScroll QScrollBar::handle:vertical,
QPlainTextEdit#logView QScrollBar::handle:vertical {
    min-height: 40px;
    border-radius: 5px;
    background: #cbd5e1;
}
QScrollArea#appScroll QScrollBar::handle:vertical:hover,
QPlainTextEdit#logView QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollArea#appScroll QScrollBar::add-line:vertical,
QScrollArea#appScroll QScrollBar::sub-line:vertical,
QPlainTextEdit#logView QScrollBar::add-line:vertical,
QPlainTextEdit#logView QScrollBar::sub-line:vertical {
    height: 0px;
    border: none;
    background: none;
}
QScrollArea#appScroll QScrollBar::add-page:vertical,
QScrollArea#appScroll QScrollBar::sub-page:vertical,
QPlainTextEdit#logView QScrollBar::add-page:vertical,
QPlainTextEdit#logView QScrollBar::sub-page:vertical {
    background: none;
}
QFrame#guideHero {
    border-radius: 14px;
    border: 1px solid #dbeafe;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #eff6ff, stop:0.55 #f8fafc, stop:1 #eef2ff);
}
QLabel#guideHeroTitle {
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
    padding: 0;
    margin: 0;
}
QLabel#guideHeroSubtitle {
    font-size: 10pt;
    color: #475569;
    line-height: 1.65;
    padding: 0;
    margin: 0;
}
QLabel#guideHeroBadge {
    font-size: 9pt;
    font-weight: 600;
    color: #1d4ed8;
    background-color: #dbeafe;
    border-radius: 20px;
    padding: 5px 14px;
    margin-top: 4px;
}
QLabel#guideSectionTitle {
    font-size: 13pt;
    font-weight: 700;
    color: #0f172a;
    padding: 2px 0 6px 0;
    border-bottom: 2px solid #e2e8f0;
}
QFrame#guideCard {
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    background-color: #fafbfc;
}
QFrame#guideCard[tone="info"] {
    border-color: #bfdbfe;
    background-color: #f8fbff;
}
QFrame#guideCard[tone="success"] {
    border-color: #bbf7d0;
    background-color: #f6fef9;
}
QFrame#guideCard[tone="warn"] {
    border-color: #fde68a;
    background-color: #fffbeb;
}
QFrame#guideCard[tone="danger"] {
    border-color: #fecaca;
    background-color: #fef2f2;
}
QLabel#guideCardTitle {
    font-size: 11pt;
    font-weight: 700;
    color: #0f172a;
    padding: 0;
    margin: 0;
}
QLabel#guideBullet {
    font-size: 9.5pt;
    color: #334155;
    line-height: 1.7;
    padding: 2px 0;
}
QWidget#guideSteps {
    background: transparent;
}
QWidget#guideStepRow {
    background: transparent;
}
QLabel#guideStepBadge {
    font-size: 11pt;
    font-weight: 700;
    color: #ffffff;
    background-color: #2563eb;
    border-radius: 17px;
}
QLabel#guideStepTitle {
    font-size: 10.5pt;
    font-weight: 600;
    color: #0f172a;
}
QLabel#guideStepDetail {
    font-size: 9.5pt;
    color: #64748b;
    line-height: 1.65;
}
QFrame#guideFaqItem {
    border-radius: 10px;
    border: 1px solid #e8ebf0;
    background-color: #fcfcfd;
}
QLabel#guideFaqQuestion {
    font-size: 10.5pt;
    font-weight: 600;
    color: #0f172a;
}
QLabel#guideFaqAnswer {
    font-size: 9.5pt;
    color: #475569;
    line-height: 1.65;
}
QFrame#guidePathBox {
    border-radius: 10px;
    border: 1px dashed #cbd5e1;
    background-color: #f8fafc;
}
QLabel#guidePathLabel {
    font-size: 9pt;
    font-weight: 600;
    color: #64748b;
}
QLabel#guidePathValue {
    font-size: 9.5pt;
    font-family: "Consolas", "Cascadia Mono", monospace;
    color: #1e293b;
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 8px 10px;
}
QFrame#contentCard {
    background-color: #ffffff;
    border: none;
    border-radius: 0px;
}
QGroupBox {
    font-weight: 600;
    font-size: 9pt;
    border: 1px solid #e8ebf0;
    border-radius: 8px;
    margin-top: 10px;
    padding: 10px 10px 8px 10px;
    background-color: #fcfcfd;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top right;
    right: 12px;
    left: unset;
    padding: 0 6px;
    color: #0f172a;
    background-color: #fcfcfd;
}
QLabel {
    color: #1e293b;
    background-color: transparent;
}
QLabel#panelTitle {
    font-size: 16px;
    font-weight: 700;
    color: #111827;
    padding: 0;
    margin: 0;
}
QLabel#rtlBody {
    color: #1e293b;
    font-size: 9.5pt;
    padding: 0;
    margin: 0;
}
QLabel#hintLabel {
    color: #6b7280;
    font-size: 8pt;
}
QLabel#ideHint {
    color: #475569;
    font-size: 9pt;
    padding: 2px 0;
    line-height: 1.6;
    background-color: transparent;
}
QLineEdit {
    border: 1px solid #d5dbe5;
    border-radius: 6px;
    padding: 3px 8px;
    background-color: #ffffff;
    color: #0f172a;
    min-height: 20px;
    max-height: 28px;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}
QComboBox {
    border: 1px solid #d5dbe5;
    border-radius: 6px;
    padding: 3px 8px;
    padding-right: 26px;
    background-color: #ffffff;
    color: #0f172a;
    min-height: 24px;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}
QComboBox#modelCombo {
    min-width: 200px;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border: none;
    border-left: 1px solid #e2e8f0;
    background: transparent;
}
QComboBox::down-arrow {
    image: none;
    width: 0px;
    height: 0px;
    border: none;
}
QComboBox QAbstractItemView {
    border: 1px solid #d5dbe5;
    background-color: #ffffff;
    color: #0f172a;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    padding: 4px;
    outline: none;
}
QPlainTextEdit#logView {
    border: none;
    border-radius: 0px;
    padding: 12px 16px;
    background-color: #ffffff;
    color: #0f172a;
    min-height: 0px;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit#logView:focus {
    border-color: #3b82f6;
}
QComboBox:focus::drop-down {
    border-left-color: #d5dbe5;
}
QLineEdit#customModelInput {
    border: 1px solid #d5dbe5;
    border-radius: 6px;
    padding: 3px 8px;
    background-color: #ffffff;
    color: #0f172a;
    min-height: 20px;
    max-height: 28px;
}
QWidget#maskedTokenEdit {
    min-height: 32px;
    background-color: transparent;
}
QWidget#formRow {
    min-height: 32px;
    background-color: transparent;
}
QPushButton {
    border: 1px solid #b8c2d0;
    border-radius: 6px;
    padding: 4px 10px;
    background-color: #f8fafc;
    color: #0f172a;
    font-weight: 600;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #eef2f7;
    border-color: #94a3b8;
    color: #020617;
}
QPushButton:pressed {
    background-color: #e2e8f0;
    color: #020617;
}
QPushButton:disabled {
    color: #94a3b8;
    background-color: #f1f5f9;
}
QPushButton#browseBtn {
    min-width: 48px;
    max-width: 48px;
    padding: 4px 2px;
    color: #0f172a;
    font-weight: 600;
}
QPushButton#primaryBtn {
    background-color: #2563eb;
    color: #ffffff;
    border-color: #1d4ed8;
    font-weight: 700;
    min-width: 130px;
}
QPushButton#primaryBtn:hover {
    background-color: #1d4ed8;
    color: #ffffff;
}
QPushButton#primaryBtn:pressed {
    background-color: #1e40af;
    color: #ffffff;
}
QMessageBox {
    background-color: #ffffff;
}
QMessageBox QLabel {
    background-color: #ffffff;
    color: #1f2937;
    min-width: 280px;
}
QMessageBox QPushButton {
    min-width: 72px;
    background-color: #f8fafc;
    color: #0f172a;
    font-weight: 600;
    border: 1px solid #b8c2d0;
}
QDialog {
    background-color: #ffffff;
}
QDialog QLabel {
    background-color: #ffffff;
    color: #1f2937;
}
QToolTip {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #d5dbe5;
    padding: 4px 8px;
}
"""


def apply_app_style(app) -> QFont:
    app.setStyle("Fusion")
    font = load_app_font(9)
    app.setFont(font)
    app.setStyleSheet(APP_STYLESHEET)
    return font

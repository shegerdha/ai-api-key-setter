"""RTL content panel inside a full-height white card."""

from __future__ import annotations

import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from ui.app_icon import load_app_pixmap


def _rtl_html(text: str, *, bold: bool = False) -> str:
    escaped = html.escape(text).replace("\n", "<br>")
    weight = "font-weight:700;" if bold else ""
    return (
        f'<div align="right" dir="rtl" style="{weight}">'
        f"{escaped}</div>"
    )


class RtlContentPanel(QWidget):
    def __init__(
        self,
        title: str,
        body: str = "",
        body_html: str = "",
        show_icon: bool = False,
        icon_size: int = 112,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        card = QFrame()
        card.setObjectName("contentCard")
        card.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        title_label = QLabel(_rtl_html(title, bold=True))
        title_label.setObjectName("panelTitle")
        title_label.setTextFormat(Qt.TextFormat.RichText)
        title_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        if body_html:
            body_content = body_html
        else:
            body_content = _rtl_html(body)

        body_label = QLabel(body_content)
        body_label.setObjectName("rtlBody")
        body_label.setTextFormat(Qt.TextFormat.RichText)
        body_label.setWordWrap(True)
        body_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        body_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        body_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.addWidget(title_label)
        text_col.addWidget(body_label)
        text_col.addStretch()

        card_row = QHBoxLayout(card)
        card_row.setContentsMargins(24, 24, 24, 24)
        card_row.setSpacing(24)
        card_row.setAlignment(Qt.AlignmentFlag.AlignTop)
        card_row.addLayout(text_col, 1)

        if show_icon:
            icon_label = QLabel()
            icon_label.setPixmap(load_app_pixmap(icon_size))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            icon_label.setFixedSize(icon_size + 8, icon_size + 8)
            card_row.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card, 1)


def build_about_body(version: str) -> str:
    safe_version = html.escape(version)
    return f"""
<div align="right" dir="rtl" style="color:#1e293b; font-size:10pt; line-height:1.7;">
  <p style="margin:2px 0 18px 0; color:#64748b; font-size:9.5pt;">
    نسخه <span style="color:#2563eb; font-weight:600;">{safe_version}</span>
  </p>
  <p style="margin:0 0 10px 0; font-weight:600; color:#0f172a;">
    ابزار portable برای تنظیم Claude Code، Codex CLI و Cursor روی Windows
  </p>
  <p style="margin:0 0 8px 0; color:#475569;">
    اتصال به gateway دلخواه (مثل Agent Router) بدون ویرایش دستی فایل‌ها:
    env کاربر، تنظیمات Claude/Codex، کلید و مدل‌های خود Cursor،
    افزونه Codex در Cursor/VS Code، پروفایل چندکلیده،
    نصب npm در صورت نیاز، و باز کردن ترمینال coach برای اجرای <code>claude</code> / <code>codex</code>.
  </p>
  <p style="margin:14px 0 0 0; color:#64748b; font-size:9pt;">
    مجوز: MIT — جزئیات در <code>LICENSE</code> و منابع گرافیکی در <code>assets/ASSETS.md</code>.
  </p>
</div>
"""

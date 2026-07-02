"""About tab."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from ui.app_meta import APP_NAME, APP_VERSION
from ui.rtl_panel import RtlContentPanel, build_about_body
from ui.scroll_area import create_app_scroll_area


class AboutTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("aboutPanel")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        panel = RtlContentPanel(
            title=APP_NAME,
            body_html=build_about_body(APP_VERSION),
            show_icon=True,
            icon_size=112,
        )

        scroll, _content, root = create_app_scroll_area(content_object_name="aboutContent")
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(panel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll, 1)

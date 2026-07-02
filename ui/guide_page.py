"""Scrollable guide/about page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from ui.guide_models import GuideDocument
from ui.guide_widgets import build_guide_document
from ui.scroll_area import create_app_scroll_area


class GuidePage(QWidget):
    def __init__(
        self,
        *,
        object_name: str,
        document: GuideDocument,
        content_object_name: str = "guideContent",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        scroll, _content, _layout = create_app_scroll_area(
            content_object_name=content_object_name,
        )
        document_widget = build_guide_document(document)
        document_widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        scroll.setWidget(document_widget)
        scroll.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll, 1)

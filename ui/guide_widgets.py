"""Native Qt widgets for guide/about pages."""

from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.guide_models import (
    CardBlock,
    FaqBlock,
    GuideDocument,
    GuideSection,
    HeroBlock,
    PathBlock,
    StepBlock,
)


def _rtl(widget: QWidget) -> QWidget:
    widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    return widget


def _expand_horiz(widget: QWidget) -> QWidget:
    policy = widget.sizePolicy()
    policy.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
    widget.setSizePolicy(policy)
    return widget


def _rtl_paragraph(text: str) -> str:
    return (
        f'<p dir="rtl" align="right" style="margin:0; line-height:1.65;">'
        f"{escape(text)}</p>"
    )


def _rtl_label(
    text: str,
    object_name: str,
    *,
    full_width: bool = True,
) -> QLabel:
    label = QLabel(_rtl_paragraph(text))
    label.setObjectName(object_name)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setWordWrap(True)
    label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    if full_width:
        _expand_horiz(label)
    return label


def _section_title(text: str) -> QLabel:
    return _rtl_label(text, "guideSectionTitle")


def _bullet_label(text: str) -> QLabel:
    return _rtl_label(f"•  {text}", "guideBullet")


def _apply_tone(frame: QFrame, tone: str) -> None:
    frame.setProperty("tone", tone)
    frame.style().unpolish(frame)
    frame.style().polish(frame)


def build_hero(hero: HeroBlock) -> QFrame:
    frame = _expand_horiz(_rtl(QFrame()))
    frame.setObjectName("guideHero")
    _apply_tone(frame, "hero")

    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(10)

    layout.addWidget(_rtl_label(hero.title, "guideHeroTitle"))
    layout.addWidget(_rtl_label(hero.subtitle, "guideHeroSubtitle"))

    if hero.badge:
        badge = _rtl_label(hero.badge, "guideHeroBadge", full_width=False)
        badge.setProperty("accent", hero.accent)
        badge.style().unpolish(badge)
        badge.style().polish(badge)
        badge_row = QWidget()
        badge_row.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        badge_layout = QHBoxLayout(badge_row)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.addStretch()
        badge_layout.addWidget(badge)
        layout.addWidget(badge_row)

    return frame


def build_card(card: CardBlock) -> QFrame:
    frame = _expand_horiz(_rtl(QFrame()))
    frame.setObjectName("guideCard")
    _apply_tone(frame, card.tone)

    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(12)

    layout.addWidget(_rtl_label(card.title, "guideCardTitle"))
    for line in card.bullets:
        layout.addWidget(_bullet_label(line))

    return frame


def build_steps(steps: StepBlock) -> QWidget:
    wrap = _expand_horiz(_rtl(QWidget()))
    wrap.setObjectName("guideSteps")
    layout = QVBoxLayout(wrap)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(14)

    for index, (title, detail) in enumerate(steps.items, start=1):
        row = _expand_horiz(QWidget())
        row.setObjectName("guideStepRow")
        row.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(14)

        badge = QLabel(str(index))
        badge.setObjectName("guideStepBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(34, 34)
        badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        text_wrap = _expand_horiz(QWidget())
        text_wrap.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        text_col = QVBoxLayout(text_wrap)
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(4)
        text_col.addWidget(_rtl_label(title, "guideStepTitle"))
        text_col.addWidget(_rtl_label(detail, "guideStepDetail"))

        row_layout.addWidget(text_wrap, 1)
        row_layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(row)

    return wrap


def build_faq(faq: FaqBlock) -> QWidget:
    wrap = _expand_horiz(_rtl(QWidget()))
    wrap.setObjectName("guideFaqList")
    layout = QVBoxLayout(wrap)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)

    for question, answer in faq.items:
        item = _expand_horiz(_rtl(QFrame()))
        item.setObjectName("guideFaqItem")
        item_layout = QVBoxLayout(item)
        item_layout.setContentsMargins(16, 14, 16, 14)
        item_layout.setSpacing(8)

        item_layout.addWidget(_rtl_label(question, "guideFaqQuestion"))
        item_layout.addWidget(_rtl_label(answer, "guideFaqAnswer"))
        layout.addWidget(item)

    return wrap


def build_path(block: PathBlock) -> QFrame:
    frame = _expand_horiz(_rtl(QFrame()))
    frame.setObjectName("guidePathBox")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(6)

    layout.addWidget(_rtl_label(block.label, "guidePathLabel"))

    path = QLabel(block.path)
    path.setObjectName("guidePathValue")
    path.setWordWrap(True)
    path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    path.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    path.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    _expand_horiz(path)
    layout.addWidget(path)

    return frame


def build_section(section: GuideSection) -> QWidget:
    wrap = _expand_horiz(_rtl(QWidget()))
    wrap.setObjectName("guideSection")
    layout = QVBoxLayout(wrap)
    layout.setContentsMargins(0, 6, 0, 0)
    layout.setSpacing(18)
    layout.addWidget(_section_title(section.title))

    if section.steps:
        layout.addWidget(build_steps(section.steps))
    for card in section.cards:
        layout.addWidget(build_card(card))
    if section.faq:
        layout.addWidget(build_faq(section.faq))
    if section.path:
        layout.addWidget(build_path(section.path))

    return wrap


def build_guide_document(document: GuideDocument) -> QWidget:
    root = _rtl(QWidget())
    root.setObjectName("guideDocument")
    root.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

    layout = QVBoxLayout(root)
    layout.setContentsMargins(24, 20, 24, 28)
    layout.setSpacing(28)
    layout.addWidget(build_hero(document.hero))

    for section in document.sections:
        layout.addWidget(build_section(section))

    layout.addStretch()
    return root

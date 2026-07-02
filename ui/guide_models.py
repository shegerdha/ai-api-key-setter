"""Structured guide/about content models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Tone = Literal["neutral", "info", "success", "warn"]


@dataclass
class HeroBlock:
    title: str
    subtitle: str
    accent: str = "#2563eb"
    badge: str | None = None


@dataclass
class CardBlock:
    title: str
    bullets: list[str]
    tone: Tone = "neutral"


@dataclass
class StepBlock:
    items: list[tuple[str, str]]


@dataclass
class FaqBlock:
    items: list[tuple[str, str]]


@dataclass
class PathBlock:
    label: str
    path: str


@dataclass
class GuideSection:
    title: str
    cards: list[CardBlock] = field(default_factory=list)
    steps: StepBlock | None = None
    faq: FaqBlock | None = None
    path: PathBlock | None = None


@dataclass
class GuideDocument:
    hero: HeroBlock
    sections: list[GuideSection]

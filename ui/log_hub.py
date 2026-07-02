"""Shared application log sink."""

from __future__ import annotations

from typing import Callable, List

_listeners: List[Callable[[str], None]] = []


def register(listener: Callable[[str], None]) -> None:
    if listener not in _listeners:
        _listeners.append(listener)


def unregister(listener: Callable[[str], None]) -> None:
    if listener in _listeners:
        _listeners.remove(listener)


def append(text: str) -> None:
    for listener in list(_listeners):
        listener(text)

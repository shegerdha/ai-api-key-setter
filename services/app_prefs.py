"""Persistent UI preferences for ai-api-key-setter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def prefs_path() -> Path:
    return Path.home() / ".claude" / "ai-api-key-setter-prefs.json"


def read_prefs() -> Dict[str, Any]:
    path = prefs_path()
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def write_prefs(data: Dict[str, Any]) -> Path:
    path = prefs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def get_pref(key: str, default: Optional[Any] = None) -> Any:
    return read_prefs().get(key, default)


def set_pref(key: str, value: Any) -> None:
    data = read_prefs()
    data[key] = value
    write_prefs(data)


def update_prefs(**kwargs: Any) -> Path:
    data = read_prefs()
    data.update(kwargs)
    return write_prefs(data)

"""Backup, merge, and restore Cursor/VS Code chatgpt.* settings for Codex."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from services.codex_config import normalize_gateway_v1

BACKUP_SUFFIX = ".bak.ai-api-key-setter"
RESTORE_SAFETY_SUFFIX = ".before-restore.ai-api-key-setter"


@dataclass
class EditorTarget:
    label: str
    settings_path: Path


def editor_targets() -> List[EditorTarget]:
    appdata = Path(os.environ.get("APPDATA", ""))
    return [
        EditorTarget("Cursor", appdata / "Cursor" / "User" / "settings.json"),
        EditorTarget("VS Code", appdata / "Code" / "User" / "settings.json"),
    ]


def backup_path(settings_path: Path) -> Path:
    return settings_path.parent / f"{settings_path.name}{BACKUP_SUFFIX}"


def _read_json_file(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not path.exists():
        return {}, None
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data, None
        return None, f"ساختار JSON نامعتبر: {path}"
    except json.JSONDecodeError as exc:
        return None, f"JSON قابل خواندن نیست ({path.name}): {exc}"
    except OSError as exc:
        return None, str(exc)


def _write_json_file(path: Path, data: Dict[str, Any]) -> Optional[str]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        return None
    except OSError as exc:
        return str(exc)


def merge_chatgpt_settings(
    existing: Dict[str, Any],
    base_url_v1: str,
) -> Dict[str, Any]:
    merged = dict(existing)
    merged["chatgpt.apiBase"] = normalize_gateway_v1(base_url_v1)
    merged["chatgpt.config"] = {
        "preferred_auth_method": "api_key",
        "model_provider": "openai-chat-completions",
    }
    return merged


def apply_chatgpt_settings(base_url_v1: str) -> List[str]:
    """Backup current settings, merge chatgpt keys, write new settings.json."""
    logs: List[str] = []
    for target in editor_targets():
        settings_path = target.settings_path
        old_data, read_error = _read_json_file(settings_path)
        if read_error:
            logs.append(f"{target.label}: رد شد — {read_error}")
            continue

        backup = backup_path(settings_path)
        if settings_path.exists():
            try:
                shutil.copy2(settings_path, backup)
                logs.append(f"{target.label}: backup → {backup}")
            except OSError as exc:
                logs.append(f"{target.label}: backup ناموفق — {exc}")
                continue

        merged = merge_chatgpt_settings(old_data or {}, base_url_v1)
        write_error = _write_json_file(settings_path, merged)
        if write_error:
            logs.append(f"{target.label}: نوشتن ناموفق — {write_error}")
            if backup.exists() and not settings_path.exists():
                try:
                    shutil.copy2(backup, settings_path)
                except OSError:
                    pass
            continue

        logs.append(f"{target.label}: chatgpt.* ذخیره شد → {settings_path}")
    return logs


def restore_chatgpt_settings() -> List[str]:
    """Restore settings.json from .bak.ai-api-key-setter backup."""
    logs: List[str] = []
    for target in editor_targets():
        settings_path = target.settings_path
        backup = backup_path(settings_path)
        if not backup.exists():
            logs.append(f"{target.label}: backup یافت نشد — {backup}")
            continue

        if settings_path.exists():
            safety = settings_path.parent / f"{settings_path.name}{RESTORE_SAFETY_SUFFIX}"
            try:
                shutil.copy2(settings_path, safety)
                logs.append(f"{target.label}: نسخه فعلی → {safety}")
            except OSError as exc:
                logs.append(f"{target.label}: ذخیره نسخه فعلی ناموفق — {exc}")
                continue

        try:
            shutil.copy2(backup, settings_path)
            logs.append(f"{target.label}: بازگردانی از backup انجام شد")
        except OSError as exc:
            logs.append(f"{target.label}: بازگردانی ناموفق — {exc}")
    return logs


def backup_status() -> List[str]:
    lines: List[str] = []
    for target in editor_targets():
        backup = backup_path(target.settings_path)
        if backup.exists():
            lines.append(f"{target.label}: backup موجود")
        else:
            lines.append(f"{target.label}: backup نیست")
    return lines

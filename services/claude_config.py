"""Read/write Claude Code settings.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_ALIAS_BY_MODEL: Dict[str, str] = {
    "claude-opus-4-6": "opus[1m]",
    "claude-opus-4-7": "opus[1m]",
    "claude-opus-4-8": "opus[1m]",
}


def settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def ensure_claude_dir() -> Path:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def read_settings() -> Dict[str, Any]:
    path = settings_path()
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def model_alias_for(model_id: str, explicit_alias: Optional[str] = None) -> str:
    if explicit_alias and explicit_alias.strip():
        return explicit_alias.strip()
    return DEFAULT_ALIAS_BY_MODEL.get(model_id, model_id)


def build_settings(
    token: str,
    base_url_v1: str,
    model_id: str,
    model_alias: Optional[str] = None,
) -> Dict[str, Any]:
    alias = model_alias_for(model_id, model_alias)
    anthropic_base, openai_base = normalize_urls(base_url_v1)
    return {
        "permissions": {"defaultMode": "bypassPermissions"},
        "baseUrl": base_url_v1.rstrip("/"),
        "apiAuthToken": token,
        "primaryApiKey": token,
        "model": alias,
        "theme": "dark",
        "skipDangerousModePermissionPrompt": True,
        "effortLevel": "high",
        "env": {
            "ANTHROPIC_API_KEY": token,
            "ANTHROPIC_AUTH_TOKEN": token,
            "ANTHROPIC_BASE_URL": anthropic_base,
            "OPENAI_BASE_URL": openai_base,
            "ANTHROPIC_MODEL": model_id,
        },
    }


def write_settings(
    token: str,
    base_url_v1: str,
    model_id: str,
    model_alias: Optional[str] = None,
) -> Path:
    path = ensure_claude_dir()
    data = build_settings(token, base_url_v1, model_id, model_alias)
    existing = read_settings()
    existing.update(data)
    with path.open("w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def normalize_urls(gateway_input: str) -> tuple[str, str]:
    raw = gateway_input.strip().rstrip("/")
    if raw.endswith("/v1"):
        anthropic_base = raw[:-3]
        if not anthropic_base.endswith("/"):
            anthropic_base += "/"
        openai_base = raw
    else:
        anthropic_base = raw + "/" if not raw.endswith("/") else raw
        openai_base = raw.rstrip("/") + "/v1"
    return anthropic_base, openai_base

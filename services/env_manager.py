"""Windows user-scope environment variable management."""

from __future__ import annotations

import os
import winreg
from typing import Dict, Optional

CLAUDE_ENV_KEYS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "OPENAI_BASE_URL",
    "ANTHROPIC_MODEL",
)

CONFLICTING_KEYS = (
    "ANTHROPIC_API_URL",
    "CLAUDE_API_KEY",
    "ANTHROPIC_DEFAULT_MODEL",
)


def _user_env_key() -> winreg.HKEYType:
    return winreg.HKEY_CURRENT_USER


def _open_env_key(write: bool = False) -> winreg.HKEYType:
    access = winreg.KEY_READ | (winreg.KEY_SET_VALUE if write else 0)
    return winreg.OpenKey(
        _user_env_key(),
        r"Environment",
        0,
        access,
    )


def read_user_env(name: str) -> Optional[str]:
    try:
        with _open_env_key() as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value if value else None
    except FileNotFoundError:
        return None
    except OSError:
        return None


def read_claude_env() -> Dict[str, Optional[str]]:
    result: Dict[str, Optional[str]] = {}
    for key in CLAUDE_ENV_KEYS:
        result[key] = read_user_env(key)
    return result


def set_user_env(name: str, value: str) -> None:
    with _open_env_key(write=True) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)


def remove_user_env(name: str) -> None:
    try:
        with _open_env_key(write=True) as key:
            winreg.DeleteValue(key, name)
    except FileNotFoundError:
        pass


def apply_claude_env(
    token: str,
    anthropic_base_url: str,
    openai_base_url: str,
    model_id: str,
) -> Dict[str, str]:
    values = {
        "ANTHROPIC_API_KEY": token,
        "ANTHROPIC_AUTH_TOKEN": token,
        "ANTHROPIC_BASE_URL": anthropic_base_url,
        "OPENAI_BASE_URL": openai_base_url,
        "ANTHROPIC_MODEL": model_id,
    }
    for key, value in values.items():
        set_user_env(key, value)
    for key in CONFLICTING_KEYS:
        remove_user_env(key)
    return values


def broadcast_env_change() -> None:
    import ctypes

    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x001A
    SMTO_ABORTIFHUNG = 0x0002
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST,
        WM_SETTINGCHANGE,
        0,
        "Environment",
        SMTO_ABORTIFHUNG,
        5000,
        None,
    )


def session_env_snapshot(values: Dict[str, str]) -> Dict[str, str]:
    snapshot = dict(os.environ)
    snapshot.update(values)
    return snapshot

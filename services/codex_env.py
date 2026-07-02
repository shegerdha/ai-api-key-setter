"""Windows user-scope environment variables for Codex / Agent Router."""

from __future__ import annotations

from typing import Dict, Optional

from services.env_manager import broadcast_env_change, read_user_env, set_user_env

CODEX_ENV_KEYS = (
    "AGENT_ROUTER_TOKEN",
    "AGENTROUTER_API_KEY",
    "OPENAI_API_KEY",
)


def read_codex_env() -> Dict[str, Optional[str]]:
    return {key: read_user_env(key) for key in CODEX_ENV_KEYS}


def apply_codex_env(token: str) -> Dict[str, str]:
    values = {
        "AGENT_ROUTER_TOKEN": token,
        "AGENTROUTER_API_KEY": token,
        "OPENAI_API_KEY": token,
    }
    for key, value in values.items():
        set_user_env(key, value)
    broadcast_env_change()
    return values

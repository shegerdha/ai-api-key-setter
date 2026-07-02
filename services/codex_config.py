"""Read/write OpenAI Codex config.toml and auth.json."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from services.codex_constants import (
    DEFAULT_RELAY_PORT,
    LOCALHOST_HOST,
    is_agentrouter_gateway,
    normalize_gateway_v1,
)

DEFAULT_MODEL = "gpt-5.5"
DEFAULT_MODEL_PROVIDER = "openai-chat-completions"
DIRECT_PROVIDER_ID = "ai-api-key-setter-gateway"
DEFAULT_GATEWAY_V1 = "https://agentrouter.org/v1"
RELAY_PROVIDER_ID = "ai-api-key-setter-relay"
AGENTROUTER_PROVIDER_ID = "agentrouter"


def codex_dir() -> Path:
    return Path.home() / ".codex"


def config_path() -> Path:
    return codex_dir() / "config.toml"


def auth_path() -> Path:
    return codex_dir() / "auth.json"


def ensure_codex_dir() -> Path:
    path = codex_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def relay_base_url(port: int = DEFAULT_RELAY_PORT) -> str:
    return f"http://{LOCALHOST_HOST}:{port}/v1"


def is_relay_base_url(base_url: str) -> bool:
    return LOCALHOST_HOST in base_url or "localhost" in base_url.lower()


def direct_provider_fields(base_url_v1: str) -> tuple[str, str, str]:
    """Return provider_id, display name, env_key for direct gateway config."""
    if is_agentrouter_gateway(base_url_v1):
        return AGENTROUTER_PROVIDER_ID, "Agent Router", "AGENTROUTER_API_KEY"
    return DIRECT_PROVIDER_ID, "Custom Gateway", "AGENT_ROUTER_TOKEN"


def build_config_toml(
    model_id: str,
    codex_base_url_v1: str,
    *,
    provider_id: str = DEFAULT_MODEL_PROVIDER,
    provider_name: str = "OpenAI using Responses API",
    wire_api: str = "responses",
    env_key: str = "AGENT_ROUTER_TOKEN",
    requires_openai_auth: bool = False,
    supports_websockets: bool = False,
) -> str:
    base = normalize_gateway_v1(codex_base_url_v1)
    model = model_id.strip() or DEFAULT_MODEL
    api = wire_api.strip() or "responses"
    if api not in ("responses", "chat"):
        api = "responses"
    return (
        f'model = "{model}"\n'
        f'model_provider = "{provider_id}"\n'
        'preferred_auth_method = "apikey"\n'
        "\n"
        f"[model_providers.{provider_id}]\n"
        f'name = "{provider_name}"\n'
        f'base_url = "{base}"\n'
        f'env_key = "{env_key}"\n'
        f'wire_api = "{api}"\n'
        f"requires_openai_auth = {'true' if requires_openai_auth else 'false'}\n"
        "query_params = {}\n"
        "stream_idle_timeout_ms = 300000\n"
        f"supports_websockets = {'true' if supports_websockets else 'false'}\n"
    )


def build_direct_config_toml(model_id: str, base_url_v1: str) -> str:
    provider_id, provider_name, env_key = direct_provider_fields(base_url_v1)
    return build_config_toml(
        model_id=model_id,
        codex_base_url_v1=base_url_v1,
        provider_id=provider_id,
        provider_name=provider_name,
        wire_api="responses",
        env_key=env_key,
        requires_openai_auth=False,
        supports_websockets=False,
    )


def build_agentrouter_legacy_config_toml(model_id: str, base_url_v1: str) -> str:
    return build_config_toml(
        model_id=model_id,
        codex_base_url_v1=base_url_v1,
        provider_id=AGENTROUTER_PROVIDER_ID,
        provider_name="Agent Router",
        wire_api="chat",
        env_key="AGENTROUTER_API_KEY",
        requires_openai_auth=False,
        supports_websockets=False,
    )


def build_relay_config_toml(model_id: str, relay_port: int) -> str:
    model = model_id.strip() or DEFAULT_MODEL
    base = build_config_toml(
        model_id=model,
        codex_base_url_v1=relay_base_url(relay_port),
        provider_id=RELAY_PROVIDER_ID,
        provider_name="Gateway via codex-relay (auto)",
        wire_api="responses",
        requires_openai_auth=False,
        supports_websockets=False,
    )
    props = (
        f'\n[model_properties."{model}"]\n'
        "context_window = 128000\n"
        "max_context_window = 128000\n"
        "supports_parallel_tool_calls = true\n"
        "supports_reasoning_summaries = false\n"
        'input_modalities = ["text"]\n'
    )
    return base + props


def build_auth_json(token: str) -> Dict[str, str]:
    return {
        "OPENAI_API_KEY": token,
        "AGENTROUTER_API_KEY": token,
    }


def read_auth() -> Dict[str, Any]:
    path = auth_path()
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def read_config_text() -> str:
    path = config_path()
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def parse_config_model(config_text: str) -> Optional[str]:
    for line in config_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("model") and "=" in stripped and not stripped.startswith("model_"):
            _, value = stripped.split("=", 1)
            return value.strip().strip('"').strip("'")
    return None


def parse_config_base_url(config_text: str) -> Optional[str]:
    for line in config_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("base_url") and "=" in stripped:
            _, value = stripped.split("=", 1)
            return value.strip().strip('"').strip("'")
    return None


def _merge_model_line(config_text: str, model_id: str) -> str:
    if re.search(r"^model\s*=", config_text, flags=re.MULTILINE):
        return re.sub(
            r'^model\s*=.*$',
            f'model = "{model_id}"',
            config_text,
            count=1,
            flags=re.MULTILINE,
        )
    return f'model = "{model_id}"\n' + config_text


def write_codex_files(
    token: str,
    upstream_base_url_v1: str,
    model_id: str,
    *,
    routing_mode,
    relay_port: int = DEFAULT_RELAY_PORT,
) -> tuple[Path, Path, str]:
    from services.codex_routing import CodexRoutingMode

    ensure_codex_dir()
    cfg = config_path()
    auth = auth_path()

    if routing_mode == CodexRoutingMode.RELAY:
        config_text = build_relay_config_toml(model_id, relay_port)
        mode_note = "relay"
        codex_target = relay_base_url(relay_port)
    elif routing_mode == CodexRoutingMode.AGENTROUTER_LEGACY:
        config_text = build_agentrouter_legacy_config_toml(model_id, upstream_base_url_v1)
        mode_note = "agentrouter-legacy"
        codex_target = normalize_gateway_v1(upstream_base_url_v1)
    else:
        config_text = build_direct_config_toml(model_id, upstream_base_url_v1)
        mode_note = "direct"
        codex_target = normalize_gateway_v1(upstream_base_url_v1)

    cfg.write_text(config_text if config_text.endswith("\n") else config_text + "\n", encoding="utf-8")
    with auth.open("w", encoding="utf-8") as f:
        json.dump(build_auth_json(token), f, indent=2, ensure_ascii=False)
        f.write("\n")
    return cfg, auth, mode_note

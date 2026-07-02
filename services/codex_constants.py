"""Shared Codex constants and helpers (no service imports)."""

from __future__ import annotations

DEFAULT_RELAY_PORT = 4444
LOCALHOST_HOST = "127.0.0.1"
AGENTROUTER_HOST = "agentrouter.org"


def normalize_gateway_v1(gateway_input: str) -> str:
    raw = gateway_input.strip().rstrip("/")
    if not raw.endswith("/v1"):
        raw = raw + "/v1"
    return raw


def is_agentrouter_gateway(base_url_v1: str) -> bool:
    return AGENTROUTER_HOST in base_url_v1.lower()

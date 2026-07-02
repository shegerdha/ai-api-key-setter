"""Choose Codex connection strategy per gateway."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.codex_constants import DEFAULT_RELAY_PORT, is_agentrouter_gateway
from services.codex_gateway_probe import (
    gateway_needs_relay,
    relay_upstream_rejected,
)
from services.codex_relay import ensure_relay_running, stop_relay

LEGACY_CODEX_VERSION = "0.92.0"


class CodexRoutingMode(str, Enum):
    DIRECT_RESPONSES = "direct"
    RELAY = "relay"
    AGENTROUTER_LEGACY = "agentrouter_legacy"


@dataclass
class CodexSavePlan:
    routing_mode: CodexRoutingMode
    route_note: str
    relay_msg: str = ""
    legacy_needed: bool = False


def resolve_codex_save_plan(
    base_url_v1: str,
    token: str,
    *,
    relay_port: int = DEFAULT_RELAY_PORT,
) -> tuple[CodexSavePlan | None, str]:
    """
    Priority:
    1. Direct responses when gateway exposes /v1/responses
    2. codex-relay when only chat/completions exists
    3. Legacy Codex + chat for Agent Router when relay is blocked
    """
    needs_relay, probe_note = gateway_needs_relay(base_url_v1, token)
    if not needs_relay:
        stop_relay()
        return CodexSavePlan(
            routing_mode=CodexRoutingMode.DIRECT_RESPONSES,
            route_note=(
                "اولویت: اتصال مستقیم با wire_api=responses و "
                f"requires_openai_auth=false — {probe_note}"
            ),
        ), ""

    relay_ok, relay_msg = ensure_relay_running(base_url_v1, token, relay_port)
    if relay_ok and not relay_upstream_rejected(relay_port, token):
        return CodexSavePlan(
            routing_mode=CodexRoutingMode.RELAY,
            route_note=f"gateway فقط Chat دارد — {probe_note}",
            relay_msg=relay_msg,
        ), ""

    if is_agentrouter_gateway(base_url_v1):
        stop_relay()
        reject_note = ""
        if relay_ok:
            reject_note = "relay بالا آمد ولی upstream آن را رد کرد (unauthorized client). "
        elif relay_msg:
            reject_note = f"relay راه‌اندازی نشد ({relay_msg}). "
        return CodexSavePlan(
            routing_mode=CodexRoutingMode.AGENTROUTER_LEGACY,
            route_note=(
                f"{reject_note}"
                f"fallback: Codex {LEGACY_CODEX_VERSION} با wire_api=chat مستقیم."
            ),
            relay_msg=relay_msg,
            legacy_needed=True,
        ), ""

    if not relay_ok:
        return None, relay_msg or "راه‌اندازی codex-relay ناموفق بود."

    return None, (
        "codex-relay فعال است ولی upstream درخواست را رد می‌کند. "
        "لاگ relay را بررسی کنید."
    )

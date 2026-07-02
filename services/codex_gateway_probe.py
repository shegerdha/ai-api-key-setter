"""Detect whether gateway needs codex-relay."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Tuple

from services.codex_constants import LOCALHOST_HOST, normalize_gateway_v1


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _post_probe(url: str, token: str, body: dict, timeout: int = 12) -> Tuple[int, str]:
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers=_auth_headers(token),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body_text = ""
        try:
            body_text = exc.read().decode("utf-8", errors="replace")
        except OSError:
            pass
        return exc.code, body_text or exc.reason
    except urllib.error.URLError as exc:
        return 0, str(exc.reason)
    except OSError as exc:
        return 0, str(exc)


def _responses_unsupported(code: int, body: str) -> bool:
    if code == 404:
        return True
    lowered = body.lower()
    if "invalid url" in lowered and "responses" in lowered:
        return True
    if "not found" in lowered and "/responses" in lowered:
        return True
    return False


def _responses_endpoint_usable(code: int, body: str) -> bool:
    """Conservative: only trust direct Codex when /responses clearly works."""
    if code == 0:
        return False
    if _responses_unsupported(code, body):
        return False
    lowered = body.lower()
    if "unauthorized client" in lowered:
        return False
    if 200 <= code < 300:
        return True
    if code == 400:
        # Route exists but payload rejected — Codex may still work.
        if "invalid url" in lowered or "not found" in lowered:
            return False
        return True
    return False


def relay_upstream_rejected(port: int, token: str) -> bool:
    """True when relay is up but upstream returns unauthorized_client."""
    url = f"http://{LOCALHOST_HOST}:{port}/v1/responses"
    code, body = _post_probe(
        url,
        token,
        {"model": "gpt-5.5", "input": "ping", "stream": True},
        timeout=20,
    )
    lowered = body.lower()
    if "unauthorized client" in lowered:
        return True
    return code in (401, 403) and "unauthorized" in lowered


def gateway_needs_relay(base_url_v1: str, token: str) -> Tuple[bool, str]:
    """Return (needs_relay, note)."""
    base = normalize_gateway_v1(base_url_v1)
    responses_url = f"{base}/responses"
    code, body = _post_probe(
        responses_url,
        token,
        {"model": "gpt-5.5", "input": "ping", "stream": True},
    )
    if _responses_endpoint_usable(code, body):
        return False, "gateway از POST /v1/responses پشتیبانی می‌کند — اتصال مستقیم."
    if _responses_unsupported(code, body):
        return True, (
            "gateway از POST /v1/responses پشتیبانی نمی‌کند (404/Invalid URL) — "
            "codex-relay فعال می‌شود."
        )
    if code in (401, 403):
        return True, (
            "gateway درخواست /v1/responses را رد کرد — "
            "اتصال مستقیم امن نیست؛ relay امتحان می‌شود."
        )
    if code == 0:
        return True, f"gateway در دسترس نبود ({body}) — relay امتحان می‌شود."
    if code >= 400:
        return True, (
            f"gateway برای /v1/responses HTTP {code} داد — "
            "اتصال مستقیم رد شد؛ relay امتحان می‌شود."
        )
    return True, "پاسخ نامشخص از /v1/responses — relay امتحان می‌شود."

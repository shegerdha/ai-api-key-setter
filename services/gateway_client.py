"""Fetch available models from Anthropic-compatible gateway."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GatewayModel:
    model_id: str
    display_name: str


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "x-api-key": token,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }


def _parse_models_payload(payload: object) -> List[GatewayModel]:
    models: List[GatewayModel] = []
    if not isinstance(payload, dict):
        return models
    data = payload.get("data")
    if not isinstance(data, list):
        return models
    for item in data:
        if isinstance(item, dict):
            model_id = item.get("id") or item.get("name") or ""
            if model_id:
                models.append(
                    GatewayModel(
                        model_id=str(model_id),
                        display_name=str(item.get("display_name") or model_id),
                    )
                )
        elif isinstance(item, str) and item:
            models.append(GatewayModel(model_id=item, display_name=item))
    return models


def _friendly_http_error(code: int, body: str) -> str:
    lowered = body.lower()
    if code == 401 and "unauthorized client" in lowered:
        return (
            "gateway درخواست مستقیم به /models را رد کرد (unauthorized client). "
            "این محدودیت کلاینت است، نه توکن — Claude Code با همین توکن کار می‌کند. "
            "از لیست پیش‌فرض یا وارد کردن دستی مدل استفاده کنید."
        )
    if code == 401:
        return f"HTTP 401: توکن نامعتبر یا دسترسی ندارید.\n{body}"
    return f"HTTP {code}: {body}"


def fetch_models(base_url_v1: str, token: str, timeout: int = 15) -> tuple[List[GatewayModel], Optional[str]]:
    base = base_url_v1.strip().rstrip("/")
    if not base.endswith("/v1"):
        base = base + "/v1"
    url = f"{base}/models"
    request = urllib.request.Request(url, headers=_auth_headers(token), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            payload = json.loads(raw)
            models = _parse_models_payload(payload)
            if models:
                return models, None
            return [], "پاسخ gateway فهرست مدلی برنگرداند."
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except OSError:
            pass
        return [], _friendly_http_error(exc.code, body or exc.reason)
    except urllib.error.URLError as exc:
        return [], f"خطای اتصال: {exc.reason}"
    except json.JSONDecodeError:
        return [], "پاسخ gateway قابل parse نیست."
    except OSError as exc:
        return [], str(exc)


def fallback_models() -> List[GatewayModel]:
    """مدل‌های شناخته‌شده gateway — از cache/تجربه Claude Code."""
    return [
        GatewayModel("claude-opus-4-6", "claude-opus-4-6"),
        GatewayModel("claude-opus-4-7", "claude-opus-4-7"),
        GatewayModel("claude-opus-4-8", "claude-opus-4-8"),
        GatewayModel("glm-5.2", "glm-5.2"),
        GatewayModel("gpt-5.5", "gpt-5.5"),
    ]

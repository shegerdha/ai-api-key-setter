"""Persistent connection profiles (token/gateway/model) per tool tab."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any, Dict, List, Optional

from services.app_prefs import read_prefs, write_prefs

KIND_CLAUDE = "claude"
KIND_CODEX = "codex"
KIND_CURSOR = "cursor"
_ROOT = "connection_profiles"


def _blank_kind() -> Dict[str, Any]:
    return {"active_id": "", "items": []}


def _root() -> Dict[str, Any]:
    data = read_prefs()
    root = data.get(_ROOT)
    if not isinstance(root, dict):
        return {}
    return root


def _write_root(root: Dict[str, Any]) -> None:
    data = read_prefs()
    data[_ROOT] = root
    write_prefs(data)


def _kind_state(kind: str) -> Dict[str, Any]:
    state = _root().get(kind)
    if not isinstance(state, dict):
        return _blank_kind()
    items = state.get("items")
    if not isinstance(items, list):
        items = []
    active = str(state.get("active_id") or "")
    return {"active_id": active, "items": items}


def list_profiles(kind: str) -> List[Dict[str, Any]]:
    items = []
    for item in _kind_state(kind)["items"]:
        if isinstance(item, dict) and item.get("id") and item.get("name"):
            items.append(item)
    return items


def get_profile(kind: str, profile_id: str) -> Optional[Dict[str, Any]]:
    for item in list_profiles(kind):
        if item.get("id") == profile_id:
            return deepcopy(item)
    return None


def active_id(kind: str) -> str:
    state = _kind_state(kind)
    current = str(state.get("active_id") or "")
    ids = {str(item.get("id")) for item in list_profiles(kind)}
    if current in ids:
        return current
    if ids:
        return next(iter(ids))
    return ""


def active_profile(kind: str) -> Optional[Dict[str, Any]]:
    pid = active_id(kind)
    return get_profile(kind, pid) if pid else None


def set_active(kind: str, profile_id: str) -> None:
    root = _root()
    state = _kind_state(kind)
    state["active_id"] = profile_id
    root[kind] = state
    _write_root(root)


def upsert_profile(
    kind: str,
    *,
    name: str,
    fields: Dict[str, Any],
    profile_id: Optional[str] = None,
    make_active: bool = True,
) -> Dict[str, Any]:
    root = _root()
    state = _kind_state(kind)
    items: List[Dict[str, Any]] = [
        item for item in state["items"] if isinstance(item, dict)
    ]
    pid = profile_id or uuid.uuid4().hex[:12]
    payload = {
        "id": pid,
        "name": name.strip() or "بدون نام",
        "fields": deepcopy(fields),
    }
    replaced = False
    for index, item in enumerate(items):
        if item.get("id") == pid:
            payload["name"] = name.strip() or str(item.get("name") or "بدون نام")
            items[index] = payload
            replaced = True
            break
    if not replaced:
        items.append(payload)
    state["items"] = items
    if make_active or not state.get("active_id"):
        state["active_id"] = pid
    root[kind] = state
    _write_root(root)
    return deepcopy(payload)


def save_fields_to_active(kind: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    current = active_profile(kind)
    if current is None:
        return None
    return upsert_profile(
        kind,
        name=str(current.get("name") or "پیش‌فرض"),
        fields=fields,
        profile_id=str(current["id"]),
        make_active=True,
    )


def create_profile(
    kind: str,
    name: str,
    fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return upsert_profile(kind, name=name, fields=fields or {}, profile_id=None)


def rename_profile(kind: str, profile_id: str, name: str) -> None:
    current = get_profile(kind, profile_id)
    if current is None:
        return
    upsert_profile(
        kind,
        name=name,
        fields=current.get("fields") if isinstance(current.get("fields"), dict) else {},
        profile_id=profile_id,
        make_active=active_id(kind) == profile_id,
    )


def delete_profile(kind: str, profile_id: str) -> None:
    root = _root()
    state = _kind_state(kind)
    items = [
        item
        for item in state["items"]
        if isinstance(item, dict) and item.get("id") != profile_id
    ]
    state["items"] = items
    if state.get("active_id") == profile_id:
        state["active_id"] = str(items[0]["id"]) if items else ""
    root[kind] = state
    _write_root(root)


def ensure_named_profile(kind: str, name: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    current = active_profile(kind)
    if current is not None:
        return upsert_profile(
            kind,
            name=str(current.get("name") or name),
            fields=fields,
            profile_id=str(current["id"]),
        )
    return create_profile(kind, name, fields)

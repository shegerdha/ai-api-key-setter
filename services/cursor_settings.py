"""Apply OpenAI-compatible gateway settings to Cursor's state.vscdb."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from services.cursor_safestorage import (
    decrypt_secret_cell,
    try_encrypt_secret,
)

APPLICATION_USER_KEY = (
    "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl."
    "persistentStorage.applicationUser"
)
CURSOR_AUTH_OPENAI_KEY = "cursorAuth/openAIKey"
CURSOR_AUTH_OPENAI_KEY_SECRET = "secret://cursorAuth/openAIKey"
BACKUP_SUFFIX = ".bak.ai-api-key-setter"
CURSOR_MODES = (
    "composer",
    "cmd-k",
    "background-composer",
    "composer-ensemble",
    "plan-execution",
    "spec",
    "deep-search",
    "quick-agent",
)


def cursor_user_dir() -> Path:
    appdata = Path(os.environ.get("APPDATA", ""))
    return appdata / "Cursor"


def state_db_path() -> Path:
    return cursor_user_dir() / "User" / "globalStorage" / "state.vscdb"


def local_state_path() -> Path:
    return cursor_user_dir() / "Local State"


def backup_db_path() -> Path:
    db = state_db_path()
    return db.parent / f"{db.name}{BACKUP_SUFFIX}"


def cursor_appears_running() -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Cursor.exe", "/NH"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    output = (result.stdout or "") + (result.stderr or "")
    return "Cursor.exe" in output


def _dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=2)
    conn.execute("PRAGMA busy_timeout=2000")
    return conn


def _read_item(conn: sqlite3.Connection, key: str) -> Optional[str]:
    row = conn.execute("SELECT value FROM ItemTable WHERE key = ?", (key,)).fetchone()
    if not row or row[0] is None:
        return None
    value = row[0]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _write_item(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO ItemTable(key, value) VALUES(?, ?)",
        (key, value),
    )


def read_application_user() -> Dict[str, Any]:
    db = state_db_path()
    if not db.exists():
        return {}
    conn = _connect(db)
    try:
        raw = _read_item(conn, APPLICATION_USER_KEY)
    finally:
        conn.close()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def read_openai_key() -> str:
    db = state_db_path()
    if not db.exists():
        return ""
    conn = _connect(db)
    try:
        secret_raw = _read_item(conn, CURSOR_AUTH_OPENAI_KEY_SECRET)
        legacy = _read_item(conn, CURSOR_AUTH_OPENAI_KEY) or ""
    finally:
        conn.close()
    if secret_raw:
        decrypted = decrypt_secret_cell(secret_raw, local_state_path())
        if decrypted:
            return decrypted
    return legacy


def patch_application_user(
    blob: Dict[str, Any],
    *,
    base_url: str,
    model_id: str,
    extra_models: Iterable[str],
) -> Dict[str, Any]:
    next_blob = dict(blob)
    next_blob["openAIBaseUrl"] = base_url
    next_blob["useOpenAIKey"] = True
    ai = dict(next_blob.get("aiSettings") or {})
    models = _dedupe([model_id, *list(extra_models)])
    user_added = _dedupe([*(ai.get("userAddedModels") or []), *models])
    enabled = _dedupe([*(ai.get("modelOverrideEnabled") or []), *models])
    disabled = [
        item
        for item in (ai.get("modelOverrideDisabled") or [])
        if item not in models
    ]
    config = dict(ai.get("modelConfig") or {})
    for mode in CURSOR_MODES:
        prev = dict(config.get(mode) or {})
        config[mode] = {
            **prev,
            "modelName": model_id,
            "selectedModels": [{"modelId": model_id, "parameters": []}],
        }
    ai["userAddedModels"] = user_added
    ai["modelOverrideEnabled"] = enabled
    ai["modelOverrideDisabled"] = disabled
    ai["modelConfig"] = config
    next_blob["aiSettings"] = ai
    return next_blob


def apply_cursor_gateway(
    *,
    token: str,
    base_url_v1: str,
    model_id: str,
    extra_models: Optional[Iterable[str]] = None,
) -> List[str]:
    logs: List[str] = []
    if cursor_appears_running():
        raise ValueError("ابتدا Cursor را کاملاً ببندید، سپس دوباره ذخیره کنید. Reload کافی نیست.")
    db = state_db_path()
    if not db.exists():
        raise ValueError("پایگاه Cursor یافت نشد. یک‌بار Cursor را باز کنید و سپس کاملاً ببندید.")

    encrypted, _enc_error = try_encrypt_secret(token, local_state_path())
    if not encrypted or decrypt_secret_cell(encrypted, local_state_path()) != token:
        raise ValueError("رمزنگاری کلید Cursor تأیید نشد؛ تنظیمات تغییر نکرد. گزارش رمزنگاری را بررسی کنید.")

    backup = backup_db_path()
    conn = _connect(db)
    try:
        shutil.copy2(db, backup)
        logs.append(f"backup → {backup}")
        conn.execute("BEGIN IMMEDIATE")
        raw = _read_item(conn, APPLICATION_USER_KEY) or "{}"
        try:
            blob = json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError("تنظیمات فعلی Cursor معتبر نیست؛ برای جلوگیری از حذف آن‌ها ذخیره متوقف شد.") from None
        if not isinstance(blob, dict):
            raise ValueError("ساختار تنظیمات Cursor معتبر نیست.")
        patched = patch_application_user(
            blob,
            base_url=base_url_v1,
            model_id=model_id,
            extra_models=extra_models or (),
        )
        compact = json.dumps(patched, ensure_ascii=False, separators=(",", ":"))
        _write_item(conn, APPLICATION_USER_KEY, compact)
        _write_item(conn, CURSOR_AUTH_OPENAI_KEY_SECRET, encrypted)
        conn.execute("DELETE FROM ItemTable WHERE key = ?", (CURSOR_AUTH_OPENAI_KEY,))
        if cursor_appears_running():
            raise ValueError("Cursor هنگام ذخیره باز شد؛ آن را ببندید و دوباره تلاش کنید.")
        if (_read_item(conn, APPLICATION_USER_KEY) != compact or
                _read_item(conn, CURSOR_AUTH_OPENAI_KEY_SECRET) != encrypted):
            raise ValueError("بازخوانی تنظیمات ذخیره‌شده تأیید نشد.")
        conn.commit()
        logs.append("کلید رمزنگاری‌شده ذخیره و بازخوانی شد.")
        try:
            conn.execute("PRAGMA wal_checkpoint(FULL)")
        except sqlite3.Error:
            pass
        logs.append(f"applicationUser به‌روز شد → {db}")
        logs.append(f"مدل ثبت‌شده در picker: {model_id}")
        extras = _dedupe(extra_models or ())
        if extras:
            logs.append("مدل‌های اضافه: " + ", ".join(extras))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return logs


def current_cursor_summary() -> Tuple[str, str, List[str]]:
    blob = read_application_user()
    base = str(blob.get("openAIBaseUrl") or "")
    ai = blob.get("aiSettings") if isinstance(blob.get("aiSettings"), dict) else {}
    models = [
        str(item)
        for item in (ai.get("userAddedModels") or [])
        if item
    ]
    config = ai.get("modelConfig") if isinstance(ai.get("modelConfig"), dict) else {}
    composer = config.get("composer") if isinstance(config.get("composer"), dict) else {}
    model_id = str(composer.get("modelName") or "")
    return base, model_id, models

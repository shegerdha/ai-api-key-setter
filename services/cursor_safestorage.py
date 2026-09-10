"""Encrypt Cursor OpenAI key the same way Electron safeStorage does on Windows."""

from __future__ import annotations

import base64
import json
import os
import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Optional, Tuple

DPAPI_PREFIX = b"DPAPI"
WIN_VERSION = b"v10"
WIN_NONCE_LEN = 12
WIN_KEY_LEN = 32


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _crypt_unprotect(data: bytes) -> bytes:
    blob_in = DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
    blob_out = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    ):
        raise OSError("CryptUnprotectData failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def load_os_crypt_key(local_state_path: Path) -> bytes:
    raw = local_state_path.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    enc_key_b64 = (parsed.get("os_crypt") or {}).get("encrypted_key")
    if not enc_key_b64 or not isinstance(enc_key_b64, str):
        raise ValueError("Local State کلید os_crypt ندارد.")
    enc_key = base64.b64decode(enc_key_b64)
    if not enc_key.startswith(DPAPI_PREFIX):
        prefix = enc_key[:5].decode("latin1", errors="replace")
        raise ValueError(
            f"پیشوند کلید OSCrypt «{prefix}» است (انتظار DPAPI). "
            "App-Bound Encryption پشتیبانی نمی‌شود."
        )
    key = _crypt_unprotect(enc_key[len(DPAPI_PREFIX) :])
    if len(key) != WIN_KEY_LEN:
        raise ValueError(f"طول کلید OSCrypt نامعتبر است: {len(key)}")
    return key


def encrypt_secret_cell(plaintext: str, local_state_path: Path) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key32 = load_os_crypt_key(local_state_path)
    nonce = os.urandom(WIN_NONCE_LEN)
    ciphertext_and_tag = AESGCM(key32).encrypt(
        nonce, plaintext.encode("utf-8"), None
    )
    blob = WIN_VERSION + nonce + ciphertext_and_tag
    return json.dumps({"type": "Buffer", "data": list(blob)}, separators=(",", ":"))


def decrypt_secret_cell(stored: str, local_state_path: Path) -> str:
    if not stored:
        return ""
    try:
        parsed = json.loads(stored)
    except json.JSONDecodeError:
        return stored
    if isinstance(parsed, dict) and parsed.get("type") == "Buffer":
        data = parsed.get("data") or []
        blob = bytes(int(b) for b in data)
    elif isinstance(stored, str) and not stored.startswith("{"):
        return stored
    else:
        return ""
    if not blob.startswith(WIN_VERSION) or len(blob) < 3 + WIN_NONCE_LEN + 16:
        return ""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key32 = load_os_crypt_key(local_state_path)
        nonce = blob[3 : 3 + WIN_NONCE_LEN]
        rest = blob[3 + WIN_NONCE_LEN :]
        return AESGCM(key32).decrypt(nonce, rest, None).decode("utf-8")
    except Exception:
        return ""


def try_encrypt_secret(plaintext: str, local_state_path: Path) -> Tuple[Optional[str], Optional[str]]:
    try:
        return encrypt_secret_cell(plaintext, local_state_path), None
    except Exception as exc:
        return None, str(exc)

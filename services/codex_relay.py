"""Install and manage codex-relay (Responses API -> Chat Completions bridge)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from services.codex_constants import DEFAULT_RELAY_PORT, normalize_gateway_v1
from services.codex_config import relay_base_url

RELAY_PROVIDER_ID = "ai-api-key-setter-relay"
CREATE_NO_WINDOW = 0x08000000


@dataclass
class RelayState:
    pid: int
    port: int
    upstream: str
    log_path: str


def relay_state_path() -> Path:
    return Path.home() / ".codex" / "ai-api-key-setter-relay.json"


def relay_log_path() -> Path:
    return Path.home() / ".codex" / "ai-api-key-setter-relay.log"


def _run(cmd: List[str], timeout: int = 120) -> Tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "زمان اجرای دستور به پایان رسید."
    except FileNotFoundError:
        return 1, "", f"دستور پیدا نشد: {cmd[0]}"


def _pip_cmd() -> List[str]:
    if getattr(sys, "frozen", False):
        py = shutil.which("python") or shutil.which("python3")
        if py:
            return [py, "-m", "pip"]
        return []
    return [sys.executable, "-m", "pip"]


def find_codex_relay_cmd() -> Optional[str]:
    found = shutil.which("codex-relay")
    if found:
        return found
    if getattr(sys, "frozen", False):
        py = shutil.which("python") or shutil.which("python3")
        if py:
            scripts = Path(py).resolve().parent / "Scripts" / "codex-relay.exe"
            if scripts.exists():
                return str(scripts)
    else:
        scripts = Path(sys.executable).resolve().parent / "Scripts" / "codex-relay.exe"
        if scripts.exists():
            return str(scripts)
    return None


def detect_codex_relay() -> Tuple[bool, Optional[str]]:
    cmd = find_codex_relay_cmd()
    if not cmd:
        return False, None
    code, stdout, stderr = _run([cmd, "--help"], timeout=20)
    if code == 0 or "codex-relay" in (stdout + stderr).lower():
        return True, cmd
    return bool(cmd), cmd


def install_codex_relay() -> Tuple[bool, str]:
    pip = _pip_cmd()
    if not pip:
        return False, "Python/pip برای نصب codex-relay پیدا نشد."
    code, stdout, stderr = _run([*pip, "install", "codex-relay"], timeout=180)
    output = "\n".join(part for part in (stdout, stderr) if part)
    if code != 0:
        return False, output or "نصب codex-relay ناموفق بود."
    ok, cmd = detect_codex_relay()
    if ok and cmd:
        return True, f"codex-relay نصب شد.\nمسیر: {cmd}"
    return False, output or "نصب انجام شد ولی codex-relay در PATH پیدا نشد."


def read_relay_state() -> Optional[RelayState]:
    path = relay_state_path()
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return RelayState(
            pid=int(data["pid"]),
            port=int(data.get("port", DEFAULT_RELAY_PORT)),
            upstream=str(data["upstream"]),
            log_path=str(data.get("log_path", str(relay_log_path()))),
        )
    except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
        return None


def write_relay_state(state: RelayState) -> None:
    path = relay_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": state.pid,
        "port": state.port,
        "upstream": state.upstream,
        "log_path": state.log_path,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def clear_relay_state() -> None:
    path = relay_state_path()
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == STILL_ACTIVE
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _relay_health_ok(port: int, timeout: float = 2.0) -> bool:
    url = f"http://127.0.0.1:{port}/v1/models"
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 500
    except urllib.error.HTTPError as exc:
        return exc.code < 500
    except (urllib.error.URLError, OSError):
        return False


def stop_relay() -> None:
    state = read_relay_state()
    if not state:
        return
    if _pid_alive(state.pid):
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(state.pid), "/F"],
                    capture_output=True,
                    timeout=10,
                    shell=False,
                )
            else:
                os.kill(state.pid, 15)
        except OSError:
            pass
    clear_relay_state()


def start_relay(upstream_v1: str, api_key: str, port: int = DEFAULT_RELAY_PORT) -> Tuple[bool, str]:
    upstream = normalize_gateway_v1(upstream_v1)
    ok, cmd = detect_codex_relay()
    if not ok or not cmd:
        install_ok, install_msg = install_codex_relay()
        if not install_ok:
            return False, install_msg
        ok, cmd = detect_codex_relay()
        if not ok or not cmd:
            return False, "codex-relay بعد از نصب پیدا نشد."

    log_path = relay_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("a", encoding="utf-8")
    log_file.write(f"\n--- start relay upstream={upstream} port={port} ---\n")
    log_file.flush()

    env = os.environ.copy()
    env["CODEX_RELAY_UPSTREAM"] = upstream
    env["CODEX_RELAY_API_KEY"] = api_key
    env["CODEX_RELAY_PORT"] = str(port)
    env["RUST_LOG"] = env.get("RUST_LOG", "codex_relay=info")

    popen_kwargs: dict = {
        "env": env,
        "stdout": log_file,
        "stderr": subprocess.STDOUT,
        "shell": False,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = CREATE_NO_WINDOW

    try:
        proc = subprocess.Popen([cmd], **popen_kwargs)
    except OSError as exc:
        log_file.close()
        return False, str(exc)

    for _ in range(30):
        if proc.poll() is not None:
            log_file.close()
            return False, (
                f"codex-relay زود بسته شد (exit={proc.returncode}).\n"
                f"لاگ: {log_path}"
            )
        if _relay_health_ok(port):
            write_relay_state(
                RelayState(
                    pid=proc.pid,
                    port=port,
                    upstream=upstream,
                    log_path=str(log_path),
                )
            )
            return True, (
                f"codex-relay فعال شد.\n"
                f"محلی: {relay_base_url(port)}\n"
                f"upstream: {upstream}\n"
                f"PID: {proc.pid}"
            )
        time.sleep(0.5)

    proc.terminate()
    log_file.close()
    return False, f"codex-relay در {port} پاسخ نداد. لاگ: {log_path}"


def ensure_relay_running(upstream_v1: str, api_key: str, port: int = DEFAULT_RELAY_PORT) -> Tuple[bool, str]:
    upstream = normalize_gateway_v1(upstream_v1)
    state = read_relay_state()
    if state and state.upstream == upstream and state.port == port:
        if _pid_alive(state.pid) and _relay_health_ok(port):
            return True, (
                f"codex-relay از قبل فعال است (PID {state.pid}, پورت {port})."
            )

    stop_relay()
    return start_relay(upstream, api_key, port)


def relay_status_text() -> str:
    state = read_relay_state()
    if not state:
        return "codex-relay: غیرفعال"
    alive = _pid_alive(state.pid)
    healthy = _relay_health_ok(state.port) if alive else False
    if alive and healthy:
        return f"codex-relay: فعال — {relay_base_url(state.port)} → {state.upstream}"
    if alive:
        return f"codex-relay: در حال اجرا ولی پاسخ نمی‌دهد (PID {state.pid})"
    return "codex-relay: متوقف شده (PID قدیمی)"


def fetch_relay_print_config(
    upstream_v1: str,
    api_key: str,
    port: int = DEFAULT_RELAY_PORT,
) -> Optional[str]:
    """Ask codex-relay for a config snippet with model_properties."""
    ok, cmd = detect_codex_relay()
    if not ok or not cmd:
        return None
    upstream = normalize_gateway_v1(upstream_v1)
    code, stdout, stderr = _run(
        [
            cmd,
            "--print-config",
            "--upstream",
            upstream,
            "--api-key",
            api_key,
            "--port",
            str(port),
        ],
        timeout=45,
    )
    if code == 0 and stdout.strip():
        return stdout.strip()
    return None

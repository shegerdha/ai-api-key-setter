"""Claude Code npm global install and detection."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class ClaudeInstallInfo:
    installed: bool
    version: Optional[str]
    shim_path: Optional[str]
    binary_path: Optional[str]
    npm_global_root: Optional[str]


def _npm_candidate_dirs() -> List[Path]:
    dirs: List[Path] = []
    for raw in (
        os.environ.get("APPDATA", ""),
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("LOCALAPPDATA", ""),
    ):
        if not raw:
            continue
        base = Path(raw)
        dirs.extend(
            [
                base / "npm",
                base / "nodejs",
                base / "Programs" / "nodejs",
            ]
        )
    seen: set[str] = set()
    unique: List[Path] = []
    for path in dirs:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def find_npm_cmd() -> Optional[str]:
    for name in ("npm.cmd", "npm"):
        found = shutil.which(name)
        if found:
            return found
    for directory in _npm_candidate_dirs():
        candidate = directory / "npm.cmd"
        if candidate.exists():
            return str(candidate)
        candidate = directory / "npm"
        if candidate.exists():
            return str(candidate)
    return None


def _augmented_env() -> dict[str, str]:
    env = dict(os.environ)
    extra: List[str] = []
    npm_cmd = find_npm_cmd()
    if npm_cmd:
        extra.append(str(Path(npm_cmd).parent))
    for directory in _npm_candidate_dirs():
        if directory.exists():
            extra.append(str(directory))
    if extra:
        current = env.get("PATH", "")
        prefix = ";".join(dict.fromkeys(extra))
        env["PATH"] = f"{prefix};{current}" if current else prefix
    return env


def _run(cmd: List[str], timeout: int = 300, env: dict[str, str] | None = None) -> Tuple[int, str, str]:
    run_env = env if env is not None else _augmented_env()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            encoding="utf-8",
            errors="replace",
            env=run_env,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "زمان اجرای دستور به پایان رسید."
    except FileNotFoundError:
        label = cmd[0] if cmd else "دستور"
        if label.lower().endswith("npm") or label.lower() == "npm.cmd":
            hint = find_npm_cmd()
            if hint:
                return 1, "", f"دستور پیدا نشد: {label} (مسیر شناخته‌شده: {hint})"
            return (
                1,
                "",
                "npm پیدا نشد. Node.js را از https://nodejs.org نصب کنید و برنامه را دوباره باز کنید.",
            )
        return 1, "", f"دستور پیدا نشد: {label}"


def _npm_cmd_or_error() -> tuple[Optional[str], str]:
    npm = find_npm_cmd()
    if npm:
        return npm, ""
    return None, (
        "npm پیدا نشد. Node.js را نصب کنید یا ترمینال را ببندید و برنامه را "
        "از همان محیطی که `npm -v` کار می‌کند دوباره اجرا کنید."
    )


def _run_npm(args: List[str], timeout: int = 300) -> Tuple[int, str, str]:
    npm, error = _npm_cmd_or_error()
    if not npm:
        return 1, "", error
    return _run([npm, *args], timeout=timeout)


def find_claude_shim() -> Optional[Path]:
    found = shutil.which("claude")
    if found:
        return Path(found)
    npm_dir = Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd"
    if npm_dir.exists():
        return npm_dir
    return None


def claude_binary_path() -> Optional[Path]:
    shim = find_claude_shim()
    if not shim:
        return None
    npm_root = Path(os.environ.get("APPDATA", "")) / "npm"
    candidate = npm_root / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
    if candidate.exists():
        return candidate
    return shim


def detect_installation() -> ClaudeInstallInfo:
    shim = find_claude_shim()
    binary = claude_binary_path()
    version: Optional[str] = None

    if binary and Path(binary).exists():
        code, stdout, stderr = _run([str(binary), "--version"])
        if code == 0 and stdout:
            version = stdout
        elif stderr:
            version = stderr

    if not version and shim:
        code, stdout, stderr = _run([str(shim), "--version"])
        if code == 0 and stdout:
            version = stdout
        elif stderr and "پیدا نشد" not in stderr:
            version = stderr

    npm_root = None
    code2, out2, _ = _run_npm(["root", "-g"])
    if code2 == 0:
        npm_root = out2

    installed = (binary is not None and Path(binary).exists()) or shim is not None
    if installed and not version:
        version = "نصب شده (نسخه قابل‌خواندن نیست)"

    return ClaudeInstallInfo(
        installed=installed,
        version=version,
        shim_path=str(shim) if shim else None,
        binary_path=str(binary) if binary else None,
        npm_global_root=npm_root,
    )


def install_claude_code(version: Optional[str] = None) -> Tuple[bool, str]:
    spec = "@anthropic-ai/claude-code"
    if version and version.strip():
        spec = f"@anthropic-ai/claude-code@{version.strip()}"
    code, stdout, stderr = _run_npm(["install", "-g", spec], timeout=600)
    output = "\n".join(part for part in (stdout, stderr) if part)
    if code != 0:
        return False, output or "نصب npm با خطا مواجه شد."
    info = detect_installation()
    if info.installed:
        return True, f"نصب موفق.\nنسخه: {info.version}\nمسیر: {info.binary_path or info.shim_path}"
    return False, output or "نصب انجام شد ولی claude در PATH پیدا نشد."


@dataclass
class CodexInstallInfo:
    installed: bool
    version: Optional[str]
    shim_path: Optional[str]
    binary_path: Optional[str]
    npm_global_root: Optional[str]


def find_codex_shim() -> Optional[Path]:
    found = shutil.which("codex")
    if found:
        return Path(found)
    npm_dir = Path(os.environ.get("APPDATA", "")) / "npm" / "codex.cmd"
    if npm_dir.exists():
        return npm_dir
    return None


def codex_binary_path() -> Optional[Path]:
    shim = find_codex_shim()
    if not shim:
        return None
    npm_root = Path(os.environ.get("APPDATA", "")) / "npm"
    candidate = npm_root / "node_modules" / "@openai" / "codex" / "bin" / "codex.exe"
    if candidate.exists():
        return candidate
    candidate2 = npm_root / "node_modules" / "@openai" / "codex" / "dist" / "cli.js"
    if candidate2.exists():
        return shim
    return shim


def detect_codex_installation() -> CodexInstallInfo:
    shim = find_codex_shim()
    binary = codex_binary_path()
    version: Optional[str] = None

    probe = binary if binary and Path(binary).exists() else shim
    if probe:
        code, stdout, stderr = _run([str(probe), "--version"])
        if code == 0 and stdout:
            version = stdout
        elif stderr and "پیدا نشد" not in stderr:
            version = stderr

    npm_root = None
    code2, out2, _ = _run_npm(["root", "-g"])
    if code2 == 0:
        npm_root = out2

    installed = shim is not None
    if installed and not version:
        version = "نصب شده (نسخه قابل‌خواندن نیست)"

    return CodexInstallInfo(
        installed=installed,
        version=version,
        shim_path=str(shim) if shim else None,
        binary_path=str(binary) if binary else None,
        npm_global_root=npm_root,
    )


def codex_needs_legacy_pin(version: Optional[str]) -> bool:
    if not version:
        return True
    return "0.92" not in version


def install_codex(version: Optional[str] = None) -> Tuple[bool, str]:
    spec = "@openai/codex"
    if version and version.strip():
        spec = f"@openai/codex@{version.strip()}"
    code, stdout, stderr = _run_npm(["install", "-g", spec], timeout=600)
    output = "\n".join(part for part in (stdout, stderr) if part)
    if code != 0:
        return False, output or "نصب npm با خطا مواجه شد."
    info = detect_codex_installation()
    if info.installed:
        return True, f"نصب موفق.\nنسخه: {info.version}\nمسیر: {info.binary_path or info.shim_path}"
    return False, output or "نصب انجام شد ولی codex در PATH پیدا نشد."

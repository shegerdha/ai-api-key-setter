"""Launch Claude Code in user-selected terminal as interactive coach."""

from __future__ import annotations

import os
import subprocess
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from services.npm_installer import (
    claude_binary_path,
    codex_binary_path,
    find_claude_shim,
    find_codex_shim,
)

# Windows Terminal از «;» برای جدا کردن subcommand استفاده می‌کند —
# پس هرگز inline -Command با ; به wt ندهید؛ فقط -File script.ps1


class TerminalKind(Enum):
    POWERSHELL = "powershell"
    CMD = "cmd"
    CUSTOM = "custom"


def _npm_path_prefix() -> str:
    npm_bin = Path(os.environ.get("APPDATA", "")) / "npm"
    if npm_bin.exists():
        return str(npm_bin)
    return ""


def _augment_path_env(env: Dict[str, str]) -> Dict[str, str]:
    merged = dict(env)
    npm_bin = _npm_path_prefix()
    if npm_bin:
        current = os.environ.get("PATH", "")
        merged["PATH"] = f"{npm_bin};{current}"
    return merged


def resolve_claude_command() -> tuple[str, bool]:
    binary = claude_binary_path()
    if binary and Path(binary).exists():
        return str(Path(binary).resolve()), True
    shim = find_claude_shim()
    if shim and Path(shim).exists():
        return "claude", True
    return "claude", False


def _ps_quote(value: str) -> str:
    return value.replace("`", "``").replace('"', '`"')


def coach_script_path() -> Path:
    path = Path.home() / ".claude" / "ai-api-key-setter-coach.ps1"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_coach_script(
    env: Dict[str, str],
    working_dir: Optional[str] = None,
) -> Path:
    """اسکریپت coach — بدون ; در argv ترمینال."""
    cwd = str(Path(working_dir or Path.home()).resolve())
    claude_cmd, claude_ok = resolve_claude_command()
    if not claude_ok:
        raise FileNotFoundError(
            "claude پیدا نشد. ابتدا Claude Code را نصب کنید یا npm global را بررسی کنید."
        )

    env = _augment_path_env(env)
    lines = [
        "# ai-api-key-setter coach script",
        "$ErrorActionPreference = 'Stop'",
    ]

    npm_bin = _npm_path_prefix()
    if npm_bin:
        lines.append(f'$env:PATH = "{_ps_quote(npm_bin)};$env:PATH"')

    for key, value in env.items():
        if key == "PATH":
            lines.append(f'$env:PATH = "{_ps_quote(value)}"')
        else:
            lines.append(f'$env:{key} = "{_ps_quote(value)}"')

    lines.append(f'Set-Location -LiteralPath "{_ps_quote(cwd)}"')
    lines.append('Write-Host "--- اعمال و اجرای Claude Code ---" -ForegroundColor Cyan')

    if claude_cmd == "claude":
        lines.append("claude")
    else:
        lines.append(f'& "{_ps_quote(claude_cmd)}"')

    script = coach_script_path()
    script.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return script


def _is_windows_terminal(path: str) -> bool:
    name = Path(path).name.lower()
    return name in ("wt.exe", "windowsterminal.exe")


def build_launch_command(
    env: Dict[str, str],
    terminal: TerminalKind,
    custom_terminal: Optional[str] = None,
    working_dir: Optional[str] = None,
) -> tuple[list[str], str, bool]:
    """Return (cmd argv, preview text, use_new_console)."""
    script = write_coach_script(env, working_dir)
    cwd = str(Path(working_dir or Path.home()).resolve())
    script_str = str(script)

    if terminal == TerminalKind.CMD:
        inner = f'powershell.exe -NoExit -File "{script_str}"'
        preview = inner
        return ["cmd.exe", "/k", inner], preview, True

    ps_args = ["powershell.exe", "-NoExit", "-File", script_str]
    preview = f'powershell -NoExit -File "{script_str}"'

    if terminal == TerminalKind.CUSTOM:
        if not custom_terminal:
            raise FileNotFoundError("مسیر ترمینال اختصاصی را وارد کنید.")
        wt_path = Path(custom_terminal).expanduser().resolve()
        if not wt_path.exists():
            raise FileNotFoundError(f"مسیر ترمینال اختصاصی معتبر نیست:\n{wt_path}")

        if _is_windows_terminal(str(wt_path)):
            # فقط یک new-tab — بدون ; در argv
            args = [
                str(wt_path),
                "new-tab",
                "--title",
                "اعمال Claude Code",
                "-d",
                cwd,
                "powershell.exe",
                "-NoExit",
                "-File",
                script_str,
            ]
            preview = (
                f'"{wt_path}" new-tab --title "اعمال Claude Code" -d "{cwd}" '
                f'powershell -NoExit -File "{script_str}"'
            )
            return args, preview, False

        args = ps_args
        preview = f'ترمینال سفارشی + {preview}'
        return args, preview, False

    return ps_args, preview, True


def launch_claude_interactive(
    env: Dict[str, str],
    terminal: TerminalKind,
    custom_terminal: Optional[str] = None,
    working_dir: Optional[str] = None,
) -> tuple[bool, str]:
    return _launch_interactive(
        env=env,
        terminal=terminal,
        custom_terminal=custom_terminal,
        working_dir=working_dir,
        write_script=write_coach_script,
        script_label="Claude Code",
        tab_title="اعمال Claude Code",
    )


def codex_coach_script_path() -> Path:
    path = Path.home() / ".codex" / "ai-api-key-setter-coach.ps1"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def resolve_codex_command() -> tuple[str, bool]:
    binary = codex_binary_path()
    if binary and Path(binary).exists():
        resolved = Path(binary).resolve()
        if resolved.suffix.lower() in (".exe", ".cmd", ".bat"):
            return str(resolved), True
        return "codex", True
    shim = find_codex_shim()
    if shim and Path(shim).exists():
        return "codex", True
    return "codex", False


def write_codex_coach_script(
    env: Dict[str, str],
    working_dir: Optional[str] = None,
) -> Path:
    cwd = str(Path(working_dir or Path.home()).resolve())
    codex_cmd, codex_ok = resolve_codex_command()
    if not codex_ok:
        raise FileNotFoundError(
            "codex پیدا نشد. ابتدا Codex را نصب کنید یا npm global را بررسی کنید."
        )

    env = _augment_path_env(env)
    lines = [
        "# ai-api-key-setter codex coach script",
        "$ErrorActionPreference = 'Stop'",
    ]

    npm_bin = _npm_path_prefix()
    if npm_bin:
        lines.append(f'$env:PATH = "{_ps_quote(npm_bin)};$env:PATH"')

    for key, value in env.items():
        if key == "PATH":
            lines.append(f'$env:PATH = "{_ps_quote(value)}"')
        else:
            lines.append(f'$env:{key} = "{_ps_quote(value)}"')

    lines.append(f'Set-Location -LiteralPath "{_ps_quote(cwd)}"')
    lines.append('Write-Host "--- اعمال و اجرای Codex ---" -ForegroundColor Cyan')

    if codex_cmd == "codex":
        lines.append("codex")
    else:
        lines.append(f'& "{_ps_quote(codex_cmd)}"')

    script = codex_coach_script_path()
    script.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return script


def build_codex_launch_command(
    env: Dict[str, str],
    terminal: TerminalKind,
    custom_terminal: Optional[str] = None,
    working_dir: Optional[str] = None,
) -> tuple[list[str], str, bool]:
    script = write_codex_coach_script(env, working_dir)
    cwd = str(Path(working_dir or Path.home()).resolve())
    script_str = str(script)

    if terminal == TerminalKind.CMD:
        inner = f'powershell.exe -NoExit -File "{script_str}"'
        preview = inner
        return ["cmd.exe", "/k", inner], preview, True

    ps_args = ["powershell.exe", "-NoExit", "-File", script_str]
    preview = f'powershell -NoExit -File "{script_str}"'

    if terminal == TerminalKind.CUSTOM:
        if not custom_terminal:
            raise FileNotFoundError("مسیر ترمینال اختصاصی را وارد کنید.")
        wt_path = Path(custom_terminal).expanduser().resolve()
        if not wt_path.exists():
            raise FileNotFoundError(f"مسیر ترمینال اختصاصی معتبر نیست:\n{wt_path}")

        if _is_windows_terminal(str(wt_path)):
            args = [
                str(wt_path),
                "new-tab",
                "--title",
                "اعمال Codex",
                "-d",
                cwd,
                "powershell.exe",
                "-NoExit",
                "-File",
                script_str,
            ]
            preview = (
                f'"{wt_path}" new-tab --title "اعمال Codex" -d "{cwd}" '
                f'powershell -NoExit -File "{script_str}"'
            )
            return args, preview, False

        return ps_args, f"ترمینال سفارشی + {preview}", False

    return ps_args, preview, True


def launch_codex_interactive(
    env: Dict[str, str],
    terminal: TerminalKind,
    custom_terminal: Optional[str] = None,
    working_dir: Optional[str] = None,
) -> tuple[bool, str]:
    return _launch_interactive(
        env=env,
        terminal=terminal,
        custom_terminal=custom_terminal,
        working_dir=working_dir,
        write_script=write_codex_coach_script,
        script_label="Codex",
        tab_title="اعمال Codex",
        build_command=build_codex_launch_command,
    )


def _launch_interactive(
    env: Dict[str, str],
    terminal: TerminalKind,
    custom_terminal: Optional[str],
    working_dir: Optional[str],
    write_script,
    script_label: str,
    tab_title: str,
    build_command=None,
) -> tuple[bool, str]:
    try:
        if build_command is None:
            cmd, preview, use_new_console = build_launch_command(
                env, terminal, custom_terminal, working_dir
            )
            script_path = coach_script_path()
        else:
            cmd, preview, use_new_console = build_command(
                env, terminal, custom_terminal, working_dir
            )
            script_path = write_script(env, working_dir)
    except FileNotFoundError as exc:
        return False, str(exc)

    popen_kwargs: dict = {
        "cwd": working_dir or str(Path.home()),
        "shell": False,
    }
    if use_new_console:
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE

    try:
        subprocess.Popen(cmd, **popen_kwargs)
        return True, (
            f"ترمینال باز شد (یک تب).\n"
            f"اسکریپت: {script_path}\n\n"
            f"دستور:\n{preview}"
        )
    except OSError as exc:
        return False, str(exc)

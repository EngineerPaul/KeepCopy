"""Автозапуск Windows: ярлык в папке Startup."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from services.path_utils import get_app_dir, get_app_executable, is_compiled_app

SHORTCUT_NAME = "Archiver.lnk"
BACKGROUND_ARG = "--background"
_STARTUP_REL = Path("Microsoft") / "Windows" / "Start Menu" / "Programs" / "Startup"


def is_windows() -> bool:
    """True на Windows."""
    return sys.platform == "win32"


def get_startup_folder() -> Path:
    """
    Папка автозагрузки текущего пользователя.

    Путь одинаков на Windows 7–11; в проводнике может отображаться как «Автозагрузка».
    """
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise OSError("Переменная APPDATA не задана")
    return Path(appdata) / _STARTUP_REL


def shortcut_path() -> Path:
    """Полный путь к ярлыку автозапуска."""
    return get_startup_folder() / SHORTCUT_NAME


def is_autostart_enabled() -> bool:
    """Есть ли ярлык автозапуска в папке Startup."""
    if not is_windows():
        return False
    return shortcut_path().is_file()


def get_launch_spec() -> tuple[Path, str, Path]:
    """
    Цель ярлыка: исполняемый файл, аргументы, рабочая папка.

    Скомпилированный exe: Archiver.exe --background
    Разработка: pythonw.exe "main.py" --background
    """
    work_dir = get_app_dir()
    if is_compiled_app():
        return get_app_executable(), BACKGROUND_ARG, work_dir

    python_dir = Path(sys.executable).parent
    pythonw = python_dir / "pythonw.exe"
    launcher = pythonw if pythonw.is_file() else Path(sys.executable)
    main_py = work_dir / "main.py"
    arguments = f'"{main_py}" {BACKGROUND_ARG}'
    return launcher, arguments, work_dir


def _ps_escape(value: str) -> str:
    return value.replace("'", "''")


def _create_shortcut(lnk: Path, target: Path, arguments: str, work_dir: Path) -> None:
    lnk.parent.mkdir(parents=True, exist_ok=True)
    script = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{_ps_escape(str(lnk))}')
$s.TargetPath = '{_ps_escape(str(target))}'
$s.Arguments = '{_ps_escape(arguments)}'
$s.WorkingDirectory = '{_ps_escape(str(work_dir))}'
$s.WindowStyle = 7
$s.Description = 'Архиватор'
$s.Save()
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def enable_autostart() -> None:
    """Создаёт ярлык с запуском в фоне (--background)."""
    if not is_windows():
        return
    target, arguments, work_dir = get_launch_spec()
    _create_shortcut(shortcut_path(), target, arguments, work_dir)


def disable_autostart() -> None:
    """Удаляет ярлык автозапуска."""
    if not is_windows():
        return
    path = shortcut_path()
    if path.is_file():
        path.unlink()


def apply_autostart(enabled: bool) -> None:
    """Включает или выключает автозапуск."""
    if enabled:
        enable_autostart()
    else:
        disable_autostart()


def sync_autostart(enabled: bool) -> None:
    """Приводит ярлык в соответствие с настройкой."""
    if not is_windows():
        return
    if enabled:
        enable_autostart()
    elif is_autostart_enabled():
        disable_autostart()


def reconcile_autostart(storage) -> None:
    """При старте сверяет галочку в settings.json с ярлыком в Startup."""
    if not is_windows():
        return
    settings = storage.get_settings()
    enabled = settings.autostart
    present = is_autostart_enabled()
    if enabled == present:
        if enabled:
            enable_autostart()
        return
    sync_autostart(enabled)

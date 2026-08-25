"""Вспомогательные функции для работы с путями и валидации."""

from __future__ import annotations

import os
import re
from datetime import date, datetime, time
from pathlib import Path
from typing import Optional

# Разрешённые символы в путях Windows (без запрещённых <>:"|?*)
_PATH_CHARS_RE = re.compile(r'^[\w\s\.\-\+\(\)\[\]@#$%&!~`\'{},;=]+$')
# Для фильтров дополнительно разрешены * и /
_FILTER_CHARS_RE = re.compile(r'^[\w\s\.\-\+\(\)\[\]@#$%&!~`\'{},;=*\\/]+$')


def is_compiled_app() -> bool:
    """True для PyInstaller, Nuitka и других упакованных сборок."""
    import sys

    if getattr(sys, "frozen", False):
        return True
    if "__compiled__" in globals():
        return True
    argv0 = Path(getattr(sys, "argv", [""])[0] or "")
    return (
        argv0.suffix.lower() == ".exe"
        and argv0.name.lower() not in ("python.exe", "pythonw.exe")
    )


def get_app_executable() -> Path:
    """Путь к исполняемому файлу приложения (exe или python)."""
    import sys

    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    argv0 = Path(sys.argv[0])
    if (
        argv0.suffix.lower() == ".exe"
        and argv0.name.lower() not in ("python.exe", "pythonw.exe")
    ):
        return argv0.resolve()
    return Path(sys.executable)


def get_app_dir() -> Path:
    """Возвращает директорию приложения (рядом с main.py или exe)."""
    if is_compiled_app():
        return get_app_executable().parent
    return Path(__file__).resolve().parent.parent


def normalize_path(path: str) -> str:
    """Нормализует слэши и приводит путь к виду ОС."""
    normalized = path.strip().replace("/", os.sep).replace("\\", os.sep)
    return os.path.normpath(normalized)


def is_absolute_drive_path(path: str) -> bool:
    """Проверяет абсолютный путь с буквой диска (Windows: C:\\...)."""
    normalized = normalize_path(path)
    if os.name == "nt":
        if len(normalized) < 3:
            return False
        return (
            normalized[0].isalpha()
            and normalized[1] == ":"
            and normalized[2] in (os.sep, "/")
        )
    return os.path.isabs(normalized)


def to_long_path(path: str | Path) -> str:
    """Добавляет префикс \\\\?\\ для длинных путей Windows (>260 символов)."""
    p = str(path)
    if os.name != "nt":
        return p
    if p.startswith("\\\\?\\"):
        return p
    abs_p = os.path.abspath(p)
    if len(abs_p) > 260 and not abs_p.startswith("\\\\"):
        return "\\\\?\\" + abs_p
    return abs_p


def validate_path(path: str) -> tuple[bool, str]:
    """
    Проверяет путь на допустимые символы и абсолютность.

    Returns:
        (успех, сообщение об ошибке)
    """
    if not path or not path.strip():
        return False, "Путь не может быть пустым"
    normalized = normalize_path(path)
    if not is_absolute_drive_path(normalized):
        return False, "Укажите полный путь с буквой диска (например, C:\\)"
    if os.name == "nt":
        # Двоеточие допустимо только в букве диска (C:)
        path_body = normalized
        if len(normalized) >= 2 and normalized[1] == ":":
            path_body = normalized[2:]
        if re.search(r'[<>:"|?*]', path_body):
            return False, "Путь содержит недопустимые символы"
    parts = normalized.replace("\\\\?\\", "").split(os.sep)
    for part in parts:
        if part and not _PATH_CHARS_RE.match(part) and part not in (".", ".."):
            if ":" in part and len(part) <= 3:
                continue
            return False, f"Недопустимые символы в компоненте: {part}"
    return True, ""


def validate_directory_path(path: str) -> tuple[bool, str]:
    """Проверяет, что путь существует и является каталогом."""
    ok, err = validate_path(path)
    if not ok:
        return ok, err
    normalized = normalize_path(path)
    long_path = to_long_path(normalized)
    if os.path.isfile(long_path):
        return False, "Укажите папку, а не файл"
    if not os.path.isdir(long_path):
        return False, "Папка назначения не существует"
    return True, ""


def validate_filter(pattern: str) -> tuple[bool, str]:
    """Проверяет шаблон исключения на допустимые символы."""
    if not pattern or not pattern.strip():
        return False, "Фильтр не может быть пустым"
    normalized = pattern.strip().replace("/", os.sep).replace("\\", os.sep)
    if not _FILTER_CHARS_RE.match(normalized.replace(os.sep, "/")):
        return False, "Фильтр содержит недопустимые символы"
    return True, ""


def path_exists(path: str) -> bool:
    """Проверяет существование пути с поддержкой длинных путей."""
    return os.path.exists(to_long_path(path))


def is_path_nested_in(inner: str, outer: str) -> bool:
    """
    Проверяет, что inner полностью вложен в outer.

    Файл-источник не может содержать другие пути.
    """
    inner_n = normalize_path(inner)
    outer_n = normalize_path(outer)
    if os.path.normcase(inner_n) == os.path.normcase(outer_n):
        return False
    if os.path.isfile(to_long_path(outer_n)):
        return False
    outer_n = outer_n.rstrip("\\/")
    inner_case = os.path.normcase(inner_n)
    outer_case = os.path.normcase(outer_n)
    return inner_case == outer_case or inner_case.startswith(outer_case + os.sep)


def find_nested_source_indices(sources: list[str]) -> list[int]:
    """Возвращает индексы источников, вложенных в другой источник списка."""
    nested: list[int] = []
    for i, inner in enumerate(sources):
        for j, outer in enumerate(sources):
            if i == j:
                continue
            if is_path_nested_in(inner, outer):
                nested.append(i)
                break
    return nested


def has_nested_sources(sources: list[str]) -> bool:
    """True, если среди источников есть полностью вложенные пути."""
    return bool(find_nested_source_indices(sources))


def open_in_explorer(path: str) -> tuple[bool, str]:
    """
    Открывает путь в проводнике Windows поверх других окон.

    Returns:
        (успех, сообщение об ошибке)
    """
    normalized = normalize_path(path)
    if not normalized:
        return False, "Путь не указан"
    long_path = to_long_path(normalized)
    if not os.path.exists(long_path):
        return False, "Путь не существует"

    try:
        if os.name == "nt":
            _open_in_explorer_windows(long_path)
        else:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices

            QDesktopServices.openUrl(QUrl.fromLocalFile(long_path))
        return True, ""
    except OSError as exc:
        return False, str(exc)


def _open_in_explorer_windows(path: str) -> None:
    """Открывает проводник Windows и выводит его на передний план."""
    import ctypes
    import threading
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32

    SW_SHOWNORMAL = 1

    def _explorer_hwnds() -> list[int]:
        hwnds: list[int] = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def callback(hwnd, _lparam):
            if user32.IsWindowVisible(hwnd):
                cls = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, cls, 256)
                if cls.value in ("CabinetWClass", "ExploreWClass"):
                    hwnds.append(hwnd)
            return True

        user32.EnumWindows(callback, 0)
        return hwnds

    def _bring_explorer_to_front(before: set[int]) -> None:
        user32.AllowSetForegroundWindow(ctypes.c_uint(0xFFFFFFFF))
        hwnds = _explorer_hwnds()
        new_hwnds = [h for h in hwnds if h not in before]
        target = new_hwnds[-1] if new_hwnds else (hwnds[-1] if hwnds else None)
        if target:
            user32.SetForegroundWindow(target)
            user32.SwitchToThisWindow(target, True)

    norm = os.path.normpath(path)
    before = set(_explorer_hwnds())
    user32.AllowSetForegroundWindow(ctypes.c_uint(0xFFFFFFFF))

    if os.path.isfile(path):
        params = f'/separate,/select,"{norm}"'
        result = shell32.ShellExecuteW(
            None, "open", "explorer.exe", params, None, SW_SHOWNORMAL
        )
    else:
        params = f'/separate,"{norm}"'
        result = shell32.ShellExecuteW(
            None, "open", "explorer.exe", params, None, SW_SHOWNORMAL
        )

    if result <= 32:
        raise OSError(f"Не удалось запустить проводник (код {result})")

    threading.Timer(0.15, _bring_explorer_to_front, args=(before,)).start()


def source_folder_name(source: str) -> str:
    """Возвращает имя подпапки или ZIP для источника.

    Для папки — имя этой папки (последний компонент пути).
    Для файла — имя родительской папки с суффиксом «_files».
    """
    normalized = normalize_path(source)
    if os.path.isfile(normalized):
        parent = os.path.dirname(normalized)
        parent_name = os.path.basename(parent)
        if parent_name:
            return f"{parent_name}_files"
        return os.path.basename(normalized)
    return os.path.basename(normalized.rstrip(os.sep))


def parse_time_str(value: Optional[str]) -> Optional[time]:
    """Парсит строку времени HH:MM."""
    if not value:
        return None
    parts = value.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        h, m = int(parts[0]), int(parts[1])
        if 0 <= h <= 23 and 0 <= m <= 59:
            return time(h, m)
    except ValueError:
        pass
    return None


def format_time(t: Optional[time]) -> str:
    """Форматирует время в HH:MM."""
    if t is None:
        return ""
    return f"{t.hour:02d}:{t.minute:02d}"


def parse_datetime_str(value: Optional[str]) -> Optional[datetime]:
    """Парсит ISO datetime строку."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_date_str(value: Optional[str]) -> Optional[date]:
    """Парсит ISO date строку."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def format_datetime(dt: Optional[datetime]) -> str:
    """Форматирует datetime для отображения."""
    if dt is None:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")


def format_date(d: Optional[date]) -> str:
    """Форматирует date для отображения."""
    if d is None:
        return ""
    return d.strftime("%d.%m.%Y")


def format_size(size_bytes: int) -> str:
    """Форматирует размер в человекочитаемый вид."""
    if size_bytes < 0:
        return "—"
    units = ["Б", "КБ", "МБ", "ГБ", "ТБ"]
    size = float(size_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "Б":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} ТБ"


def backup_layer_name(run_date: date, suffix: int) -> str:
    """Формирует имя слоя backup_DD.MM.YYYY_NNN."""
    return f"backup_{run_date.strftime('%d.%m.%Y')}_{suffix:03d}"


def errors_file_name(run_date: date, suffix: int) -> str:
    """Формирует имя файла ошибок errors_DD.MM.YYYY_NNN."""
    return f"errors_{run_date.strftime('%d.%m.%Y')}_{suffix:03d}"

"""Загрузка и сохранение данных в settings.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.app_settings import AppSettings
from models.task import Task
from services.path_utils import get_app_dir


def normalize_size_entry(raw: Any) -> dict[str, Any]:
    """Приводит запись кэша к {total: int, sources: {path: int}}."""
    if isinstance(raw, bool):
        return {"total": -1, "sources": {}}
    if isinstance(raw, int):
        return {"total": raw, "sources": {}}
    if not isinstance(raw, dict):
        return {"total": -1, "sources": {}}
    sources: dict[str, int] = {}
    sources_raw = raw.get("sources", {})
    if isinstance(sources_raw, dict):
        for key, value in sources_raw.items():
            try:
                sources[str(key)] = int(value)
            except (TypeError, ValueError):
                continue
    total_raw = raw.get("total", sum(sources.values()) if sources else -1)
    try:
        total = int(total_raw)
    except (TypeError, ValueError):
        total = sum(sources.values()) if sources else -1
    return {"total": total, "sources": sources}


class StorageService:
    """Сервис хранения данных приложения в JSON."""

    def __init__(self, path: Path | None = None) -> None:
        """
        Инициализирует сервис хранения.

        Args:
            path: Путь к файлу настроек (по умолчанию settings.json рядом с приложением).
        """
        self._path = path or (get_app_dir() / "settings.json")
        self._data: dict[str, Any] = {
            "tasks": [],
            "settings": {},
            "size_cache": {},
        }

    @property
    def path(self) -> Path:
        """Путь к файлу настроек."""
        return self._path

    def load(self) -> None:
        """Загружает данные из JSON-файла."""
        if not self._path.exists():
            self._data = {"tasks": [], "settings": {}, "size_cache": {}}
            return
        with open(self._path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        self._data = {
            "tasks": loaded.get("tasks", []),
            "settings": loaded.get("settings", {}),
            "size_cache": loaded.get("size_cache", {}),
        }

    def save(self) -> None:
        """Сохраняет данные в JSON-файл."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get_tasks(self) -> list[Task]:
        """Возвращает список задач."""
        return [Task.from_dict(t) for t in self._data.get("tasks", [])]

    def set_tasks(self, tasks: list[Task]) -> None:
        """Сохраняет список задач."""
        self._data["tasks"] = [t.to_dict() for t in tasks]

    def get_settings(self) -> AppSettings:
        """Возвращает настройки приложения."""
        return AppSettings.from_dict(self._data.get("settings", {}))

    def set_settings(self, settings: AppSettings) -> None:
        """Сохраняет настройки приложения."""
        self._data["settings"] = settings.to_dict()

    def get_size_cache(self) -> dict[str, dict[str, Any]]:
        """Возвращает кэш размеров {task_id: {total, sources}}."""
        raw = self._data.get("size_cache", {})
        if not isinstance(raw, dict):
            return {}
        return {
            str(task_id): normalize_size_entry(entry)
            for task_id, entry in raw.items()
        }

    def set_size_cache(self, cache: dict[str, Any]) -> None:
        """Сохраняет кэш размеров задач."""
        self._data["size_cache"] = {
            str(task_id): normalize_size_entry(entry)
            for task_id, entry in cache.items()
        }

    def update_task_size(
        self,
        task_id: str,
        size: int,
        sources: dict[str, int] | None = None,
    ) -> None:
        """Обновляет кэшированный размер задачи (сумма и по источникам)."""
        cache = self._data.setdefault("size_cache", {})
        cache[task_id] = {
            "total": int(size),
            "sources": {str(k): int(v) for k, v in (sources or {}).items()},
        }

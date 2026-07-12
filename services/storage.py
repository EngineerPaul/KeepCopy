"""Загрузка и сохранение данных в settings.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.app_settings import AppSettings
from models.task import Task
from services.path_utils import get_app_dir


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

    def get_size_cache(self) -> dict[str, int]:
        """Возвращает кэш размеров задач {task_id: bytes}."""
        return dict(self._data.get("size_cache", {}))

    def set_size_cache(self, cache: dict[str, int]) -> None:
        """Сохраняет кэш размеров задач."""
        self._data["size_cache"] = cache

    def update_task_size(self, task_id: str, size: int) -> None:
        """Обновляет кэшированный размер одной задачи."""
        cache = self.get_size_cache()
        cache[task_id] = size
        self.set_size_cache(cache)

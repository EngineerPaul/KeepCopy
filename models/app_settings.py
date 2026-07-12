"""Модель настроек приложения."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# Порядок колонок таблицы задач (фиксированный)
COLUMN_KEYS = [
    "name",
    "description",
    "sources",
    "destination",
    "schedule_time",
    "period_days",
    "exclusions",
    "total_size",
    "last_run",
    "next_run",
    "copy_mode",
    "compress",
    "actions",
]

COLUMN_LABELS = {
    "name": "Название",
    "description": "Описание",
    "sources": "Источники",
    "destination": "Архив",
    "schedule_time": "Время",
    "period_days": "Период.",
    "exclusions": "Исключения",
    "total_size": "Размер",
    "last_run": "Послед.вып.",
    "next_run": "След.вып.",
    "copy_mode": "Режим копирования",
    "compress": "Сжатие",
    "actions": "Действия",
}

DEFAULT_VISIBLE_COLUMNS = {k: True for k in COLUMN_KEYS}
DEFAULT_VISIBLE_COLUMNS["description"] = False
DEFAULT_VISIBLE_COLUMNS["exclusions"] = False

ROW_NUM_COLUMN_WIDTH = 30
TABLE_WIDTH_EXTRA = 0  # вертикальная полоса прокрутки и рамка таблицы
DEFAULT_WINDOW_HEIGHT = 600


def round_width_up(value: int, step: int = 5) -> int:
    """Округляет ширину вверх с заданным шагом."""
    return math.ceil(value / step) * step


# Ширины колонок по умолчанию (округлены вверх с шагом 5 px).
DEFAULT_COLUMN_WIDTHS: dict[str, int] = {
    "name": 150,
    "description": 120,
    "sources": 305,
    "destination": 160,
    "schedule_time": 60,
    "period_days": 65,
    "exclusions": 120,
    "total_size": 80,
    "last_run": 115,
    "next_run": 95,
    "copy_mode": 145,
    "compress": 65,
    "actions": 90,
}


def compute_table_columns_width(
    visible_columns: dict[str, bool] | None = None,
    column_widths: dict[str, int] | None = None,
    *,
    row_num_width: int = ROW_NUM_COLUMN_WIDTH,
) -> int:
    """Суммарная ширина видимых колонок таблицы (включая №)."""
    vis = visible_columns or DEFAULT_VISIBLE_COLUMNS
    widths = column_widths or DEFAULT_COLUMN_WIDTHS
    total = row_num_width
    for key in COLUMN_KEYS:
        if vis.get(key, True):
            total += widths.get(key, DEFAULT_COLUMN_WIDTHS.get(key, 120))
    return total


def compute_default_window_width(
    visible_columns: dict[str, bool] | None = None,
    column_widths: dict[str, int] | None = None,
    *,
    row_num_width: int = ROW_NUM_COLUMN_WIDTH,
) -> int:
    """Ширина окна по умолчанию, чтобы все колонки помещались без горизонтальной прокрутки."""
    content = compute_table_columns_width(visible_columns, column_widths, row_num_width=row_num_width)
    return round_width_up(content + TABLE_WIDTH_EXTRA, 5)


DEFAULT_WINDOW_WIDTH = compute_default_window_width()


@dataclass
class AppSettings:
    """Глобальные настройки приложения."""

    theme: str = "light"
    font_size: int = 12
    visible_columns: dict[str, bool] = field(default_factory=lambda: dict(DEFAULT_VISIBLE_COLUMNS))
    column_widths: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_COLUMN_WIDTHS))
    autostart: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Сериализует настройки в словарь."""
        return {
            "theme": self.theme,
            "font_size": self.font_size,
            "visible_columns": self.visible_columns,
            "column_widths": self.column_widths,
            "autostart": self.autostart,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        """Десериализует настройки из словаря."""
        visible = dict(DEFAULT_VISIBLE_COLUMNS)
        visible.update(data.get("visible_columns", {}))
        visible["actions"] = True
        widths = dict(DEFAULT_COLUMN_WIDTHS)
        widths.update(data.get("column_widths", {}))
        return cls(
            theme=data.get("theme", "light"),
            font_size=data.get("font_size", 12),
            visible_columns=visible,
            column_widths=widths,
            autostart=data.get("autostart", False),
        )

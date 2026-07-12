"""Модель задачи резервного копирования."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Any, Optional
import uuid

from services.path_utils import format_time, parse_date_str, parse_time_str


class CopyMode(str, Enum):
    """Режим копирования файлов."""

    KEEP_CHANGES = "keep_changes"
    LAYERED = "layered"
    DUPLICATE = "duplicate"

    @property
    def label(self) -> str:
        """Человекочитаемое название режима."""
        return {
            CopyMode.KEEP_CHANGES: "Сохранять изменения",
            CopyMode.LAYERED: "Сохранять слоями",
            CopyMode.DUPLICATE: "Дублирование",
        }[self]

    @classmethod
    def from_value(cls, value: str) -> "CopyMode":
        """Создаёт режим из строкового значения."""
        return cls(value)


@dataclass
class Task:
    """Задача резервного копирования."""

    id: str
    name: str
    description: str = ""
    sources: list[str] = field(default_factory=list)
    destination: str = ""
    schedule_time: Optional[time] = None
    period_days: Optional[int] = 7
    exclusions: list[str] = field(default_factory=list)
    max_size_mb: Optional[float] = None
    compress: bool = False
    copy_mode: CopyMode = CopyMode.KEEP_CHANGES
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    last_auto_run: Optional[datetime] = None
    next_run: Optional[date] = None
    errors_counter: int = 0

    @classmethod
    def create_default(cls, name: str) -> "Task":
        """Создаёт новую задачу с параметрами по умолчанию."""
        now = datetime.now()
        task = cls(
            id=str(uuid.uuid4()),
            name=name,
            schedule_time=time(0, 0),
            period_days=7,
            is_active=True,
            created_at=now,
        )
        task.next_run = now.date() + timedelta(days=task.period_days)
        return task

    def has_schedule(self) -> bool:
        """Проверяет, заданы ли периодичность и время."""
        return self.schedule_time is not None and self.period_days is not None

    def to_dict(self) -> dict[str, Any]:
        """Сериализует задачу в словарь для JSON."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "sources": self.sources,
            "destination": self.destination,
            "schedule_time": format_time(self.schedule_time),
            "period_days": self.period_days,
            "exclusions": self.exclusions,
            "max_size_mb": self.max_size_mb,
            "compress": self.compress,
            "copy_mode": (
                self.copy_mode.value
                if isinstance(self.copy_mode, CopyMode)
                else CopyMode.from_value(str(self.copy_mode)).value
            ),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_auto_run": (
                self.last_auto_run.isoformat() if self.last_auto_run else None
            ),
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "errors_counter": self.errors_counter,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Десериализует задачу из словаря JSON."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            sources=data.get("sources", []),
            destination=data.get("destination", ""),
            schedule_time=parse_time_str(data.get("schedule_time")),
            period_days=data.get("period_days"),
            exclusions=data.get("exclusions", []),
            max_size_mb=data.get("max_size_mb"),
            compress=data.get("compress", False),
            copy_mode=CopyMode.from_value(data.get("copy_mode", "keep_changes")),
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_run=datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None,
            last_auto_run=(
                datetime.fromisoformat(data["last_auto_run"])
                if data.get("last_auto_run")
                else None
            ),
            next_run=parse_date_str(data.get("next_run")),
            errors_counter=data.get("errors_counter", 0),
        )

    def copy_mode_label(self) -> str:
        """Возвращает название режима копирования."""
        return self.copy_mode.label

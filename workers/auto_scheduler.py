"""Таймер планировщика автоматических запусков."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer

from models.task import Task
from services.scheduler import SchedulerService


class AutoScheduler(QObject):
    """Планировщик автоматических и догоняющих запусков."""

    def __init__(
        self,
        get_tasks: Callable[[], list[Task]],
        on_run: Callable[[list[Task]], None],
        parent: QObject | None = None,
    ) -> None:
        """
        Инициализирует планировщик.

        Args:
            get_tasks: Функция получения актуального списка задач.
            on_run: Callback для запуска задач (automatic=True).
        """
        super().__init__(parent)
        self._get_tasks = get_tasks
        self._on_run = on_run
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_schedule)
        self._catchup_timer = QTimer(self)
        self._catchup_timer.setSingleShot(True)
        self._catchup_timer.timeout.connect(self._run_catchup)
        self._catchup_pending: list[Task] = []

    def start(self) -> None:
        """Запускает планировщик."""
        self._timer.start(30_000)  # проверка каждые 30 сек
        self._schedule_catchup()

    def stop(self) -> None:
        """Останавливает планировщик."""
        self._timer.stop()
        self._catchup_timer.stop()

    def _schedule_catchup(self) -> None:
        """Планирует догоняющий запуск через 5 минут после старта."""
        due = [
            t for t in self._get_tasks()
            if SchedulerService.needs_catchup(t)
        ]
        if due:
            self._catchup_pending = due
            self._catchup_timer.start(5 * 60 * 1000)

    def _run_catchup(self) -> None:
        """Выполняет догоняющий запуск пропущенных задач."""
        if self._catchup_pending:
            self._on_run(self._catchup_pending)
            self._catchup_pending = []

    def _check_schedule(self) -> None:
        """Проверяет расписание и запускает задачи."""
        now = datetime.now()
        due = [
            t for t in self._get_tasks()
            if t.is_active and SchedulerService.is_due(t, now)
        ]
        if due:
            self._on_run(due)

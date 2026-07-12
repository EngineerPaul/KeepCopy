"""Расчёт расписания и планировщик задач."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional

from models.task import Task


class SchedulerService:
    """Сервис расчёта дат следующего выполнения."""

    @staticmethod
    def compute_next_run(
        current_next: Optional[date],
        period_days: int,
        reference_date: Optional[date] = None,
    ) -> date:
        """
        Вычисляет следующую дату выполнения по формуле 5.3.

        Args:
            current_next: Текущее значение След.вып.
            period_days: Периодичность в днях.
            reference_date: Базовая дата (если current_next отсутствует).

        Returns:
            Новая дата След.вып.
        """
        today = date.today()
        base = current_next or reference_date or today
        diff = (today - base).days
        if diff < 0:
            return base
        periods = (diff // period_days) + 1
        return base + timedelta(days=periods * period_days)

    @staticmethod
    def initial_next_run(created_at: datetime, period_days: int) -> date:
        """
        Вычисляет След.вып. при создании задачи.

        Первый запуск не в день создания.
        """
        return created_at.date() + timedelta(days=period_days)

    @staticmethod
    def scheduled_datetime(task: Task) -> Optional[datetime]:
        """Объединяет След.вып. и время задачи."""
        if task.next_run is None or task.schedule_time is None:
            return None
        return datetime.combine(task.next_run, task.schedule_time)

    @staticmethod
    def is_due(task: Task, now: Optional[datetime] = None) -> bool:
        """Проверяет, наступило ли время автоматического запуска."""
        if not task.is_active or not task.has_schedule() or task.next_run is None:
            return False
        now = now or datetime.now()
        scheduled = SchedulerService.scheduled_datetime(task)
        return scheduled is not None and now >= scheduled

    @staticmethod
    def needs_catchup(task: Task, now: Optional[datetime] = None) -> bool:
        """Проверяет, пропущен ли запланированный запуск."""
        return SchedulerService.is_due(task, now)

    @staticmethod
    def update_after_auto_run(task: Task) -> None:
        """Обновляет След.вып. после автоматического запуска."""
        if task.period_days is None:
            return
        task.next_run = SchedulerService.compute_next_run(
            task.next_run, task.period_days
        )

    @staticmethod
    def recalc_on_activate(task: Task) -> None:
        """Пересчитывает След.вып. при активации задачи."""
        if not task.has_schedule():
            task.next_run = None
            return
        ref = task.next_run
        if ref is None:
            if task.last_run:
                ref = task.last_run.date()
            else:
                ref = task.created_at.date()
        task.next_run = SchedulerService.compute_next_run(
            ref, task.period_days
        )

    @staticmethod
    def recalc_on_edit(task: Task) -> None:
        """Пересчитывает След.вып. при редактировании (если задано расписание)."""
        if not task.has_schedule():
            task.next_run = None
            task.is_active = False
            return
        ref = task.next_run
        if ref is None:
            if task.last_run:
                ref = task.last_run.date()
            else:
                ref = task.created_at.date()
        task.next_run = SchedulerService.compute_next_run(
            ref, task.period_days
        )

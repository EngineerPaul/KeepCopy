"""Фоновое выполнение резервного копирования."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from models.task import Task
from services.backup_engine import BackupEngine, BackupResult
from services.scheduler import SchedulerService


class BackupWorker(QThread):
    """Поток выполнения резервного копирования одной задачи."""

    progress = Signal(str, str, int, int)  # task_name, phase, current, total
    finished_backup = Signal(str, object)  # task_id, BackupResult
    error = Signal(str, str)

    def __init__(
        self,
        task: Task,
        automatic: bool = False,
        parent: QObject | None = None,
    ) -> None:
        """Инициализирует воркер копирования."""
        super().__init__(parent)
        self._task = task
        self._automatic = automatic
        self._engine = BackupEngine()

    def run(self) -> None:
        """Выполняет копирование."""
        try:
            total = len(self._task.sources)
            for i, source in enumerate(self._task.sources, 1):
                self.progress.emit(
                    self._task.name,
                    "копирование",
                    i,
                    total,
                )
            result = self._engine.run(self._task, automatic=self._automatic)
            if result.update_last_run:
                from datetime import datetime

                now = datetime.now()
                self._task.last_run = now
                if self._automatic:
                    self._task.last_auto_run = now
            if result.update_next_run:
                SchedulerService.update_after_auto_run(self._task)
            self.finished_backup.emit(self._task.id, result)
        except Exception as e:
            self.error.emit(self._task.id, str(e))

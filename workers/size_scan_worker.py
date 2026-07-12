"""Фоновый подсчёт размеров задач."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from models.task import Task
from services.backup_engine import BackupEngine


class SizeScanWorker(QThread):
    """Поток подсчёта размера одной задачи."""

    finished_scan = Signal(str, "qint64")  # task_id, size (bytes)
    error = Signal(str, str)

    def __init__(self, task: Task, parent: QObject | None = None) -> None:
        """Инициализирует воркер подсчёта."""
        super().__init__(parent)
        self._task = task
        self._engine = BackupEngine()

    def run(self) -> None:
        """Выполняет подсчёт размера."""
        try:
            size = self._engine.calculate_task_size(self._task)
            self.finished_scan.emit(self._task.id, size)
        except Exception as e:
            self.error.emit(self._task.id, str(e))

"""Фоновый подсчёт размеров задач."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from models.task import Task
from services.backup_engine import BackupEngine


class SizeScanWorker(QThread):
    """Поток подсчёта размера одной задачи."""

    # task_name, source_path, current, total
    progress = Signal(str, str, int, int)
    # task_id, {"total": int, "sources": {path: int}}
    finished_scan = Signal(str, object)
    error = Signal(str, str)

    def __init__(self, task: Task, parent: QObject | None = None) -> None:
        """Инициализирует воркер подсчёта."""
        super().__init__(parent)
        self._task = task
        self._engine = BackupEngine()

    def run(self) -> None:
        """Выполняет подсчёт размера."""
        try:
            def on_source(current: int, source: str, total: int) -> None:
                self.progress.emit(self._task.name, source, current, total)

            total, sources = self._engine.calculate_task_size(
                self._task, on_source=on_source
            )
            self.finished_scan.emit(
                self._task.id,
                {"total": total, "sources": sources},
            )
        except Exception as e:
            self.error.emit(self._task.id, str(e))

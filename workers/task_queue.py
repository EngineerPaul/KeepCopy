"""Менеджер очереди задач: подсчёт → копирование."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal

from models.task import Task
from services.backup_engine import BackupEngine, BackupResult
from services.scheduler import SchedulerService
from services.storage import StorageService
from workers.backup_worker import BackupWorker
from workers.size_scan_worker import SizeScanWorker


def _short_source(path: str, max_len: int = 72) -> str:
    """Сокращает длинный путь источника для строки статуса."""
    if len(path) <= max_len:
        return path
    return "…" + path[-(max_len - 1) :]


class TaskQueueManager(QObject):
    """Последовательное выполнение задач в фоне."""

    status_changed = Signal(str)
    task_size_updated = Signal(str, "qint64")
    task_finished = Signal(str, object)
    queue_finished = Signal()
    busy_changed = Signal(bool)

    def __init__(
        self,
        storage: StorageService,
        parent: QObject | None = None,
    ) -> None:
        """Инициализирует менеджер очереди."""
        super().__init__(parent)
        self._storage = storage
        self._queue: list[tuple[Task, bool]] = []
        self._busy = False
        self._current_scan: Optional[SizeScanWorker] = None
        self._current_backup: Optional[BackupWorker] = None
        self._engine = BackupEngine()
        self._on_tasks_changed: Optional[Callable[[], None]] = None

    def set_tasks_changed_callback(self, cb: Callable[[], None]) -> None:
        """Устанавливает callback при изменении задач."""
        self._on_tasks_changed = cb

    @property
    def is_busy(self) -> bool:
        """Занят ли менеджер выполнением."""
        return self._busy

    def enqueue(self, tasks: list[Task], automatic: bool = False) -> None:
        """
        Добавляет задачи в очередь.

        Args:
            tasks: Список задач.
            automatic: Автоматический запуск.
        """
        for task in tasks:
            self._queue.append((task, automatic))
        if not self._busy:
            self._process_next()

    def scan_task_size(self, task: Task) -> None:
        """Запускает подсчёт размера одной задачи."""
        worker = SizeScanWorker(task, self)
        worker.progress.connect(self._on_scan_progress)
        worker.finished_scan.connect(self._on_startup_scan_done)
        worker.start()

    def scan_all_sizes(self, tasks: list[Task]) -> None:
        """Запускает подсчёт размеров всех задач при старте."""
        self._startup_tasks = list(tasks)
        self._startup_index = 0
        if self._startup_tasks and not self._busy:
            self._scan_startup_next()

    def _scan_startup_next(self) -> None:
        """Подсчитывает размер следующей задачи при старте."""
        if self._startup_index >= len(self._startup_tasks):
            if not self._busy:
                self.status_changed.emit("")
            return
        task = self._startup_tasks[self._startup_index]
        self._startup_index += 1
        worker = SizeScanWorker(task, self)
        worker.progress.connect(self._on_scan_progress)
        worker.finished_scan.connect(self._on_startup_scan_done)
        worker.finished.connect(self._scan_startup_next)
        worker.start()

    def _on_startup_scan_done(self, task_id: str, size: int) -> None:
        """Обработчик завершения стартового подсчёта."""
        self._storage.update_task_size(task_id, size)
        self.task_size_updated.emit(task_id, size)

    def _set_busy(self, busy: bool) -> None:
        """Устанавливает флаг занятости."""
        self._busy = busy
        self.busy_changed.emit(busy)

    def _process_next(self) -> None:
        """Обрабатывает следующую задачу в очереди."""
        if not self._queue:
            self._set_busy(False)
            self.status_changed.emit("")
            self.queue_finished.emit()
            return

        self._set_busy(True)
        task, automatic = self._queue.pop(0)
        self._current_task = task
        self._current_automatic = automatic
        self._start_scan_for_backup(task)

    def _start_scan_for_backup(self, task: Task) -> None:
        """Запускает подсчёт перед копированием."""
        self._current_scan = SizeScanWorker(task, self)
        self._current_scan.progress.connect(self._on_scan_progress)
        self._current_scan.finished_scan.connect(self._on_pre_backup_scan)
        self._current_scan.error.connect(self._on_pre_backup_scan_error)
        self._current_scan.start()

    def _on_scan_progress(
        self, task_name: str, source: str, current: int, total: int
    ) -> None:
        """Обновляет статус подсчёта размера по текущему источнику."""
        self.status_changed.emit(
            f"Задача {task_name}: подсчёт — {_short_source(source)} "
            f"({current} из {total})"
        )

    def _on_pre_backup_scan_error(self, task_id: str, message: str) -> None:
        """Продолжает копирование, если подсчёт размера не удался."""
        self.status_changed.emit(
            f"Ошибка подсчёта: {message}. Запуск копирования..."
        )
        self._on_pre_backup_scan(task_id, 0)

    def _on_pre_backup_scan(self, task_id: str, size: int) -> None:
        """Обработчик подсчёта перед копированием."""
        self._storage.update_task_size(task_id, size)
        self.task_size_updated.emit(task_id, size)
        task = self._current_task
        self._current_backup = BackupWorker(
            task, automatic=self._current_automatic, parent=self
        )
        self._current_backup.progress.connect(self._on_backup_progress)
        self._current_backup.finished_backup.connect(self._on_backup_done)
        self._current_backup.error.connect(self._on_backup_error)
        self._current_backup.start()

    def _on_backup_progress(
        self,
        task_name: str,
        source: str,
        current: int,
        total: int,
        percent: int,
    ) -> None:
        """Обновляет статус копирования: источник и процент по объёму."""
        self.status_changed.emit(
            f"Задача {task_name}: копирование — {_short_source(source)} "
            f"({current} из {total}) — {percent}%"
        )

    def _on_backup_done(self, task_id: str, result: BackupResult) -> None:
        """Обработчик завершения копирования."""
        self._save_task_state()
        self.task_finished.emit(task_id, result)
        self._process_next()

    def _on_backup_error(self, task_id: str, message: str) -> None:
        """Обработчик ошибки копирования."""
        self._process_next()

    def _save_task_state(self) -> None:
        """Сохраняет состояние задач после выполнения."""
        if self._on_tasks_changed:
            self._on_tasks_changed()

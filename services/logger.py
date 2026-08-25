"""Логирование операций резервного копирования."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional

from models.task import Task
from services.path_utils import errors_file_name, get_app_dir


class BackupLogger:
    """Запись логов в backup.log и файлы ошибок."""

    MAX_LINES = 1000

    def __init__(self, log_path: Path | None = None, errors_dir: Path | None = None) -> None:
        """
        Инициализирует логгер.

        Args:
            log_path: Путь к файлу логов.
            errors_dir: Директория для файлов ошибок.
        """
        app_dir = get_app_dir()
        self._log_path = log_path or (app_dir / "backup.log")
        self._errors_dir = errors_dir or (app_dir / "errors")

    def _truncate_log(self) -> None:
        """Обрезает лог до MAX_LINES строк."""
        if not self._log_path.exists():
            return
        with open(self._log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > self.MAX_LINES:
            lines = lines[-self.MAX_LINES :]
            with open(self._log_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

    def _format_description(self, desc: str) -> str:
        """Обрезает описание до 100 символов."""
        if len(desc) <= 100:
            return desc
        return desc[:97] + "..."

    def log(
        self,
        task: Task,
        source: str,
        result: str,
    ) -> None:
        """
        Записывает строку лога.

        Args:
            task: Задача.
            source: Путь источника.
            result: Результат (успешно | ошибка | скопировано с ошибками ...).
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        desc = self._format_description(task.description or "")
        line = f"{now} | {task.name} | {source} | {desc} | {result}\n"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(line)
        self._truncate_log()

    def write_errors_file(
        self,
        task: Task,
        skipped_files: list[tuple[str, str]],
        run_date: date,
        suffix: int,
    ) -> str:
        """
        Создаёт файл ошибок для запуска задачи.

        Args:
            task: Задача.
            skipped_files: Список (путь, текст ошибки).
            run_date: Дата запуска.
            suffix: Номер файла ошибок.

        Returns:
            Имя созданного файла.
        """
        self._errors_dir.mkdir(parents=True, exist_ok=True)
        filename = errors_file_name(run_date, suffix)
        filepath = self._errors_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Задача: {task.name}\n")
            f.write(f"ID: {task.id}\n")
            f.write(f"Описание: {task.description}\n")
            f.write(f"Источники: {', '.join(task.sources)}\n")
            f.write(f"Назначение: {task.destination}\n")
            f.write(f"Режим: {task.copy_mode_label()}\n")
            f.write(f"Сжатие: {'да' if task.compress else 'нет'}\n")
            f.write("---\n")
            for path, error in skipped_files:
                f.write(f"{path} — {error}\n")
        return filename

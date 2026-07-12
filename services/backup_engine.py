"""Движок резервного копирования: подсчёт, проверка места, копирование."""

from __future__ import annotations

import os
import re
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from models.task import CopyMode, Task
from services.file_matcher import FileEntry, FileMatcher
from services.logger import BackupLogger
from services.path_utils import (
    backup_layer_name,
    normalize_path,
    source_folder_name,
    to_long_path,
)


class BackupResultKind(Enum):
    """Тип результата выполнения задачи."""

    SUCCESS = auto()
    PARTIAL = auto()
    DISK_FULL = auto()


@dataclass
class SourceBackupResult:
    """Результат копирования одного источника."""

    source: str
    kind: BackupResultKind
    skipped: list[tuple[str, str]] = field(default_factory=list)
    files_copied: int = 0


@dataclass
class BackupResult:
    """Результат выполнения всей задачи."""

    task_id: str
    source_results: list[SourceBackupResult] = field(default_factory=list)
    errors_file: Optional[str] = None
    update_last_run: bool = True
    update_next_run: bool = False

    @property
    def is_disk_full(self) -> bool:
        """True, если хотя бы один источник завершился из-за нехватки места."""
        return any(r.kind == BackupResultKind.DISK_FULL for r in self.source_results)

    @property
    def has_skipped(self) -> bool:
        """True, если были пропущенные файлы."""
        return any(r.skipped for r in self.source_results)

    @property
    def files_copied(self) -> int:
        """Число успешно скопированных файлов."""
        return sum(r.files_copied for r in self.source_results)


class BackupEngine:
    """Выполнение резервного копирования."""

    DISK_MARGIN = 1.10

    def __init__(self, logger: Optional[BackupLogger] = None) -> None:
        """
        Инициализирует движок.

        Args:
            logger: Логгер операций.
        """
        self.logger = logger or BackupLogger()

    def calculate_task_size(self, task: Task) -> int:
        """Подсчитывает общий размер файлов задачи для кэша."""
        matcher = FileMatcher(task)
        return matcher.calculate_size()

    def calculate_copy_size(self, task: Task) -> int:
        """Подсчитывает размер файлов для предстоящего копирования."""
        matcher = FileMatcher(task)
        return matcher.calculate_copy_size(task.last_run)

    def _get_free_space(self, path: str) -> int:
        """Возвращает свободное место на диске в байтах."""
        dest = normalize_path(path)
        if not os.path.exists(dest):
            dest = os.path.dirname(dest) or dest
        try:
            usage = shutil.disk_usage(to_long_path(dest))
            return usage.free
        except OSError:
            return 0

    def _next_layer_suffix(self, parent_dir: str, run_date: date, compress: bool) -> int:
        """Определяет следующий суффикс слоя backup_... в директории."""
        parent = Path(to_long_path(parent_dir))
        if not parent.exists():
            return 1
        date_part = run_date.strftime("%d.%m.%Y")
        pattern = re.compile(
            rf"^backup_{re.escape(date_part)}_(\d{{3}})(\.zip)?$"
        )
        max_suffix = 0
        for item in parent.iterdir():
            m = pattern.match(item.name)
            if m:
                max_suffix = max(max_suffix, int(m.group(1)))
        return max_suffix + 1

    def _next_errors_suffix(self, task: Task, run_date: date) -> int:
        """Определяет суффикс файла ошибок."""
        return task.errors_counter + 1

    def _ensure_dir(self, path: str) -> None:
        """Создаёт директорию при необходимости."""
        os.makedirs(to_long_path(path), exist_ok=True)

    def _copy_file(self, src: str, dst: str) -> None:
        """Копирует один файл без изменения источника."""
        dst_dir = os.path.dirname(dst)
        self._ensure_dir(dst_dir)
        shutil.copy2(to_long_path(src), to_long_path(dst))

    def _copy_entries_flat(
        self,
        entries: list[FileEntry],
        dest_root: str,
    ) -> list[tuple[str, str]]:
        """Копирует файлы в dest_root с сохранением структуры."""
        skipped: list[tuple[str, str]] = []
        dirs_done: set[str] = set()
        for entry in entries:
            if entry.is_dir:
                dst = os.path.join(dest_root, entry.relative_path)
                if dst not in dirs_done:
                    try:
                        self._ensure_dir(dst)
                        dirs_done.add(dst)
                    except OSError as e:
                        skipped.append((entry.absolute_path, str(e)))
                continue
            dst = os.path.join(dest_root, entry.relative_path)
            try:
                self._copy_file(entry.absolute_path, dst)
            except OSError as e:
                skipped.append((entry.absolute_path, str(e)))
        return skipped

    def _add_to_zip(
        self,
        zip_path: str,
        entries: list[FileEntry],
    ) -> list[tuple[str, str]]:
        """Добавляет файлы в zip-архив."""
        skipped: list[tuple[str, str]] = []
        mode = "a" if os.path.exists(to_long_path(zip_path)) else "w"
        try:
            with zipfile.ZipFile(
                to_long_path(zip_path), mode, compression=zipfile.ZIP_DEFLATED, compresslevel=5
            ) as zf:
                for entry in entries:
                    if entry.is_dir:
                        arcname = entry.relative_path.replace("\\", "/")
                        if arcname and not arcname.endswith("/"):
                            arcname += "/"
                        if arcname:
                            try:
                                zf.writestr(arcname, "")
                            except OSError as e:
                                skipped.append((entry.absolute_path, str(e)))
                        continue
                    arcname = entry.relative_path.replace("\\", "/")
                    try:
                        zf.write(to_long_path(entry.absolute_path), arcname)
                    except OSError as e:
                        skipped.append((entry.absolute_path, str(e)))
        except OSError as e:
            for entry in entries:
                if not entry.is_dir:
                    skipped.append((entry.absolute_path, str(e)))
            if not skipped:
                skipped.append((zip_path, str(e)))
        return skipped

    def _create_zip(
        self,
        zip_path: str,
        entries: list[FileEntry],
    ) -> list[tuple[str, str]]:
        """Создаёт новый zip-архив."""
        skipped: list[tuple[str, str]] = []
        try:
            with zipfile.ZipFile(
                to_long_path(zip_path), "w", compression=zipfile.ZIP_DEFLATED, compresslevel=5
            ) as zf:
                for entry in entries:
                    if entry.is_dir:
                        continue
                    arcname = entry.relative_path.replace("\\", "/")
                    try:
                        zf.write(to_long_path(entry.absolute_path), arcname)
                    except OSError as e:
                        skipped.append((entry.absolute_path, str(e)))
        except OSError as e:
            for entry in entries:
                if not entry.is_dir:
                    skipped.append((entry.absolute_path, str(e)))
        return skipped

    def _file_entries_only(self, entries: list[FileEntry]) -> list[FileEntry]:
        """Возвращает только файловые записи."""
        return [e for e in entries if not e.is_dir]

    def _has_files_to_copy(self, entries: list[FileEntry]) -> bool:
        """Проверяет наличие файлов для копирования."""
        return any(not e.is_dir for e in entries)

    def _dest_base(self, task: Task, source: str) -> str:
        """Базовая директория назначения для источника."""
        folder = source_folder_name(source)
        return os.path.join(normalize_path(task.destination), folder)

    def _copy_source(
        self,
        task: Task,
        source: str,
        entries: list[FileEntry],
        run_date: date,
    ) -> SourceBackupResult:
        """Копирует один источник согласно режиму задачи."""
        skipped: list[tuple[str, str]] = []
        files_copied = 0
        dest_base = self._dest_base(task, source)

        if task.copy_mode == CopyMode.KEEP_CHANGES:
            if not self._has_files_to_copy(entries):
                return SourceBackupResult(source, BackupResultKind.SUCCESS, [], 0)
            if task.compress:
                zip_path = dest_base + ".zip"
                skipped = self._add_to_zip(zip_path, entries)
            else:
                skipped = self._copy_entries_flat(entries, dest_base)
            files_copied = len(self._file_entries_only(entries)) - len(skipped)

        elif task.copy_mode in (CopyMode.LAYERED, CopyMode.DUPLICATE):
            if task.copy_mode == CopyMode.LAYERED and not self._has_files_to_copy(entries):
                return SourceBackupResult(source, BackupResultKind.SUCCESS, [], 0)

            suffix = self._next_layer_suffix(dest_base, run_date, task.compress)
            layer_name = backup_layer_name(run_date, suffix)

            if task.compress:
                zip_path = os.path.join(dest_base, f"{layer_name}.zip")
                file_entries = self._file_entries_only(entries)
                if file_entries or task.copy_mode == CopyMode.DUPLICATE:
                    skipped = self._create_zip(zip_path, entries)
                    files_copied = len(file_entries) - len(
                        [s for s in skipped if not s[0].endswith(".zip")]
                    )
            else:
                layer_path = os.path.join(dest_base, layer_name)
                skipped = self._copy_entries_flat(entries, layer_path)
                files_copied = len(self._file_entries_only(entries)) - len(skipped)
        else:
            return SourceBackupResult(source, BackupResultKind.SUCCESS, [], 0)

        kind = BackupResultKind.PARTIAL if skipped else BackupResultKind.SUCCESS
        return SourceBackupResult(source, kind, skipped, files_copied)

    def run(
        self,
        task: Task,
        *,
        automatic: bool = False,
        run_datetime: Optional[datetime] = None,
    ) -> BackupResult:
        """
        Выполняет резервное копирование задачи.

        Args:
            task: Задача.
            automatic: Автоматический запуск (обновляет След.вып.).
            run_datetime: Время запуска.

        Returns:
            Результат выполнения.
        """
        run_datetime = run_datetime or datetime.now()
        run_date = run_datetime.date()
        matcher = FileMatcher(task)
        copy_last_run = task.last_run
        if automatic and task.last_auto_run is None:
            copy_last_run = None
        if not automatic and task.copy_mode == CopyMode.KEEP_CHANGES:
            dest_bases = {s: self._dest_base(task, s) for s in task.sources}
            files_by_source = matcher.collect_for_copy(
                copy_last_run,
                manual=True,
                dest_bases=dest_bases,
            )
        else:
            files_by_source = matcher.collect_for_copy(copy_last_run)

        # Проверка места
        total_size = 0
        for source, entries in files_by_source.items():
            for e in entries:
                if not e.is_dir:
                    total_size += e.size

        required = int(total_size * self.DISK_MARGIN)
        free = self._get_free_space(task.destination)
        if total_size > 0 and free < required:
            results = [
                SourceBackupResult(s, BackupResultKind.DISK_FULL)
                for s in task.sources
            ]
            for src, res in zip(task.sources, results):
                self.logger.log(
                    task, src, "ошибка: недостаточно места на диске"
                )
            return BackupResult(
                task_id=task.id,
                source_results=results,
                update_last_run=False,
                update_next_run=automatic,
            )

        source_results: list[SourceBackupResult] = []
        all_skipped: list[tuple[str, str]] = []

        for source in task.sources:
            entries = files_by_source.get(source, [])
            result = self._copy_source(task, source, entries, run_date)
            source_results.append(result)
            all_skipped.extend(result.skipped)

        errors_file: Optional[str] = None
        if all_skipped:
            suffix = self._next_errors_suffix(task, run_date)
            errors_file = self.logger.write_errors_file(
                task, all_skipped, run_date, suffix
            )
            task.errors_counter = suffix

        # Логирование по источникам
        for res in source_results:
            if res.kind == BackupResultKind.DISK_FULL:
                continue
            if res.skipped:
                err_name = errors_file or ""
                self.logger.log(
                    task,
                    res.source,
                    f"скопировано с ошибками (файл {err_name})",
                )
            else:
                self.logger.log(task, res.source, "успешно")

        return BackupResult(
            task_id=task.id,
            source_results=source_results,
            errors_file=errors_file,
            update_last_run=True,
            update_next_run=automatic,
        )

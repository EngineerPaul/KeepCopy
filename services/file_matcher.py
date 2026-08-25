"""Сопоставление файлов с фильтрами-исключениями."""

from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterator, Optional

from pathspec import PathSpec

from models.task import CopyMode, Task
from services.path_utils import normalize_path, path_exists, to_long_path


@dataclass
class FileEntry:
    """Запись о файле для копирования."""

    source_root: str
    absolute_path: str
    relative_path: str
    size: int
    mtime: float
    is_dir: bool = False


class FileMatcher:
    """Поиск и фильтрация файлов задачи."""

    def __init__(self, task: Task) -> None:
        """
        Инициализирует сопоставитель для задачи.

        Args:
            task: Задача резервного копирования.
        """
        self.task = task
        self._spec = self._build_spec(task.exclusions)
        self._max_bytes = (
            int(task.max_size_mb * 1024 * 1024) if task.max_size_mb else None
        )
        # Индекс файлов в слоях: dest_base → set относительных путей.
        self._layer_file_index: dict[str, set[str]] = {}

    @staticmethod
    def _build_spec(exclusions: list[str]) -> Optional[PathSpec]:
        """Создаёт PathSpec из списка исключений."""
        if not exclusions:
            return None
        patterns = []
        for exc in exclusions:
            p = exc.replace("\\", "/").strip()
            if p:
                patterns.append(p)
        if not patterns:
            return None
        return PathSpec.from_lines("gitwildmatch", patterns)

    def is_excluded(self, relative_path: str, is_dir: bool = False) -> bool:
        """
        Проверяет, исключён ли путь.

        Args:
            relative_path: Относительный путь от корня источника.
            is_dir: Является ли путь директорией.
        """
        if self._spec is None:
            return False
        rel = relative_path.replace("\\", "/")
        if is_dir and not rel.endswith("/"):
            rel = rel + "/"
        return self._spec.match_file(rel)

    def _should_copy_by_date(self, mtime: float, last_run: Optional[datetime]) -> bool:
        """Проверяет, нужно ли копировать файл по дате изменения."""
        if self.task.copy_mode == CopyMode.DUPLICATE:
            return True
        if last_run is None:
            return True
        return mtime > last_run.timestamp()

    def _is_missing_in_destination(self, entry: FileEntry, dest_base: str) -> bool:
        """Проверяет отсутствие файла в назначении (по относительному пути)."""
        if entry.is_dir:
            return False
        rel = entry.relative_path.replace("\\", "/")
        if self.task.copy_mode == CopyMode.LAYERED:
            return rel not in self._layered_file_index(dest_base)
        if self.task.compress:
            zip_path = to_long_path(dest_base + ".zip")
            if not os.path.isfile(zip_path):
                return True
            with zipfile.ZipFile(zip_path, "r") as zf:
                return rel not in zf.namelist()
        dest = to_long_path(os.path.join(dest_base, entry.relative_path))
        return not os.path.isfile(dest)

    def _layered_file_index(self, dest_base: str) -> set[str]:
        """Множество относительных путей во всех слоях backup_* под dest_base."""
        cached = self._layer_file_index.get(dest_base)
        if cached is not None:
            return cached
        found: set[str] = set()
        base = to_long_path(dest_base)
        if os.path.isdir(base):
            for name in os.listdir(base):
                if not name.startswith("backup_"):
                    continue
                path = os.path.join(base, name)
                if name.endswith(".zip") and os.path.isfile(path):
                    try:
                        with zipfile.ZipFile(path, "r") as zf:
                            for arc in zf.namelist():
                                if arc.endswith("/"):
                                    continue
                                found.add(arc.replace("\\", "/"))
                    except OSError:
                        continue
                elif os.path.isdir(path):
                    for dirpath, _, filenames in os.walk(path):
                        for filename in filenames:
                            abs_file = os.path.join(dirpath, filename)
                            rel = os.path.relpath(abs_file, path).replace("\\", "/")
                            found.add(rel)
        self._layer_file_index[dest_base] = found
        return found

    def _collect_by_date_or_missing(
        self,
        source: str,
        last_run: Optional[datetime],
        dest_base: str,
    ) -> list[FileEntry]:
        """
        Файлы новее last_run или отсутствующие в назначении.

        Для keep_changes — dest_base / dest_base.zip.
        Для layered — любой предыдущий слой backup_* под dest_base.
        """
        entries: list[FileEntry] = []
        for entry in self.iter_entries(source, for_copy=False):
            if entry.is_dir:
                continue
            if self._should_copy_by_date(entry.mtime, last_run):
                entries.append(entry)
            elif self._is_missing_in_destination(entry, dest_base):
                entries.append(entry)
        return entries

    def _passes_size(self, size: int) -> bool:
        """Проверяет ограничение max size (> а не >=)."""
        if self._max_bytes is None:
            return True
        return size <= self._max_bytes

    def iter_entries(
        self,
        source: str,
        for_copy: bool = False,
        last_run: Optional[datetime] = None,
    ) -> Iterator[FileEntry]:
        """
        Итерирует файлы и директории источника с учётом фильтров.

        Args:
            source: Абсолютный путь источника.
            for_copy: Если True, применяется фильтр по дате для режимов копирования.
            last_run: Время последнего запуска для фильтрации по дате.
        """
        source = normalize_path(source)
        if not path_exists(source):
            return

        if os.path.isfile(source):
            rel = os.path.basename(source)
            if self.is_excluded(rel):
                return
            try:
                stat = os.stat(to_long_path(source))
            except OSError:
                return
            if not self._passes_size(stat.st_size):
                return
            if for_copy and not self._should_copy_by_date(stat.st_mtime, last_run):
                return
            yield FileEntry(
                source_root=source,
                absolute_path=source,
                relative_path=rel,
                size=stat.st_size,
                mtime=stat.st_mtime,
            )
            return

        root = source
        for dirpath, dirnames, filenames in os.walk(root):
            dirpath_long = to_long_path(dirpath)
            rel_dir = os.path.relpath(dirpath, root)
            if rel_dir == ".":
                rel_dir = ""

            # Исключаем поддиректории
            kept_dirs = []
            for d in dirnames:
                rel_sub = os.path.join(rel_dir, d) if rel_dir else d
                if not self.is_excluded(rel_sub, is_dir=True):
                    kept_dirs.append(d)
            dirnames[:] = kept_dirs

            if rel_dir and self.is_excluded(rel_dir, is_dir=True):
                continue

            # Пустые директории
            if not filenames and not dirnames:
                if for_copy:
                    if self.task.copy_mode == CopyMode.DUPLICATE:
                        yield FileEntry(
                            source_root=root,
                            absolute_path=dirpath,
                            relative_path=rel_dir,
                            size=0,
                            mtime=0,
                            is_dir=True,
                        )
                    elif last_run is None:
                        yield FileEntry(
                            source_root=root,
                            absolute_path=dirpath,
                            relative_path=rel_dir,
                            size=0,
                            mtime=0,
                            is_dir=True,
                        )
                else:
                    yield FileEntry(
                        source_root=root,
                        absolute_path=dirpath,
                        relative_path=rel_dir,
                        size=0,
                        mtime=0,
                        is_dir=True,
                    )

            for fname in filenames:
                rel_file = os.path.join(rel_dir, fname) if rel_dir else fname
                if self.is_excluded(rel_file):
                    continue
                abs_file = os.path.join(dirpath, fname)
                try:
                    stat = os.stat(to_long_path(abs_file))
                except OSError:
                    continue
                if not self._passes_size(stat.st_size):
                    continue
                if for_copy and not self._should_copy_by_date(stat.st_mtime, last_run):
                    continue
                yield FileEntry(
                    source_root=root,
                    absolute_path=abs_file,
                    relative_path=rel_file,
                    size=stat.st_size,
                    mtime=stat.st_mtime,
                )

    def calculate_size(
        self,
        on_source: Optional[Callable[[int, str, int], None]] = None,
    ) -> tuple[int, dict[str, int]]:
        """
        Подсчитывает размер файлов по каждому источнику (без режима копирования).

        Args:
            on_source: Колбэк (номер, путь источника, всего источников).

        Returns:
            (сумма байт, {путь источника: байт}).
        """
        per_source: dict[str, int] = {}
        sources = self.task.sources
        sources_total = len(sources)
        for index, source in enumerate(sources, 1):
            if on_source is not None:
                on_source(index, source, sources_total)
            source_total = 0
            for entry in self.iter_entries(source, for_copy=False):
                if entry.is_dir:
                    continue
                source_total += entry.size
            per_source[source] = source_total
        return sum(per_source.values()), per_source

    def collect_for_copy(
        self,
        last_run: Optional[datetime] = None,
        *,
        include_missing: bool = False,
        dest_bases: Optional[dict[str, str]] = None,
    ) -> dict[str, list[FileEntry]]:
        """
        Собирает файлы для копирования по каждому источнику.

        Args:
            last_run: Время последнего запуска.
            include_missing: Для keep_changes/layered также брать отсутствующие в назначении.
            dest_bases: Пути назначения по источникам (нужны при include_missing).
        """
        result: dict[str, list[FileEntry]] = {}
        use_missing = (
            include_missing
            and self.task.copy_mode in (CopyMode.KEEP_CHANGES, CopyMode.LAYERED)
            and dest_bases is not None
        )
        for source in self.task.sources:
            if use_missing:
                entries = self._collect_by_date_or_missing(
                    source,
                    last_run,
                    dest_bases.get(source, ""),
                )
            else:
                entries = list(
                    self.iter_entries(source, for_copy=True, last_run=last_run)
                )
            result[source] = entries
        return result

    def calculate_copy_size(
        self, last_run: Optional[datetime] = None
    ) -> int:
        """Подсчитывает размер файлов для копирования с учётом режима."""
        total = 0
        for source in self.task.sources:
            for entry in self.iter_entries(source, for_copy=True, last_run=last_run):
                if not entry.is_dir:
                    total += entry.size
        return total

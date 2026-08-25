"""Фикстуры pytest для тестов KeepCopy."""

from __future__ import annotations

import os
import shutil
import time
from datetime import datetime
from pathlib import Path

import pytest

from models.task import CopyMode, Task
from services.backup_engine import BackupEngine
from services.logger import BackupLogger


@pytest.fixture
def test_root(tmp_path: Path) -> Path:
    """Корневая директория для тестовых файлов."""
    root = tmp_path / "keepcopy_tests"
    root.mkdir(exist_ok=True)
    yield root
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def backup_engine(test_root: Path) -> BackupEngine:
    """Движок с логами в тестовой директории."""
    return BackupEngine(
        logger=BackupLogger(
            log_path=test_root / "backup.log",
            errors_dir=test_root / "errors",
        )
    )


def make_task(
    sources: list[str],
    dest: str,
    *,
    mode: CopyMode = CopyMode.KEEP_CHANGES,
    exclusions: list[str] | None = None,
    max_size_mb: float | None = None,
    compress: bool = False,
    last_run: datetime | None = None,
) -> Task:
    """Создаёт тестовую задачу."""
    task = Task.create_default("Тест")
    task.sources = sources
    task.destination = dest
    task.copy_mode = mode
    task.exclusions = exclusions or []
    task.max_size_mb = max_size_mb
    task.compress = compress
    task.last_run = last_run
    task.is_active = False
    return task


def write_file(path: Path, content: str = "data", mtime: float | None = None) -> None:
    """Создаёт файл с опциональным mtime."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def touch_later(path: Path, delta: float = 2.0) -> None:
    """Сдвигает mtime файла вперёд."""
    stat = path.stat()
    new_mtime = stat.st_mtime + delta
    os.utime(path, (new_mtime, new_mtime))

"""Тесты резервного копирования."""

from __future__ import annotations

import os
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from models.task import CopyMode
from services.backup_engine import BackupResultKind
from tests.conftest import make_task, touch_later, write_file


class TestKeepChanges:
    """Тесты режима «Сохранять изменения»."""

    def test_basic_copy_and_incremental(
        self, test_root: Path, backup_engine
    ) -> None:
        """Копирование без фильтров, повторный запуск — только новый файл."""
        src = test_root / "src1"
        dest = test_root / "dest"
        dest.mkdir()
        write_file(src / "a.txt", "aaa")
        write_file(src / "b.txt", "bbb")

        task = make_task([str(src)], str(dest))
        result = backup_engine.run(task)
        assert not result.is_disk_full
        assert (dest / "src1" / "a.txt").exists()
        assert (dest / "src1" / "b.txt").exists()

        task.last_run = datetime.now()
        write_file(src / "c.txt", "ccc")
        backup_engine.run(task)
        assert (dest / "src1" / "c.txt").exists()
        # старые файлы на месте
        assert (dest / "src1" / "a.txt").read_text() == "aaa"

    def test_empty_archive_manual_copies_missing(
        self, test_root: Path, backup_engine
    ) -> None:
        """Ручной запуск: отсутствующие в архиве файлы копируются даже со старой датой."""
        src = test_root / "src_empty"
        dest = test_root / "dest_empty"
        dest.mkdir()
        write_file(src / "a.txt", "aaa")

        task = make_task([str(src)], str(dest))
        task.last_run = datetime.now()
        result = backup_engine.run(task, automatic=False)
        assert result.files_copied == 1
        assert (dest / "src_empty" / "a.txt").exists()

    def test_first_automatic_run_copies_all(
        self, test_root: Path, backup_engine
    ) -> None:
        """Первый автозапуск копирует все файлы, даже если last_run уже задан."""
        src = test_root / "src_first_auto"
        dest = test_root / "dest_first_auto"
        dest.mkdir()
        write_file(src / "a.txt", "aaa")

        task = make_task([str(src)], str(dest))
        task.last_run = datetime.now() + timedelta(hours=1)
        result = backup_engine.run(task, automatic=True)
        assert result.files_copied == 1
        assert (dest / "src_first_auto" / "a.txt").exists()

    def test_automatic_run_skips_old_files_after_first(
        self, test_root: Path, backup_engine
    ) -> None:
        """Повторный автозапуск: файлы старше last_run не копируются."""
        src = test_root / "src_auto"
        dest = test_root / "dest_auto"
        dest.mkdir()
        write_file(src / "a.txt", "aaa")

        task = make_task([str(src)], str(dest))
        task.last_run = datetime.now() + timedelta(hours=1)
        task.last_auto_run = datetime.now()
        result = backup_engine.run(task, automatic=True)
        assert result.files_copied == 0
        assert not (dest / "src_auto" / "a.txt").exists()


class TestFilters:
    """Тесты фильтров исключений."""

    def test_simple_filter(self, test_root: Path, backup_engine) -> None:
        """Простой фильтр *.tmp."""
        src = test_root / "src2"
        dest = test_root / "dest2"
        dest.mkdir()
        write_file(src / "keep.txt")
        write_file(src / "skip.tmp")

        task = make_task([str(src)], str(dest), exclusions=["*.tmp"])
        backup_engine.run(task)
        assert (dest / "src2" / "keep.txt").exists()
        assert not (dest / "src2" / "skip.tmp").exists()

    def test_star_filter(self, test_root: Path, backup_engine) -> None:
        """Фильтр */* — файлы в поддиректориях 1 уровня."""
        src = test_root / "src3"
        dest = test_root / "dest3"
        dest.mkdir()
        write_file(src / "root.txt")
        write_file(src / "sub" / "inner.txt")

        task = make_task([str(src)], str(dest), exclusions=["*/*"])
        backup_engine.run(task)
        assert (dest / "src3" / "root.txt").exists()
        assert not (dest / "src3" / "sub" / "inner.txt").exists()

    def test_double_star_filter(self, test_root: Path, backup_engine) -> None:
        """Фильтр **.png — все PNG рекурсивно."""
        src = test_root / "src4"
        dest = test_root / "dest4"
        dest.mkdir()
        write_file(src / "a.png", "png")
        write_file(src / "deep" / "b.png", "png")
        write_file(src / "c.txt", "txt")

        task = make_task([str(src)], str(dest), exclusions=["**.png"])
        backup_engine.run(task)
        assert (dest / "src4" / "c.txt").exists()
        assert not (dest / "src4" / "a.png").exists()
        assert not (dest / "src4" / "deep" / "b.png").exists()


class TestMaxSize:
    """Тесты ограничения размера."""

    def test_max_size_boundary(self, test_root: Path, backup_engine) -> None:
        """Файл равный лимиту копируется, больший — нет."""
        src = test_root / "src5"
        dest = test_root / "dest5"
        dest.mkdir()
        src.mkdir()
        # 1 MB = 1048576 bytes
        small = src / "small.bin"
        big = src / "big.bin"
        small.write_bytes(b"x" * 1048576)
        big.write_bytes(b"x" * (1048576 + 1))

        task = make_task([str(src)], str(dest), max_size_mb=1.0)
        backup_engine.run(task)
        assert (dest / "src5" / "small.bin").exists()
        assert not (dest / "src5" / "big.bin").exists()


class TestLayered:
    """Тесты режима «Сохранять слоями»."""

    def test_two_layers(self, test_root: Path, backup_engine) -> None:
        """Два слоя, во втором только изменённый файл."""
        src = test_root / "src6"
        dest = test_root / "dest6"
        dest.mkdir()
        write_file(src / "f1.txt", "v1")
        write_file(src / "f2.txt", "v2")

        task = make_task([str(src)], str(dest), mode=CopyMode.LAYERED)
        backup_engine.run(task)
        layers = list((dest / "src6").glob("backup_*"))
        assert len(layers) == 1
        assert (layers[0] / "f1.txt").exists()

        task.last_run = datetime.now()
        touch_later(src / "f1.txt")
        backup_engine.run(task)
        layers = sorted((dest / "src6").glob("backup_*"))
        assert len(layers) == 2
        assert (layers[1] / "f1.txt").exists()
        assert not (layers[1] / "f2.txt").exists()


class TestDuplicate:
    """Тесты режима «Дублирование»."""

    def test_two_full_layers(self, test_root: Path, backup_engine) -> None:
        """Два слоя, во втором все файлы."""
        src = test_root / "src7"
        dest = test_root / "dest7"
        dest.mkdir()
        write_file(src / "a.txt")
        write_file(src / "b.txt")

        task = make_task([str(src)], str(dest), mode=CopyMode.DUPLICATE)
        backup_engine.run(task)
        task.last_run = datetime.now()
        touch_later(src / "a.txt")
        backup_engine.run(task)
        layers = sorted((dest / "src7").glob("backup_*"))
        assert len(layers) == 2
        assert (layers[1] / "a.txt").exists()
        assert (layers[1] / "b.txt").exists()


class TestDiskFull:
    """Тест нехватки места."""

    def test_insufficient_space(self, test_root: Path, backup_engine) -> None:
        """Ошибка нехватки места, исходник не тронут."""
        src = test_root / "src8"
        dest = test_root / "dest8"
        dest.mkdir()
        content = "x" * 10000
        write_file(src / "big.txt", content)
        original = (src / "big.txt").read_text()

        task = make_task([str(src)], str(dest))
        with patch.object(backup_engine, "_get_free_space", return_value=0):
            result = backup_engine.run(task)
        assert result.is_disk_full
        assert (src / "big.txt").read_text() == original
        assert not (dest / "src8" / "big.txt").exists()


class TestCompression:
    """Тесты сжатия ZIP."""

    def test_zip_created(self, test_root: Path, backup_engine) -> None:
        """ZIP создан, содержимое проверено."""
        src = test_root / "src9"
        dest = test_root / "dest9"
        dest.mkdir()
        write_file(src / "doc.txt", "hello zip")

        task = make_task([str(src)], str(dest), compress=True)
        backup_engine.run(task)
        zip_path = dest / "src9.zip"
        assert zip_path.exists()
        with zipfile.ZipFile(zip_path) as zf:
            assert "doc.txt" in zf.namelist()
            assert zf.read("doc.txt") == b"hello zip"

    def test_zip_incremental_multi_source(
        self, test_root: Path, backup_engine
    ) -> None:
        """Добавление в существующий zip, несколько источников."""
        src1 = test_root / "src10a"
        src2 = test_root / "src10b"
        dest = test_root / "dest10"
        dest.mkdir()
        write_file(src1 / "a.txt", "a")
        write_file(src2 / "b.txt", "b")

        task = make_task(
            [str(src1), str(src2)], str(dest), compress=True
        )
        backup_engine.run(task)
        assert (dest / "src10a.zip").exists()
        assert (dest / "src10b.zip").exists()

        task.last_run = datetime.now()
        write_file(src1 / "c.txt", "c")
        backup_engine.run(task)
        with zipfile.ZipFile(dest / "src10a.zip") as zf:
            names = zf.namelist()
            assert "a.txt" in names
            assert "c.txt" in names


class TestMultiSource:
    """Тест нескольких источников."""

    def test_multiple_sources(self, test_root: Path, backup_engine) -> None:
        """Несколько источников — отдельные подпапки."""
        src1 = test_root / "ms1"
        src2 = test_root / "ms2"
        dest = test_root / "dest_ms"
        dest.mkdir()
        write_file(src1 / "f.txt")
        write_file(src2 / "g.txt")

        task = make_task([str(src1), str(src2)], str(dest))
        backup_engine.run(task)
        assert (dest / "ms1" / "f.txt").exists()
        assert (dest / "ms2" / "g.txt").exists()

    def test_file_source_uses_parent_folder(
        self, test_root: Path, backup_engine
    ) -> None:
        """Файл копируется в подпапку «родитель_files»."""
        parent = test_root / "source"
        dest = test_root / "dest_file"
        dest.mkdir()
        write_file(parent / "file1.txt", "content")

        task = make_task([str(parent / "file1.txt")], str(dest))
        backup_engine.run(task)
        assert (dest / "source_files" / "file1.txt").exists()
        assert not (dest / "source" / "file1.txt").exists()
        assert not (dest / "file1.txt").exists()


class TestScheduler:
    """Тесты планировщика."""

    def test_inactive_skipped(self, test_root: Path) -> None:
        """Неактивная задача не считается просроченной для авто."""
        from services.scheduler import SchedulerService

        src = test_root / "sched_src"
        dest = test_root / "sched_dest"
        dest.mkdir()
        task = make_task([str(src)], str(dest))
        task.is_active = False
        task.next_run = datetime.now().date() - timedelta(days=1)
        assert not SchedulerService.is_due(task)

    def test_manual_run_allowed(self, test_root: Path, backup_engine) -> None:
        """Неактивная задача выполняется вручную (через run)."""
        src = test_root / "manual_src"
        dest = test_root / "manual_dest"
        dest.mkdir()
        write_file(src / "x.txt")
        task = make_task([str(src)], str(dest))
        task.is_active = False
        backup_engine.run(task)
        assert (dest / "manual_src" / "x.txt").exists()

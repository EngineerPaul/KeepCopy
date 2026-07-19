"""Тесты кэша размеров и подсчёта по источникам."""

from __future__ import annotations

from pathlib import Path

from models.task import Task
from services.file_matcher import FileMatcher
from services.storage import normalize_size_entry


def test_normalize_size_entry_legacy_int() -> None:
    assert normalize_size_entry(1500) == {"total": 1500, "sources": {}}


def test_normalize_size_entry_dict() -> None:
    raw = {"total": 30, "sources": {"a": 10, "b": 20}}
    assert normalize_size_entry(raw) == raw


def test_calculate_size_per_source(tmp_path: Path) -> None:
    src_a = tmp_path / "a"
    src_b = tmp_path / "b"
    src_a.mkdir()
    src_b.mkdir()
    (src_a / "f1.txt").write_bytes(b"12345")
    (src_b / "f2.txt").write_bytes(b"1234567890")

    task = Task(
        id="t1",
        name="t",
        sources=[str(src_a), str(src_b)],
        destination=str(tmp_path / "out"),
    )
    total, per_source = FileMatcher(task).calculate_size()

    assert per_source[str(src_a)] == 5
    assert per_source[str(src_b)] == 10
    assert total == 15

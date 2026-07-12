"""Тесты валидации путей."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.path_utils import (
    find_nested_source_indices,
    is_absolute_drive_path,
    is_path_nested_in,
    validate_directory_path,
    validate_path,
)
from tests.conftest import write_file


class TestAbsoluteDrivePath:
    """Тесты абсолютных путей с буквой диска."""

    @pytest.mark.parametrize(
        "path",
        [
            ".",
            "..",
            "folder",
            "t\\archive",
            "t/archive",
            "C:relative",
        ],
    )
    def test_rejects_relative_paths(self, path: str) -> None:
        assert not is_absolute_drive_path(path)
        ok, err = validate_path(path)
        assert not ok
        assert "диска" in err.lower()

    def test_accepts_drive_path(self, test_root: Path) -> None:
        path = str(test_root)
        assert is_absolute_drive_path(path)
        ok, err = validate_path(path)
        assert ok
        assert err == ""

    def test_dot_rejected_for_destination(self, test_root: Path) -> None:
        ok, err = validate_directory_path(".")
        assert not ok
        assert "диска" in err.lower()

    def test_relative_rejected_for_destination(self) -> None:
        ok, err = validate_directory_path("t\\archive")
        assert not ok
        assert "диска" in err.lower()

    def test_existing_absolute_directory(self, test_root: Path) -> None:
        ok, err = validate_directory_path(str(test_root))
        assert ok
        assert err == ""

    def test_file_instead_of_directory(self, test_root: Path) -> None:
        file_path = test_root / "file.txt"
        write_file(file_path)
        ok, err = validate_directory_path(str(file_path))
        assert not ok
        assert "папку" in err.lower()


class TestNestedSources:
    """Тесты вложенности источников."""

    def test_folder_contains_subfolder(self, test_root: Path) -> None:
        parent = test_root / "parent"
        child = parent / "child"
        parent.mkdir()
        child.mkdir()
        assert is_path_nested_in(str(child), str(parent))
        assert not is_path_nested_in(str(parent), str(child))

    def test_file_in_folder(self, test_root: Path) -> None:
        folder = test_root / "folder"
        folder.mkdir()
        file_path = folder / "a.txt"
        write_file(file_path)
        assert is_path_nested_in(str(file_path), str(folder))
        assert not is_path_nested_in(str(folder), str(file_path))

    def test_files_in_same_folder_not_nested(self, test_root: Path) -> None:
        folder = test_root / "folder"
        folder.mkdir()
        file_a = folder / "a.txt"
        file_b = folder / "b.txt"
        write_file(file_a)
        write_file(file_b)
        assert not is_path_nested_in(str(file_a), str(file_b))

    def test_find_nested_indices(self, test_root: Path) -> None:
        parent = test_root / "parent"
        child = parent / "child"
        parent.mkdir()
        child.mkdir()
        sources = [str(parent), str(child)]
        assert find_nested_source_indices(sources) == [1]

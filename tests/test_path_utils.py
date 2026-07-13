"""Тесты валидации путей."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.path_utils import (
    find_nested_source_indices,
    get_app_executable,
    is_absolute_drive_path,
    is_compiled_app,
    is_path_nested_in,
    validate_directory_path,
    validate_path,
)
from tests.conftest import write_file


def test_is_compiled_app_pyinstaller() -> None:
    import sys
    from unittest.mock import patch

    with patch.object(sys, "frozen", True, create=True):
        assert is_compiled_app() is True


def test_is_compiled_app_nuitka_argv() -> None:
    import sys
    from unittest.mock import patch

    exe = r"C:\Apps\Archiver\Archiver.exe"
    with (
        patch.object(sys, "frozen", False, create=True),
        patch.object(sys, "argv", [exe]),
    ):
        assert is_compiled_app() is True


def test_is_compiled_app_python_dev() -> None:
    import sys
    from unittest.mock import patch

    with (
        patch.object(sys, "frozen", False, create=True),
        patch.object(sys, "argv", ["main.py"]),
        patch.dict("services.path_utils.__dict__", {"__compiled__": None}, clear=False),
    ):
        # __compiled__ may exist in real Nuitka build; ensure python dev path still works
        import services.path_utils as pu

        original = pu.__dict__.get("__compiled__")
        try:
            if "__compiled__" in pu.__dict__:
                del pu.__dict__["__compiled__"]
            assert is_compiled_app() is False
        finally:
            if original is not None:
                pu.__dict__["__compiled__"] = original


def test_get_app_executable_prefers_argv_exe() -> None:
    import sys
    from unittest.mock import patch

    exe = r"C:\Apps\Archiver\Archiver.exe"
    with (
        patch.object(sys, "frozen", False, create=True),
        patch.object(sys, "argv", [exe]),
        patch.object(sys, "executable", r"C:\Apps\Archiver\python.exe"),
    ):
        assert get_app_executable() == Path(exe).resolve()


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

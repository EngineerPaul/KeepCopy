"""Тесты валидации формы задачи."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from services.path_utils import validate_directory_path
from tests.conftest import write_file
from ui.task_dialog import TaskDialog


@pytest.fixture(scope="module")
def qapp():
    """Единый QApplication для тестов UI."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _make_dialog(tmp_path: Path, *, dest: str = "", name: str = "Тест") -> TaskDialog:
    src = tmp_path / "src"
    write_file(src / "a.txt")
    dlg = TaskDialog([], parent=None)
    dlg._name.setText(name)
    dlg._destination.setText(dest)
    dlg._sources = [str(src)]
    return dlg


class TestValidateDirectoryPath:
    """Тесты validate_directory_path."""

    def test_empty_path(self, test_root: Path) -> None:
        ok, err = validate_directory_path("")
        assert not ok
        assert err

    def test_missing_directory(self, test_root: Path) -> None:
        missing = test_root / "missing_dir"
        ok, err = validate_directory_path(str(missing))
        assert not ok
        assert "не существует" in err

    def test_file_instead_of_directory(self, test_root: Path) -> None:
        file_path = test_root / "file.txt"
        write_file(file_path)
        ok, err = validate_directory_path(str(file_path))
        assert not ok
        assert "папку" in err.lower()

    def test_existing_directory(self, test_root: Path) -> None:
        ok, err = validate_directory_path(str(test_root))
        assert ok
        assert err == ""


class TestTaskDialogValidate:
    """Тесты _validate в диалоге задачи."""

    def test_rejects_empty_name(self, test_root: Path, qapp) -> None:
        dlg = _make_dialog(test_root, dest=str(test_root), name="")
        assert dlg._validate() is False
        assert "название" in dlg._error_labels["name"].text().lower()

    def test_rejects_empty_destination(self, test_root: Path, qapp) -> None:
        dlg = _make_dialog(test_root, dest="")
        assert dlg._validate() is False
        assert "назначения" in dlg._error_labels["destination"].text().lower()

    def test_rejects_missing_destination(self, test_root: Path, qapp) -> None:
        missing = test_root / "no_such_folder"
        dlg = _make_dialog(test_root, dest=str(missing))
        assert dlg._validate() is False
        assert dlg._error_labels["destination"].text()

    def test_rejects_relative_destination(self, test_root: Path, qapp) -> None:
        dlg = _make_dialog(test_root, dest=".", name="Задача")
        assert dlg._validate() is False
        assert "диска" in dlg._error_labels["destination"].text().lower()

    def test_rejects_relative_source_on_save(self, test_root: Path, qapp) -> None:
        dlg = _make_dialog(test_root, dest=str(test_root), name="Задача")
        dlg._sources = ["t\\source"]
        assert dlg._validate() is False
        assert "диска" in dlg._error_labels["sources"].text().lower()

    def test_accepts_valid_form(self, test_root: Path, qapp) -> None:
        dlg = _make_dialog(test_root, dest=str(test_root), name="Задача")
        assert dlg._validate() is True
        assert dlg._error_labels["name"].text() == ""
        assert dlg._error_labels["destination"].text() == ""

    def test_nested_sources_excluded_from_active(self, test_root: Path, qapp) -> None:
        parent = test_root / "parent"
        child = parent / "child"
        parent.mkdir()
        child.mkdir()
        write_file(child / "a.txt")
        dlg = _make_dialog(test_root, dest=str(test_root), name="Задача")
        dlg._sources = [str(parent), str(child)]
        dlg._update_nested_sources()
        assert str(child) in dlg._nested_sources
        assert dlg._active_sources() == [str(parent)]
        assert dlg._validate() is True

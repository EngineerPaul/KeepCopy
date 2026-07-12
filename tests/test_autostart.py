"""Тесты автозапуска."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from services import autostart


def test_background_arg_constant() -> None:
    assert autostart.BACKGROUND_ARG == "--background"


def test_startup_folder_under_appdata() -> None:
    with patch.dict("os.environ", {"APPDATA": r"C:\Users\Test\AppData\Roaming"}):
        folder = autostart.get_startup_folder()
    assert folder == Path(
        r"C:\Users\Test\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
    )


def test_shortcut_path() -> None:
    with patch.dict("os.environ", {"APPDATA": r"C:\Users\Test\AppData\Roaming"}):
        path = autostart.shortcut_path()
    assert path.name == "Archiver.lnk"
    assert path.parent.name == "Startup"


def test_get_launch_spec_frozen() -> None:
    exe = Path(r"C:\Apps\Archiver\Archiver.exe")
    with (
        patch.object(sys, "frozen", True, create=True),
        patch.object(sys, "executable", str(exe)),
        patch("services.autostart.get_app_dir", return_value=exe.parent),
    ):
        target, arguments, work_dir = autostart.get_launch_spec()
    assert target == exe
    assert arguments == "--background"
    assert work_dir == exe.parent


def test_apply_autostart_non_windows() -> None:
    with patch.object(autostart, "is_windows", return_value=False):
        autostart.apply_autostart(True)
        autostart.apply_autostart(False)


def test_sync_autostart_creates_when_missing(tmp_path: Path) -> None:
    lnk = tmp_path / "Archiver.lnk"
    with (
        patch.object(autostart, "is_windows", return_value=True),
        patch.object(autostart, "shortcut_path", return_value=lnk),
        patch.object(autostart, "enable_autostart") as enable,
        patch.object(autostart, "disable_autostart") as disable,
    ):
        autostart.sync_autostart(True)
        enable.assert_called_once()
        disable.assert_not_called()


def test_sync_autostart_removes_when_disabled(tmp_path: Path) -> None:
    lnk = tmp_path / "Archiver.lnk"
    lnk.write_text("stub", encoding="utf-8")
    with (
        patch.object(autostart, "is_windows", return_value=True),
        patch.object(autostart, "shortcut_path", return_value=lnk),
        patch.object(autostart, "enable_autostart") as enable,
        patch.object(autostart, "disable_autostart") as disable,
    ):
        autostart.sync_autostart(False)
        disable.assert_called_once()
        enable.assert_not_called()

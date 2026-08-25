"""Тесты автозапуска."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    assert path.name == "KeepCopy.lnk"
    assert path.parent.name == "Startup"


def test_is_autostart_enabled_legacy_shortcut() -> None:
    current = MagicMock()
    current.is_file.return_value = False
    legacy = MagicMock()
    legacy.is_file.return_value = True
    with (
        patch.object(autostart, "is_windows", return_value=True),
        patch.object(autostart, "shortcut_path", return_value=current),
        patch.object(autostart, "_legacy_shortcut_path", return_value=legacy),
    ):
        assert autostart.is_autostart_enabled() is True


def test_get_launch_spec_frozen() -> None:
    exe = Path(r"C:\Apps\KeepCopy\KeepCopy.exe")
    with (
        patch.object(sys, "frozen", True, create=True),
        patch.object(sys, "executable", str(exe)),
        patch.object(sys, "argv", [str(exe)]),
        patch("services.autostart.get_app_dir", return_value=exe.parent),
        patch("services.autostart.is_compiled_app", return_value=True),
        patch("services.autostart.get_app_executable", return_value=exe),
    ):
        target, arguments, work_dir = autostart.get_launch_spec()
    assert target == exe
    assert arguments == "--background"
    assert work_dir == exe.parent


def test_get_launch_spec_nuitka_exe_argv() -> None:
    exe = Path(r"C:\Apps\KeepCopy\KeepCopy.exe")
    with (
        patch.object(sys, "frozen", False, create=True),
        patch.object(sys, "executable", r"C:\Apps\KeepCopy\python.exe"),
        patch.object(sys, "argv", [str(exe)]),
        patch("services.autostart.get_app_dir", return_value=exe.parent),
        patch("services.autostart.is_compiled_app", return_value=True),
        patch("services.autostart.get_app_executable", return_value=exe),
    ):
        target, arguments, work_dir = autostart.get_launch_spec()
    assert target == exe
    assert arguments == "--background"
    assert work_dir == exe.parent


def test_apply_autostart_non_windows() -> None:
    with patch.object(autostart, "is_windows", return_value=False):
        autostart.apply_autostart(True)
        autostart.apply_autostart(False)


def test_sync_autostart_enabled_always_refreshes_shortcut() -> None:
    with (
        patch.object(autostart, "is_windows", return_value=True),
        patch.object(autostart, "is_autostart_enabled", return_value=True),
        patch.object(autostart, "enable_autostart") as enable,
        patch.object(autostart, "disable_autostart") as disable,
    ):
        autostart.sync_autostart(True)
        enable.assert_called_once()
        disable.assert_not_called()


def test_sync_autostart_disabled_removes_shortcut() -> None:
    with (
        patch.object(autostart, "is_windows", return_value=True),
        patch.object(autostart, "is_autostart_enabled", return_value=True),
        patch.object(autostart, "enable_autostart") as enable,
        patch.object(autostart, "disable_autostart") as disable,
    ):
        autostart.sync_autostart(False)
        disable.assert_called_once()
        enable.assert_not_called()


def test_reconcile_autostart_fixes_missing_shortcut() -> None:
    storage = MagicMock()
    storage.get_settings.return_value = MagicMock(autostart=True)
    with (
        patch.object(autostart, "is_windows", return_value=True),
        patch.object(autostart, "is_autostart_enabled", return_value=False),
        patch.object(autostart, "sync_autostart") as sync,
        patch.object(autostart, "enable_autostart") as enable,
    ):
        autostart.reconcile_autostart(storage)
        sync.assert_called_once_with(True)
        enable.assert_not_called()


def test_reconcile_autostart_refreshes_matching_enabled() -> None:
    storage = MagicMock()
    storage.get_settings.return_value = MagicMock(autostart=True)
    with (
        patch.object(autostart, "is_windows", return_value=True),
        patch.object(autostart, "is_autostart_enabled", return_value=True),
        patch.object(autostart, "sync_autostart") as sync,
        patch.object(autostart, "enable_autostart") as enable,
    ):
        autostart.reconcile_autostart(storage)
        sync.assert_not_called()
        enable.assert_called_once()

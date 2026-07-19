"""Сборка Archiver.exe через Nuitka в папку compiler/."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPILER_DIR = ROOT / "compiler"
ICON = ROOT / "assets" / "archiver_icon.ico"


def main() -> int:
    """Запускает Nuitka с параметрами проекта."""
    # Короткий путь без пробелов: иначе MinGW из кэша Nuitka не находит windows.h.
    if not os.environ.get("NUITKA_CACHE_DIR"):
        os.environ["NUITKA_CACHE_DIR"] = r"C:\NuitkaCache"

    icon_script = ROOT / "scripts" / "build_icon.py"
    if not ICON.is_file():
        rc = subprocess.call([sys.executable, str(icon_script)], cwd=ROOT)
        if rc != 0:
            return rc

    COMPILER_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--windows-console-mode=disable",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        "--include-package=pathspec",
        f"--include-data-dir={ROOT / 'assets'}=assets",
        f"--output-dir={COMPILER_DIR}",
        "--output-filename=Archiver.exe",
        "--company-name=Archiver",
        "--product-name=Архиватор",
        "--file-version=1.0.0",
        f"--windows-icon-from-ico={ICON}",
        str(ROOT / "main.py"),
    ]
    print(" ".join(f'"{part}"' if " " in part else part for part in cmd))
    rc = subprocess.call(cmd, cwd=ROOT)
    if rc != 0:
        return rc

    built_dist = COMPILER_DIR / "main.dist"
    dist_dir = COMPILER_DIR / "Archiver.dist"
    if built_dist.is_dir():
        # Сохраняем settings.json из предыдущей сборки, чтобы не сбрасывать задачи/настройки.
        preserved_settings: bytes | None = None
        settings_path = dist_dir / "settings.json"
        if settings_path.is_file():
            preserved_settings = settings_path.read_bytes()

        if dist_dir.is_dir():
            shutil.rmtree(dist_dir)
        built_dist.rename(dist_dir)

        if preserved_settings is not None:
            (dist_dir / "settings.json").write_bytes(preserved_settings)
            print(f"Восстановлен: {dist_dir / 'settings.json'}")

        print(f"Готово: {dist_dir / 'Archiver.exe'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

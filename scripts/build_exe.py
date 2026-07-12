"""Сборка Archiver.exe через Nuitka в папку compiler/."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPILER_DIR = ROOT / "compiler"
ICON = ROOT / "assets" / "archiver_icon.ico"


def main() -> int:
    """Запускает Nuitka с параметрами проекта."""
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
        "--windows-disable-console",
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
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    sys.exit(main())

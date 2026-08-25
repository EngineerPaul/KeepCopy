"""Упаковка KeepCopy.dist в zip без локальных настроек и логов."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.app_info import ARCHIVE_NAME, DIST_DIR, EXE_NAME

COMPILER_DIR = ROOT / "compiler"
SKIP_FILES = {"settings.json", "backup.log"}
SKIP_DIRS = {"errors"}


def _should_skip(relative: Path) -> bool:
    """True для пользовательских данных, которых не должно быть в дистрибутиве."""
    if relative.name.lower() in SKIP_FILES:
        return True
    return any(part.lower() in SKIP_DIRS for part in relative.parts)


def pack() -> Path:
    """Создаёт compiler/KeepCopy.zip с папкой KeepCopy.dist внутри."""
    dist_dir = COMPILER_DIR / DIST_DIR
    exe_path = dist_dir / EXE_NAME
    if not exe_path.is_file():
        raise FileNotFoundError(f"Нет сборки: {exe_path}")

    archive_path = COMPILER_DIR / ARCHIVE_NAME
    if archive_path.exists():
        archive_path.unlink()

    COMPILER_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in dist_dir.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(dist_dir)
            if _should_skip(relative):
                print(f"Пропущен: {relative}")
                continue
            arcname = Path(DIST_DIR, relative).as_posix()
            zf.write(path, arcname)

    print(f"Архив: {archive_path} ({archive_path.stat().st_size} байт)")
    return archive_path


def main() -> int:
    """Собирает zip дистрибутива."""
    pack()
    return 0


if __name__ == "__main__":
    sys.exit(main())

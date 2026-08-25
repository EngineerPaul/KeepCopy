"""Генерация keepcopy_icon.ico из assets/keepcopy_icon.svg для сборки Nuitka."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.app_info import ICON_ICO, ICON_SVG

SVG_PATH = ROOT / "assets" / ICON_SVG
ICO_PATH = ROOT / "assets" / ICON_ICO
ICO_SIZES = (16, 32, 48, 64, 128, 256)


def _render_png(svg_path: Path, size: int) -> bytes:
    """Рендерит SVG в PNG-байты заданного размера."""
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        raise RuntimeError(f"Некорректный SVG: {svg_path}")

    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise RuntimeError(f"Не удалось сохранить PNG {size}x{size}")
    return bytes(buffer.data())


def _write_ico(png_images: list[tuple[int, bytes]], output: Path) -> None:
    """Записывает ICO с PNG-кадрами (Windows Vista+)."""
    count = len(png_images)
    header = struct.pack("<HHH", 0, 1, count)
    entries = bytearray()
    images = bytearray()
    offset = 6 + 16 * count

    for size, png in png_images:
        width = 0 if size >= 256 else size
        height = width
        entries.extend(
            struct.pack(
                "<BBBBHHII",
                width,
                height,
                0,
                0,
                1,
                32,
                len(png),
                offset,
            )
        )
        images.extend(png)
        offset += len(png)

    output.write_bytes(header + bytes(entries) + bytes(images))


def main() -> int:
    """Создаёт assets/keepcopy_icon.ico из SVG."""
    if not SVG_PATH.is_file():
        print(f"Файл не найден: {SVG_PATH}", file=sys.stderr)
        return 1

    app = QApplication([])
    png_images = [(size, _render_png(SVG_PATH, size)) for size in ICO_SIZES]
    _write_ico(png_images, ICO_PATH)
    print(f"Создан: {ICO_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

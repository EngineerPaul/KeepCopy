"""SVG-иконки 16×16 для интерфейса."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


def _svg_to_icon(svg: str, size: int = 16) -> QIcon:
    """Конвертирует SVG-строку в QIcon."""
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    icon = QIcon(pixmap)
    return icon


ICON_PLAY = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<polygon points="4,2 14,8 4,14" fill="#2e7d32"/>
</svg>"""

ICON_PAUSE = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<circle cx="8" cy="8" r="7" fill="none" stroke="#616161" stroke-width="1.2"/>
<rect x="5.5" y="5.5" width="1.5" height="5" rx="0.4" fill="#616161"/>
<rect x="9" y="5.5" width="1.5" height="5" rx="0.4" fill="#616161"/>
</svg>"""

ICON_EDIT = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<path d="M11.5 1.5l3 3L5 14H2v-3L11.5 1.5z" fill="none" stroke="#2e7d32" stroke-width="1.5"/>
</svg>"""

ICON_DELETE = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<path d="M4 4l8 8M12 4l-8 8" stroke="#c62828" stroke-width="2"/>
</svg>"""

ICON_PLUS = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<path d="M8 3v10M3 8h10" stroke="#2e7d32" stroke-width="2"/>
</svg>"""

ICON_REMOVE = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<path d="M4 4l8 8M12 4l-8 8" stroke="#c62828" stroke-width="2.5" stroke-linecap="round"/>
</svg>"""

ICON_REMOVE_WHITE = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<path d="M4 4l8 8M12 4l-8 8" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round"/>
</svg>"""

ICON_FOLDER = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<path d="M2 4h5l1 2h6v7H2V4z" fill="#ffc107" stroke="#f9a825" stroke-width="1"/>
</svg>"""

ICON_FILE = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<path d="M4 1h6l3 3v10H4V1z" fill="#ffffff" stroke="#616161" stroke-width="1"/>
<path d="M10 1v3h3" fill="none" stroke="#616161" stroke-width="1"/>
<path d="M6 8h5M6 10h5M6 12h3" stroke="#9e9e9e" stroke-width="0.8"/>
</svg>"""

ICON_CHEVRON_DOWN = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<path d="M4 6l4 4 4-4" fill="none" stroke="#424242" stroke-width="2" stroke-linecap="round"/>
</svg>"""

ICON_CHEVRON_RIGHT = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<path d="M6 4l4 4-4 4" fill="none" stroke="#424242" stroke-width="2" stroke-linecap="round"/>
</svg>"""


def play_icon() -> QIcon:
    """Иконка активации (play)."""
    return _svg_to_icon(ICON_PLAY)


def pause_icon() -> QIcon:
    """Иконка паузы (деактивированная задача)."""
    return _svg_to_icon(ICON_PAUSE)


def edit_icon() -> QIcon:
    """Иконка редактирования (карандаш)."""
    return _svg_to_icon(ICON_EDIT)


def delete_icon() -> QIcon:
    """Иконка удаления (крестик)."""
    return _svg_to_icon(ICON_DELETE)


def plus_icon() -> QIcon:
    """Иконка плюс."""
    return _svg_to_icon(ICON_PLUS)


def remove_icon() -> QIcon:
    """Иконка удаления из списка."""
    return _svg_to_icon(ICON_REMOVE)


def remove_icon_white() -> QIcon:
    """Иконка удаления (белый крестик для hover)."""
    return _svg_to_icon(ICON_REMOVE_WHITE)


def folder_icon() -> QIcon:
    """Иконка папки."""
    return _svg_to_icon(ICON_FOLDER)


def file_icon() -> QIcon:
    """Иконка текстового файла."""
    return _svg_to_icon(ICON_FILE)


def chevron_down_icon() -> QIcon:
    """Иконка раскрытого блока."""
    return _svg_to_icon(ICON_CHEVRON_DOWN)


def chevron_right_icon() -> QIcon:
    """Иконка свёрнутого блока."""
    return _svg_to_icon(ICON_CHEVRON_RIGHT)

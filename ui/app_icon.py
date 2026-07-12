"""Иконка приложения из SVG."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from services.path_utils import get_app_dir

APP_ICON_SVG = "archiver_icon.svg"
APP_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def app_icon_path() -> Path:
    """Путь к SVG-иконке приложения."""
    return get_app_dir() / "assets" / APP_ICON_SVG


def app_icon() -> QIcon:
    """Загружает иконку приложения из SVG (несколько размеров для DPI)."""
    path = app_icon_path()
    icon = QIcon()
    if not path.is_file():
        return icon

    renderer = QSvgRenderer(str(path))
    if not renderer.isValid():
        return icon

    for size in APP_ICON_SIZES:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon

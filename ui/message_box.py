"""Диалоги сообщений без выделения текста."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMessageBox, QWidget

from ui.window_chrome import schedule_window_chrome


def _theme_name(parent: Optional[QWidget]) -> str:
    if parent is not None and hasattr(parent, "_settings"):
        return parent._settings.theme
    return "light"


def _prepare_box(box: QMessageBox, parent: Optional[QWidget]) -> None:
    """Отключает выделение текста и настраивает заголовок окна."""
    for label in box.findChildren(QLabel):
        label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    schedule_window_chrome(box, theme=_theme_name(parent))


def question(parent: Optional[QWidget], title: str, text: str) -> bool:
    """Вопрос «Да / Нет»."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    yes_btn = box.button(QMessageBox.StandardButton.Yes)
    no_btn = box.button(QMessageBox.StandardButton.No)
    if yes_btn is not None:
        yes_btn.setText("Да")
    if no_btn is not None:
        no_btn.setText("Нет")
    _prepare_box(box, parent)
    return box.exec() == QMessageBox.StandardButton.Yes


def information(parent: Optional[QWidget], title: str, text: str) -> None:
    """Информационное сообщение."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Information)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    ok_btn = box.button(QMessageBox.StandardButton.Ok)
    if ok_btn is not None:
        ok_btn.setText("ОК")
    _prepare_box(box, parent)
    box.exec()


def warning(parent: Optional[QWidget], title: str, text: str) -> None:
    """Предупреждение."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    ok_btn = box.button(QMessageBox.StandardButton.Ok)
    if ok_btn is not None:
        ok_btn.setText("ОК")
    _prepare_box(box, parent)
    box.exec()

"""Курсор «рука» для интерактивных элементов."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QComboBox,
    QListWidget,
    QWidget,
)


def _set_hand_cursor(widget: QWidget) -> None:
    widget.setCursor(Qt.CursorShape.PointingHandCursor)


def _set_arrow_cursor(widget: QWidget) -> None:
    widget.setCursor(Qt.CursorShape.ArrowCursor)


def _apply_widget_cursor(widget: QWidget) -> None:
    """Задаёт курсор одному виджету по его типу."""
    if isinstance(widget, QCheckBox):
        if widget.text().strip():
            _set_arrow_cursor(widget)
        else:
            _set_hand_cursor(widget)
        return
    if isinstance(widget, QAbstractButton):
        _set_hand_cursor(widget)
        return
    if isinstance(widget, (QComboBox, QListWidget)):
        _set_hand_cursor(widget)


def apply_interactive_cursors(root: QWidget) -> None:
    """Устанавливает курсор-указатель на кликабельные элементы."""
    _apply_widget_cursor(root)
    for child in root.findChildren(QWidget):
        _apply_widget_cursor(child)


class InteractiveCursorFilter(QObject):
    """Автоматически задаёт курсор для новых интерактивных виджетов."""

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ChildAdded:
            child = event.child()
            if isinstance(child, QWidget):
                _apply_widget_cursor(child)
        return False


def install_interactive_cursors(app: QApplication) -> InteractiveCursorFilter:
    """Подключает глобальный фильтр курсора."""
    cursor_filter = InteractiveCursorFilter(app)
    app.installEventFilter(cursor_filter)
    return cursor_filter


# Совместимость со старым именем
apply_pointing_hand_cursors = apply_interactive_cursors
install_button_cursors = install_interactive_cursors

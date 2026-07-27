"""Переопределённые виджеты для особых случаев ввода."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QSpinBox, QWidget


class NoWheelComboBox(QComboBox):
    """QComboBox без смены значения колёсиком мыши."""

    def wheelEvent(self, event) -> None:
        event.ignore()


class FullRowCheckBox(QCheckBox):
    """Чекбокс, у которого кликабельна вся площадь виджета."""

    def hitButton(self, pos: QPoint) -> bool:
        return self.rect().contains(pos)


class NoSelectStepSpinBox(QSpinBox):
    """QSpinBox без выделения текста после нажатия кнопок +/-."""

    def stepBy(self, steps: int) -> None:
        super().stepBy(steps)
        editor = self.lineEdit()
        if editor is not None:
            editor.deselect()
            editor.setCursorPosition(len(editor.text()))


class ActionCellContainer(QWidget):
    """Контейнер кнопок в ячейке: фон строки (select/hover) без смены QSS."""

    def __init__(self, parent=None) -> None:
        """Создаёт контейнер с полной отрисовкой фона ячейки."""
        super().__init__(parent)
        self._base_bg = QColor()
        self._highlight_bg: Optional[QColor] = None
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        # Рисуем все пиксели сами: и базовый фон таблицы, и select/hover.
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def set_row_chrome(
        self,
        *,
        base: QColor,
        highlight: Optional[QColor],
    ) -> None:
        """Задаёт фон таблицы и поверх — выделение или hover (с альфой)."""
        new_base = QColor(base) if base.isValid() else QColor()
        new_hi = (
            QColor(highlight)
            if highlight is not None and highlight.isValid()
            else None
        )
        if self._base_bg == new_base and self._highlight_bg == new_hi:
            return
        self._base_bg = new_base
        self._highlight_bg = new_hi
        self.update()

    def paintEvent(self, event) -> None:
        """Сначала фон таблицы, затем select/hover (как у делегата строки)."""
        painter = QPainter(self)
        rect = self.rect()
        if self._base_bg.isValid():
            painter.fillRect(rect, self._base_bg)
        if self._highlight_bg is not None:
            painter.fillRect(rect, self._highlight_bg)

def static_label(text: str) -> QLabel:
    """Метка без выделения текста мышью."""
    label = QLabel(text)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    label.setCursor(Qt.CursorShape.ArrowCursor)
    return label

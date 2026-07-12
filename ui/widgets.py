"""Переопределённые виджеты для особых случаев ввода."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLabel, QSpinBox


class NoWheelComboBox(QComboBox):
    """QComboBox без смены значения колёсиком мыши."""

    def wheelEvent(self, event) -> None:
        event.ignore()


class NoSelectStepSpinBox(QSpinBox):
    """QSpinBox без выделения текста после нажатия кнопок +/-."""

    def stepBy(self, steps: int) -> None:
        super().stepBy(steps)
        editor = self.lineEdit()
        if editor is not None:
            editor.deselect()
            editor.setCursorPosition(len(editor.text()))


def static_label(text: str) -> QLabel:
    """Метка без выделения текста мышью."""
    label = QLabel(text)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    label.setCursor(Qt.CursorShape.ArrowCursor)
    return label

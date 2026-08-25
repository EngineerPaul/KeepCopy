"""Окно настроек приложения."""

from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
)

from models.app_settings import COLUMN_KEYS, COLUMN_LABELS, AppSettings
from ui.cursors import apply_interactive_cursors
from ui.themes import apply_window_theme
from ui.widgets import FullRowCheckBox, NoSelectStepSpinBox, static_label
from ui.window_chrome import schedule_window_chrome


class SettingsDialog(QDialog):
    """Диалог настроек приложения."""

    def __init__(self, settings: AppSettings, parent=None) -> None:
        """Создаёт окно настроек."""
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.resize(420, 380)
        self._original = deepcopy(settings)
        self._result = deepcopy(settings)
        self._build_ui()

    def _build_ui(self) -> None:
        """Строит интерфейс настроек."""
        layout = QVBoxLayout(self)

        theme_row = QHBoxLayout()
        theme_row.addWidget(static_label("Тема:"))
        self._theme = QComboBox()
        self._theme.addItem("Светлая", "light")
        self._theme.addItem("Тёмная", "dark")
        idx = self._theme.findData(self._result.theme)
        self._theme.setCurrentIndex(max(idx, 0))
        theme_row.addWidget(self._theme)
        theme_row.addStretch()
        layout.addLayout(theme_row)

        layout.addWidget(static_label("Поля панели задач:"))
        self._columns = QListWidget()
        self._columns.setMaximumHeight(140)
        self._columns.setSelectionMode(QAbstractItemView.NoSelection)
        self._columns.setFocusPolicy(Qt.NoFocus)
        self._columns.setAutoScroll(False)
        self._columns.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        for key in COLUMN_KEYS:
            if key == "actions":
                continue
            item = QListWidgetItem()
            item.setData(Qt.UserRole, key)
            item.setFlags(Qt.ItemIsEnabled)
            self._columns.addItem(item)
            checkbox = FullRowCheckBox(COLUMN_LABELS[key])
            checkbox.setChecked(self._result.visible_columns.get(key, True))
            checkbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            checkbox.setMinimumWidth(1)
            self._columns.setItemWidget(item, checkbox)
        layout.addWidget(self._columns)

        font_row = QHBoxLayout()
        font_row.addWidget(static_label("Шрифт:"))
        self._font_size = NoSelectStepSpinBox()
        self._font_size.setRange(10, 16)
        self._font_size.setValue(self._result.font_size)
        font_row.addWidget(self._font_size)
        font_row.addStretch()
        layout.addLayout(font_row)

        autostart_row = QHBoxLayout()
        autostart_row.setSpacing(6)
        self._autostart = QCheckBox()
        self._autostart.setChecked(self._result.autostart)
        autostart_row.addWidget(self._autostart)
        autostart_row.addWidget(static_label("Автозапуск при старте системы"))
        autostart_row.addStretch()
        layout.addLayout(autostart_row)

        layout.addStretch()

        buttons = QDialogButtonBox()
        apply_btn = buttons.addButton("Применить", QDialogButtonBox.ApplyRole)
        cancel_btn = buttons.addButton("Отмена", QDialogButtonBox.RejectRole)
        apply_btn.clicked.connect(self._apply)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def showEvent(self, event) -> None:
        """Подстраивает заголовок окна и курсоры под тему."""
        super().showEvent(event)
        theme = self._dialog_theme()
        apply_window_theme(self, theme)
        schedule_window_chrome(self, theme=theme)
        apply_interactive_cursors(self)

    def _dialog_theme(self) -> str:
        parent = self.parent()
        if parent is not None and hasattr(parent, "_settings"):
            return parent._settings.theme
        return "light"

    def _apply(self) -> None:
        """Применяет настройки и закрывает окно."""
        self._result.theme = self._theme.currentData()
        self._result.font_size = self._font_size.value()
        self._result.autostart = self._autostart.isChecked()
        for i in range(self._columns.count()):
            item = self._columns.item(i)
            key = item.data(Qt.UserRole)
            checkbox = self._columns.itemWidget(item)
            checked = isinstance(checkbox, QCheckBox) and checkbox.isChecked()
            self._result.visible_columns[key] = checked
        self._result.visible_columns["actions"] = True
        self._original = deepcopy(self._result)
        self.accept()

    def get_settings(self) -> AppSettings:
        """Возвращает применённые настройки."""
        return self._result

    def reject(self) -> None:
        """Отменяет изменения."""
        self._result = deepcopy(self._original)
        super().reject()

"""Окно справки."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTextBrowser,
    QVBoxLayout,
)

from ui.themes import apply_window_theme, set_themed_html
from ui.window_chrome import schedule_window_chrome

HELP_TEXT = """
<h2>Архиватор — краткая справка</h2>

<p><b>Создание задачи.</b> Нажмите «Создать», укажите название, один или несколько путей копирования и папку архива. Добавьте исключения при необходимости. Выберите режим копирования и нажмите «Сохранить».</p>

<p><b>Источники.</b> Для папки в архиве создаётся подпапка с её именем; для отдельного файла — подпапка «имя_родительской_папки_files». Несколько источников добавляются кнопкой «+».</p>

<p><b>Исключения.</b> Шаблоны вроде <code>*.tmp</code> или <code>**.png</code> исключают файлы из копирования. Подробнее — в файле FILTERS.md.</p>

<p><b>Режимы.</b> «Сохранять изменения» и «Сохранять слоями» — копируются файлы новее последнего запуска и файлы, которых ещё нет в архиве (даты создания/изменения не важны, если файла в архиве нет). «Сохранять слоями» и «Дублирование» каждый раз создают новый слой backup_ДД.ММ.ГГГГ_NNN; «Дублирование» кладёт в слой полную копию всех подходящих файлов. Ручной и автоматический запуск используют одинаковые правила отбора.</p>

<p><b>Расписание.</b> Укажите время и периодичность (дней). Активные задачи запускаются автоматически. Кнопка «Выполнить» запускает выделенные задачи вручную.</p>

<p><b>Таблица.</b> Клик по строке раскрывает список источников и исключений. Правый клик по пути в колонках «Источники» или «Архив» открывает эту директорию в проводнике. Кнопки в колонке «Действия»: активация, редактирование, удаление. Для горизонтальной прокрутки зажмите Alt и прокрутите колёсико мыши.</p>

<p><b>Ошибки.</b> Пропущенные файлы записываются в папку errors. Журнал — в backup.log.</p>
"""


class HelpDialog(QDialog):
    """Диалог справки по программе."""

    def __init__(self, parent=None) -> None:
        """Создаёт окно справки."""
        super().__init__(parent)
        self.setWindowTitle("Помощь")
        self.resize(520, 420)
        layout = QVBoxLayout(self)
        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        layout.addWidget(self._browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn is not None:
            close_btn.setText("Закрыть")
        buttons.rejected.connect(self.close)
        buttons.accepted.connect(self.close)
        layout.addWidget(buttons)

    def _dialog_theme(self) -> str:
        parent = self.parent()
        if parent is not None and hasattr(parent, "_settings"):
            return parent._settings.theme
        return "light"

    def showEvent(self, event) -> None:
        """Подстраивает оформление под текущую тему."""
        super().showEvent(event)
        theme = self._dialog_theme()
        apply_window_theme(self, theme)
        set_themed_html(self._browser, HELP_TEXT, theme)
        schedule_window_chrome(self, theme=theme)

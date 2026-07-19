"""Таблица задач на главном окне: выделение, hover, обрезка путей."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QEvent, QObject, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFontMetrics, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.icons import edit_icon, pause_icon, play_icon, remove_icon, remove_icon_white
from ui.themes import ThemeColors, apply_table_theme, delete_button_style, get_theme_colors, icon_button_style
from ui.widgets import ActionCellContainer

UI_ROW_NUM = "__row_num__"

TASK_ID_ROLE = Qt.ItemDataRole.UserRole
SOURCES_FIRST_ROLE = Qt.ItemDataRole.UserRole + 1
SOURCES_EXTRA_ROLE = Qt.ItemDataRole.UserRole + 2
PATH_TEXT_ROLE = Qt.ItemDataRole.UserRole + 3
FADED_ROLE = Qt.ItemDataRole.UserRole + 4
ACTIVE_ROW_ROLE = Qt.ItemDataRole.UserRole + 5
DETAIL_ROW_ROLE = Qt.ItemDataRole.UserRole + 6

_ROW_NUM_WIDTH = 30

_CENTERED_COLS = frozenset({
    UI_ROW_NUM,
    "schedule_time",
    "period_days",
    "last_run",
    "next_run",
    "copy_mode",
    "compress",
    "total_size",
})

_ELIDE_COLS = frozenset({"sources", "destination", "exclusions"})
_CLICKABLE_PATH_COLS = frozenset({"sources", "destination"})

_DELETE_BTN_STYLE = delete_button_style()


def _icon_btn_style(theme: str) -> str:
    return icon_button_style(theme)


class DeleteActionButton(QPushButton):
    """Кнопка удаления задачи: красный hover, белый крестик."""

    def __init__(self, parent=None) -> None:
        """Создаёт кнопку удаления."""
        super().__init__(parent)
        self.setIcon(remove_icon())
        self.setIconSize(QSize(12, 12))
        self.setFlat(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(16, 16)
        self.setStyleSheet(_DELETE_BTN_STYLE)
        self.setToolTip("Удалить")

    def enterEvent(self, event) -> None:
        """Белый крестик при наведении."""
        self.setIcon(remove_icon_white())
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Красный крестик в обычном состоянии."""
        self.setIcon(remove_icon())
        super().leaveEvent(event)


class MainTableDelegate(QStyledItemDelegate):
    """Делегат ячеек таблицы задач."""

    def __init__(self, table: "MainTableWidget") -> None:
        """Привязывает делегат к таблице."""
        super().__init__(table)
        self._table = table

    def _col_key(self, col: int) -> str:
        cols = self._table.column_keys()
        if 0 <= col < len(cols):
            return cols[col]
        return ""

    def _row_bg(self, row: int) -> Optional[QColor]:
        if self._table.is_detail_row(row):
            return None
        colors = self._table.theme_colors()
        selected = self._table.is_row_selected(row)
        hovered = row == self._table.hover_row() and not selected
        if selected:
            return colors.select_bg
        if hovered:
            return colors.hover_bg
        return None

    def _text_color(self, index, selected: bool) -> QColor:
        row = index.row()
        colors = self._table.theme_colors()
        if index.data(DETAIL_ROW_ROLE):
            return colors.detail
        if selected:
            return colors.select_text
        fg = index.data(Qt.ItemDataRole.ForegroundRole)
        if fg is not None:
            return fg.color() if hasattr(fg, "color") else QColor(fg)
        if self._table.is_inactive_row(row):
            return colors.faded
        return colors.text

    def paint(self, painter, option, index) -> None:
        """Рисует ячейку с фоном строки и обрезкой по элементам."""
        # Своё выделение строк; флаги Qt Selected/HasFocus дают «подсветку ячейки».
        opt = QStyleOptionViewItem(option)
        opt.state &= ~(
            QStyle.StateFlag.State_Selected
            | QStyle.StateFlag.State_HasFocus
            | QStyle.StateFlag.State_MouseOver
        )
        row = index.row()
        col_key = self._col_key(index.column())
        selected = self._table.is_row_selected(row)
        bg = self._row_bg(row)

        painter.save()
        if bg is not None:
            painter.fillRect(opt.rect, bg)

        if col_key in _ELIDE_COLS:
            self._paint_elided(painter, opt, index, col_key, selected)
        else:
            text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
            align = Qt.AlignmentFlag.AlignCenter if col_key in _CENTERED_COLS else (
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            painter.setPen(self._text_color(index, selected))
            painter.drawText(opt.rect.adjusted(4, 0, -4, 0), int(align), text)
        painter.restore()

    def _paint_elided(
        self, painter, option, index, col_key: str, selected: bool
    ) -> None:
        """Рисует путь с обрезкой по элементам (суффикс +N не обрезается)."""
        metrics = QFontMetrics(option.font)
        rect = option.rect.adjusted(4, 0, -4, 0)
        painter.setPen(self._text_color(index, selected))

        if col_key in ("sources", "exclusions"):
            first = str(index.data(SOURCES_FIRST_ROLE) or "")
            extra = int(index.data(SOURCES_EXTRA_ROLE) or 0)
            suffix = f"  +{extra}" if extra > 0 else ""
            suffix_w = metrics.horizontalAdvance(suffix) if suffix else 0
            path_w = max(0, rect.width() - suffix_w)
            elided = metrics.elidedText(first, Qt.TextElideMode.ElideRight, path_w)
            painter.drawText(
                rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                elided + suffix,
            )
        else:
            path = str(index.data(PATH_TEXT_ROLE) or index.data(
                Qt.ItemDataRole.DisplayRole
            ) or "")
            elided = metrics.elidedText(path, Qt.TextElideMode.ElideRight, rect.width())
            painter.drawText(
                rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                elided,
            )


class MainTableWidget(QTableWidget):
    """Таблица задач с кастомным выделением и hover."""

    def __init__(self, parent=None) -> None:
        """Создаёт таблицу задач."""
        super().__init__(parent)
        self._col_keys: list[str] = []
        self._theme = "light"
        self._hover_row = -1
        self._selected_rows: set[int] = set()
        self._anchor_row = -1
        self._task_row_ids: dict[int, str] = {}
        self._active_rows: set[int] = set()
        self._detail_rows: set[int] = set()
        self._on_task_selected: Optional[Callable[[list[str]], None]] = None

        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)
        self.installEventFilter(self)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setItemDelegate(MainTableDelegate(self))
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._theme = "light"

    def set_theme(self, theme: str) -> None:
        """Задаёт тему отрисовки таблицы."""
        self._theme = theme
        apply_table_theme(self, theme)
        for row in range(self.rowCount()):
            self._apply_row_widget_bg(row)
        self.viewport().update()

    def theme_colors(self) -> ThemeColors:
        """Палитра текущей темы."""
        return get_theme_colors(self._theme)

    def column_keys(self) -> list[str]:
        """Ключи колонок в порядке отображения."""
        return self._col_keys

    def set_column_keys(self, keys: list[str]) -> None:
        """Задаёт ключи колонок."""
        self._col_keys = list(keys)

    def col_index(self, key: str) -> int:
        """Индекс колонки по ключу."""
        try:
            return self._col_keys.index(key)
        except ValueError:
            return -1

    def _col_key_at(self, col: int) -> str:
        """Ключ колонки по индексу."""
        if 0 <= col < len(self._col_keys):
            return self._col_keys[col]
        return ""

    def set_on_task_selected(self, callback: Callable[[list[str]], None]) -> None:
        """Callback при изменении выделения задач."""
        self._on_task_selected = callback

    def hover_row(self) -> int:
        """Строка под курсором."""
        return self._hover_row

    def is_row_selected(self, row: int) -> bool:
        """Проверяет, выделена ли строка."""
        return row in self._selected_rows

    def selected_row(self) -> int:
        """Первая выделенная строка (для совместимости)."""
        if not self._selected_rows:
            return -1
        return min(self._selected_rows)

    def selected_task_ids(self) -> list[str]:
        """ID выделенных задач в порядке строк таблицы."""
        rows = sorted(self._selected_rows)
        return [self._task_row_ids[r] for r in rows if r in self._task_row_ids]

    def set_selected_task_ids(self, task_ids: list[str]) -> None:
        """Устанавливает выделение по списку ID задач."""
        id_set = set(task_ids)
        rows = {r for r, tid in self._task_row_ids.items() if tid in id_set}
        anchor = max(rows) if rows else -1
        self._set_selected_rows(rows, anchor=anchor)

    def set_selected_task_id(self, task_id: Optional[str]) -> None:
        """Устанавливает выделение одной задачи."""
        if task_id:
            self.set_selected_task_ids([task_id])
        else:
            self.clear_selection()

    def clear_selection(self) -> None:
        """Снимает выделение со всех строк."""
        self._set_selected_rows(set(), anchor=-1)

    def register_task_row(self, row: int, task_id: str, *, active: bool) -> None:
        """Регистрирует строку задачи."""
        self._task_row_ids[row] = task_id
        if active:
            self._active_rows.add(row)

    def register_detail_row(self, row: int) -> None:
        """Регистрирует строку деталей."""
        self._detail_rows.add(row)

    def clear_row_registry(self) -> None:
        """Сбрасывает реестр строк перед перестроением таблицы."""
        self._task_row_ids.clear()
        self._active_rows.clear()
        self._detail_rows.clear()
        self._hover_row = -1
        self._selected_rows.clear()
        self._anchor_row = -1

    def is_detail_row(self, row: int) -> bool:
        """Проверяет, является ли строка детализацией."""
        return row in self._detail_rows

    def is_active_row(self, row: int) -> bool:
        """Проверяет, активна ли задача в строке."""
        return row in self._active_rows

    def is_inactive_row(self, row: int) -> bool:
        """Проверяет, деактивирована ли задача в строке."""
        return row in self._task_row_ids and row not in self._active_rows

    def task_id_at_row(self, row: int) -> Optional[str]:
        """Возвращает ID задачи для строки."""
        return self._task_row_ids.get(row)

    def row_for_task_id(self, task_id: str) -> int:
        """Возвращает строку задачи по ID."""
        for row, tid in self._task_row_ids.items():
            if tid == task_id:
                return row
        return -1

    def set_actions_widget(self, row: int, widget: QWidget) -> None:
        """Устанавливает виджет действий и подключает отслеживание мыши."""
        ci = self.col_index("actions")
        if ci < 0:
            return
        self.setCellWidget(row, ci, widget)
        self._track_action_widget(widget)
        self._apply_row_widget_bg(row)

    def _track_action_widget(self, widget: QWidget) -> None:
        """Подключает фильтр событий к виджету действий."""
        widget.setMouseTracking(True)
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            if child is widget:
                continue
            child.setMouseTracking(True)
            child.installEventFilter(self)

    def _row_for_action_widget(self, obj: QObject) -> int:
        """Возвращает строку для виджета действий."""
        ci = self.col_index("actions")
        if ci < 0:
            return -1
        for row in range(self.rowCount()):
            widget = self.cellWidget(row, ci)
            if widget is not None and (obj is widget or widget.isAncestorOf(obj)):
                return row
        return -1

    def _is_action_widget(self, obj: QObject) -> bool:
        """Проверяет, относится ли объект к колонке действий."""
        return self._row_for_action_widget(obj) >= 0

    def eventFilter(self, obj, event) -> bool:
        """Отслеживает положение мыши."""
        et = event.type()
        if et in (
            QEvent.Type.MouseMove,
            QEvent.Type.HoverMove,
            QEvent.Type.Enter,
        ):
            action_row = self._row_for_action_widget(obj)
            if action_row >= 0:
                self._set_hover_row(action_row)
                self.viewport().unsetCursor()
            elif obj is self.viewport() or obj is self:
                self._update_hover_from_global(event.globalPosition().toPoint())
        elif et == QEvent.Type.Leave:
            if obj is self.viewport() or self._is_action_widget(obj):
                QTimer.singleShot(0, self._recheck_hover)
        return super().eventFilter(obj, event)

    def _recheck_hover(self) -> None:
        """Проверяет, остался ли курсор над таблицей."""
        if not self.isVisible():
            return
        from PySide6.QtGui import QCursor

        global_pos = QCursor.pos()
        if not self.rect().contains(self.mapFromGlobal(global_pos)):
            self._set_hover_row(-1)
            self.viewport().unsetCursor()
            return
        self._update_hover_from_global(global_pos)

    def leaveEvent(self, event) -> None:
        """Сбрасывает hover при уходе курсора."""
        self._set_hover_row(-1)
        self.viewport().unsetCursor()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Обновляет hover при движении мыши."""
        super().mouseMoveEvent(event)
        self._update_hover_from_global(event.globalPosition().toPoint())

    def mousePressEvent(self, event) -> None:
        """Выделяет строки задач (Ctrl/Shift) или снимает выделение."""
        pos = event.position().toPoint()
        row = self.rowAt(pos.y())
        mods = event.modifiers()
        has_modifier = bool(
            mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
        )
        # Сначала Qt (cellClicked и т.п.), затем своё выделение строки.
        super().mousePressEvent(event)
        if event.button() != Qt.MouseButton.LeftButton:
            self._clear_qt_current_cell()
            return
        if row in self._task_row_ids:
            self._apply_selection_click(row, mods)
            self._notify_selection_changed()
        elif (row < 0 or row in self._detail_rows) and not has_modifier:
            self.clear_selection()
            self._notify_selection_changed()
        # Иначе Qt оставляет «текущую ячейку» — визуально как выделение одной клетки.
        self._clear_qt_current_cell()

    def _clear_qt_current_cell(self) -> None:
        """Сбрасывает системное текущее/выделенное состояние Qt."""
        from PySide6.QtCore import QModelIndex

        self.setCurrentIndex(QModelIndex())
        QAbstractItemView.clearSelection(self)

    def _sorted_task_rows(self) -> list[int]:
        """Строки задач в порядке отображения."""
        return sorted(self._task_row_ids.keys())

    def _apply_selection_click(self, row: int, mods: Qt.KeyboardModifier) -> None:
        """Обрабатывает клик с учётом Ctrl и Shift."""
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)

        if shift:
            anchor = self._anchor_row if self._anchor_row in self._task_row_ids else row
            task_rows = self._sorted_task_rows()
            i_anchor = task_rows.index(anchor)
            i_row = task_rows.index(row)
            lo, hi = min(i_anchor, i_row), max(i_anchor, i_row)
            range_rows = set(task_rows[lo : hi + 1])
            if ctrl:
                new_sel = self._selected_rows | range_rows
            else:
                new_sel = range_rows
            self._set_selected_rows(new_sel, anchor=anchor)
        elif ctrl:
            new_sel = set(self._selected_rows)
            if row in new_sel:
                new_sel.discard(row)
            else:
                new_sel.add(row)
            self._set_selected_rows(new_sel, anchor=row)
        else:
            self._set_selected_rows({row}, anchor=row)

    def _notify_selection_changed(self) -> None:
        """Уведомляет о смене выделения."""
        if self._on_task_selected:
            self._on_task_selected(self.selected_task_ids())

    def _update_hover_from_global(self, global_pos) -> None:
        """Определяет строку под курсором."""
        local = self.viewport().mapFromGlobal(global_pos)
        if not self.viewport().rect().contains(local):
            self._set_hover_row(-1)
            self._update_path_cursor_at_global(global_pos)
            return
        row = self.rowAt(local.y())
        if row in self._task_row_ids:
            self._set_hover_row(row)
        else:
            self._set_hover_row(-1)
        self._update_path_cursor_at_global(global_pos)

    def _is_clickable_path_cell(self, row: int, col: int) -> bool:
        """Проверяет, открывается ли ячейка в проводнике по клику."""
        col_key = self._col_key_at(col)
        if col_key not in _CLICKABLE_PATH_COLS:
            return False
        item = self.item(row, col)
        if item is None:
            return False
        if row in self._detail_rows:
            return col_key == "sources" and bool(item.data(PATH_TEXT_ROLE))
        if row not in self._task_row_ids:
            return False
        if col_key == "destination":
            return bool(item.data(PATH_TEXT_ROLE))
        return bool(item.data(SOURCES_FIRST_ROLE))

    def _update_path_cursor_at_global(self, global_pos) -> None:
        """Меняет курсор над кликабельными путями «Источник» и «Архив»."""
        local = self.viewport().mapFromGlobal(global_pos)
        if not self.viewport().rect().contains(local):
            self.viewport().unsetCursor()
            return
        index = self.indexAt(local)
        if (
            index.isValid()
            and self._is_clickable_path_cell(index.row(), index.column())
        ):
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.viewport().unsetCursor()

    def _set_hover_row(self, row: int) -> None:
        """Обновляет подсветку при наведении."""
        if row == self._hover_row:
            return
        old = self._hover_row
        self._hover_row = row
        self._refresh_rows(old, row)

    def _set_selected_rows(self, rows: set[int], *, anchor: int) -> None:
        """Обновляет выделение нескольких строк."""
        rows = {r for r in rows if r in self._task_row_ids}
        if rows == self._selected_rows and anchor == self._anchor_row:
            return
        old = set(self._selected_rows)
        self._selected_rows = rows
        self._anchor_row = anchor if rows else -1
        self._refresh_rows(*old, *rows)

    def _refresh_rows(self, *rows: int) -> None:
        """Перерисовывает указанные строки."""
        for row in rows:
            if row >= 0:
                self._apply_row_widget_bg(row)
        self.viewport().update()

    def _apply_row_widget_bg(self, row: int) -> None:
        """Подсвечивает контейнер кнопок: select и hover, как у остальных ячеек."""
        ci = self.col_index("actions")
        if ci < 0:
            return
        widget = self.cellWidget(row, ci)
        if not isinstance(widget, ActionCellContainer):
            return
        widget.set_row_chrome(
            base=self._row_base_color(row),
            highlight=self._row_bg_color(row),
        )

    def _row_base_color(self, row: int) -> QColor:
        """Фон строки без select/hover (с учётом чередования цветов)."""
        pal = self.palette()
        if self.alternatingRowColors() and row % 2 == 1:
            return pal.color(QPalette.ColorRole.AlternateBase)
        return pal.color(QPalette.ColorRole.Base)

    def _row_bg_color(self, row: int) -> Optional[QColor]:
        """Фон контейнера кнопок: выделение (фокус) или наведение."""
        if row in self._detail_rows:
            return None
        colors = self.theme_colors()
        if row in self._selected_rows:
            return colors.select_bg
        if row == self._hover_row:
            return colors.hover_bg
        return None


def make_table_item(
    text: str,
    *,
    task_id: Optional[str] = None,
    centered: bool = False,
    faded: bool = False,
    detail: bool = False,
    active: bool = False,
    sources_first: str = "",
    sources_extra: int = 0,
    path_text: str = "",
) -> QTableWidgetItem:
    """Создаёт ячейку таблицы задач."""
    item = QTableWidgetItem(text)
    item.setFlags(
        item.flags()
        & ~Qt.ItemFlag.ItemIsEditable
        & ~Qt.ItemFlag.ItemIsSelectable
    )
    if centered:
        item.setTextAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
    if task_id is not None:
        item.setData(TASK_ID_ROLE, task_id)
    if faded:
        item.setData(FADED_ROLE, True)
    if detail:
        item.setData(DETAIL_ROW_ROLE, True)
    if active:
        item.setData(ACTIVE_ROW_ROLE, True)
    if sources_first:
        item.setData(SOURCES_FIRST_ROLE, sources_first)
        item.setData(SOURCES_EXTRA_ROLE, sources_extra)
    if path_text:
        item.setData(PATH_TEXT_ROLE, path_text)
    return item


def make_actions_widget(
    *,
    is_active: bool,
    on_toggle,
    on_edit,
    on_delete,
    theme: str = "light",
) -> QWidget:
    """Создаёт центрированный блок кнопок действий."""
    container = ActionCellContainer()
    container.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
    )
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    btn_toggle = QPushButton()
    if is_active:
        btn_toggle.setIcon(play_icon())
        btn_toggle.setToolTip("Приостановить")
    else:
        btn_toggle.setIcon(pause_icon())
        btn_toggle.setToolTip("Активировать")
    btn_toggle.setIconSize(QSize(16, 16))
    btn_toggle.setFlat(True)
    btn_toggle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    btn_toggle.setFixedSize(18, 18)
    btn_style = _icon_btn_style(theme)
    btn_toggle.setStyleSheet(btn_style)
    btn_toggle.clicked.connect(on_toggle)

    btn_edit = QPushButton()
    btn_edit.setIcon(edit_icon())
    btn_edit.setIconSize(QSize(16, 16))
    btn_edit.setFlat(True)
    btn_edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    btn_edit.setFixedSize(18, 18)
    btn_edit.setStyleSheet(btn_style)
    btn_edit.setToolTip("Изменить")
    btn_edit.clicked.connect(on_edit)

    btn_del = DeleteActionButton()
    btn_del.clicked.connect(on_delete)

    layout.addWidget(btn_toggle)
    layout.addWidget(btn_edit)
    layout.addWidget(btn_del)
    return container

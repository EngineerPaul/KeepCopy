"""Окно создания и редактирования задачи."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Optional

from PySide6.QtCore import QEvent, QObject, QSize, QTimer, Qt
from PySide6.QtGui import QBrush, QColor, QCursor, QFontMetrics, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from models.task import CopyMode, Task
from services.path_utils import (
    find_nested_source_indices,
    format_time,
    normalize_path,
    path_exists,
    validate_directory_path,
    validate_filter,
    validate_path,
)
from services.scheduler import SchedulerService
from ui.icons import (
    chevron_down_icon,
    chevron_right_icon,
    file_icon,
    folder_icon,
    plus_icon,
    remove_icon,
    remove_icon_white,
)
from ui.message_box import question
from ui.cursors import apply_interactive_cursors
from ui.themes import (
    ThemeColors,
    apply_panel_inner,
    apply_panel_theme,
    apply_table_theme,
    apply_window_theme,
    collapsible_header_style,
    color,
    delete_button_style,
    get_theme_colors,
)
from ui.widgets import NoSelectStepSpinBox, NoWheelComboBox
from ui.window_chrome import schedule_window_chrome

_COL_NUM = 0
_COL_TEXT = 1
_COL_ACTION = 2
_NUM_WIDTH = 30
_ACTION_WIDTH = 30
_DELETE_BTN_SIZE = 16
_DELETE_ICON_SIZE = 12

_DELETE_BTN_STYLE = delete_button_style()


class DeleteRowButton(QPushButton):
    """Кнопка удаления строки: красный hover, белый крестик."""

    def __init__(self, parent=None) -> None:
        """Создаёт кнопку удаления."""
        super().__init__(parent)
        self.setIcon(remove_icon())
        self.setIconSize(QSize(_DELETE_ICON_SIZE, _DELETE_ICON_SIZE))
        self.setFlat(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(_DELETE_BTN_SIZE, _DELETE_BTN_SIZE)
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


class RowHighlightDelegate(QStyledItemDelegate):
    """Делегат: фон строки (hover/selected) и отрисовка ячеек."""

    def __init__(self, table: "ListTableWidget") -> None:
        """Привязывает делегат к таблице для доступа к hover-строке."""
        super().__init__(table)
        self._table = table

    def _row_state(self, row: int) -> tuple[bool, bool]:
        """Возвращает (выделена, наведена) для строки."""
        if row < 0:
            return False, False
        selected = self._table.selectionModel().isRowSelected(
            row, self._table.rootIndex()
        )
        hovered = row == self._table.hover_row() and not selected
        return selected, hovered

    def _paint_background(self, painter, option, row: int) -> None:
        """Рисует фон строки: основной или лёгкий."""
        colors = self._table.theme_colors()
        selected, hovered = self._row_state(row)
        if selected:
            painter.fillRect(option.rect, colors.select_bg)
        elif hovered:
            painter.fillRect(option.rect, colors.hover_bg)

    def _item_text_color(self, option, index, row: int) -> QColor:
        """Цвет текста ячейки: вложенный источник, выделение или по умолчанию."""
        fg = index.data(Qt.ItemDataRole.ForegroundRole)
        if isinstance(fg, QBrush):
            color = fg.color()
            if color.isValid():
                return color
        colors = self._table.theme_colors()
        selected, _ = self._row_state(row)
        if selected:
            return colors.select_text
        return colors.text

    def paint(self, painter, option, index) -> None:
        """Рисует ячейку с учётом состояния строки."""
        row = index.row()
        col = index.column()
        if col == _COL_ACTION:
            return
        painter.save()
        self._paint_background(painter, option, row)

        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        text_color = self._item_text_color(option, index, row)
        if col == _COL_TEXT:
            metrics = QFontMetrics(option.font)
            elided = metrics.elidedText(
                text, Qt.TextElideMode.ElideRight, option.rect.width() - 8
            )
            painter.setPen(text_color)
            painter.drawText(
                option.rect.adjusted(4, 0, -4, 0),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                elided,
            )
        elif col == _COL_NUM:
            painter.setPen(text_color)
            painter.drawText(
                option.rect,
                int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter),
                text,
            )
        painter.restore()


class ListTableWidget(QTableWidget):
    """Таблица списка с подсветкой строки при наведении и одиночным выбором."""

    def __init__(self, rows: int = 0, columns: int = 3, parent=None) -> None:
        """Создаёт таблицу списка."""
        super().__init__(rows, columns, parent)
        self._theme = "light"
        self._hover_row = -1
        self._selection_handler = None
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)
        self.installEventFilter(self)
        self.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setItemDelegate(RowHighlightDelegate(self))
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def set_theme(self, theme: str) -> None:
        """Задаёт тему отрисовки таблицы."""
        self._theme = theme
        apply_table_theme(self, theme)
        self.viewport().update()

    def theme_colors(self) -> ThemeColors:
        """Палитра текущей темы."""
        return get_theme_colors(self._theme)

    def hover_row(self) -> int:
        """Индекс строки под курсором (-1 если нет)."""
        return self._hover_row

    def set_selection_handler(self, handler) -> None:
        """Callback при выборе строки (table) или сбросе (None)."""
        self._selection_handler = handler

    def setCellWidget(self, row: int, column: int, widget: QWidget) -> None:
        """Устанавливает виджет ячейки и подключает отслеживание мыши."""
        old = self.cellWidget(row, column)
        if old is not None and old is not widget:
            self.removeCellWidget(row, column)
        super().setCellWidget(row, column, widget)
        self._track_action_widget(widget)

    def clear_rows(self) -> None:
        """Полностью очищает строки и виджеты действий."""
        for row in range(self.rowCount() - 1, -1, -1):
            if self.cellWidget(row, _COL_ACTION) is not None:
                self.removeCellWidget(row, _COL_ACTION)
        self.setRowCount(0)
        self._hover_row = -1
        self.clearSelection()

    def _track_action_widget(self, widget: QWidget) -> None:
        """Подключает фильтр событий к ячейке и её дочерним виджетам."""
        widget.setMouseTracking(True)
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            if child is widget:
                continue
            child.setMouseTracking(True)
            child.installEventFilter(self)

    def _row_for_action_widget(self, obj: QObject) -> int:
        """Возвращает номер строки для виджета в колонке действий."""
        for row in range(self.rowCount()):
            widget = self.cellWidget(row, _COL_ACTION)
            if widget is not None and (obj is widget or widget.isAncestorOf(obj)):
                return row
        return -1

    def _is_action_widget(self, obj: QObject) -> bool:
        """Проверяет, относится ли объект к кнопке удаления в колонке действий."""
        return self._row_for_action_widget(obj) >= 0

    def eventFilter(self, obj, event) -> bool:
        """Отслеживает положение мыши, в том числе над кнопкой удаления."""
        et = event.type()
        if et in (
            QEvent.Type.MouseMove,
            QEvent.Type.HoverMove,
            QEvent.Type.Enter,
        ):
            action_row = self._row_for_action_widget(obj)
            if action_row >= 0:
                self._set_hover_row(action_row)
            elif obj is self.viewport() or obj is self:
                self._update_hover_from_global(
                    event.globalPosition().toPoint()
                )
        elif et == QEvent.Type.Leave:
            if obj is self.viewport() or self._is_action_widget(obj):
                QTimer.singleShot(0, self._recheck_hover)
        return super().eventFilter(obj, event)

    def _recheck_hover(self) -> None:
        """Проверяет, остался ли курсор над таблицей (в т.ч. над кнопкой удаления)."""
        if not self.isVisible():
            return
        global_pos = QCursor.pos()
        if not self.rect().contains(self.mapFromGlobal(global_pos)):
            self._set_hover_row(-1)
            return
        self._update_hover_from_global(global_pos)

    def leaveEvent(self, event) -> None:
        """Сбрасывает hover при уходе курсора с таблицы."""
        self._set_hover_row(-1)
        super().leaveEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Обновляет hover при движении мыши."""
        super().mouseMoveEvent(event)
        self._update_hover_from_global(event.globalPosition().toPoint())

    def mousePressEvent(self, event) -> None:
        """Выделяет строку по клику; сбрасывает выделение при клике вне строк."""
        pos = event.position().toPoint()
        idx = self.indexAt(pos)
        if idx.isValid() and idx.column() != _COL_ACTION:
            self.selectRow(idx.row())
            if self._selection_handler:
                self._selection_handler(self)
        elif self.rowAt(pos.y()) < 0:
            self.clearSelection()
            if self._selection_handler:
                self._selection_handler(None)
        super().mousePressEvent(event)

    def _update_hover_from_global(self, global_pos) -> None:
        """Определяет строку под курсором."""
        local = self.viewport().mapFromGlobal(global_pos)
        if not self.viewport().rect().contains(local):
            self._set_hover_row(-1)
            return
        idx = self.indexAt(local)
        if idx.isValid():
            self._set_hover_row(idx.row())
        else:
            row = self.rowAt(local.y())
            self._set_hover_row(row if row >= 0 else -1)

    def _set_hover_row(self, row: int) -> None:
        """Обновляет лёгкую подсветку строки при наведении."""
        if row == self._hover_row:
            return
        self._hover_row = row
        self._refresh_row_visuals()

    def _on_selection_changed(self) -> None:
        """Перерисовывает строки при смене выделения (выделение не сбрасывается)."""
        self._refresh_row_visuals()

    def _refresh_row_visuals(self) -> None:
        """Перерисовывает строки (фон рисует делегат, не кнопки)."""
        self.viewport().update()


class CollapsibleSection(QWidget):
    """Сворачиваемый блок с нажимаемым заголовком."""

    def __init__(
        self,
        title: str,
        *,
        expanded: bool = True,
        parent=None,
    ) -> None:
        """Создаёт сворачиваемый блок."""
        super().__init__(parent)
        self._expanded = expanded
        self._on_toggled = None
        self.setObjectName("themePanel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self._header = QPushButton()
        self._header.setFlat(True)
        self._header.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.clicked.connect(self.toggle)
        self._header.setStyleSheet(collapsible_header_style("light"))
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(4, 0, 4, 0)
        self._chevron = QLabel()
        self._chevron.setFixedSize(16, 16)
        self._title = QLabel(title)
        self._title.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self._chevron)
        header_layout.addWidget(self._title)
        header_layout.addStretch()
        layout.addWidget(self._header)

        self._body = QWidget()
        self._body.setObjectName("themePanelBody")
        self._body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._body.setAutoFillBackground(False)
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._body)

        self._body.setVisible(expanded)
        self._update_chevron()

    @property
    def body_layout(self) -> QVBoxLayout:
        """Layout содержимого блока."""
        return self._body_layout

    def apply_theme(self, theme: str) -> None:
        """Подстраивает стили блока под тему."""
        self._header.setStyleSheet(collapsible_header_style(theme))
        apply_panel_theme(self, theme)
        apply_panel_inner(self._body, theme)
        self._title.setStyleSheet(
            f"font-weight: bold; background: transparent; color: {color('text', theme)};"
        )

    def toggle(self) -> None:
        """Переключает видимость содержимого."""
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        self._update_chevron()
        if self._on_toggled:
            self._on_toggled()

    def set_on_toggled(self, callback) -> None:
        """Устанавливает callback после сворачивания/разворачивания."""
        self._on_toggled = callback

    def _update_chevron(self) -> None:
        """Обновляет иконку свёрнуто/развёрнуто."""
        icon = chevron_down_icon() if self._expanded else chevron_right_icon()
        self._chevron.setPixmap(icon.pixmap(16, 16))


class TaskDialog(QDialog):
    """Диалог создания/редактирования задачи."""

    def __init__(
        self,
        tasks: list[Task],
        edit_task: Optional[Task] = None,
        parent=None,
    ) -> None:
        """
        Создаёт диалог задачи.

        Args:
            tasks: Существующие задачи (для генерации имени).
            edit_task: Задача для редактирования (None = создание).
        """
        super().__init__(parent)
        self._all_tasks = tasks
        self._edit_task = edit_task
        self._saved = False
        self._sources: list[str] = []
        self._exclusions: list[str] = []
        self._error_labels: dict[str, QLabel] = {}
        self._nested_sources: set[str] = set()

        if edit_task:
            self.setWindowTitle(f"Редактирование: {edit_task.name}")
            self._sources = list(edit_task.sources)
            self._exclusions = list(edit_task.exclusions)
        else:
            self.setWindowTitle("Создание задачи")

        self.resize(520, 600)
        self.setMinimumHeight(600)
        self.setMaximumHeight(600)
        self._build_ui()
        if edit_task:
            self._fill_from_task(edit_task)
        else:
            self._name.setText(self._default_name())

    def _default_name(self) -> str:
        """Генерирует имя «Задача N» по существующим задачам."""
        nums = []
        for t in self._all_tasks:
            m = re.match(r"Задача\s+(\d+)", t.name)
            if m:
                nums.append(int(m.group(1)))
        n = max(nums, default=0) + 1
        return f"Задача {n}"

    def _build_ui(self) -> None:
        """Строит интерфейс диалога."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)

        # Блок Описание
        desc_section = CollapsibleSection("Описание", expanded=True)
        desc_layout = desc_section.body_layout

        self._name = QLineEdit()
        desc_layout.addWidget(QLabel("Название:"))
        desc_layout.addWidget(self._name)
        desc_layout.addWidget(self._make_error_label("name"))

        self._description = QTextEdit()
        self._description.setMaximumHeight(72)
        self._description.document().setDocumentMargin(2)
        desc_layout.addWidget(QLabel("Описание:"))
        desc_layout.addWidget(self._description)

        desc_layout.addWidget(QLabel("Путь копирования:"))
        src_row = QHBoxLayout()
        self._source_input = QLineEdit()
        src_row.addWidget(self._source_input)
        browse_folder = QPushButton()
        browse_folder.setIcon(folder_icon())
        browse_folder.setFlat(True)
        browse_folder.setToolTip("Выбрать папку")
        browse_folder.clicked.connect(self._browse_source_folder)
        src_row.addWidget(browse_folder)
        browse_file = QPushButton()
        browse_file.setIcon(file_icon())
        browse_file.setFlat(True)
        browse_file.setToolTip("Выбрать файл")
        browse_file.clicked.connect(self._browse_source_file)
        src_row.addWidget(browse_file)
        add_src = QPushButton()
        add_src.setIcon(plus_icon())
        add_src.setFlat(True)
        add_src.clicked.connect(self._add_source)
        src_row.addWidget(add_src)
        desc_layout.addLayout(src_row)
        desc_layout.addWidget(self._make_error_label("sources"))

        self._sources_table = ListTableWidget(0, 3)
        self._sources_table.setHorizontalHeaderLabels(["№", "Путь", ""])
        self._configure_list_table(self._sources_table, visible_rows=5)
        desc_layout.addWidget(self._sources_table)

        desc_layout.addWidget(QLabel("Путь вставки:"))
        dest_row = QHBoxLayout()
        self._destination = QLineEdit()
        dest_row.addWidget(self._destination)
        browse_dest = QPushButton()
        browse_dest.setIcon(folder_icon())
        browse_dest.setFlat(True)
        browse_dest.setToolTip("Выбрать папку")
        browse_dest.clicked.connect(self._browse_dest)
        dest_row.addWidget(browse_dest)
        desc_layout.addLayout(dest_row)
        desc_layout.addWidget(self._make_error_label("destination"))

        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("Время:"))
        self._time = QLineEdit()
        self._time.setPlaceholderText("ЧЧ:ММ")
        self._time.setText("00:00")
        time_row.addWidget(self._time)
        time_row.addStretch()
        desc_layout.addLayout(time_row)
        desc_layout.addWidget(self._make_error_label("time"))

        period_row = QHBoxLayout()
        period_row.addWidget(QLabel("Периодичность (дней):"))
        self._period = NoSelectStepSpinBox()
        self._period.setRange(0, 366)
        self._period.setSpecialValueText("")
        self._period.setValue(7)
        period_row.addWidget(self._period)
        period_row.addStretch()
        desc_layout.addLayout(period_row)
        desc_layout.addWidget(self._make_error_label("period"))

        layout.addWidget(desc_section)
        layout.addSpacing(8)

        # Блок Исключения
        exc_section = CollapsibleSection("Исключения", expanded=False)
        exc_section.set_on_toggled(
            lambda: QTimer.singleShot(0, self._sync_all_tables)
        )
        exc_layout = exc_section.body_layout
        exc_row = QHBoxLayout()
        self._exc_input = QLineEdit()
        exc_row.addWidget(self._exc_input)
        add_exc = QPushButton()
        add_exc.setIcon(plus_icon())
        add_exc.setFlat(True)
        add_exc.clicked.connect(self._add_exclusion)
        exc_row.addWidget(add_exc)
        exc_layout.addLayout(exc_row)

        self._exc_table = ListTableWidget(0, 3)
        self._exc_table.setHorizontalHeaderLabels(["№", "Фильтр", ""])
        self._configure_list_table(self._exc_table, visible_rows=6)
        exc_layout.addWidget(self._exc_table)
        layout.addWidget(exc_section)
        layout.addSpacing(8)

        # Блок Дополнительно
        extra_section = CollapsibleSection("Дополнительно", expanded=False)
        extra_section.set_on_toggled(
            lambda: QTimer.singleShot(0, self._sync_all_tables)
        )
        extra_layout = QFormLayout()
        extra_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
        )
        extra_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        self._max_size = QLineEdit()
        self._max_size.setPlaceholderText("не ограничено")
        self._max_size.setFixedWidth(120)
        extra_layout.addRow("Макс. размер (МБ):", self._max_size)

        self._compress = QCheckBox()
        extra_layout.addRow("Архивирование:", self._compress)

        self._copy_mode = NoWheelComboBox()
        for mode in CopyMode:
            self._copy_mode.addItem(mode.label, mode.value)
        self._copy_mode.setFixedWidth(160)
        extra_layout.addRow("Режим копирования:", self._copy_mode)

        extra_section.body_layout.addLayout(extra_layout)
        layout.addWidget(extra_section)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self._save)
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(12, 4, 12, 12)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        btn_row.addStretch()
        outer.addLayout(btn_row)

        self._wire_table_selection()
        self._install_selection_clear_filter(content)
        scroll.viewport().installEventFilter(self)
        save_btn.installEventFilter(self)

    def _wire_table_selection(self) -> None:
        """Связывает таблицы: выбор в одной снимает выделение в другой."""
        handler = self._on_list_table_pressed
        self._sources_table.set_selection_handler(handler)
        self._exc_table.set_selection_handler(handler)

    def _on_list_table_pressed(self, table: Optional[ListTableWidget]) -> None:
        """Обрабатывает клик по строке или сброс выделения в таблице."""
        if table is None:
            self._clear_all_table_selections()
            return
        if table is self._sources_table:
            self._exc_table.clearSelection()
        else:
            self._sources_table.clearSelection()

    def _clear_all_table_selections(self) -> None:
        """Снимает полное выделение во всех таблицах списка."""
        self._sources_table.clearSelection()
        self._exc_table.clearSelection()

    def _install_selection_clear_filter(self, root: QWidget) -> None:
        """Снимает выделение таблиц при клике вне их области."""
        root.installEventFilter(self)
        for child in root.findChildren(QWidget):
            child.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        """Сбрасывает выделение строк при клике вне таблиц."""
        if event.type() == QEvent.Type.MouseButtonPress:
            if isinstance(obj, QWidget) and not self._is_inside_list_table(obj):
                self._clear_all_table_selections()
        return super().eventFilter(obj, event)

    def _is_inside_list_table(self, widget: QWidget) -> bool:
        """Проверяет, находится ли виджет внутри таблицы путей или фильтров."""
        w: Optional[QWidget] = widget
        while w is not None:
            if w in (
                self._sources_table.horizontalHeader(),
                self._exc_table.horizontalHeader(),
            ):
                return False
            if w is self._sources_table or w is self._exc_table:
                return True
            w = w.parentWidget()
        return False

    def _configure_list_table(self, table: ListTableWidget, visible_rows: int) -> None:
        """Настраивает таблицу путей/фильтров: колонки, высота, обрезка текста."""
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, _NUM_WIDTH)
        header.resizeSection(2, _ACTION_WIDTH)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(24)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.TextElideMode.ElideRight)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setShowGrid(True)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row_h = table.verticalHeader().defaultSectionSize()
        header_h = 28
        height = header_h + row_h * visible_rows + 2
        table.setFixedHeight(height)

    def _sync_table_columns(self, table: QTableWidget) -> None:
        """Фиксирует ширину боковых колонок; средняя растягивается сама."""
        table.setColumnWidth(_COL_NUM, _NUM_WIDTH)
        table.setColumnWidth(_COL_ACTION, _ACTION_WIDTH)
        table.viewport().update()

    def _sync_all_tables(self) -> None:
        """Синхронизирует ширину колонок обеих таблиц."""
        self._sync_table_columns(self._sources_table)
        self._sync_table_columns(self._exc_table)

    def showEvent(self, event) -> None:
        """Синхронизирует колонки после отображения окна."""
        super().showEvent(event)
        QTimer.singleShot(0, self._sync_all_tables)

    def resizeEvent(self, event) -> None:
        """Пересчитывает ширину колонок таблиц при изменении окна."""
        super().resizeEvent(event)
        self._sync_all_tables()

    def _make_num_item(self, number: int, *, nested: bool = False) -> QTableWidgetItem:
        """Создаёт ячейку номера строки."""
        item = QTableWidgetItem(str(number))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setTextAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        if nested:
            item.setForeground(self._nested_color())
        return item

    def _make_path_item(self, text: str, *, nested: bool = False) -> QTableWidgetItem:
        """Создаёт ячейку пути с обрезкой справа по символам."""
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setToolTip(text)
        item.setTextAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        if nested:
            item.setForeground(self._nested_color())
        return item

    def _nested_color(self) -> QColor:
        return get_theme_colors(self._dialog_theme()).nested_source

    def _active_sources(self) -> list[str]:
        """Источники без вложенных (они не сохраняются в задачу)."""
        return [s for s in self._sources if s not in self._nested_sources]

    def _make_error_label(self, key: str) -> QLabel:
        """Создаёт метку ошибки валидации под полем."""
        lbl = QLabel()
        lbl.setProperty("class", "error")
        lbl.setVisible(False)
        lbl.setWordWrap(True)
        self._error_labels[key] = lbl
        return lbl

    def _show_error(self, key: str, message: str) -> None:
        """Показывает ошибку валидации."""
        if key in self._error_labels:
            self._error_labels[key].setText(message)
            self._error_labels[key].setVisible(bool(message))

    def _fill_from_task(self, task: Task) -> None:
        """Заполняет форму из задачи."""
        self._name.setText(task.name)
        self._description.setPlainText(task.description)
        self._destination.setText(task.destination)
        if task.schedule_time:
            self._time.setText(format_time(task.schedule_time))
        else:
            self._time.clear()
        if task.period_days:
            self._period.setValue(task.period_days)
        else:
            self._period.setValue(0)
        if task.max_size_mb is not None:
            self._max_size.setText(str(task.max_size_mb))
        self._compress.setChecked(task.compress)
        idx = self._copy_mode.findData(
            task.copy_mode.value
            if isinstance(task.copy_mode, CopyMode)
            else task.copy_mode
        )
        if idx >= 0:
            self._copy_mode.setCurrentIndex(idx)
        self._update_nested_sources()
        self._refresh_exc_table()

    def _browse_source_folder(self) -> None:
        """Диалог выбора папки-источника."""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self._source_input.setText(folder)

    def _browse_source_file(self) -> None:
        """Диалог выбора файла-источника."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл", "", "Все файлы (*.*)",
        )
        if path:
            self._source_input.setText(path)

    def _browse_dest(self) -> None:
        """Диалог выбора папки архива."""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку архива")
        if folder:
            self._destination.setText(folder)

    def _add_source(self) -> None:
        """Добавляет путь источника в таблицу."""
        raw = self._source_input.text().strip()
        if not raw:
            return
        path = normalize_path(raw)
        ok, err = validate_path(path)
        if not ok:
            self._show_error("sources", err)
            return
        if not path_exists(path):
            self._show_error("sources", "Путь не существует")
            return
        if path in self._sources:
            return
        self._sources.append(path)
        self._source_input.clear()
        self._show_error("sources", "")
        self._update_nested_sources()

    def _update_nested_sources(self) -> None:
        """Помечает вложенные источники для отображения и исключения при сохранении."""
        self._nested_sources = {
            self._sources[i] for i in find_nested_source_indices(self._sources)
        }
        self._refresh_sources_table()

    def _remove_source(self, index: int) -> None:
        """Удаляет источник из списка."""
        if 0 <= index < len(self._sources):
            self._sources.pop(index)
            self._update_nested_sources()

    def _make_delete_button(self, callback) -> QWidget:
        """Создаёт центрированную кнопку удаления строки."""
        btn = DeleteRowButton()
        btn.clicked.connect(callback)
        container = QWidget()
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn)
        return container

    def _refresh_sources_table(self) -> None:
        """Обновляет таблицу источников."""
        self._sources_table.clear_rows()
        self._sources_table.setRowCount(len(self._sources))
        for i, src in enumerate(self._sources):
            nested = src in self._nested_sources
            self._sources_table.setItem(i, _COL_NUM, self._make_num_item(i + 1, nested=nested))
            self._sources_table.setItem(i, _COL_TEXT, self._make_path_item(src, nested=nested))
            container = self._make_delete_button(
                lambda checked, idx=i: self._remove_source(idx)
            )
            self._sources_table.setCellWidget(i, _COL_ACTION, container)
        self._sources_table._refresh_row_visuals()
        self._sync_table_columns(self._sources_table)

    def _add_exclusion(self) -> None:
        """Добавляет фильтр исключения."""
        raw = self._exc_input.text().strip()
        if not raw:
            return
        ok, err = validate_filter(raw)
        if not ok:
            return
        norm = raw.replace("\\", "/")
        if norm in self._exclusions:
            return
        self._exclusions.append(norm)
        self._exc_input.clear()
        self._refresh_exc_table()

    def _remove_exclusion(self, index: int) -> None:
        """Удаляет исключение."""
        if 0 <= index < len(self._exclusions):
            self._exclusions.pop(index)
            self._refresh_exc_table()

    def _refresh_exc_table(self) -> None:
        """Обновляет таблицу исключений."""
        self._exc_table.clear_rows()
        self._exc_table.setRowCount(len(self._exclusions))
        for i, exc in enumerate(self._exclusions):
            self._exc_table.setItem(i, _COL_NUM, self._make_num_item(i + 1))
            self._exc_table.setItem(i, _COL_TEXT, self._make_path_item(exc))
            container = self._make_delete_button(
                lambda checked, idx=i: self._remove_exclusion(idx)
            )
            self._exc_table.setCellWidget(i, _COL_ACTION, container)
        self._exc_table._refresh_row_visuals()
        self._sync_table_columns(self._exc_table)

    def _validate(self) -> bool:
        """Проверяет все поля формы."""
        valid = True

        if not self._name.text().strip():
            self._show_error("name", "Укажите название задачи")
            valid = False
        else:
            self._show_error("name", "")

        if not self._active_sources():
            self._show_error("sources", "Укажите хотя бы один источник")
            valid = False
        else:
            for source in self._active_sources():
                ok, err = validate_path(source)
                if not ok:
                    self._show_error("sources", err)
                    valid = False
                    break
                if not path_exists(source):
                    self._show_error("sources", "Путь не существует")
                    valid = False
                    break
            else:
                self._show_error("sources", "")

        dest_raw = self._destination.text().strip()
        if not dest_raw:
            self._show_error("destination", "Укажите папку назначения")
            valid = False
        else:
            ok, err = validate_directory_path(dest_raw)
            if not ok:
                self._show_error("destination", err)
                valid = False
            else:
                self._show_error("destination", "")

        time_str = self._time.text().strip()
        if time_str:
            parts = time_str.split(":")
            if len(parts) != 2:
                valid = False
            else:
                try:
                    h, m = int(parts[0]), int(parts[1])
                    if not (0 <= h <= 23 and 0 <= m <= 59):
                        valid = False
                except ValueError:
                    valid = False

        return valid

    def _selected_copy_mode(self) -> CopyMode:
        """Возвращает выбранный режим копирования из комбобокса."""
        data = self._copy_mode.currentData()
        if isinstance(data, CopyMode):
            return data
        return CopyMode.from_value(str(data))

    def _save(self) -> None:
        """Сохраняет задачу."""
        if not self._validate():
            return

        from datetime import time as dt_time

        time_str = self._time.text().strip()
        schedule_time = None
        if time_str:
            h, m = map(int, time_str.split(":"))
            schedule_time = dt_time(h, m)

        period = self._period.value() if self._period.value() > 0 else None
        max_size = None
        if self._max_size.text().strip():
            try:
                max_size = float(self._max_size.text().strip())
            except ValueError:
                return

        if self._edit_task:
            task = self._edit_task
            task.name = self._name.text().strip()
            task.description = self._description.toPlainText()
            task.sources = list(self._active_sources())
            task.destination = normalize_path(self._destination.text().strip())
            task.schedule_time = schedule_time
            task.period_days = period
            task.exclusions = list(self._exclusions)
            task.max_size_mb = max_size
            task.compress = self._compress.isChecked()
            task.copy_mode = self._selected_copy_mode()
            if not task.has_schedule():
                task.is_active = False
                task.next_run = None
            else:
                SchedulerService.recalc_on_edit(task)
            self._result_task = task
        else:
            task = Task.create_default(self._name.text().strip())
            task.description = self._description.toPlainText()
            task.sources = list(self._active_sources())
            task.destination = normalize_path(self._destination.text().strip())
            task.schedule_time = schedule_time
            task.period_days = period
            task.exclusions = list(self._exclusions)
            task.max_size_mb = max_size
            task.compress = self._compress.isChecked()
            task.copy_mode = self._selected_copy_mode()
            if not task.has_schedule():
                task.is_active = False
                task.next_run = None
            else:
                task.next_run = SchedulerService.initial_next_run(
                    task.created_at, task.period_days
                )
            self._result_task = task

        self._saved = True
        self.accept()

    def _dialog_theme(self) -> str:
        parent = self.parent()
        if parent is not None and hasattr(parent, "_settings"):
            return parent._settings.theme
        return "light"

    def _apply_widget_theme(self, theme: str) -> None:
        """Подстраивает вложенные виджеты под тему."""
        for section in self.findChildren(CollapsibleSection):
            section.apply_theme(theme)

    def showEvent(self, event) -> None:
        """Подстраивает тему таблиц и заголовок окна."""
        super().showEvent(event)
        theme = self._dialog_theme()
        self._sources_table.set_theme(theme)
        self._exc_table.set_theme(theme)
        self._apply_widget_theme(theme)
        apply_window_theme(self, theme)
        schedule_window_chrome(self, theme=theme)
        apply_interactive_cursors(self)

    def get_task(self) -> Optional[Task]:
        """Возвращает сохранённую задачу."""
        return getattr(self, "_result_task", None)

    def closeEvent(self, event) -> None:
        """Предупреждение при закрытии с несохранёнными изменениями."""
        if not self._saved:
            if not question(self, "Несохранённые изменения", "Закрыть без сохранения?"):
                event.ignore()
                return
        super().closeEvent(event)

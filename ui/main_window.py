"""Главное окно приложения."""

from __future__ import annotations

import html
from typing import Optional

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QSizeGrip,
    QStatusBar,
    QTableWidgetItem,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from models.app_settings import (
    COLUMN_KEYS,
    COLUMN_LABELS,
    DEFAULT_COLUMN_WIDTHS,
    DEFAULT_WINDOW_HEIGHT,
    AppSettings,
    compute_default_window_width,
)
from models.task import Task
from services.autostart import apply_autostart
from services.path_utils import (
    format_date,
    format_datetime,
    format_size,
    format_time,
    open_in_explorer,
)
from services.scheduler import SchedulerService
from services.storage import StorageService
from ui.help_dialog import HelpDialog
from ui.main_table import (
    UI_ROW_NUM,
    PATH_TEXT_ROLE,
    MainTableWidget,
    TASK_ID_ROLE,
    _ROW_NUM_WIDTH,
    make_actions_widget,
    make_table_item,
)
from ui.message_box import information, question, warning
from ui.settings_dialog import SettingsDialog
from ui.task_dialog import TaskDialog
from ui.themes import apply_window_theme, get_palette, refresh_theme_for_app
from ui.window_chrome import schedule_window_chrome
from workers.auto_scheduler import AutoScheduler
from workers.task_queue import TaskQueueManager


def _format_task_tooltip(task: Task, theme: str) -> str:
    """Формирует подсказку задачи: название, архив (выделен), источники."""
    archive_color = get_palette(theme).tooltip_archive
    parts = [f"<b>{html.escape(task.name)}</b>"]
    if task.destination:
        dest = html.escape(task.destination)
        parts.append(
            "<br><br>"
            f"<span style='color:{archive_color};'><b>Архив</b></span><br>"
            f"<span style='color:{archive_color};'>{dest}</span>"
        )
    if task.sources:
        src_lines = "<br>".join(html.escape(src) for src in task.sources)
        parts.append(f"<br><br><b>Источники</b><br>{src_lines}")
    return "<qt>" + "".join(parts) + "</qt>"


class MainWindow(QMainWindow):
    """Главное окно с таблицей задач."""

    def __init__(self, storage: StorageService, *, start_hidden: bool = False) -> None:
        """Инициализирует главное окно."""
        super().__init__()
        self._storage = storage
        self._background_mode = start_hidden
        self._force_quit = False
        self._tasks: list[Task] = []
        self._settings = AppSettings()
        self._size_cache: dict[str, dict] = {}
        self._stale_sizes: set[str] = set()
        self._expanded: set[str] = set()
        self._selected_ids: list[str] = []
        self._detail_rows: dict[str, list[int]] = {}

        self.setWindowTitle("Архиватор")
        self._load_data()
        self._setup_geometry()
        self._build_ui()
        self._apply_settings()

        self._queue = TaskQueueManager(storage, self)
        self._queue.status_changed.connect(self._on_status)
        self._queue.busy_changed.connect(self._on_busy)
        self._queue.task_size_updated.connect(self._on_size_updated)
        self._queue.task_finished.connect(self._on_task_finished)
        self._queue.set_tasks_changed_callback(self._persist_tasks)

        self._scheduler = AutoScheduler(self._get_tasks, self._run_auto, self)
        self._scheduler.start()

        QTimer.singleShot(100, lambda: self._queue.scan_all_sizes(self._tasks))

    def _setup_geometry(self) -> None:
        """Устанавливает ширину окна под все колонки, высоту — 60% экрана (мин. 600)."""
        screen = QApplication.primaryScreen().availableGeometry()
        w = compute_default_window_width(
            self._settings.visible_columns,
            self._settings.column_widths,
            row_num_width=_ROW_NUM_WIDTH,
        )
        h = max(DEFAULT_WINDOW_HEIGHT, int(screen.height() * 0.6))
        self.resize(w, h)

    def _load_data(self) -> None:
        """Загружает данные из хранилища."""
        self._storage.load()
        self._tasks = self._storage.get_tasks()
        self._settings = self._storage.get_settings()
        self._size_cache = self._storage.get_size_cache()
        self._stale_sizes = {t.id for t in self._tasks}

    def _persist_tasks(self) -> None:
        """Сохраняет задачи в JSON."""
        self._storage.set_tasks(self._tasks)
        self._storage.save()

    def _get_tasks(self) -> list[Task]:
        """Возвращает актуальный список задач."""
        return self._tasks

    def _build_ui(self) -> None:
        """Строит интерфейс главного окна."""
        self._central = QWidget()
        self._central.setObjectName("appCentral")
        self.setCentralWidget(self._central)
        layout = QVBoxLayout(self._central)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QToolBar()
        toolbar.setObjectName("appToolBar")
        toolbar.setMovable(False)
        self._toolbar = toolbar
        self.addToolBar(toolbar)

        self._btn_create = QToolButton()
        self._btn_create.setText("Создать")
        self._btn_create.clicked.connect(self._on_create)
        toolbar.addWidget(self._btn_create)

        self._btn_run = QToolButton()
        self._btn_run.setText("Выполнить")
        self._btn_run.clicked.connect(self._on_run)
        toolbar.addWidget(self._btn_run)

        self._btn_settings = QToolButton()
        self._btn_settings.setText("Настройки")
        self._btn_settings.clicked.connect(self._on_settings)
        toolbar.addWidget(self._btn_settings)

        self._btn_help = QToolButton()
        self._btn_help.setText("Помощь")
        self._btn_help.clicked.connect(self._on_help)
        toolbar.addWidget(self._btn_help)

        self._table = MainTableWidget()
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setMinimumSectionSize(20)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.verticalHeader().setVisible(False)
        self._table.set_on_task_selected(self._on_task_selected)
        self._table.cellClicked.connect(self._on_cell_clicked)
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_path_context_menu)
        self._table.horizontalHeader().sectionResized.connect(self._on_column_resized)
        layout.addWidget(self._table)

        self._status_label = QLabel("")
        status = QStatusBar()
        status.setObjectName("appStatusBar")
        status.setSizeGripEnabled(False)
        status.addWidget(self._status_label, 1)
        status.addPermanentWidget(QSizeGrip(status), 0)
        self.setStatusBar(status)

        self._install_selection_clear_filter(self._central)

        self._rebuild_columns()
        self._refresh_table()

    def _visible_columns(self) -> list[str]:
        """Возвращает список видимых колонок (№ всегда первый)."""
        cols = [k for k in COLUMN_KEYS if self._settings.visible_columns.get(k, True)]
        return [UI_ROW_NUM] + cols

    def _rebuild_columns(self) -> None:
        """Перестраивает колонки таблицы."""
        cols = self._visible_columns()
        self._table.set_column_keys(cols)
        self._table.setColumnCount(len(cols))
        labels = [COLUMN_LABELS.get(c, "№") if c != UI_ROW_NUM else "№" for c in cols]
        self._table.setHorizontalHeaderLabels(labels)
        self._col_map = cols
        for i, key in enumerate(cols):
            if key == UI_ROW_NUM:
                header = self._table.horizontalHeader()
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                header.resizeSection(i, _ROW_NUM_WIDTH)
            else:
                w = self._settings.column_widths.get(key, DEFAULT_COLUMN_WIDTHS.get(key, 120))
                self._table.setColumnWidth(i, max(w, 50))

    def _refresh_table(self) -> None:
        """Обновляет содержимое таблицы."""
        selected = list(self._selected_ids)
        # Старая анимация могла испортить defaultSectionSize всей таблицы.
        header = self._table.verticalHeader()
        if header.defaultSectionSize() < 16:
            header.setDefaultSectionSize(max(header.minimumSectionSize(), 24))
        self._table.setRowCount(0)
        self._table.clear_row_registry()
        self._detail_rows.clear()
        row = 0
        for index, task in enumerate(self._tasks, start=1):
            self._insert_task_row(row, task, index)
            row += 1
            if task.id in self._expanded:
                row = self._insert_detail_rows(row, task)
        self._table.set_selected_task_ids(selected)

    def _col_index(self, key: str) -> int:
        """Индекс колонки по ключу."""
        return self._table.col_index(key)

    def _set_item(
        self,
        row: int,
        col_key: str,
        item: QTableWidgetItem,
    ) -> None:
        """Устанавливает ячейку, если колонка видима."""
        ci = self._col_index(col_key)
        if ci >= 0:
            self._table.setItem(row, ci, item)

    def _insert_task_row(self, row: int, task: Task, index: int) -> None:
        """Вставляет строку задачи."""
        self._table.insertRow(row)
        self._table.register_task_row(row, task.id, active=task.is_active)

        num_item = make_table_item(str(index), centered=True)
        self._set_item(row, UI_ROW_NUM, num_item)

        self._set_item(
            row,
            "name",
            make_table_item(task.name, task_id=task.id),
        )
        self._set_item(
            row,
            "description",
            make_table_item(task.description, task_id=task.id),
        )

        src_first = task.sources[0] if task.sources else ""
        src_extra = max(0, len(task.sources) - 1)
        src_display = src_first + (f"  +{src_extra}" if src_extra else "")
        self._set_item(
            row,
            "sources",
            make_table_item(
                src_display,
                task_id=task.id,
                sources_first=src_first,
                sources_extra=src_extra,
            ),
        )

        dest = task.destination
        self._set_item(
            row,
            "destination",
            make_table_item(dest, task_id=task.id, path_text=dest),
        )

        self._set_item(
            row,
            "schedule_time",
            make_table_item(
                format_time(task.schedule_time) if task.schedule_time else "",
                task_id=task.id,
                centered=True,
            ),
        )
        self._set_item(
            row,
            "period_days",
            make_table_item(
                str(task.period_days) if task.period_days else "",
                task_id=task.id,
                centered=True,
            ),
        )

        exc_first = task.exclusions[0] if task.exclusions else ""
        exc_extra = max(0, len(task.exclusions) - 1)
        exc_display = exc_first + (f"  +{exc_extra}" if exc_extra else "")
        self._set_item(
            row,
            "exclusions",
            make_table_item(
                exc_display,
                task_id=task.id,
                sources_first=exc_first,
                sources_extra=exc_extra,
            ),
        )

        expanded = task.id in self._expanded
        if expanded and task.sources:
            size = self._source_size(task.id, task.sources[0])
            size_as_detail = True
        else:
            size = self._task_total_size(task.id)
            size_as_detail = False
        size_text = format_size(size) if size >= 0 else "—"
        size_item = make_table_item(
            size_text,
            task_id=task.id,
            centered=True,
            detail=size_as_detail,
        )
        if task.id in self._stale_sizes:
            size_item.setForeground(QColor("#f57c00"))
        self._set_item(row, "total_size", size_item)

        self._set_item(
            row,
            "last_run",
            make_table_item(
                format_datetime(task.last_run),
                task_id=task.id,
                centered=True,
            ),
        )
        next_text = format_date(task.next_run) if task.next_run else ""
        self._set_item(
            row,
            "next_run",
            make_table_item(next_text, task_id=task.id, centered=True),
        )
        self._set_item(
            row,
            "copy_mode",
            make_table_item(
                task.copy_mode_label(),
                task_id=task.id,
                centered=True,
            ),
        )
        self._set_item(
            row,
            "compress",
            make_table_item(
                "да" if task.compress else "нет",
                task_id=task.id,
                centered=True,
            ),
        )

        if self._col_index("actions") >= 0:
            widget = make_actions_widget(
                is_active=task.is_active,
                on_toggle=lambda checked, tid=task.id: self._toggle_active(tid),
                on_edit=lambda checked, tid=task.id: self._edit_task(tid),
                on_delete=lambda checked, tid=task.id: self._delete_task(tid),
                theme=self._settings.theme,
            )
            self._table.set_actions_widget(row, widget)

        tip = _format_task_tooltip(task, self._settings.theme)
        for ci in range(self._table.columnCount()):
            item = self._table.item(row, ci)
            if item:
                item.setToolTip(tip)

    def _task_total_size(self, task_id: str) -> int:
        """Суммарный размер задачи из кэша (-1 если нет данных)."""
        entry = self._size_cache.get(task_id)
        if not isinstance(entry, dict):
            return -1
        try:
            return int(entry.get("total", -1))
        except (TypeError, ValueError):
            return -1

    def _source_size(self, task_id: str, source: str) -> int:
        """Размер одного источника из кэша (-1 если нет данных)."""
        entry = self._size_cache.get(task_id)
        if not isinstance(entry, dict):
            return -1
        sources = entry.get("sources", {})
        if not isinstance(sources, dict) or source not in sources:
            return -1
        try:
            return int(sources[source])
        except (TypeError, ValueError):
            return -1

    def _insert_detail_rows(self, row: int, task: Task) -> int:
        """Вставляет доп. строки источников/исключений (без первого — он в строке задачи)."""
        details = []
        for src in task.sources[1:]:
            details.append(("sources", src))
        for exc in task.exclusions[1:]:
            details.append(("exclusions", exc))
        if not details:
            return row
        indices = []
        for kind, text in details:
            self._table.insertRow(row)
            self._table.register_detail_row(row)
            for ci, col_key in enumerate(self._col_map):
                if col_key == kind:
                    item = make_table_item(
                        f"  → {text}",
                        detail=True,
                        path_text=text,
                        sources_first=text,
                    )
                    self._table.setItem(row, ci, item)
                elif col_key == "total_size" and kind == "sources":
                    src_size = self._source_size(task.id, text)
                    size_text = format_size(src_size) if src_size >= 0 else "—"
                    size_item = make_table_item(
                        size_text, detail=True, centered=True
                    )
                    if task.id in self._stale_sizes:
                        size_item.setForeground(QColor("#f57c00"))
                    self._table.setItem(row, ci, size_item)
                else:
                    self._table.setItem(row, ci, make_table_item("", detail=True))
            indices.append(row)
            row += 1
        self._detail_rows[task.id] = indices
        return row

    def _find_task(self, task_id: str) -> Optional[Task]:
        """Находит задачу по ID."""
        for t in self._tasks:
            if t.id == task_id:
                return t
        return None

    def _task_row_index(self, task_id: str) -> int:
        """Находит индекс строки задачи."""
        return self._table.row_for_task_id(task_id)

    def _on_task_selected(self, task_ids: list[str]) -> None:
        """Синхронизирует выделение задач."""
        self._selected_ids = list(task_ids)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Раскрывает/сворачивает список источников и исключений."""
        if col >= len(self._col_map):
            return
        col_key = self._col_map[col]
        if col_key not in ("sources", "exclusions"):
            return
        item = self._table.item(row, col)
        if not item:
            return
        task_id = item.data(TASK_ID_ROLE)
        if not task_id:
            return
        task = self._find_task(task_id)
        if not task:
            return
        has_multi = len(task.sources) > 1 or len(task.exclusions) > 1
        if not has_multi:
            return
        if task_id in self._expanded:
            self._collapse_task(task_id)
        else:
            self._expand_task(task_id)

    def _paths_at_cell(self, row: int, col: int) -> list[str]:
        """Возвращает пути для ячейки «Источники» или «Архив»."""
        if col < 0 or col >= len(self._col_map):
            return []
        col_key = self._col_map[col]
        if col_key not in ("sources", "destination"):
            return []

        item = self._table.item(row, col)
        if not item:
            return []

        if self._table.is_detail_row(row):
            if col_key != "sources":
                return []
            path = item.data(PATH_TEXT_ROLE)
            return [path] if path else []

        task_id = item.data(TASK_ID_ROLE)
        if not task_id:
            return []
        task = self._find_task(task_id)
        if not task:
            return []

        if col_key == "destination":
            return [task.destination] if task.destination else []
        return list(task.sources)

    def _open_path(self, path: str) -> None:
        """Открывает путь в проводнике или показывает ошибку."""
        ok, err = open_in_explorer(path)
        if not ok:
            warning(self, "Проводник", err or "Не удалось открыть путь")

    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        """Открывает путь в проводнике по двойному клику."""
        paths = self._paths_at_cell(row, col)
        if not paths:
            return
        if len(paths) == 1:
            self._open_path(paths[0])
            return
        menu = QMenu(self)
        for path in paths:
            action = menu.addAction(path)
            action.triggered.connect(
                lambda checked=False, p=path: self._open_path(p)
            )
        menu.exec(QCursor.pos())

    def _on_path_context_menu(self, pos) -> None:
        """Контекстное меню: открыть путь в проводнике."""
        index = self._table.indexAt(pos)
        if not index.isValid():
            return
        paths = self._paths_at_cell(index.row(), index.column())
        if not paths:
            return
        if len(paths) == 1:
            self._open_path(paths[0])
            return
        menu = QMenu(self)
        for path in paths:
            action = menu.addAction(path)
            action.triggered.connect(
                lambda checked=False, p=path: self._open_path(p)
            )
        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _expand_task(self, task_id: str) -> None:
        """Разворачивает детали задачи."""
        self._expanded.add(task_id)
        self._refresh_table()

    def _collapse_task(self, task_id: str) -> None:
        """Сворачивает детали задачи."""
        self._expanded.discard(task_id)
        self._refresh_table()

    def _install_selection_clear_filter(self, root: QWidget) -> None:
        """Снимает выделение при клике вне таблицы."""
        root.installEventFilter(self)
        for child in root.findChildren(QWidget):
            child.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        """Сбрасывает выделение задачи при клике вне таблицы."""
        if event.type() == QEvent.Type.MouseButtonPress:
            if isinstance(obj, QWidget) and not self._is_inside_task_table(obj):
                self._clear_task_selection()
        return super().eventFilter(obj, event)

    def _is_inside_task_table(self, widget: QWidget) -> bool:
        """Проверяет, находится ли виджет внутри таблицы задач."""
        w: Optional[QWidget] = widget
        while w is not None:
            if w is self._table.horizontalHeader():
                return False
            if w is self._table:
                return True
            w = w.parentWidget()
        return False

    def _clear_task_selection(self) -> None:
        """Снимает выделение задач."""
        self._selected_ids = []
        self._table.clear_selection()

    def _on_create(self) -> None:
        """Открывает диалог создания задачи."""
        dlg = TaskDialog(self._tasks, parent=self)
        if dlg.exec():
            task = dlg.get_task()
            if task:
                self._tasks.append(task)
                self._stale_sizes.add(task.id)
                self._persist_tasks()
                self._refresh_table()
                self._queue.scan_task_size(task)

    def _edit_task(self, task_id: str) -> None:
        """Редактирует задачу."""
        task = self._find_task(task_id)
        if not task:
            return
        dlg = TaskDialog(self._tasks, edit_task=task, parent=self)
        if dlg.exec():
            self._stale_sizes.add(task_id)
            self._persist_tasks()
            self._refresh_table()
            self._queue.scan_task_size(task)

    def _delete_task(self, task_id: str) -> None:
        """Удаляет задачу с подтверждением."""
        task = self._find_task(task_id)
        if not task:
            return
        if not question(self, "Удаление", f"Удалить задачу «{task.name}»?"):
            return
        self._tasks = [t for t in self._tasks if t.id != task_id]
        self._expanded.discard(task_id)
        if task_id in self._selected_ids:
            self._selected_ids = [i for i in self._selected_ids if i != task_id]
        self._persist_tasks()
        self._refresh_table()

    def _toggle_active(self, task_id: str) -> None:
        """Переключает активность задачи."""
        task = self._find_task(task_id)
        if not task:
            return
        if task.is_active:
            task.is_active = False
        else:
            task.is_active = True
            if task.has_schedule():
                SchedulerService.recalc_on_activate(task)
        self._persist_tasks()
        self._refresh_table()

    def _resolved_selected_tasks(self) -> list[Task]:
        """Возвращает выделенные задачи в порядке таблицы."""
        ids = self._selected_ids or self._table.selected_task_ids()
        tasks: list[Task] = []
        for task_id in ids:
            task = self._find_task(task_id)
            if task:
                tasks.append(task)
        return tasks

    def _on_run(self) -> None:
        """Запускает выполнение задач."""
        if self._queue.is_busy:
            information(
                self,
                "Выполнить",
                "Уже выполняется задача. Дождитесь завершения.",
            )
            return

        to_run = self._resolved_selected_tasks()
        if not to_run:
            to_run = [t for t in self._tasks if t.is_active]
            if not to_run and self._tasks:
                to_run = list(self._tasks)

        if not to_run:
            information(
                self,
                "Выполнить",
                "Нет задач для выполнения.",
            )
            return

        self._queue.enqueue(to_run, automatic=False)

    def _run_auto(self, tasks: list[Task]) -> None:
        """Автоматический запуск задач."""
        if not self._queue.is_busy:
            self._queue.enqueue(tasks, automatic=True)

    def _on_settings(self) -> None:
        """Открывает настройки."""
        dlg = SettingsDialog(self._settings, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._settings = dlg.get_settings()
            self._storage.set_settings(self._settings)
            self._storage.save()
            apply_autostart(self._settings.autostart)
            self._apply_settings()
            self._rebuild_columns()
            self._refresh_table()

    def _on_help(self) -> None:
        """Открывает справку."""
        HelpDialog(self).exec()

    def _apply_settings(self) -> None:
        """Применяет тему и шрифт."""
        refresh_theme_for_app(self._settings.theme, self._settings.font_size)

    def showEvent(self, event) -> None:
        """Настраивает заголовок окна при первом показе."""
        super().showEvent(event)
        apply_window_theme(self, self._settings.theme)
        schedule_window_chrome(self, theme=self._settings.theme)

    def show_window(self) -> None:
        """Показывает и активирует главное окно."""
        if self.isMinimized():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()
        # После первого показа из трея HWND уже с корректной рамкой —
        # повторно подтягиваем тему заголовка.
        schedule_window_chrome(self, theme=self._settings.theme)

    def quit_application(self) -> None:
        """Полностью завершает приложение."""
        self._force_quit = True
        self._scheduler.stop()
        QApplication.instance().quit()

    def _on_status(self, text: str) -> None:
        """Обновляет строку статуса."""
        self._status_label.setText(text)

    def _on_busy(self, busy: bool) -> None:
        """Блокирует кнопку Выполнить при занятости."""
        self._btn_run.setEnabled(not busy)

    def _on_size_updated(self, task_id: str, payload: object) -> None:
        """Обновляет кэш размера в таблице."""
        if isinstance(payload, dict):
            entry = {
                "total": int(payload.get("total", 0)),
                "sources": {
                    str(k): int(v)
                    for k, v in (payload.get("sources") or {}).items()
                },
            }
        elif isinstance(payload, int) and not isinstance(payload, bool):
            entry = {"total": payload, "sources": {}}
        else:
            entry = {"total": 0, "sources": {}}
        self._size_cache[task_id] = entry
        self._stale_sizes.discard(task_id)
        self._storage.update_task_size(
            task_id, entry["total"], entry["sources"]
        )
        self._storage.save()
        self._refresh_table()

    def _on_task_finished(self, task_id: str, result: object) -> None:
        """Обработчик завершения задачи."""
        self._persist_tasks()
        self._refresh_table()
        if isinstance(result, BackupResult):
            task = self._find_task(task_id)
            name = task.name if task else "Задача"
            if result.files_copied > 0:
                self._status_label.setText(
                    f"{name}: скопировано файлов — {result.files_copied}"
                )
            elif result.is_disk_full:
                self._status_label.setText(f"{name}: недостаточно места на диске")
            else:
                self._status_label.setText(
                    f"{name}: нет новых файлов для копирования"
                )

    def _on_column_resized(self, index: int, old: int, new: int) -> None:
        """Сохраняет ширину колонки."""
        if index < len(self._col_map):
            key = self._col_map[index]
            if key == UI_ROW_NUM:
                return
            self._settings.column_widths[key] = new
            self._storage.set_settings(self._settings)
            self._storage.save()
        self._table.viewport().update()

    def closeEvent(self, event) -> None:
        """В фоновом режиме скрывает в трей; иначе останавливает планировщик и закрывает."""
        if self._background_mode and not self._force_quit:
            event.ignore()
            self.hide()
            return
        self._scheduler.stop()
        super().closeEvent(event)

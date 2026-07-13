"""Генерация true_prompt.docx — актуальное ТЗ по готовому коду."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "true_prompt.docx"


def _shade_cell(cell, fill: str) -> None:
    shading = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    shd.set(qn("w:val"), "clear")
    shading.append(shd)


def _add_title_page(doc: Document) -> None:
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Техническое задание\n")
    run.bold = True
    run.font.size = Pt(24)
    run2 = title.add_run("Архиватор")
    run2.bold = True
    run2.font.size = Pt(28)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sub.add_run("Актуальная спецификация по реализованному коду")
    r.font.size = Pt(14)
    r.italic = True

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run(f"Версия документа: 1.0\nДата: {date.today().strftime('%d.%m.%Y')}")

    note = doc.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    nr = note.add_run(
        "Документ составлен по готовому приложению и отражает фактическую "
        "реализацию, включая доработки после исходного prompt.docx."
    )
    nr.font.size = Pt(10)
    nr.italic = True

    doc.add_page_break()


def _add_info_box(doc: Document, title: str, lines: list[str]) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    cell = table.rows[0].cells[0]
    _shade_cell(cell, "E8F0FE")
    p = cell.paragraphs[0]
    r = p.add_run(title + "\n")
    r.bold = True
    for line in lines:
        cell.add_paragraph(line, style="List Bullet")
    doc.add_paragraph()


def _add_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, text in enumerate(headers):
        hdr[i].text = text
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.bold = True
        _shade_cell(hdr[i], "F2F2F2")
    for row in rows:
        cells = table.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = text
    doc.add_paragraph()


def build_document() -> Document:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    _add_title_page(doc)

    # --- 1. Общие сведения ---
    doc.add_heading("1. Общие сведения", level=1)
    doc.add_paragraph(
        "Архиватор — настольное приложение для периодического резервного копирования "
        "файлов и каталогов на Windows. Пользователь задаёт один или несколько источников, "
        "папку назначения, расписание и правила исключения; программа выполняет копирование "
        "в фоне, не блокируя интерфейс."
    )
    _add_table(
        doc,
        ["Параметр", "Значение"],
        [
            ["Название", "Архиватор (Archiver)"],
            ["Целевая ОС", "Windows 10 и новее"],
            ["Язык интерфейса", "Русский"],
            ["Точка входа", "main.py / Archiver.exe"],
            ["Данные", "settings.json рядом с программой"],
            ["Логи", "backup.log"],
            ["Ошибки копирования", "папка errors/"],
            ["Режимы запуска", "Обычный и фоновый (--background)"],
        ],
    )

    _add_info_box(
        doc,
        "Важно: два способа запуска",
        [
            "Двойной щелчок по Archiver.exe — обычный режим, окно открывается сразу.",
            "Автозапуск Windows или Archiver.exe --background — фоновый режим: только иконка в трее.",
        ],
    )

    # --- 2. Глоссарий ---
    doc.add_heading("2. Глоссарий", level=1)
    glossary = [
        ("Задача", "Настроенное резервное копирование с источниками, архивом, расписанием и режимом."),
        ("Источник", "Файл или папка, из которых копируются данные. В задаче может быть несколько."),
        ("Архив", "Папка назначения (должна существовать до копирования)."),
        ("Фильтр / исключение", "Шаблон относительного пути от корня источника; совпавшие файлы не копируются."),
        ("Режим копирования", "Способ размещения данных: инкрементально, слоями или полное дублирование."),
        ("След.вып.", "Дата следующего автоматического запуска (без времени в ячейке). Обновляется только после автозапуска."),
        ("Послед.вып.", "Дата и время последнего запуска задачи (ручного или автоматического)."),
        ("Слой", "Папка или ZIP backup_ДД.ММ.ГГГГ_NNN в режимах «слоями» и «дублирование»."),
        ("Активная задача", "Участвует в автоматическом расписании (is_active = true)."),
    ]
    for term, definition in glossary:
        p = doc.add_paragraph(style="List Bullet")
        r = p.add_run(f"{term} — ")
        r.bold = True
        p.add_run(definition)

    # --- 3. UI ---
    doc.add_heading("3. Пользовательский интерфейс", level=1)
    doc.add_paragraph(
        "Оконное приложение на PySide6 (Qt 6). Дизайн в стиле современного десктопного "
        "приложения: светлая тема по умолчанию, тёмная тема в настройках, адаптивная таблица, "
        "векторные SVG-иконки 16×16, подсветка кнопок при наведении."
    )

    doc.add_heading("3.1. Главное окно", level=2)
    doc.add_paragraph("Заголовок: «Архиватор». Три зоны: панель инструментов, таблица задач, строка статуса.")

    doc.add_heading("Панель инструментов", level=3)
    _add_table(
        doc,
        ["Кнопка", "Поведение"],
        [
            ["Создать", "Открывает диалог создания задачи"],
            ["Выполнить", "Запускает выделенные задачи; если ничего не выделено — все активные; если активных нет — все задачи. Блокируется во время работы очереди"],
            ["Настройки", "Открывает диалог настроек"],
            ["Помощь", "Открывает краткую справку"],
        ],
    )

    doc.add_heading("Таблица задач", level=3)
    doc.add_paragraph(
        "Колонки (порядок фиксирован). Видимость настраивается, кроме колонки «Действия» — она всегда видна."
    )
    _add_table(
        doc,
        ["Колонка", "Описание"],
        [
            ["№", "Порядковый номер строки"],
            ["Название", "Имя задачи"],
            ["Описание", "Текст описания (по умолчанию скрыта)"],
            ["Источники", "Первый путь + «+N»; клик раскрывает полный список"],
            ["Архив", "Путь назначения"],
            ["Время", "ЧЧ:ММ"],
            ["Период.", "Периодичность в днях"],
            ["Исключения", "Первый фильтр + «+N» (по умолчанию скрыта)"],
            ["Размер", "Кэшированный размер; «—» если неизвестен; оранжевый при устаревшем кэше"],
            ["Послед.вып.", "ДД.ММ.ГГГГ ЧЧ:ММ или «—»"],
            ["След.вып.", "ДД.ММ.ГГГГ; у неактивных задач — приглушённый цвет"],
            ["Режим копирования", "Текстовая метка режима"],
            ["Сжатие", "«да» / «нет»"],
            ["Действия", "Активация, редактирование, удаление (SVG-иконки)"],
        ],
    )

    doc.add_paragraph("Поведение таблицы:", style="List Bullet")
    behaviors = [
        "Ширина колонок изменяется мышью и сохраняется в settings.json.",
        "Одиночный клик выделяет строку; Ctrl и Shift — множественное выделение.",
        "Раскрытие источников/исключений — анимация ~0,5 с.",
        "Двойной клик по пути «Источники» или «Архив» открывает проводник.",
        "Горизонтальная прокрутка: Alt + колёсико мыши.",
        "Неактивные задачи отображаются приглушённым текстом.",
        "Размер окна: ширина по сумме колонок; высота max(600 px, 60% экрана).",
    ]
    for b in behaviors:
        doc.add_paragraph(b, style="List Bullet 2")

    doc.add_heading("3.2. Диалог «Создание / редактирование задачи»", level=2)
    doc.add_paragraph("Три секции: Описание, Исключения, Дополнительно. Кнопка «Сохранить» внизу по центру.")

    doc.add_heading("Секция «Описание»", level=3)
    _add_table(
        doc,
        ["Поле", "Требования"],
        [
            ["Название", "Обязательное; по умолчанию «Задача N»"],
            ["Описание", "Необязательное, многострочное"],
            ["Пути копирования", "≥1 источник; папка или файл; кнопки выбора; таблица с удалением; вложенные источники подсвечиваются и не сохраняются"],
            ["Путь вставки", "Обязательная существующая папка с буквой диска"],
            ["Время", "ЧЧ:ММ, 00:00–23:59; пустое = без расписания"],
            ["Периодичность", "Целое 1–366 дней; 0 или пусто = без периода; по умолчанию 7"],
        ],
    )

    doc.add_heading("Секция «Исключения»", level=3)
    doc.add_paragraph(
        "Поле ввода + кнопка «+». Таблица фильтров с удалением. Дубликаты не сохраняются. "
        "Синтаксис gitwildmatch (pathspec): *, **, слэши. Подробности — FILTERS.md."
    )

    doc.add_heading("Секция «Дополнительно»", level=3)
    _add_table(
        doc,
        ["Поле", "Описание"],
        [
            ["Макс. размер (МБ)", "Файлы строго больше лимита игнорируются; равные — копируются"],
            ["Архивирование", "ZIP DEFLATED, уровень сжатия 5"],
            ["Режим копирования", "Сохранять изменения / Сохранять слоями / Дублирование"],
        ],
    )

    doc.add_paragraph(
        "При сохранении — полная валидация с подсветкой ошибок под полями. "
        "Закрытие с несохранёнными изменениями — предупреждение."
    )

    doc.add_heading("3.3. Диалог «Настройки»", level=2)
    _add_table(
        doc,
        ["Настройка", "Описание"],
        [
            ["Тема", "Светлая (по умолчанию) / Тёмная"],
            ["Поля панели задач", "Чекбоксы видимости колонок (кроме «Действия»)"],
            ["Шрифт", "10–16 px, по умолчанию 12"],
            ["Автозапуск", "Создаёт/удаляет ярлык в папке Startup"],
        ],
    )
    doc.add_paragraph("Кнопки «Применить» и «Отмена». Изменения сохраняются только по «Применить».")

    doc.add_heading("3.4. Диалог «Помощь»", level=2)
    doc.add_paragraph(
        "Краткая HTML-справка: создание задачи, источники, исключения, режимы, расписание, "
        "таблица, ошибки. Кнопка «Закрыть»."
    )

    doc.add_heading("3.5. Оформление и заголовок окна", level=2)
    doc.add_paragraph(
        "Темы light/dark через единый реестр COLORS и QSS (Fusion). "
        "На Windows 11 — цвет заголовка из темы (DWM). На Windows 10 — тёмный/светлый immersive mode. "
        "Курсор «рука» на интерактивных элементах."
    )

    # --- 4. Логика копирования ---
    doc.add_heading("4. Логика резервного копирования", level=1)

    doc.add_heading("4.1. Именование в архиве", level=2)
    doc.add_paragraph(
        "Для каждого источника в папке архива создаётся подпапка с именем последнего компонента пути. "
        "Для одиночного файла — подпапка «имя_родительской_папки_files». "
        "Структура внутри повторяет относительные пути от корня источника."
    )

    doc.add_heading("4.2. Режимы копирования", level=2)
    _add_table(
        doc,
        ["Режим", "Поведение"],
        [
            [
                "Сохранять изменения",
                "Копируются новые и изменённые файлы (mtime > послед.вып.) в одну целевую папку/ZIP. "
                "При ручном запуске дополнительно копируются файлы, отсутствующие в архиве.",
            ],
            [
                "Сохранять слоями",
                "Каждый запуск — новый слой backup_ДД.ММ.ГГГГ_NNN только с изменёнными файлами. "
                "Пустой слой не создаётся.",
            ],
            [
                "Дублирование",
                "Каждый запуск — полная копия всех подходящих файлов в новый слой, даже без изменений.",
            ],
        ],
    )

    doc.add_heading("4.3. Сжатие ZIP", level=2)
    doc_items = [
        "Один ZIP на источник в режиме «Сохранять изменения» (дополнение к существующему архиву).",
        "В режимах «слоями» и «дублирование» — отдельный ZIP на каждый слой.",
        "Алгоритм ZIP_DEFLATED, compresslevel = 5.",
    ]
    for item in doc_items:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_heading("4.4. Фильтры и ограничение размера", level=2)
    doc.add_paragraph(
        "Фильтры проверяются относительно корня каждого источника. "
        "Совпадение с папкой исключает всю ветку. Max size применяется после фильтров. "
        "Колонка «Размер» учитывает фильтры и max size, но не режим копирования и не дату послед.вып."
    )

    doc.add_heading("4.5. Алгоритм выполнения задачи", level=2)
    steps = [
        "Сбор файлов (FileMatcher) с учётом источников, фильтров, max size и режима.",
        "Проверка свободного места: требуется объём + 10% запас.",
        "При нехватке места — отмена, лог «недостаточно места», послед.вып. не обновляется.",
        "Копирование по каждому источнику.",
        "Пропущенные файлы (нет прав, файл занят) — в errors/, лог «скопировано с ошибками».",
        "Источник только для чтения — удаление и изменение исходников запрещено.",
        "Поддержка длинных путей Windows (>260) через префикс \\\\?\\.",
    ]
    for i, step in enumerate(steps, 1):
        doc.add_paragraph(step, style="List Number")

    # --- 5. Расписание ---
    doc.add_heading("5. Расписание и планировщик", level=1)
    doc.add_paragraph(
        "Задача активна, если заданы и время, и периодичность. При создании: "
        "след.вып. = дата_создания + период; первый автозапуск не в день создания."
    )
    schedule_rules = [
        "Автозапуск: когда сейчас ≥ след.вып. + время задачи.",
        "После автозапуска след.вып. пересчитывается по формуле (без циклов): base + ceil((today - base) / period) * period.",
        "Ручной запуск не меняет след.вып.",
        "При старте приложения — проверка пропущенных задач; догоняющий запуск через 5 минут.",
        "При нескольких пропусках выполняется один прогон, не несколько.",
        "Планировщик (таймер 30 с) запускает только активные задачи, если очередь свободна.",
        "Выключение задачи кнопкой Play/Pause сохраняет след.вып.; при активации — пересчёт.",
    ]
    for rule in schedule_rules:
        doc.add_paragraph(rule, style="List Bullet")

    # --- 6. Очередь и потоки ---
    doc.add_heading("6. Очередь задач и фоновые потоки", level=1)
    doc.add_paragraph(
        "Копирование и подсчёт размеров выполняются в фоновых потоках (QThread), UI не блокируется."
    )
    queue_rules = [
        "При старте — фоновый пересчёт размеров всех задач.",
        "Перед копированием каждой задачи — новый подсчёт размера этой задачи.",
        "Задачи в очереди выполняются последовательно: scan → copy → следующая.",
        "Строка статуса показывает текущую операцию и результат.",
    ]
    for rule in queue_rules:
        doc.add_paragraph(rule, style="List Bullet")

    # --- 7. Хранение ---
    doc.add_heading("7. Хранение данных (settings.json)", level=1)
    doc.add_paragraph("Файл рядом с main.py или Archiver.exe. Структура:")
    doc.add_paragraph("tasks — массив задач (id, name, sources, destination, schedule, exclusions, copy_mode, compress, is_active, created_at, last_run, last_auto_run, next_run, errors_counter и др.)", style="List Bullet")
    doc.add_paragraph("settings — тема, шрифт, видимые колонки, ширины колонок, autostart", style="List Bullet")
    doc.add_paragraph("size_cache — кэш размеров задач {task_id: bytes}", style="List Bullet")

    # --- 8. Логи ---
    doc.add_heading("8. Логирование и ошибки", level=1)
    _add_table(
        doc,
        ["Файл", "Формат / правила"],
        [
            ["backup.log", "Строка: дата время | задача | источник | описание≤100 | результат. Ротация 1000 строк. UTF-8."],
            ["errors/errors_ДД.ММ.ГГГГ_NNN", "Метаданные задачи + список пропущенных файлов с текстом ошибки. Один файл на запуск задачи."],
        ],
    )
    doc.add_paragraph(
        "Результаты: «успешно», «скопировано с ошибками (файл …)», «ошибка: недостаточно места на диске». "
        "На каждый источник — отдельная строка лога."
    )

    # --- 9. Автозапуск ---
    doc.add_heading("9. Автозапуск и фоновый режим", level=1)
    _add_table(
        doc,
        ["Параметр", "Значение"],
        [
            ["Папка Startup", "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"],
            ["Ярлык", "Archiver.lnk"],
            ["Цель", "Archiver.exe --background"],
            ["Режим окна ярлыка", "Свёрнуто (WindowStyle = 7)"],
            ["Разработка", "pythonw.exe main.py --background"],
        ],
    )
    autostart_rules = [
        "При старте reconcile_autostart сверяет галочку в settings.json с наличием ярлыка.",
        "При совпадении и включённом автозапуске ярлык пересоздаётся (актуальный путь к exe).",
        "Фоновый режим: окно скрыто, иконка в трее; «Открыть» / двойной клик — показать окно; «Выход» — завершить.",
        "Определение Nuitka-сборки: sys.argv[0] = .exe (не python.exe), т.к. Nuitka не устанавливает sys.frozen.",
        "После переноса папки с exe — выключить и включить автозапуск в настройках.",
    ]
    for rule in autostart_rules:
        doc.add_paragraph(rule, style="List Bullet")

    # --- 10. Сборка ---
    doc.add_heading("10. Сборка и развёртывание", level=1)
    doc.add_paragraph("Сборка: python scripts/build_exe.py (Nuitka 4.x, standalone, PySide6).")
    build_items = [
        "Результат: compiler/Archiver.dist/ — папка целиком (exe, DLL, assets/).",
        "Промежуточная папка main.build не нужна для работы — только артефакт сборки.",
        "NUITKA_CACHE_DIR=C:\\NuitkaCache — короткий путь кэша для MinGW на Windows.",
        "Антивирус/Defender может ложно блокировать exe (Bearfoos.A!ml) — добавить папку в исключения.",
        "Для распространения желательна цифровая подпись Code Signing.",
    ]
    for item in build_items:
        doc.add_paragraph(item, style="List Bullet")

    # --- 11. Стек ---
    doc.add_heading("11. Технический стек и структура проекта", level=1)
    _add_table(
        doc,
        ["Компонент", "Технология"],
        [
            ["Язык", "Python 3.10+"],
            ["UI", "PySide6"],
            ["Фильтры", "pathspec (gitwildmatch)"],
            ["Хранение", "JSON (settings.json)"],
            ["Сборка", "Nuitka"],
            ["Тесты", "pytest"],
        ],
    )
    doc.add_paragraph("Структура каталогов:")
    structure = [
        "main.py — точка входа",
        "models/ — Task, AppSettings",
        "services/ — storage, backup_engine, file_matcher, scheduler, autostart, logger, path_utils",
        "ui/ — main_window, main_table, task_dialog, settings_dialog, help_dialog, themes, tray, window_chrome",
        "workers/ — task_queue, backup_worker, size_scan_worker, auto_scheduler",
        "tests/ — pytest без GUI",
        "scripts/ — build_exe.py, build_icon.py",
        "assets/ — иконки SVG/ICO",
        "BUILD.md, README.md, FILTERS.md — документация",
    ]
    for item in structure:
        doc.add_paragraph(item, style="List Bullet")

    # --- 12. Тесты ---
    doc.add_heading("12. Тестирование", level=1)
    doc.add_paragraph("Запуск: pytest tests/ -v. Тесты без GUI, с реальными файлами во временных папках.")
    _add_table(
        doc,
        ["Область", "Файл тестов"],
        [
            ["Все режимы копирования, ZIP, фильтры, max size, disk full", "test_backup.py"],
            ["Автозапуск, ярлык, reconcile", "test_autostart.py"],
            ["Пути, Nuitka detection", "test_path_utils.py"],
            ["Валидация формы задачи", "test_task_dialog.py"],
            ["Сигнал размера >2 ГБ", "test_size_signal.py"],
        ],
    )

    # --- 13. Критерии ---
    doc.add_heading("13. Критерии приёмки", level=1)
    criteria = [
        "Рабочее GUI-приложение по описанию интерфейса.",
        "Три режима копирования, ZIP, фильтры, расписание, ручной и автоматический запуск.",
        "settings.json, backup.log, errors/ работают как описано.",
        "Автозапуск Windows с фоновым режимом и треем.",
        "Сборка в Archiver.exe через Nuitka.",
        "Все pytest-тесты проходят.",
        "Документация: README.md, BUILD.md, FILTERS.md.",
    ]
    for c in criteria:
        doc.add_paragraph(c, style="List Number")

    doc.add_page_break()
    doc.add_heading("Приложение А. Схема потока выполнения", level=1)
    flow = (
        "Запуск → load settings.json → reconcile автозапуска → MainWindow (+ Tray если --background)\n"
        "    → AutoScheduler (30 с) + catch-up (5 мин)\n"
        "    → scan_all_sizes при старте\n"
        "Кнопка «Выполнить» / планировщик → TaskQueue\n"
        "    → SizeScanWorker → BackupWorker → BackupEngine\n"
        "    → FileMatcher → проверка места → копирование → лог → обновление task в JSON"
    )
    p = doc.add_paragraph()
    r = p.add_run(flow)
    r.font.name = "Consolas"
    r.font.size = Pt(9)

    doc.add_heading("Приложение Б. Отличия от исходного prompt.docx", level=1)
    diffs = [
        "Реализованы автозапуск, трей, сборка Nuitka (были «отложены» в исходном ТЗ).",
        "Тёмная тема и нативное оформление заголовка окна (DWM).",
        "Поле last_auto_run для отличия первого автозапуска.",
        "Определение Nuitka-сборки без sys.frozen.",
        "Документация по антивирусу и ложным срабатываниям Defender.",
        "Высота окна по умолчанию: min 600 px (не 800×600 как в раннем ТЗ).",
        "Ручной запуск в режиме «Сохранять изменения» также копирует отсутствующие в архиве файлы.",
    ]
    for d in diffs:
        doc.add_paragraph(d, style="List Bullet")

    return doc


def main() -> None:
    doc = build_document()
    doc.save(OUTPUT)
    print(f"Создан файл: {OUTPUT}")


if __name__ == "__main__":
    main()

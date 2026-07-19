"""Темы оформления приложения."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPalette

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication, QHeaderView, QScrollArea, QTableWidget, QWidget

THEMES: tuple[str, ...] = ("light", "dark")
DEFAULT_THEME = "light"

# Единый реестр: colors["имя"][theme].
COLORS: dict[str, dict[str, str]] = {
    "window": {"light": "#d4eaf0", "dark": "#1c282d"},
    "base": {"light": "#e6f3f7", "dark": "#243238"},
    "table": {"light": "#cae4ec", "dark": "#2a383e"},
    "table_alt": {"light": "#bfdde8", "dark": "#253238"},
    "input": {"light": "#dff0f5", "dark": "#2a383e"},
    "toolbar": {"light": "#cae4ec", "dark": "#253238"},
    "header": {"light": "#b5d8e4", "dark": "#30444c"},
    "status": {"light": "#d0e6ed", "dark": "#253238"},
    "caption": {"light": "#bddce6", "dark": "#1c282d"},
    "caption_text": {"light": "#1e3a42", "dark": "#dce8eb"},
    "grid": {"light": "#b0d0da", "dark": "#3a525c"},
    "border": {"light": "#bddce6", "dark": "#3a525c"},
    "panel": {"light": "#d2eff7", "dark": "#253238"},
    "scrollbar": {"light": "#dceef4", "dark": "#1c282d"},
    "text": {"light": "#1e3a42", "dark": "#dce8eb"},
    "text_accent": {"light": "#1a5563", "dark": "#9ec4cc"},
    "header_text": {"light": "#1a5563", "dark": "#b8d4dc"},
    "text_disabled": {"light": "#8aa4ad", "dark": "#6a848c"},
    "selection_text": {"light": "#1e3a42", "dark": "#f0f8fa"},
    "hover_bg": {"light": "#d9f0ec", "dark": "#2f4a52"},
    "hover_border": {"light": "#8ec5b8", "dark": "#4a7a86"},
    "pressed_bg": {"light": "#c5e8df", "dark": "#26444c"},
    "selection_bg": {"light": "#b8e0d8", "dark": "#3d6b74"},
    "button_border": {"light": "#9cc4cf", "dark": "#4a626c"},
    "button_bg": {"light": "#dff0f5", "dark": "#30444c"},
    "button_hover": {"light": "#d9f0ec", "dark": "#3d5a64"},
    "button_hover_border": {"light": "#2d95ad", "dark": "#5a9aaa"},
    "focus_border": {"light": "#2d95ad", "dark": "#5a9aaa"},
    "control_border": {"light": "#b0d0da", "dark": "#4a626c"},
    "icon_btn_hover": {"light": "#d9f0ec", "dark": "#3d5a64"},
    "scrollbar_handle": {"light": "#b0d0da", "dark": "#4a626c"},
    "scrollbar_handle_hover": {"light": "#8eb8c4", "dark": "#5a7a86"},
    "error": {"light": "#c62828", "dark": "#ef5350"},
    "error_border": {"light": "#e53935", "dark": "#ef5350"},
    "faded": {"light": "#8aa4ad", "dark": "#8aa4ad"},
    "detail": {"light": "#5a7a84", "dark": "#9ec4cc"},
    "accent_green": {"light": "#43a86f", "dark": "#43a86f"},
    "accent_green_border": {"light": "#2d8a5a", "dark": "#2d8a5a"},
    "tooltip_archive": {"light": "#14566a", "dark": "#9ec4cc"},
    "nested_source": {"light": "#c62828", "dark": "#ef5350"},
    "delete_hover": {"light": "#c62828", "dark": "#c62828"},
    "delete_pressed": {"light": "#b71c1c", "dark": "#b71c1c"},
}

_DELEGATE_SELECT_RGB: dict[str, tuple[int, int, int]] = {
    "light": (184, 224, 216),
    "dark": (61, 107, 116),
}
_HOVER_ALPHA = 128
_SELECT_ALPHA = 255


def color(name: str, theme: str) -> str:
    """Возвращает цвет: colors[name][theme]."""
    values = COLORS[name]
    if theme not in values:
        raise KeyError(f"Неизвестная тема {theme!r} для цвета {name!r}")
    return values[theme]


@dataclass(frozen=True)
class ThemePalette:
    """Полная палитра одной темы."""

    window: str
    base: str
    table: str
    table_alt: str
    input: str
    toolbar: str
    header: str
    status: str
    caption: str
    caption_text: str
    grid: str
    border: str
    panel: str
    scrollbar: str
    text: str
    text_accent: str
    header_text: str
    text_disabled: str
    selection_text: str
    hover_bg: str
    hover_border: str
    pressed_bg: str
    selection_bg: str
    button_border: str
    button_bg: str
    button_hover: str
    button_hover_border: str
    focus_border: str
    control_border: str
    icon_btn_hover: str
    scrollbar_handle: str
    scrollbar_handle_hover: str
    error: str
    error_border: str
    faded: str
    detail: str
    accent_green: str
    accent_green_border: str
    tooltip_archive: str
    nested_source: str
    delete_hover: str
    delete_pressed: str


@dataclass(frozen=True)
class ThemeColors:
    """Цвета таблиц и делегатов."""

    text: QColor
    select_text: QColor
    faded: QColor
    detail: QColor
    select_bg: QColor
    hover_bg: QColor
    icon_btn_hover: str
    nested_source: QColor


@dataclass(frozen=True)
class ThemeSurfaces:
    """Фоновые цвета (совместимость с window_chrome)."""

    window: str
    base: str
    table: str
    table_alt: str
    input: str
    toolbar: str
    header: str
    status: str
    caption: str
    caption_text: str
    grid: str
    border: str
    panel: str
    scrollbar: str


def get_palette(theme: str) -> ThemePalette:
    """Возвращает палитру для темы."""
    return ThemePalette(**{key: color(key, theme) for key in COLORS})


def get_theme_surfaces(theme: str) -> ThemeSurfaces:
    """Возвращает фоновые цвета для темы."""
    p = get_palette(theme)
    return ThemeSurfaces(
        window=p.window,
        base=p.base,
        table=p.table,
        table_alt=p.table_alt,
        input=p.input,
        toolbar=p.toolbar,
        header=p.header,
        status=p.status,
        caption=p.caption,
        caption_text=p.caption_text,
        grid=p.grid,
        border=p.border,
        panel=p.panel,
        scrollbar=p.scrollbar,
    )


def get_theme_colors(theme: str) -> ThemeColors:
    """Возвращает палитру для отрисовки таблиц."""
    p = get_palette(theme)
    if theme not in _DELEGATE_SELECT_RGB:
        theme = DEFAULT_THEME
    r, g, b = _DELEGATE_SELECT_RGB[theme]
    return ThemeColors(
        text=QColor(p.text),
        select_text=QColor(p.selection_text),
        faded=QColor(p.faded),
        detail=QColor(p.detail),
        select_bg=QColor(r, g, b, _SELECT_ALPHA),
        hover_bg=QColor(r, g, b, _HOVER_ALPHA),
        icon_btn_hover=p.icon_btn_hover,
        nested_source=QColor(p.nested_source),
    )


def get_stylesheet(theme: str, font_size: int = 12) -> str:
    """Возвращает QSS-стили для темы."""
    return _build_stylesheet(get_palette(theme), font_size)


def setup_application_style(app: QApplication) -> None:
    """Настраивает стиль Qt: только Fusion, без системной палитры."""
    app.setStyle("Fusion")
    apply_application_palette(app, DEFAULT_THEME)


def _palette_groups() -> tuple[QPalette.ColorGroup, ...]:
    return (
        QPalette.ColorGroup.Active,
        QPalette.ColorGroup.Inactive,
        QPalette.ColorGroup.Disabled,
    )


def _make_surface_palette(theme: str, surface: str) -> QPalette:
    """Палитра поверхности для всех групп — без системных значений."""
    bg = _qcolor(color(surface, theme))
    fg = _qcolor(color("text", theme))
    pal = QPalette()
    for group in _palette_groups():
        pal.setColor(group, QPalette.ColorRole.Window, bg)
        pal.setColor(group, QPalette.ColorRole.Base, bg)
        pal.setColor(group, QPalette.ColorRole.Text, fg)
        pal.setColor(group, QPalette.ColorRole.WindowText, fg)
    return pal


def apply_application_palette(app: QApplication, theme: str) -> None:
    """Задаёт палитру приложения явно — без системных белых фонов."""
    p = get_palette(theme)
    pal = QPalette()
    window = _qcolor(p.window)
    base = _qcolor(p.input)
    text = _qcolor(p.text)
    for group in _palette_groups():
        pal.setColor(group, QPalette.ColorRole.Window, window)
        pal.setColor(group, QPalette.ColorRole.WindowText, text)
        pal.setColor(group, QPalette.ColorRole.Base, base)
        pal.setColor(group, QPalette.ColorRole.AlternateBase, _qcolor(p.table_alt))
        pal.setColor(group, QPalette.ColorRole.Text, text)
        pal.setColor(group, QPalette.ColorRole.Button, _qcolor(p.button_bg))
        pal.setColor(group, QPalette.ColorRole.ButtonText, text)
        pal.setColor(group, QPalette.ColorRole.BrightText, _qcolor(p.selection_text))
        pal.setColor(group, QPalette.ColorRole.Link, _qcolor(p.text_accent))
        pal.setColor(group, QPalette.ColorRole.Highlight, _qcolor(p.selection_bg))
        pal.setColor(group, QPalette.ColorRole.HighlightedText, _qcolor(p.selection_text))
        pal.setColor(group, QPalette.ColorRole.PlaceholderText, _qcolor(p.text_disabled))
        pal.setColor(group, QPalette.ColorRole.Light, _qcolor(p.panel))
        pal.setColor(group, QPalette.ColorRole.Midlight, _qcolor(p.border))
        pal.setColor(group, QPalette.ColorRole.Mid, _qcolor(p.grid))
        pal.setColor(group, QPalette.ColorRole.Dark, _qcolor(p.control_border))
        pal.setColor(group, QPalette.ColorRole.Shadow, _qcolor(p.control_border))
    app.setPalette(pal)


def apply_app_stylesheet(theme: str, font_size: int = 12) -> None:
    """Применяет QSS и палитру ко всему приложению."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        apply_application_palette(app, theme)
        app.setStyleSheet(get_stylesheet(theme, font_size))


def _qcolor(value: str) -> QColor:
    return QColor(value)


def _apply_widget_colors(widget: QWidget, theme: str, surface: str) -> None:
    """Задаёт фон виджета и его viewport из COLORS[surface][theme]."""
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    widget.setAutoFillBackground(True)
    widget.setPalette(_make_surface_palette(theme, surface))

    viewport_fn = getattr(widget, "viewport", None)
    if callable(viewport_fn):
        viewport = viewport_fn()
        if viewport is not None:
            viewport.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            viewport.setAutoFillBackground(True)
            viewport.setPalette(_make_surface_palette(theme, surface))


def _text_view_stylesheet(theme: str) -> str:
    bg = color("input", theme)
    fg = color("text", theme)
    border = color("border", theme)
    return (
        f"QTextEdit#themedTextView, QTextBrowser#themedTextView {{"
        f" background-color: {bg};"
        f" color: {fg};"
        f" border: 1px solid {border};"
        f" border-radius: 6px;"
        f" padding: 4px;"
        f"}}"
        f"QTextEdit#themedTextView QAbstractScrollArea::viewport,"
        f"QTextBrowser#themedTextView QAbstractScrollArea::viewport {{"
        f" background-color: {bg};"
        f"}}"
    )


def wrap_themed_html(fragment: str, theme: str) -> str:
    """Оборачивает HTML-фрагмент стилями из COLORS для выбранной темы."""
    bg = color("input", theme)
    fg = color("text", theme)
    accent = color("text_accent", theme)
    panel = color("panel", theme)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<style>"
        f"body {{ background-color: {bg}; color: {fg}; margin: 0; }}"
        f"h2 {{ color: {accent}; }}"
        f"code {{ background-color: {panel}; padding: 1px 4px; }}"
        f"a {{ color: {accent}; }}"
        "</style></head><body>"
        f"{fragment}"
        "</body></html>"
    )


def apply_text_view_theme(widget: QWidget, theme: str) -> None:
    """Тема для QTextEdit / QTextBrowser: палитра, viewport, QSS и документ."""
    widget.setObjectName("themedTextView")
    _apply_widget_colors(widget, theme, "input")
    widget.setStyleSheet(_text_view_stylesheet(theme))

    document = getattr(widget, "document", None)
    if not callable(document):
        return
    doc = document()
    if doc is None:
        return

    bg = color("input", theme)
    fg = color("text", theme)
    accent = color("text_accent", theme)
    panel = color("panel", theme)
    doc.setDefaultStyleSheet(
        f"body {{ background-color: {bg}; color: {fg}; margin: 0; }}"
        f"h2 {{ color: {accent}; }}"
        f"code {{ background-color: {panel}; padding: 1px 4px; }}"
        f"a {{ color: {accent}; }}"
    )
    root = doc.rootFrame()
    frame = root.frameFormat()
    frame.setBackground(QBrush(_qcolor(bg)))
    frame.setBorder(0)
    root.setFrameFormat(frame)


def set_themed_html(widget: QWidget, html_fragment: str, theme: str) -> None:
    """Применяет тему и загружает HTML с явным фоном body."""
    apply_text_view_theme(widget, theme)
    set_html = getattr(widget, "setHtml", None)
    if callable(set_html):
        set_html(wrap_themed_html(html_fragment, theme))


def apply_toolbar_theme(toolbar: "QToolBar", theme: str) -> None:
    """Фон панели кнопок (явно, без системного цвета)."""
    from PySide6.QtWidgets import QToolBar

    if not isinstance(toolbar, QToolBar):
        return
    toolbar.setObjectName("appToolBar")
    bg = color("toolbar", theme)
    border = color("border", theme)
    _apply_widget_colors(toolbar, theme, "toolbar")
    toolbar.setStyleSheet(
        f"QToolBar#appToolBar {{"
        f" background-color: {bg};"
        f" border: none;"
        f" border-bottom: 1px solid {border};"
        f" spacing: 6px;"
        f" padding: 6px 8px;"
        f"}}"
    )


def apply_table_theme(table: "QTableWidget", theme: str) -> None:
    """Применяет фон таблицы и цветные заголовки."""
    _apply_widget_colors(table, theme, "table")
    table.setStyleSheet(_table_stylesheet(theme))
    for header in (table.horizontalHeader(), table.verticalHeader()):
        if header is not None:
            header.setStyleSheet(_table_header_stylesheet(theme))


def apply_panel_theme(widget: QWidget, theme: str) -> None:
    """Применяет фон панели-блока (палитра + QSS, без системного цвета)."""
    if not widget.objectName():
        widget.setObjectName("themePanel")
    bg = color("panel", theme)
    border = color("border", theme)
    _apply_widget_colors(widget, theme, "panel")
    name = widget.objectName()
    widget.setStyleSheet(
        f"QWidget#{name} {{"
        f" background-color: {bg};"
        f" border: 1px solid {border};"
        f" border-radius: 6px;"
        f"}}"
        f"QWidget#{name} QLabel {{"
        f" background: transparent;"
        f" color: {color('text', theme)};"
        f"}}"
        f"QWidget#{name} QWidget#themePanelBody {{"
        f" background: transparent;"
        f"}}"
    )


def apply_panel_inner(widget: QWidget, theme: str) -> None:
    """Внутренний контейнер панели — прозрачный, виден фон panel."""
    widget.setObjectName("themePanelBody")
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    widget.setAutoFillBackground(False)
    widget.setStyleSheet("background: transparent;")


def apply_scroll_area_theme(scroll: QScrollArea, theme: str) -> None:
    """Применяет фон области прокрутки."""
    _apply_widget_colors(scroll, theme, "window")
    content = scroll.widget()
    if content is not None:
        _apply_widget_colors(content, theme, "window")


def apply_window_theme(root: QWidget, theme: str) -> None:
    """Программно применяет фоны окна и вложенных панелей."""
    from PySide6.QtWidgets import (
        QDialog,
        QLineEdit,
        QListWidget,
        QMainWindow,
        QScrollArea,
        QSizeGrip,
        QStatusBar,
        QTableWidget,
        QTextEdit,
        QToolBar,
        QWidget,
    )

    if isinstance(root, (QMainWindow, QDialog)):
        _apply_widget_colors(root, theme, "window")

    central = getattr(root, "centralWidget", lambda: None)()
    if central is not None:
        _apply_widget_colors(central, theme, "window")

    for toolbar in root.findChildren(QToolBar):
        apply_toolbar_theme(toolbar, theme)

    status_bar = getattr(root, "statusBar", lambda: None)()
    if status_bar is not None:
        _apply_widget_colors(status_bar, theme, "status")

    for grip in root.findChildren(QSizeGrip):
        _apply_widget_colors(grip, theme, "status")

    for table in root.findChildren(QTableWidget):
        apply_table_theme(table, theme)

    for scroll in root.findChildren(QScrollArea):
        apply_scroll_area_theme(scroll, theme)

    for editor in root.findChildren(QTextEdit):
        apply_text_view_theme(editor, theme)

    for field in root.findChildren(QLineEdit):
        _apply_widget_colors(field, theme, "input")

    for list_widget in root.findChildren(QListWidget):
        _apply_widget_colors(list_widget, theme, "input")

    for panel in root.findChildren(QWidget):
        if panel.objectName() == "themePanel":
            apply_panel_theme(panel, theme)


def refresh_theme_for_app(theme: str, font_size: int = 12) -> None:
    """Обновляет тему для всех открытых окон."""
    from PySide6.QtWidgets import QApplication

    from ui.window_chrome import refresh_window_chrome_for_app

    app = QApplication.instance()
    if app is not None:
        setup_application_style(app)
    apply_app_stylesheet(theme, font_size)
    if app is not None:
        for widget in app.topLevelWidgets():
            apply_window_theme(widget, theme)
            table = getattr(widget, "_table", None)
            if table is not None and hasattr(table, "set_theme"):
                table.set_theme(theme)
    refresh_window_chrome_for_app(theme)


def icon_button_style(theme: str) -> str:
    """Стили плоской кнопки-иконки в таблице."""
    hover = color("icon_btn_hover", theme)
    return (
        "QPushButton { background: transparent; border: none; padding: 0px; margin: 0px; }"
        f"QPushButton:hover {{ background-color: {hover}; border-radius: 2px; }}"
    )


def delete_button_style(theme: str = DEFAULT_THEME) -> str:
    """Стили кнопки удаления."""
    return (
        "QPushButton { background: transparent; border: none; padding: 0px; margin: 0px; }"
        f"QPushButton:hover {{ background-color: {color('delete_hover', theme)}; border-radius: 2px; }}"
        f"QPushButton:pressed {{ background-color: {color('delete_pressed', theme)}; border-radius: 2px; }}"
    )


def collapsible_header_style(theme: str) -> str:
    """Стили заголовка сворачиваемого блока."""
    hover = color("hover_bg", theme)
    return (
        "QPushButton { text-align: left; padding: 6px 4px; border: none; "
        "outline: none; font-weight: bold; background: transparent; }"
        f"QPushButton:hover {{ background-color: {hover}; border-radius: 6px; }}"
        "QPushButton:focus { border: none; outline: none; }"
    )


def panel_surface_style(theme: str) -> str:
    """Стили панели-блока."""
    return (
        f"background-color: {color('panel', theme)};"
        f"border: 1px solid {color('border', theme)};"
        "border-radius: 6px;"
    )


def _table_stylesheet(theme: str) -> str:
    return (
        f"QTableWidget {{"
        f" background-color: {color('table', theme)};"
        f" alternate-background-color: {color('table_alt', theme)};"
        f" gridline-color: {color('grid', theme)};"
        f" border: 1px solid {color('border', theme)};"
        f" color: {color('text', theme)};"
        f"}}"
        f"QTableWidget::viewport {{"
        f" background-color: {color('table', theme)};"
        f"}}"
        f"QTableWidget::item {{"
        f" background: transparent;"
        f" color: {color('text', theme)};"
        f" outline: none;"
        f"}}"
        f"QTableWidget::item:selected,"
        f"QTableWidget::item:focus {{"
        f" background: transparent;"
        f" color: {color('text', theme)};"
        f" outline: none;"
        f"}}"
    )


def _table_header_stylesheet(theme: str) -> str:
    return (
        f"QHeaderView::section {{"
        f" background-color: {color('header', theme)};"
        f" color: {color('header_text', theme)};"
        f" border: none;"
        f" border-right: 1px solid {color('grid', theme)};"
        f" border-bottom: 1px solid {color('control_border', theme)};"
        f" padding: 7px 6px;"
        f" font-weight: 600;"
        f"}}"
    )


def _build_stylesheet(p: ThemePalette, fs: int) -> str:
    """Единый QSS для любой темы."""
    return f"""
    QWidget {{
        font-size: {fs}px;
        font-family: "Segoe UI", sans-serif;
        color: {p.text};
        background-color: {p.base};
    }}
    QMainWindow, QDialog {{
        background-color: {p.window};
    }}
    QWidget#appCentral {{
        background-color: {p.window};
    }}
    QWidget#themePanel {{
        background-color: {p.panel};
        border: 1px solid {p.border};
        border-radius: 6px;
    }}
    QWidget#themePanel QLabel {{
        background: transparent;
        color: {p.text};
    }}
    QWidget#themePanelBody {{
        background: transparent;
    }}
    QLabel {{
        background: transparent;
        color: {p.text};
    }}
    QMessageBox QLabel {{
        background: transparent;
    }}
    QToolBar {{
        background-color: {p.toolbar};
        border-bottom: 1px solid {p.border};
        spacing: 6px;
        padding: 6px 8px;
    }}
    QToolBar#appToolBar {{
        background-color: {p.toolbar};
        border: none;
        border-bottom: 1px solid {p.border};
        spacing: 6px;
        padding: 6px 8px;
    }}
    QToolButton {{
        padding: 6px 14px;
        border: 1px solid transparent;
        border-radius: 6px;
        background-color: transparent;
        color: {p.text};
    }}
    QToolButton:hover {{
        background-color: {p.hover_bg};
        border: 1px solid {p.hover_border};
    }}
    QToolButton:pressed {{
        background-color: {p.pressed_bg};
    }}
    QToolButton:disabled {{
        color: {p.text_disabled};
    }}
    QTableWidget {{
        gridline-color: {p.grid};
        background-color: {p.table};
        alternate-background-color: {p.table_alt};
        selection-background-color: {p.selection_bg};
        selection-color: {p.selection_text};
        border: 1px solid {p.border};
        border-radius: 4px;
        color: {p.text};
    }}
    QTableWidget::viewport {{
        background-color: {p.table};
    }}
    QTableWidget::item {{
        padding: 4px;
        background: transparent;
        color: {p.text};
        outline: none;
    }}
    QTableWidget::item:selected,
    QTableWidget::item:focus,
    QTableWidget::item:selected:active,
    QTableWidget::item:selected:!active {{
        background: transparent;
        color: {p.text};
        outline: none;
    }}
    QHeaderView::section {{
        background-color: {p.header};
        padding: 7px 6px;
        border: none;
        border-right: 1px solid {p.grid};
        border-bottom: 1px solid {p.control_border};
        font-weight: 600;
        color: {p.header_text};
    }}
    QPushButton {{
        padding: 6px 16px;
        border: 1px solid {p.button_border};
        border-radius: 6px;
        background-color: {p.button_bg};
        color: {p.text};
    }}
    QPushButton:hover {{
        background-color: {p.button_hover};
        border-color: {p.button_hover_border};
    }}
    QPushButton:pressed {{
        background-color: {p.pressed_bg};
    }}
    QPushButton:flat {{
        border: none;
        background-color: transparent;
    }}
    QPushButton:flat:hover {{
        background-color: {p.hover_bg};
        border-radius: 6px;
    }}
    QLineEdit, QTextEdit, QSpinBox, QComboBox {{
        border: 1px solid {p.control_border};
        border-radius: 5px;
        padding: 5px 6px;
        background-color: {p.input};
        color: {p.text};
        selection-background-color: {p.selection_bg};
        selection-color: {p.selection_text};
    }}
    QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {p.focus_border};
    }}
    QTextEdit, QTextBrowser {{
        background-color: {p.input};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 4px;
    }}
    QTextEdit#themedTextView,
    QTextBrowser#themedTextView {{
        background-color: {p.input};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 4px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {p.input};
        border: 1px solid {p.control_border};
        selection-background-color: {p.selection_bg};
        selection-color: {p.selection_text};
        color: {p.text};
    }}
    QLineEdit[invalid="true"], QTextEdit[invalid="true"] {{
        border: 2px solid {p.error_border};
    }}
    QLabel.error {{
        color: {p.error};
        font-size: {max(fs - 1, 9)}px;
    }}
    QLabel.section {{
        font-weight: 600;
        font-size: {fs + 1}px;
        padding-top: 8px;
        color: {p.text_accent};
        border-bottom: 1px solid {p.border};
        margin-bottom: 4px;
    }}
    QStatusBar {{
        background-color: {p.status};
        border-top: 1px solid {p.border};
        color: {p.text_accent};
    }}
    QStatusBar::item {{
        border: none;
    }}
    QSizeGrip {{
        background-color: {p.status};
        width: 14px;
        height: 14px;
    }}
    QGroupBox {{
        border: 1px solid {p.border};
        border-radius: 6px;
        margin-top: 8px;
        padding-top: 16px;
        background-color: {p.panel};
        color: {p.text};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 6px;
        color: {p.text_accent};
    }}
    QListWidget {{
        background-color: {p.input};
        border: 1px solid {p.border};
        border-radius: 5px;
        outline: none;
        color: {p.text};
    }}
    QListWidget::item {{
        padding: 4px 6px;
        border-radius: 3px;
        color: {p.text};
    }}
    QListWidget::item:hover {{
        background: transparent;
    }}
    QListWidget::item:selected {{
        background-color: {p.selection_bg};
        color: {p.selection_text};
    }}
    QCheckBox {{
        spacing: 6px;
        color: {p.text};
        background: transparent;
    }}
    QCheckBox:hover {{
        background: transparent;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 3px;
        border: 1px solid {p.button_border};
        background-color: {p.input};
    }}
    QCheckBox::indicator:checked {{
        background-color: {p.accent_green};
        border-color: {p.accent_green_border};
    }}
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QAbstractScrollArea::viewport {{
        background-color: {p.window};
    }}
    QTableWidget QAbstractScrollArea::viewport {{
        background-color: {p.table};
    }}
    QTextEdit QAbstractScrollArea::viewport,
    QTextBrowser QAbstractScrollArea::viewport,
    QTextEdit#themedTextView QAbstractScrollArea::viewport,
    QTextBrowser#themedTextView QAbstractScrollArea::viewport {{
        background-color: {p.input};
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: {p.window};
    }}
    QScrollBar:vertical {{
        background-color: {p.scrollbar};
        width: 10px;
        margin: 0;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {p.scrollbar_handle};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {p.scrollbar_handle_hover};
    }}
    QScrollBar:horizontal {{
        background-color: {p.scrollbar};
        height: 10px;
        margin: 0;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {p.scrollbar_handle};
        border-radius: 5px;
        min-width: 24px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {p.scrollbar_handle_hover};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        width: 0;
        height: 0;
    }}
    QDialogButtonBox QPushButton {{
        background-color: {p.button_bg};
        border: 1px solid {p.button_border};
        color: {p.text};
    }}
    """

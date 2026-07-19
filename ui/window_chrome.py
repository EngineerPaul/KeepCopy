"""Оформление системной рамки окна (заголовок) под тему приложения."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication, QWidget

from ui.themes import color

if TYPE_CHECKING:
    from ctypes import c_void_p

_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_BORDER_COLOR = 34
_DWMWA_CAPTION_COLOR = 35
_DWMWA_TEXT_COLOR = 36
_DWMWA_SYSTEMBACKDROP_TYPE = 38
_DWMSBT_NONE = 1

_WM_THEMECHANGED = 0x031A
_GA_ROOT = 2

_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOZORDER = 0x0004
_SWP_FRAMECHANGED = 0x0020

_RDW_INVALIDATE = 0x0001
_RDW_UPDATENOW = 0x0100
_RDW_FRAME = 0x0400

_UXTHEME_ORDINALS_LOADED = False
_SetPreferredAppMode = None
_AllowDarkModeForWindow = None
_FlushMenuThemes = None


def _windows_build() -> int:
    if sys.platform != "win32":
        return 0
    return sys.getwindowsversion().build


def supports_caption_color_api() -> bool:
    """DWMWA_CAPTION_COLOR доступен только на Windows 11 (build 22000+)."""
    return _windows_build() >= 22000


def _load_uxtheme() -> None:
    global _UXTHEME_ORDINALS_LOADED, _SetPreferredAppMode, _AllowDarkModeForWindow, _FlushMenuThemes
    if _UXTHEME_ORDINALS_LOADED or sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        uxtheme = ctypes.WinDLL("uxtheme")

        set_mode = uxtheme[135]
        set_mode.restype = ctypes.c_int
        set_mode.argtypes = [ctypes.c_int]
        _SetPreferredAppMode = set_mode

        allow_dark = uxtheme[133]
        allow_dark.restype = wintypes.BOOL
        allow_dark.argtypes = [wintypes.HWND, wintypes.BOOL]
        _AllowDarkModeForWindow = allow_dark

        flush = uxtheme[136]
        flush.restype = None
        flush.argtypes = []
        _FlushMenuThemes = flush

        _UXTHEME_ORDINALS_LOADED = True
    except (AttributeError, OSError):
        _UXTHEME_ORDINALS_LOADED = True


def _hex_to_colorref(hex_color: str) -> int:
    """#RRGGBB -> COLORREF (0x00BBGGRR)."""
    value = hex_color.lstrip("#")
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return (blue << 16) | (green << 8) | red


def _resolve_hwnd(widget: QWidget):
    import ctypes
    from ctypes import wintypes

    wid = int(widget.effectiveWinId() or widget.winId())
    if wid == 0:
        return None
    hwnd = wintypes.HWND(wid)
    root = ctypes.windll.user32.GetAncestor(hwnd, _GA_ROOT)
    return wintypes.HWND(root) if root else hwnd


def _set_dwm_bool(dwm, hwnd: c_void_p, attr: int, value: bool) -> None:
    import ctypes
    from ctypes import wintypes

    cval = wintypes.BOOL(value)
    dwm.DwmSetWindowAttribute(
        hwnd,
        attr,
        ctypes.byref(cval),
        ctypes.sizeof(cval),
    )


def _set_dwm_color(dwm, hwnd: c_void_p, attr: int, colorref: int) -> None:
    import ctypes
    from ctypes import wintypes

    cval = wintypes.DWORD(colorref)
    dwm.DwmSetWindowAttribute(
        hwnd,
        attr,
        ctypes.byref(cval),
        ctypes.sizeof(cval),
    )


def _apply_uxtheme(hwnd, *, dark: bool) -> None:
    _load_uxtheme()
    if _SetPreferredAppMode is None or _AllowDarkModeForWindow is None:
        return
    from ctypes import wintypes

    if dark:
        _SetPreferredAppMode(1)
        _AllowDarkModeForWindow(hwnd, wintypes.BOOL(True))
    else:
        _SetPreferredAppMode(0)
        _AllowDarkModeForWindow(hwnd, wintypes.BOOL(False))
        if _FlushMenuThemes is not None:
            _FlushMenuThemes()


def _apply_caption_colors_from_theme(dwm, hwnd: c_void_p, theme: str) -> None:
    """COLORS: caption — фон, caption_text — текст, border — рамка."""
    for attr, key in (
        (_DWMWA_CAPTION_COLOR, "caption"),
        (_DWMWA_TEXT_COLOR, "caption_text"),
        (_DWMWA_BORDER_COLOR, "border"),
    ):
        _set_dwm_color(dwm, hwnd, attr, _hex_to_colorref(color(key, theme)))


def _force_frame_refresh(user32, hwnd) -> None:
    user32.SendMessageW(hwnd, _WM_THEMECHANGED, 0, 0)
    user32.SetWindowPos(
        hwnd,
        0,
        0,
        0,
        0,
        0,
        _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOZORDER | _SWP_FRAMECHANGED,
    )
    user32.RedrawWindow(
        hwnd,
        None,
        None,
        _RDW_INVALIDATE | _RDW_UPDATENOW | _RDW_FRAME,
    )


def apply_window_chrome(widget: QWidget, *, theme: str, force: bool = False) -> None:
    """Подстраивает цвет заголовка окна под тему (Windows)."""
    if sys.platform != "win32":
        return
    del force  # раньше force применял chrome к скрытым окнам и ломал рамку
    # Не трогаем HWND до первого реального показа: SetWindowPos(FRAMECHANGED)
    # на скрытом окне ломает non-client metrics (сдвиг контента, чёрная полоса).
    if not widget.isVisible():
        return
    try:
        import ctypes

        hwnd = _resolve_hwnd(widget)
        if hwnd is None:
            return
        dwm = ctypes.windll.dwmapi
        user32 = ctypes.windll.user32

        dark = theme == "dark"

        if supports_caption_color_api():
            # Win11+: произвольный цвет из COLORS. Immersive dark даёт системный чёрный
            # и перекрывает caption — поэтому выключаем его.
            _set_dwm_bool(dwm, hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, False)
            _set_dwm_color(dwm, hwnd, _DWMWA_SYSTEMBACKDROP_TYPE, _DWMSBT_NONE)
            _apply_caption_colors_from_theme(dwm, hwnd, theme)
        else:
            # Win10: только системный светлый/тёмный заголовок (чёрный = immersive dark).
            # DWMWA_CAPTION_COLOR на этой версии ОС недоступен.
            _apply_uxtheme(hwnd, dark=dark)
            _set_dwm_bool(dwm, hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, dark)

        _force_frame_refresh(user32, hwnd)
        dwm.DwmFlush()
    except (AttributeError, OSError, ValueError):
        pass


def schedule_window_chrome(widget: QWidget, *, theme: str, force: bool = False) -> None:
    """Применяет оформление заголовка после того, как окно стало видимым."""
    del force  # совместимость вызовов; chrome только на видимых окнах
    apply_window_chrome(widget, theme=theme)
    if widget.isVisible():
        from PySide6.QtCore import QTimer

        QTimer.singleShot(
            0,
            lambda w=widget, t=theme: apply_window_chrome(w, theme=t),
        )


_pending_chrome_theme: str | None = None
_chrome_refresh_timer = None


def refresh_window_chrome_for_app(theme: str) -> None:
    """Обновляет заголовки всех открытых окон (один раз, с дебаунсом)."""
    global _pending_chrome_theme, _chrome_refresh_timer

    from PySide6.QtCore import QTimer

    _pending_chrome_theme = theme
    if _chrome_refresh_timer is not None:
        _chrome_refresh_timer.stop()

    _chrome_refresh_timer = QTimer()
    _chrome_refresh_timer.setSingleShot(True)
    _chrome_refresh_timer.timeout.connect(_apply_pending_chrome_refresh)
    _chrome_refresh_timer.start(80)


def _apply_pending_chrome_refresh() -> None:
    theme = _pending_chrome_theme
    if theme is None:
        return
    app = QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        if widget.isVisible():
            apply_window_chrome(widget, theme=theme)

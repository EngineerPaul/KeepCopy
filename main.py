"""Точка входа приложения Архиватор."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from services.autostart import BACKGROUND_ARG, reconcile_autostart
from services.storage import StorageService
from ui.app_icon import app_icon
from ui.app_tray import AppTray
from ui.cursors import apply_pointing_hand_cursors, install_interactive_cursors
from ui.main_window import MainWindow
from ui.qt_logging import install_qt_log_filter
from ui.themes import setup_application_style


def _warmup_hidden_window(window: MainWindow) -> None:
    """
    Создаёт HWND с корректной системной рамкой без мигания на экране.

    Без этого при первом show() из трея Windows/Qt ошибочно считает клиентскую
    область (сдвиг UI вверх/влево и чёрная полоса снизу).
    """
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    window.hide()
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)


def _background_mode(argv: list[str]) -> bool:
    return BACKGROUND_ARG in argv


def main() -> int:
    """Запускает приложение."""
    install_qt_log_filter()
    background = _background_mode(sys.argv)

    app = QApplication(sys.argv)
    app.setApplicationName("Архиватор")
    app.setQuitOnLastWindowClosed(not background)
    setup_application_style(app)
    icon = app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    install_interactive_cursors(app)

    if background and not QSystemTrayIcon.isSystemTrayAvailable():
        print("Системный трей недоступен.", file=sys.stderr)
        return 1

    storage = StorageService()
    storage.load()
    reconcile_autostart(storage)

    window = MainWindow(storage, start_hidden=background)
    apply_pointing_hand_cursors(window)

    if background:
        _warmup_hidden_window(window)
        app._tray = AppTray(window, app)  # type: ignore[attr-defined]
    else:
        window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

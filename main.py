"""Точка входа приложения KeepCopy."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from models.app_info import APP_NAME
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
    app.setApplicationName(APP_NAME)
    setup_application_style(app)
    icon = app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    install_interactive_cursors(app)

    storage = StorageService()
    storage.load()
    reconcile_autostart(storage)

    # С автозапуском закрытие окна оставляет процесс в трее и при обычном старте.
    stay_in_background = background or storage.get_settings().autostart
    if stay_in_background and not QSystemTrayIcon.isSystemTrayAvailable():
        if background:
            print("Системный трей недоступен.", file=sys.stderr)
            return 1
        stay_in_background = False

    app.setQuitOnLastWindowClosed(not stay_in_background)

    window = MainWindow(storage, start_hidden=background)
    apply_pointing_hand_cursors(window)

    if stay_in_background:
        app._tray = AppTray(window, app)  # type: ignore[attr-defined]
        if background:
            _warmup_hidden_window(window)
        else:
            window.show()
    else:
        window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

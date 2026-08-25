"""Иконка в области уведомлений (трей)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from models.app_info import APP_NAME
from ui.app_icon import app_icon

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

    from ui.main_window import MainWindow


class AppTray:
    """Трей: фоновый режим без окна на панели задач."""

    def __init__(self, window: MainWindow, app: QApplication) -> None:
        self._window = window
        self._app = app
        self._tray = QSystemTrayIcon(app_icon(), window)
        self._tray.setToolTip(APP_NAME)

        menu = QMenu()
        open_action = QAction("Открыть", menu)
        open_action.triggered.connect(self.show_window)
        menu.addAction(open_action)
        menu.addSeparator()
        quit_action = QAction("Выход", menu)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def hide(self) -> None:
        """Скрывает иконку трея."""
        self._tray.hide()

    def show_icon(self) -> None:
        """Показывает иконку трея."""
        self._tray.show()

    def show_window(self) -> None:
        """Показывает главное окно."""
        self._window.show_window()

    def quit(self) -> None:
        """Завершает приложение."""
        self._window.quit_application()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

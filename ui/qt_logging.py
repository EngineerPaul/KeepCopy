"""Фильтрация шумных сообщений Qt в консоли."""

from __future__ import annotations

import sys

from PySide6.QtCore import QtMsgType, qInstallMessageHandler

_SUPPRESSED = (
    'QWindowsNativeFileDialogBase::shellItem : Unhandled scheme:  "data"',
)


def install_qt_log_filter() -> None:
    """Скрывает известные безвредные предупреждения нативного диалога Windows."""
    def handler(mode: QtMsgType, context, message: str) -> None:
        if any(text in message for text in _SUPPRESSED):
            return
        if mode in (QtMsgType.QtDebugMsg, QtMsgType.QtInfoMsg):
            return
        stream = sys.stderr
        if mode == QtMsgType.QtFatalMsg:
            stream.write(f"Fatal: {message}\n")
        else:
            stream.write(f"{message}\n")

    qInstallMessageHandler(handler)

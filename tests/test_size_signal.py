"""Тест передачи больших размеров через сигналы Qt."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_qint64_signal_accepts_large_size(qapp) -> None:
    """Размер > 2 ГБ передаётся без OverflowError."""
    large = 2_328_164_181
    received: list[int] = []

    class Receiver(QObject):
        sig = Signal(str, "qint64")

        def __init__(self) -> None:
            super().__init__()
            self.sig.connect(self._on_size)

        def _on_size(self, task_id: str, size: int) -> None:
            received.append(size)

    obj = Receiver()
    obj.sig.emit("task-1", large)
    assert received == [large]

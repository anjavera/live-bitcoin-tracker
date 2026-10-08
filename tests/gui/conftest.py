"""Shared GUI test fixtures: an offscreen QApplication and an event pump."""

import os
import time
from collections.abc import Callable

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def pump(predicate: Callable[[], bool], timeout: float = 3.0) -> bool:
    """Process Qt events until `predicate()` is true or `timeout` seconds pass."""
    from PySide6.QtWidgets import QApplication

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    QApplication.processEvents()
    return predicate()

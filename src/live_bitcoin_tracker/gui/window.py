"""The main window: header, live chart, odds, 24-hour history, colour key and status line."""

from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout,
                               QWidget)

from live_bitcoin_tracker.gui.controller import Controller, utcnow
from live_bitcoin_tracker.gui.viewmodel import header_vm, odds_vm, status_text, table_rows
from live_bitcoin_tracker.gui.widgets.chart import PriceChart
from live_bitcoin_tracker.gui.widgets.header import HeaderCard
from live_bitcoin_tracker.gui.widgets.history_table import HistoryTable
from live_bitcoin_tracker.gui.widgets.legend import LegendBar
from live_bitcoin_tracker.gui.widgets.odds import OddsCard
from live_bitcoin_tracker.gui.widgets.statusbar import StatusBar
from live_bitcoin_tracker.gui.widgets.strip import StripWidget
from live_bitcoin_tracker.windows import floor_window

TITLE = "BTC 15m Tracker"
MIN_WIDTH, MIN_HEIGHT = 760, 640


def is_wayland() -> bool:
    platform = (QGuiApplication.platformName() or "").lower()
    return "wayland" in platform


class MainWindow(QMainWindow):
    def __init__(self, controller: Controller, clock: Callable[[], datetime] = utcnow) -> None:
        super().__init__()
        self.controller, self._clock = controller, clock
        self.view, self.local_time = "table", False
        self.setWindowTitle(TITLE)
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)

        self.header, self.odds, self.chart = HeaderCard(), OddsCard(), PriceChart()
        self.table, self.strip = HistoryTable(), StripWidget()
        self.legend, self.status = LegendBar(), StatusBar()
        chart_card = QFrame()
        chart_card.setObjectName("card")
        QVBoxLayout(chart_card).addWidget(self.chart)

        self.table_button, self.strip_button = QPushButton("Table"), QPushButton("Strip")
        group = QButtonGroup(self)
        for button in (self.table_button, self.strip_button):
            button.setObjectName("pill")
            button.setCheckable(True)
            group.addButton(button)
        self.table_button.setChecked(True)
        self.table_button.clicked.connect(lambda: self.set_view("table"))
        self.strip_button.clicked.connect(lambda: self.set_view("strip"))
        section = QHBoxLayout()
        heading = QLabel("Past 24 h")
        heading.setObjectName("big")
        section.addWidget(heading)
        section.addStretch(1)
        section.addWidget(self.table_button)
        section.addWidget(self.strip_button)

        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 12)
        layout.setSpacing(12)
        layout.addWidget(self.header)
        layout.addWidget(chart_card, 2)
        layout.addWidget(self.odds)
        layout.addLayout(section)
        layout.addWidget(self.table, 3)
        layout.addWidget(self.strip, 3)
        layout.addWidget(self.legend)
        layout.addWidget(self.status)
        self.setCentralWidget(page)
        self.strip.hide()

        self._build_actions()
        controller.updated.connect(self.refresh_view)
        self._timer = QTimer(self)
        self._timer.timeout.connect(controller.tick)  # housekeeping once a second; it emits `updated`
        self._timer.start(1000)
        self.refresh_view()

    # ---- menu and keys ----------------------------------------------------------------------
    def _action(self, text: str, shortcut: str, slot, checkable: bool = False) -> QAction:
        action = QAction(text, self)
        action.setShortcut(QKeySequence(shortcut))
        action.setCheckable(checkable)
        (action.toggled if checkable else action.triggered).connect(slot)
        self.addAction(action)  # also makes the shortcut work without a visible menu
        return action

    def _build_actions(self) -> None:
        quit_action = self._action("Quit", "Ctrl+Q", self.close)
        toggle = self._action("Table / strip", "V", self.toggle_view)
        refresh = self._action("Refresh", "R", self.refresh_data)
        self.local_action = self._action("Local time", "", self.set_local_time, checkable=True)
        self.top_action = self._action("Always on top", "", self.set_always_on_top, checkable=True)
        if is_wayland():
            self.top_action.setEnabled(False)
            hint = "Controlled by desktop on Wayland (use Alt+Space or title bar)"
            self.top_action.setToolTip(hint)
            self.top_action.setStatusTip(hint)
        self.menuBar().addMenu("&File").addAction(quit_action)
        view = self.menuBar().addMenu("&View")
        for action in (toggle, refresh, self.local_action, self.top_action):
            view.addAction(action)

    # ---- actions ----------------------------------------------------------------------------
    def set_view(self, view: str) -> None:
        self.view = view
        self.table.setVisible(view == "table")
        self.strip.setVisible(view == "strip")
        (self.table_button if view == "table" else self.strip_button).setChecked(True)

    def toggle_view(self) -> None:
        self.set_view("strip" if self.view == "table" else "table")

    def refresh_data(self) -> None:
        self.controller.refresh()

    def set_local_time(self, on: bool) -> None:
        self.local_time = bool(on)
        if self.local_action.isChecked() != self.local_time:
            self.local_action.blockSignals(True)
            self.local_action.setChecked(self.local_time)
            self.local_action.blockSignals(False)
        self.table.set_local_time(self.local_time)
        self.refresh_view()

    def set_always_on_top(self, on: bool) -> None:
        if is_wayland():
            if self.top_action.isChecked():
                self.top_action.blockSignals(True)
                self.top_action.setChecked(False)
                self.top_action.blockSignals(False)
            return
        was_visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(on))
        if was_visible:
            self.show()  # changing window flags hides the window
        if self.top_action.isChecked() != bool(on):
            self.top_action.blockSignals(True)
            self.top_action.setChecked(bool(on))
            self.top_action.blockSignals(False)

    # ---- painting ---------------------------------------------------------------------------
    def refresh_view(self) -> None:
        now, state = self._clock(), self.controller.state
        head = header_vm(state, now)
        self.header.set_vm(head)
        self.odds.set_vm(odds_vm(state, now))
        start = self.controller.chart_start or floor_window(now)
        self.chart.set_data(self.controller.chart_points, start, state.live_window(now).open, head.caption, self.local_time)
        rows = table_rows(state, now, local_time=self.local_time)
        self.table.set_rows(rows)
        self.strip.set_rows(rows)
        self.status.set_text(status_text(state, now, self.controller.feed_status(now)))

    def closeEvent(self, event: QCloseEvent) -> None:
        self._timer.stop()
        self.controller.stop()
        event.accept()

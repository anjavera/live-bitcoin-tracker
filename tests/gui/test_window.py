import os
import threading
from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QKeySequence  # noqa: E402
from PySide6.QtWidgets import QLabel  # noqa: E402

from live_bitcoin_tracker.gui.controller import Controller  # noqa: E402
from live_bitcoin_tracker.gui.window import MainWindow  # noqa: E402
from live_bitcoin_tracker.history import NO_MARKET  # noqa: E402
from live_bitcoin_tracker.model import LiveTick, Window  # noqa: E402
from live_bitcoin_tracker.sources import DataSources  # noqa: E402
from live_bitcoin_tracker.windows import MARKET_SLUG, floor_window  # noqa: E402

from .conftest import pump  # noqa: E402

UTC = timezone.utc
STEP = timedelta(minutes=15)
NOW = datetime(2026, 10, 2, 21, 5, 30, tzinfo=UTC)


class Clock:
    def __init__(self, now=NOW):
        self.now = now

    def __call__(self):
        return self.now


def history(now, mode="ok"):
    live = floor_window(now)
    if mode == "fail":
        return [Window(live - i * STEP, open=None, close=None, error="HTTP 500") for i in range(96, -1, -1)]
    out = [Window(live - i * STEP, open=84000.0 + i, close=None if i == 0 else 84001.0 + i) for i in range(96, -1, -1)]
    if mode == "nomarket":
        out[-1] = Window(live, open=None, close=None, error=NO_MARKET)
    return out


class FakeFeed:
    def __init__(self, on_tick, now):
        self.on_tick, self.now = on_tick, now

    async def run(self, stop):
        self.on_tick(LiveTick(slug=MARKET_SLUG.format(floor_window(self.now)), up_price=0.92, best_bid=0.91,
                              best_ask=0.93, last_trade=0.92, shares_traded=3.0))
        await stop.wait()


def sources(clock, mode="ok", index=True):
    ts = int(clock().timestamp()) - 1
    return DataSources(
        load_history=lambda now: history(now, mode), fetch_quotes=lambda: {}, fetch_candles=lambda a, b: {},
        feed_factory=lambda cb: FakeFeed(cb, clock()),
        fetch_index=(lambda: (84044.04, int(clock().timestamp()) - 1)) if index else (lambda: None),
        fetch_index_history=(lambda since: [(since + i, 84000.0 + i) for i in range(0, 300, 10)]) if index else (lambda since: []),
        mode="keyless")


@pytest.fixture
def make(qapp):
    made = []

    def _make(mode="ok", clock=None, index=True):
        clock = clock or Clock()
        controller = Controller(sources(clock, mode, index), clock)
        window = MainWindow(controller, clock)
        window.show()
        controller.start()
        made.append(window)
        return window, controller, clock

    yield _make
    for window in made:
        window.close()


def labels(window):
    return [label.text() for label in window.findChildren(QLabel)]


def test_window_shows_live_data(make):
    window, controller, clock = make()
    assert pump(lambda: window.table.model().rowCount() == 97
                and {"$84,044.04", "92%"} <= set(labels(window)))  # price and odds arrive separately
    shown = labels(window)
    assert "$84,000.00" in shown and "BTC UP OR DOWN 15M" in shown
    assert window.windowTitle() == "BTC 15m Tracker"
    assert window.minimumWidth() >= 760 and window.minimumHeight() >= 640
    assert pump(lambda: not window.chart.empty)
    assert "feed: live" in window.status.text()


def test_toggle_view_switches_table_and_strip(make):
    window, _, _ = make()
    assert pump(lambda: window.table.model().rowCount() == 97)
    assert window.table.isVisibleTo(window) and not window.strip.isVisibleTo(window)
    window.toggle_view()
    assert window.strip.isVisibleTo(window) and not window.table.isVisibleTo(window)
    window.toggle_view()
    assert window.table.isVisibleTo(window)


def test_keyboard_shortcuts_are_registered(make):
    window, _, _ = make()
    keys = {a.shortcut().toString() for a in window.actions()}
    assert {"Ctrl+Q", "V", "R"} <= keys


def test_local_time_toggle_relabels_rows(make):
    window, _, _ = make()
    assert pump(lambda: window.table.model().rowCount() == 97)
    model = window.table.model()
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Window (ET)"
    window.set_local_time(True)
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Window (local)"
    assert window.chart.local_time is True
    window.set_local_time(False)
    assert window.chart.local_time is False


def test_always_on_top_toggle(make):
    window, _, _ = make()
    window.set_always_on_top(True)
    assert window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    window.set_always_on_top(False)
    assert not window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint


def test_always_on_top_disabled_on_wayland(monkeypatch, make):
    monkeypatch.setattr("live_bitcoin_tracker.gui.window.is_wayland", lambda: True)
    window, _, _ = make()
    assert not window.top_action.isEnabled()
    assert "Wayland" in window.top_action.toolTip()
    window.set_always_on_top(True)
    assert not (window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
    assert not window.top_action.isChecked()


def test_close_stops_controller(make):
    window, controller, _ = make()
    assert pump(lambda: window.table.model().rowCount() == 97)
    window.close()
    assert [t for t in threading.enumerate() if t.name.startswith("tracker-")] == []


def test_no_market_state_shows_dashes_and_message(make):
    window, _, _ = make(mode="nomarket", index=False)
    assert pump(lambda: window.table.model().rowCount() == 97 and window.table.model().data(
        window.table.model().index(96, 5), Qt.ItemDataRole.DisplayRole) == "none")
    assert "feed: no market yet" in window.status.text()
    assert "—" in labels(window)
    assert window.chart.empty


def test_history_failure_shows_error_in_status(make):
    window, _, _ = make(mode="fail")
    assert pump(lambda: "history unavailable" in window.status.text())
    model = window.table.model()
    assert model.rowCount() == 97 and model.data(model.index(10, 5), Qt.ItemDataRole.DisplayRole) == "gap"
    assert window.isVisible()  # still responsive


def test_rollover_updates_header_and_chart(make):
    clock = Clock(datetime(2026, 10, 2, 21, 14, 55, tzinfo=UTC))
    window, controller, _ = make(clock=clock)
    assert pump(lambda: not window.chart.empty and window.header.beat_label.text() == "$84,000.00")
    clock.now = datetime(2026, 10, 2, 21, 15, 2, tzinfo=UTC)
    window.refresh_view()
    controller.tick()
    assert window.chart.start == datetime(2026, 10, 2, 21, 15, tzinfo=UTC)
    assert pump(lambda: window.chart.start == datetime(2026, 10, 2, 21, 15, tzinfo=UTC)
                and all(p.t >= int(window.chart.start.timestamp()) for p in window.chart.points))
    assert window.header.countdown_label.text() in {"14:58", "14:57"}


def test_refresh_action_forces_history_reload(make):
    window, controller, _ = make()
    assert pump(lambda: window.table.model().rowCount() == 97)
    window.refresh_data()
    assert controller.state.history_at is None


def test_snapshot_writes_png(qapp, tmp_path, monkeypatch):
    from live_bitcoin_tracker.gui import main as gui_main

    clock = Clock()
    monkeypatch.setattr(gui_main, "_sources_override", sources(clock))
    monkeypatch.setattr(gui_main, "_clock_override", clock)
    out = tmp_path / "shot.png"
    assert gui_main.main(["--snapshot", str(out)]) == 0
    assert out.exists() and out.stat().st_size > 5_000


def test_snapshot_unwritable_path_returns_error(qapp, tmp_path, monkeypatch, capsys):
    from live_bitcoin_tracker.gui import main as gui_main

    clock = Clock()
    monkeypatch.setattr(gui_main, "_sources_override", sources(clock))
    monkeypatch.setattr(gui_main, "_clock_override", clock)
    assert gui_main.main(["--snapshot", str(tmp_path / "missing" / "dir" / "shot.png")]) == 1
    assert "could not save" in capsys.readouterr().err.lower()

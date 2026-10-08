import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

from live_bitcoin_tracker.gui.series import ChartPoint
from live_bitcoin_tracker.model import LiveTick, Window
from live_bitcoin_tracker.sources import DataSources
from live_bitcoin_tracker.windows import MARKET_SLUG, floor_window

from .conftest import pump

UTC = timezone.utc
STEP = timedelta(minutes=15)
NOW = datetime(2026, 10, 2, 21, 5, 30, tzinfo=UTC)


class Clock:
    def __init__(self, now=NOW):
        self.now = now

    def __call__(self):
        return self.now


def history(now, error=None):
    live = floor_window(now)
    if error:
        return [Window(live - i * STEP, open=None, close=None, error=error) for i in range(96, -1, -1)]
    return [Window(live - i * STEP, open=84000.0 + i, close=None if i == 0 else 84001.0 + i) for i in range(96, -1, -1)]


def make_sources(**over) -> DataSources:
    args = dict(load_history=history, fetch_quotes=lambda: {}, fetch_candles=lambda a, b: {},
                feed_factory=lambda cb: None, fetch_index=lambda: None, fetch_index_history=lambda since: [])
    args.update(over)
    return DataSources(**args)


def live_tick(now):
    return LiveTick(slug=MARKET_SLUG.format(floor_window(now)), up_price=0.6, best_bid=0.59, best_ask=0.61,
                    last_trade=0.6, shares_traded=10.0)


class FakeFeed:
    def __init__(self, on_tick, tick):
        self.on_tick, self.tick = on_tick, tick

    async def run(self, stop):
        self.on_tick(self.tick)
        await stop.wait()


@pytest.fixture
def make(qapp):
    from live_bitcoin_tracker.gui.controller import Controller

    made = []

    def _make(sources=None, clock=None, **kw):
        controller = Controller(sources if sources is not None else make_sources(), clock or Clock(), **kw)
        made.append(controller)
        return controller

    yield _make
    for controller in made:
        controller.stop()


def tracker_threads():
    return [t for t in threading.enumerate() if t.name.startswith("tracker-")]


def test_history_loads_into_state(make):
    c = make()
    c.start()
    assert pump(lambda: len(c.state.windows) == 97 and not c.state.loading)
    assert c.state.error is None


def test_retry_constant_matches_the_terminal_app():
    from live_bitcoin_tracker import app
    from live_bitcoin_tracker.gui import controller

    assert controller.RETRY_FAILED_LOAD_AFTER == app.RETRY_FAILED_LOAD_AFTER


def test_index_tick_updates_state_and_chart_on_the_ui_thread(make):
    ts = int(NOW.timestamp()) - 1
    c = make(make_sources(fetch_index=lambda: (84123.45, ts)))
    threads = []
    original = c.state.apply_index
    c.state.apply_index = lambda price, now: (threads.append(threading.current_thread()), original(price, now))
    c.start()
    assert pump(lambda: ChartPoint(ts, 84123.45) in c.chart_points)
    assert c.state.index_price == 84123.45
    assert threads and all(t is threading.main_thread() for t in threads)


def test_feed_tick_from_the_asyncio_thread_reaches_state(make):
    tick = live_tick(NOW)
    c = make(make_sources(feed_factory=lambda cb: FakeFeed(cb, tick)))
    c.start()
    assert pump(lambda: c.state.live_tick(NOW) is not None)
    assert c.state.live_tick(NOW).up_price == 0.6


def test_rollover_resets_chart_and_refetches_history(make):
    clock = Clock(datetime(2026, 10, 2, 21, 14, 50, tzinfo=UTC))
    calls = []

    def index_history(since):
        calls.append(since)
        return [(since - 5, 1.0)] + [(since + i, 100.0 + i) for i in range(10)]

    c = make(make_sources(fetch_index_history=index_history), clock)
    c.start()
    first = int(datetime(2026, 10, 2, 21, 0, tzinfo=UTC).timestamp())
    assert pump(lambda: len(c.chart_points) == 10)
    assert calls[0] == first and c.chart_points[0].t == first

    clock.now = datetime(2026, 10, 2, 21, 15, 1, tzinfo=UTC)
    c.tick()
    second = int(datetime(2026, 10, 2, 21, 15, tzinfo=UTC).timestamp())
    assert c.chart_points == [] and c.chart_start == datetime(2026, 10, 2, 21, 15, tzinfo=UTC)
    assert pump(lambda: len(c.chart_points) == 10)
    assert calls[-1] == second
    assert all(p.t >= second for p in c.chart_points)


def test_stale_chart_history_after_rollover_is_discarded(make):
    clock = Clock(datetime(2026, 10, 2, 21, 14, 50, tzinfo=UTC))
    release, entered = threading.Event(), threading.Event()
    old_start = int(datetime(2026, 10, 2, 21, 0, tzinfo=UTC).timestamp())

    def index_history(since):
        if since == old_start:
            entered.set()
            release.wait(5)
            return [(since + 1, 111.0)]
        return [(since + 1, 222.0)]

    c = make(make_sources(fetch_index_history=index_history), clock)
    c.start()
    assert entered.wait(3)
    clock.now = datetime(2026, 10, 2, 21, 15, 2, tzinfo=UTC)
    c.tick()
    assert pump(lambda: any(p.price == 222.0 for p in c.chart_points))
    release.set()
    pump(lambda: False, timeout=0.3)  # let the late reply arrive
    assert [p.price for p in c.chart_points] == [222.0]


def test_failed_history_sets_error_and_backs_off(make):
    clock = Clock()
    calls = []
    c = make(make_sources(load_history=lambda now: calls.append(now) or history(now, error="boom")), clock)
    c.start()
    assert pump(lambda: c.state.error is not None and not c.state.loading)
    assert c.state.error.startswith("history unavailable") and len(calls) == 1
    clock.now += timedelta(seconds=5)
    c.tick()
    pump(lambda: False, timeout=0.3)
    assert len(calls) == 1  # still inside the 30 s back-off
    clock.now += timedelta(seconds=40)
    c.tick()
    assert pump(lambda: len(calls) == 2)


def test_history_exception_is_reported_not_raised(make):
    def boom(now):
        raise RuntimeError("api down")

    c = make(make_sources(load_history=boom))
    c.start()
    assert pump(lambda: c.state.error == "api down")


def test_refresh_forces_a_reload(make):
    calls = []
    c = make(make_sources(load_history=lambda now: calls.append(1) or history(now)))
    c.start()
    assert pump(lambda: len(calls) == 1 and not c.state.loading)
    c.refresh()
    c.tick()
    assert pump(lambda: len(calls) == 2)


def test_calibration_runs_on_a_copy_and_lands_on_state(make, monkeypatch):
    from live_bitcoin_tracker.gui import controller

    seen = {}

    def fake(state, sources, now):
        seen["windows"] = len(state.windows)
        state.calibration = "CAL"
        return "CAL"

    monkeypatch.setattr(controller, "run_calibration", fake)
    c = make()
    c.start()
    assert pump(lambda: c.state.calibration == "CAL")
    assert seen["windows"] == 97  # calibration saw the freshly loaded windows


def test_updated_signal_is_emitted_on_the_ui_thread(make):
    c = make(make_sources(fetch_index=lambda: (84000.0, int(NOW.timestamp()) - 1)))
    seen = []
    c.updated.connect(lambda: seen.append(threading.current_thread()))
    c.start()
    assert pump(lambda: c.state.index_price == 84000.0)
    assert seen and all(t is threading.main_thread() for t in seen)


def test_stop_ends_threads_quickly(make):
    c = make(make_sources(feed_factory=lambda cb: FakeFeed(cb, live_tick(NOW)),
                          fetch_index=lambda: (84000.0, int(NOW.timestamp()) - 1)))
    c.start()
    assert pump(lambda: c.state.live_tick(NOW) is not None)
    began = time.monotonic()
    c.stop()
    assert time.monotonic() - began < 5
    assert tracker_threads() == []
    c.stop()  # idempotent


def test_stop_during_history_load_does_not_raise(make, monkeypatch):
    errors = []
    monkeypatch.setattr(threading, "excepthook", lambda args: errors.append(args.exc_value))
    entered, release = threading.Event(), threading.Event()

    def slow(now):
        entered.set()
        release.wait(5)
        return history(now)

    c = make(make_sources(load_history=slow))
    c.start()
    assert entered.wait(3)
    threading.Timer(0.2, release.set).start()
    c.stop()
    pump(lambda: False, timeout=0.3)  # a late reply must be dropped quietly
    assert errors == [] and tracker_threads() == []
    assert c.state.windows == []


def test_sources_unavailable_sets_error_not_crash(make, monkeypatch):
    from live_bitcoin_tracker.gui import controller

    def no_sources(use_keys=True):
        raise RuntimeError("no creds")

    monkeypatch.setattr(controller, "default_sources", no_sources)
    c = make(sources=None)
    c._sources = None
    c.start()
    c.tick()
    assert c.state.error == "no creds"
    assert c.feed_status(NOW) == "offline"


def test_feed_status_matches_the_terminal_wording(make):
    clock = Clock()
    c = make(make_sources(), clock)
    c.start()
    assert pump(lambda: len(c.state.windows) == 97)
    assert c.feed_status(clock.now) == "connecting"
    c.state.apply_tick(live_tick(clock.now), clock.now)
    assert c.feed_status(clock.now) == "live"
    assert c.feed_status(clock.now + timedelta(seconds=30)) == "reconnecting"


def test_chart_follows_the_exchange_proxy_when_the_index_is_down(make):
    """Review finding: with no index the header shows an approximate price; the chart must plot it too."""
    c = make(make_sources(fetch_quotes=lambda: {"coinbase": 84100.0, "kraken": 84100.0}, fetch_index=lambda: None))
    c.start()
    assert pump(lambda: any(p.price == 84100.0 for p in c.chart_points))
    assert c.state.price_source(NOW) == "proxy"
    assert all(int(c.chart_start.timestamp()) <= p.t < int(c.chart_start.timestamp()) + 900 for p in c.chart_points)


def test_proxy_points_are_not_added_while_the_index_is_fresh(make):
    ts = int(NOW.timestamp()) - 1
    c = make(make_sources(fetch_quotes=lambda: {"coinbase": 90000.0, "kraken": 90000.0},
                          fetch_index=lambda: (84123.45, ts)))
    c.start()
    assert pump(lambda: ChartPoint(ts, 84123.45) in c.chart_points)
    pump(lambda: False, timeout=0.4)  # let a quote poll land too
    assert all(p.price != 90000.0 for p in c.chart_points)


def test_proxy_points_are_replaced_once_the_index_arrives(make):
    """A quote landing before the first index tick must not leave an approximate point in the exact line."""
    c = make(make_sources(fetch_quotes=lambda: {"coinbase": 84100.0, "kraken": 84100.0}, fetch_index=lambda: None))
    c.start()
    assert pump(lambda: any(p.price == 84100.0 for p in c.chart_points))
    assert c._proxy_seconds
    ts = int(NOW.timestamp()) - 1
    c._apply_index(84123.45, ts)
    assert c._proxy_seconds == set()
    assert [p.price for p in c.chart_points] == [84123.45]

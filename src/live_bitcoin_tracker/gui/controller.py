"""Headless controller: owns the widget state and the data sources, runs the background work, and tells the UI.

Every worker thread hands its result to the UI thread through one queued signal, so `state` and the chart are only
ever touched on the thread the controller lives in. Nothing here creates a widget, so it is testable without a display.
"""

import asyncio
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from PySide6.QtCore import QObject, Qt, Signal, Slot

from live_bitcoin_tracker.history import NO_MARKET
from live_bitcoin_tracker.gui.series import ChartPoint, append_point, window_points
from live_bitcoin_tracker.sources import CALIBRATION_EVERY, INDEX_EVERY, QUOTES_EVERY, DataSources, default_sources, run_calibration
from live_bitcoin_tracker.state import WidgetState
from live_bitcoin_tracker.timeframes import FIFTEEN_MIN, TIMEFRAMES, Timeframe

RETRY_FAILED_LOAD_AFTER = timedelta(seconds=30)  # same back-off as the terminal widget
STOP_JOIN_SECONDS = 5.0
OTHER_FRAME_REFRESH = timedelta(seconds=60)  # a hidden frame is reloaded at most this often


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class _FeedRun:
    """One running live feed: lets the controller stop it when the user switches to another time frame."""

    def __init__(self, timeframe: Timeframe) -> None:
        self.timeframe = timeframe
        self.loop: asyncio.AbstractEventLoop | None = None
        self.stop: asyncio.Event | None = None
        self.cancelled = threading.Event()

    def cancel(self) -> None:
        self.cancelled.set()
        if self.loop is not None and self.stop is not None:
            try:
                self.loop.call_soon_threadsafe(self.stop.set)
            except RuntimeError:  # the loop already finished
                pass


class Controller(QObject):
    """State for all three time frames (15 min, hourly, daily); `state`, the chart and the live feed follow the active one."""

    updated = Signal()  # emitted on the UI thread after any change to `state` or the chart
    _call = Signal(object)  # worker -> UI thread: a zero-argument callable to run there

    def __init__(self, sources: DataSources | None = None, clock: Callable[[], datetime] = utcnow,
                 use_keys: bool = True, timeframe: Timeframe = FIFTEEN_MIN) -> None:
        super().__init__()
        self._sources, self._clock, self._use_keys = sources, clock, use_keys
        self.timeframe = timeframe
        self.states = {tf.key: WidgetState(timeframe=tf) for tf in TIMEFRAMES}
        self.chart_points: list[ChartPoint] = []
        self._proxy_seconds: set[int] = set()  # chart points that came from the exchange proxy, not the index
        self.chart_start: datetime | None = None
        self._stopped = threading.Event()
        self._started = False
        self._threads: list[threading.Thread] = []
        self._loading_key: str | None = None  # history is loaded for one frame at a time, to stay clear of rate limits
        self._retry_history_at: dict[str, datetime] = {}
        self._last_load: dict[str, datetime] = {}
        self._last_calibration: datetime | None = None
        self._feed_run: _FeedRun | None = None
        self._call.connect(self._dispatch, Qt.ConnectionType.QueuedConnection)

    @property
    def state(self) -> WidgetState:
        """The state of the active time frame."""
        return self.states[self.timeframe.key]

    @property
    def chart_seconds(self) -> int:
        """Length of the charted window in seconds (a daily window is 23 to 25 hours)."""
        start = self.chart_start or self.timeframe.floor(self._clock())
        return int(self.timeframe.length(start).total_seconds())

    # ---- plumbing ---------------------------------------------------------------------------
    def _post(self, fn: Callable, *args) -> None:
        """Run `fn(*args)` on the UI thread; quietly dropped once the controller is stopped."""
        if not self._stopped.is_set():
            self._call.emit(lambda: fn(*args))

    @Slot(object)
    def _dispatch(self, fn: Callable[[], None]) -> None:
        if self._stopped.is_set():
            return
        fn()
        self.updated.emit()

    def _spawn(self, name: str, target: Callable[[], None]) -> None:
        self._threads = [t for t in self._threads if t.is_alive()]
        thread = threading.Thread(target=target, daemon=True, name=f"tracker-{name}")
        self._threads.append(thread)
        thread.start()

    # ---- lifecycle --------------------------------------------------------------------------
    def start(self) -> None:
        if self._started:
            return
        self._started = True
        if self._sources is None:
            try:
                self._sources = default_sources(use_keys=self._use_keys)
            except Exception as e:  # missing credentials etc.: show it in the window, never a traceback
                for state in self.states.values():
                    state.error = str(e)[:200] or type(e).__name__
        if self._sources is not None:
            for state in self.states.values():
                state.feed_mode = self._sources.mode
            self._begin_window(self.timeframe.floor(self._clock()))
            self._maybe_load_history(self._clock())
            self._spawn("quotes", self._poll_quotes)
            self._spawn("index", self._poll_index)
            self._start_feed()
        self.updated.emit()

    def stop(self) -> None:
        """End every worker (within a few seconds) and close the data sources. Safe to call twice."""
        if self._stopped.is_set():
            return
        self._stopped.set()
        if self._feed_run is not None:
            self._feed_run.cancel()
        deadline = threading.Event()
        timer = threading.Timer(STOP_JOIN_SECONDS, deadline.set)
        timer.daemon = True
        timer.start()
        for thread in self._threads:
            while thread.is_alive() and not deadline.is_set():
                thread.join(0.05)
        timer.cancel()
        if self._sources is not None:
            try:
                self._sources.close()
            except Exception:
                pass

    def refresh(self) -> None:
        """Reload the active frame's history on the next tick (the terminal widget's `r`), overriding any failure back-off."""
        self.state.history_at = None
        self._retry_history_at.pop(self.timeframe.key, None)
        self._last_load.pop(self.timeframe.key, None)

    def set_timeframe(self, timeframe: Timeframe) -> None:
        """Switch the chart, the live odds and the table to another time frame (history for it is usually loaded already)."""
        if timeframe is self.timeframe:
            return
        self.timeframe = timeframe
        self.chart_points, self._proxy_seconds, self.chart_start = [], set(), None
        if self._sources is not None and not self._stopped.is_set():
            self._begin_window(timeframe.floor(self._clock()))
            self._start_feed()
            self._maybe_load_history(self._clock())
        self.updated.emit()

    # ---- once a second ----------------------------------------------------------------------
    def tick(self) -> None:
        now = self._clock()
        if self._sources is not None and not self._stopped.is_set():
            window = self.timeframe.floor(now)
            if self.chart_start != window:
                self._begin_window(window)
            self._maybe_load_history(now)
        self.state.feed_status = self.feed_status(now)
        self.updated.emit()

    def feed_status(self, now: datetime) -> str:
        if self._sources is None:
            return "offline"
        if self.state.live_market_missing(now):
            return "no market yet"  # Polymarket has not published this window's market
        if self.state.live_tick(now) is None:
            return "connecting"
        return "reconnecting" if self.state.is_stale("tick", now) else "live"

    # ---- chart ------------------------------------------------------------------------------
    def _begin_window(self, start: datetime) -> None:
        """A new live window: forget the old chart and fetch this window's index points so far."""
        self.chart_start, self.chart_points = start, []
        self._proxy_seconds = set()
        timeframe = self.timeframe
        self._spawn("chart", lambda: self._load_chart(timeframe, start))

    def _load_chart(self, timeframe: Timeframe, start: datetime) -> None:
        try:
            ticks = self._sources.index_history_for(timeframe, int(start.timestamp()))
        except Exception:
            ticks = []
        self._post(self._chart_loaded, timeframe, start, ticks)

    def _chart_loaded(self, timeframe: Timeframe, start: datetime, ticks: list[tuple[int, float]]) -> None:
        if start != self.chart_start or timeframe is not self.timeframe:  # a reply for a window or frame that is gone
            return
        if ticks:
            self._drop_proxy_points()
        merged = dict(ticks)
        merged.update({p.t: p.price for p in self.chart_points})  # live ticks that arrived meanwhile win
        self.chart_points = window_points(list(merged.items()), start, self.chart_seconds)

    # ---- history ----------------------------------------------------------------------------
    def _maybe_load_history(self, now: datetime) -> None:
        """Start at most one history load: the active frame first, then the others once it has something to show."""
        if self._loading_key is not None or self._sources is None or self._stopped.is_set():
            return
        active = self.timeframe.key
        order = [self.states[active]] + [s for k, s in self.states.items() if k != active]
        for state in order:
            key = state.timeframe.key
            if self._retry_history_at.get(key) and now < self._retry_history_at[key]:
                continue  # an earlier load failed; do not hammer the API
            if key != active:
                if not self.state.windows:
                    continue  # show the frame the user is looking at first
                if self._last_load.get(key) and now - self._last_load[key] < OTHER_FRAME_REFRESH:
                    continue
            if state.needs_history_refresh(now):
                self._start_history_load(state.timeframe, now)
                return

    def _start_history_load(self, timeframe: Timeframe, now: datetime) -> None:
        self._loading_key = timeframe.key
        self._last_load[timeframe.key] = now
        self.states[timeframe.key].loading = True
        self._spawn("history", lambda: self._load_history(timeframe, now))

    def _load_history(self, timeframe: Timeframe, now: datetime) -> None:
        windows, message, ok = None, None, False
        try:
            windows = self._sources.history_for(timeframe, now)
            failed = [w for w in windows if w.error and w.error != NO_MARKET]  # "none" before a market existed is not a failure
            if windows and len(failed) * 2 > len(windows):  # load_history never raises: outages arrive as gaps
                message = f"history unavailable: {len(failed)} of {len(windows)} windows failed ({failed[0].error})"
            else:
                ok = True
        except Exception as e:
            message = str(e)[:200] or type(e).__name__
        self._post(self._history_done, timeframe.key, windows, now, message)
        if ok and timeframe is FIFTEEN_MIN:
            self._maybe_calibrate(windows, now)

    def _history_done(self, key: str, windows, now: datetime, message: str | None) -> None:
        state = self.states[key]
        if windows is not None:
            state.set_history(windows, now)
        state.error = message
        if message is None:
            self._retry_history_at.pop(key, None)
        else:
            self._retry_history_at[key] = self._clock() + RETRY_FAILED_LOAD_AFTER
        self._loading_key = None
        state.loading = False

    def _maybe_calibrate(self, windows, now: datetime) -> None:
        """Runs in the history worker on a scratch state, so the UI-thread state is never read from here."""
        if self._last_calibration and (now - self._last_calibration).total_seconds() < CALIBRATION_EVERY:
            return
        self._last_calibration = now
        scratch = WidgetState()
        scratch.windows = list(windows)
        if run_calibration(scratch, self._sources, now) is not None:
            self._post(self._set_calibration, scratch.calibration)

    def _set_calibration(self, calibration) -> None:
        for state in self.states.values():
            state.calibration = calibration

    # ---- live data --------------------------------------------------------------------------
    def _poll_quotes(self) -> None:
        while not self._stopped.is_set():
            try:
                quotes = self._sources.fetch_quotes()
                self._post(self._apply_quotes, quotes)
            except Exception:
                pass  # a failed poll just leaves the last quotes to go stale
            self._stopped.wait(QUOTES_EVERY)

    def _poll_index(self) -> None:
        while not self._stopped.is_set():
            try:
                result = self._sources.fetch_index()
                if result is not None:
                    self._post(self._apply_index, *result)
            except Exception:
                pass  # falls back to the exchange proxy once the last index price goes stale
            self._stopped.wait(INDEX_EVERY)

    def _apply_quotes(self, quotes: dict) -> None:
        """Exchange quotes feed the chart only while the official index is unavailable (the header says 'approx.')."""
        now = self._clock()
        for state in self.states.values():
            state.apply_quotes(quotes, now)
        if self.chart_start is not None and self.state.price_source(now) == "proxy":
            price = self.state.proxy_price(now)
            if price is not None:
                t = int(now.timestamp())
                self.chart_points = append_point(self.chart_points, t, price, self.chart_start, self.chart_seconds)
                self._proxy_seconds.add(t)

    def _drop_proxy_points(self) -> None:
        """The official index is back: approximate points must not sit in the same line as exact ones."""
        if self._proxy_seconds:
            self.chart_points = [p for p in self.chart_points if p.t not in self._proxy_seconds]
            self._proxy_seconds = set()

    def _apply_index(self, price: float, when: int) -> None:
        now = self._clock()
        for state in self.states.values():
            state.apply_index(price, now)
        self._drop_proxy_points()
        if self.chart_start is not None:
            self.chart_points = append_point(self.chart_points, when, price, self.chart_start, self.chart_seconds)

    # ---- the live feed (one at a time: the active frame's) ------------------------------------
    def _start_feed(self) -> None:
        if self._feed_run is not None:
            self._feed_run.cancel()
        run = self._feed_run = _FeedRun(self.timeframe)
        self._spawn("feed", lambda: self._run_feed_thread(run))

    def _run_feed_thread(self, run: _FeedRun) -> None:
        try:
            asyncio.run(self._run_feed(run))
        except Exception:
            pass  # the feed retries inside itself; anything that escapes just leaves the odds to go stale

    def _apply_tick(self, key: str, tick) -> None:
        self.states[key].apply_tick(tick, self._clock())

    async def _run_feed(self, run: _FeedRun) -> None:
        key = run.timeframe.key
        feed = self._sources.feed_for(run.timeframe, lambda tick: self._post(self._apply_tick, key, tick))
        if feed is None:
            return
        run.loop, run.stop = asyncio.get_running_loop(), asyncio.Event()
        if self._stopped.is_set() or run.cancelled.is_set():
            return
        await feed.run(run.stop)

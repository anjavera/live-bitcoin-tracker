"""Injectable data sources for the widget, plus price-proxy calibration."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from live_bitcoin_tracker.calibration import Calibration, fetch_candles, measure
from live_bitcoin_tracker.client import get_public_client, has_credentials
from live_bitcoin_tracker.feed import LiveFeed, PollingFeed
from live_bitcoin_tracker.history import HISTORY_CACHE, history_cache, load_history
from live_bitcoin_tracker.index import fetch_index, fetch_index_history
from live_bitcoin_tracker.model import LiveTick, Window
from live_bitcoin_tracker.proxy import fetch_quotes
from live_bitcoin_tracker.state import WidgetState
from live_bitcoin_tracker.timeframes import FIFTEEN_MIN, Timeframe

QUOTES_EVERY = 2.0
INDEX_EVERY = 1.0  # the index publishes about once a second  # seconds between exchange quote polls
CALIBRATION_EVERY = 1800  # seconds between calibration runs
CALIBRATION_HOURS = 4  # keeps the candle range under Coinbase's 300-candle cap


@dataclass
class DataSources:
    load_history: Callable[[datetime], list[Window]]
    fetch_quotes: Callable[[], dict[str, float | None]]
    fetch_candles: Callable[[datetime, datetime], dict]
    feed_factory: Callable[[Callable[[LiveTick], None]], PollingFeed | LiveFeed | None]
    close: Callable[[], None] = lambda: None
    fetch_index: Callable[[], tuple[float, int] | None] = lambda: None  # official index; None = unavailable
    fetch_index_history: Callable[[int], list[tuple[int, float]]] = lambda since: []  # index ticks since unix seconds
    mode: str = "keyless"  # "keyed" when the user's own API keys are in use
    # The hourly and daily frames. The 15-minute frame keeps using the fields above, which the terminal widget shares.
    load_frame_history: Callable[[Timeframe, datetime], list[Window]] = lambda tf, now: []
    frame_feed_factory: Callable[[Timeframe, Callable[[LiveTick], None]], PollingFeed | LiveFeed | None] = lambda tf, cb: None
    fetch_frame_index_history: Callable[[int, str], list[tuple[int, float]]] = lambda since, bucket: []

    def history_for(self, timeframe: Timeframe, now: datetime) -> list[Window]:
        return self.load_history(now) if timeframe is FIFTEEN_MIN else self.load_frame_history(timeframe, now)

    def feed_for(self, timeframe: Timeframe, on_tick: Callable[[LiveTick], None]):
        return self.feed_factory(on_tick) if timeframe is FIFTEEN_MIN else self.frame_feed_factory(timeframe, on_tick)

    def index_history_for(self, timeframe: Timeframe, since: int) -> list[tuple[int, float]]:
        """Index points since `since` (unix seconds), in the candle size that suits the frame's chart."""
        if timeframe is FIFTEEN_MIN:
            return self.fetch_index_history(since)
        return self.fetch_frame_index_history(since, timeframe.chart_bucket)


def default_sources(use_keys: bool = True) -> DataSources:
    """Real sources. Everything needed is public data, so keys are optional.

    With `use_keys` (the default) and API keys set up by the user, the faster authenticated live feed is used;
    otherwise (or with use_keys=False) prices are polled from the public order book.
    """
    api = get_public_client()
    keyed = use_keys and has_credentials()
    return DataSources(
        load_history=lambda now: load_history(api, now, hours=24, cache_path=HISTORY_CACHE, with_volume=False),
        fetch_quotes=fetch_quotes,
        fetch_index=fetch_index,
        fetch_index_history=fetch_index_history,
        fetch_candles=fetch_candles,
        feed_factory=lambda on_tick: _feed(api, keyed, FIFTEEN_MIN, on_tick),
        load_frame_history=lambda tf, now: load_history(api, now, cache_path=history_cache(tf), timeframe=tf),
        frame_feed_factory=lambda tf, on_tick: _feed(api, keyed, tf, on_tick),
        fetch_frame_index_history=lambda since, bucket: fetch_index_history(since, bucket=bucket),
        close=api.close,
        mode="keyed" if keyed else "keyless",
    )


def _feed(api, keyed: bool, timeframe: Timeframe, on_tick):
    """The live feed for one frame: the authenticated stream when the user has keys, else the public order book."""
    if keyed:
        return LiveFeed(on_tick, timeframe=timeframe)
    return PollingFeed(on_tick, api.markets.book, fetch_bbo=api.markets.bbo, timeframe=timeframe,
                       fetch_event=lambda slug: api.events.list({"slug": [slug.removeprefix("cpc-")], "limit": 1}))


def run_calibration(state: WidgetState, sources: DataSources, now: datetime) -> Calibration | None:
    """Measure proxy error over the last few hours of settled windows; state is untouched on failure."""
    since = now - timedelta(hours=CALIBRATION_HOURS)
    windows = [w for w in state.windows if w.settled and w.start >= since]
    try:
        candles = sources.fetch_candles(since - timedelta(minutes=15), now)
        calibration = measure(windows, candles)
    except Exception:
        return None
    if calibration is not None:
        state.calibration = calibration
    return calibration

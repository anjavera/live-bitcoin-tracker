"""15-minute window maths for Polymarket US BTC Up/Down markets (see `timeframes` for the hourly and daily frames)."""

from datetime import datetime

from live_bitcoin_tracker.timeframes import FIFTEEN_MIN

EVENT_SLUG = "btc-updown-15m-{:%Y-%m-%d-%H%M}z"
MARKET_SLUG = "cpc-btc-updown-15m-{:%Y-%m-%d-%H%M}z"


def floor_window(now: datetime) -> datetime:
    """Start of the 15-minute window containing `now` (UTC)."""
    return FIFTEEN_MIN.floor(now)


def window_slugs(now: datetime, ahead: int, back: int = 0) -> list[str]:
    """Market slugs from `back` windows ago through the current window plus `ahead - 1` more."""
    start = floor_window(now)
    for _ in range(back):
        start = FIFTEEN_MIN.prev(start)
    slugs = []
    for _ in range(back + ahead):
        slugs.append(FIFTEEN_MIN.market_slug(start))
        start = FIFTEEN_MIN.next(start)
    return slugs


def event_slug(start: datetime) -> str:
    return FIFTEEN_MIN.event_slug(start)


def seconds_remaining(now: datetime, start: datetime) -> float:
    """Seconds until the window starting at `start` ends; never negative."""
    return FIFTEEN_MIN.seconds_remaining(now, start)

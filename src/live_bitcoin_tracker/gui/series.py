"""Chart data for the live window: pure functions, no Qt."""

from dataclasses import dataclass
from datetime import datetime, timedelta

WINDOW_SECONDS = int(timedelta(minutes=15).total_seconds())
MIN_SPAN = 20.0  # dollars: a flat market still gets a readable axis
PAD = 0.10


@dataclass(frozen=True)
class ChartPoint:
    t: int  # unix seconds
    price: float


def _in_window(t: int, start: datetime, seconds: int = WINDOW_SECONDS) -> bool:
    first = int(start.timestamp())
    return first <= t < first + seconds


def window_points(ticks: list[tuple[int, float]], start: datetime, seconds: int = WINDOW_SECONDS) -> list[ChartPoint]:
    """Ticks that fall inside the window of `seconds` starting at `start`, oldest first, one per second (last wins)."""
    by_second = {t: price for t, price in sorted(ticks, key=lambda tick: tick[0]) if _in_window(t, start, seconds)}
    return [ChartPoint(t, price) for t, price in sorted(by_second.items())]


def append_point(points: list[ChartPoint], t: int, price: float, start: datetime,
                 seconds: int = WINDOW_SECONDS) -> list[ChartPoint]:
    """`points` with one more tick; outside-window ticks are ignored and a same-second tick replaces the old one."""
    if not _in_window(t, start, seconds):
        return points
    return sorted([p for p in points if p.t != t] + [ChartPoint(t, price)], key=lambda p: p.t)


def y_range(points: list[ChartPoint], beat: float | None) -> tuple[float, float]:
    """(low, high) for the price axis: spans the prices and the price to beat, padded 10 %, at least $20 tall."""
    values = [p.price for p in points] + ([beat] if beat is not None else [])
    if not values:
        return 0.0, 1.0
    low, high = min(values), max(values)
    span = max(high - low, MIN_SPAN)
    mid = (high + low) / 2
    half = span / 2 * (1 + 2 * PAD) if high - low >= MIN_SPAN else span / 2
    return mid - half, mid + half

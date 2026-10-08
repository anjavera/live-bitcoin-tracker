"""Window maths for Polymarket US's BTC Up/Down markets, which come in three time frames.

- 15 minutes: every quarter hour (UTC clock).
- 1 hour: every hour on the hour (UTC clock).
- 1 day: from 5 PM ET to the next 5 PM ET, so a day is 24 hours except on the two daylight-saving changes (25 and 23).

Everything that differs between the frames lives here, so the rest of the app asks a `Timeframe` instead of hard-coding
fifteen minutes. A window is identified by its start (a timezone-aware UTC datetime), which is also what the slugs carry.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
DAILY_CLOSE = time(17, 0)  # 5 PM ET
EVENT_SLUG = "btc-updown-{part}-{start:%Y-%m-%d-%H%M}z"
MARKET_SLUG = "cpc-" + EVENT_SLUG


def _daily_start(day: date) -> datetime:
    """5 PM ET on `day`, as UTC."""
    return datetime.combine(day, DAILY_CLOSE, tzinfo=ET).astimezone(UTC)


@dataclass(frozen=True)
class Timeframe:
    key: str  # "15m", "1h", "1d": also the part of the slug
    label: str  # tab text
    heading: str  # over the history table
    count: int  # past windows shown
    band_scale: float  # colour bands (dollars of change) are the 15-minute ones times this
    chart_bucket: str  # candle size for the live chart's index history
    chart_label_every: int  # seconds between time labels on the chart
    countdown_hours: bool  # show h:mm:ss instead of mm:ss

    # ---- the clock ---------------------------------------------------------------------------
    def floor(self, now: datetime) -> datetime:
        """Start of the window containing `now`."""
        now = now.astimezone(UTC)
        if self.key == "15m":
            return now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0)
        if self.key == "1h":
            return now.replace(minute=0, second=0, microsecond=0)
        local = now.astimezone(ET)
        today = _daily_start(local.date())
        return today if now >= today else _daily_start(local.date() - timedelta(days=1))

    def next(self, start: datetime) -> datetime:
        """Start of the window after the one starting at `start` (which is also its end)."""
        if self.key == "15m":
            return start + timedelta(minutes=15)
        if self.key == "1h":
            return start + timedelta(hours=1)
        return _daily_start(start.astimezone(ET).date() + timedelta(days=1))

    def prev(self, start: datetime) -> datetime:
        if self.key == "15m":
            return start - timedelta(minutes=15)
        if self.key == "1h":
            return start - timedelta(hours=1)
        return _daily_start(start.astimezone(ET).date() - timedelta(days=1))

    def end(self, start: datetime) -> datetime:
        return self.next(start)

    def length(self, start: datetime) -> timedelta:
        return self.end(start) - start

    def seconds_remaining(self, now: datetime, start: datetime) -> float:
        """Seconds until the window starting at `start` closes; never negative."""
        return max(0.0, (self.end(start) - now).total_seconds())

    def past_starts(self, now: datetime) -> list[datetime]:
        """The `count` windows before the live one, oldest first."""
        starts, cursor = [], self.floor(now)
        for _ in range(self.count):
            cursor = self.prev(cursor)
            starts.append(cursor)
        return starts[::-1]

    # ---- slugs -------------------------------------------------------------------------------
    def event_slug(self, start: datetime) -> str:
        return EVENT_SLUG.format(part=self.key, start=start.astimezone(UTC))

    def market_slug(self, start: datetime) -> str:
        return MARKET_SLUG.format(part=self.key, start=start.astimezone(UTC))

    def event_slugs(self, start: datetime) -> list[str]:
        """The slug to try first, then (daily only) the same day named an hour either side.

        The daily slug carries the UTC start, which moves between 21:00 and 22:00 with daylight saving. The primary is
        computed from the New York clock; the neighbours cover a naming difference around the change without a release.
        """
        slugs = [self.event_slug(start)]
        if self.key == "1d":
            slugs += [self.event_slug(start + timedelta(hours=h)) for h in (-1, 1)]
        return slugs

    def market_slugs(self, start: datetime) -> list[str]:
        return ["cpc-" + s for s in self.event_slugs(start)]

    # ---- display -----------------------------------------------------------------------------
    def row_label(self, start: datetime, tz: ZoneInfo | timezone | None = ET) -> str:
        """Table label for a window, in `tz` (ET by default; None means the computer's own zone)."""
        t = start.astimezone(tz) if tz is not None else start.astimezone()
        e = self.end(start).astimezone(tz) if tz is not None else self.end(start).astimezone()
        if self.key == "1d":
            return f"{t:%m-%d %H:%M} → {e:%m-%d %H:%M}"
        return f"{t:%m-%d %H:%M}-{e:%H:%M}"


FIFTEEN_MIN = Timeframe("15m", "15 min", "Past 24 h", 96, 1, "ASSET_PRICE_BUCKET_1S", 120, False)
HOURLY = Timeframe("1h", "Hourly", "Past 24 hours", 24, 2, "ASSET_PRICE_BUCKET_5S", 600, False)
DAILY = Timeframe("1d", "Daily", "Past 30 days", 30, 10, "ASSET_PRICE_BUCKET_1M", 4 * 3600, True)
TIMEFRAMES = (FIFTEEN_MIN, HOURLY, DAILY)


def by_key(key: str) -> Timeframe:
    """The frame with this key; the 15-minute one for anything unknown (a stale saved setting must not crash the app)."""
    return next((t for t in TIMEFRAMES if t.key == key), FIFTEEN_MIN)

"""Exact window history from Polymarket's settled BRTI values, with a local cache.

History is fetched with one bulk request per 100 windows; a per-window path remains as a fallback.
"""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from polymarket_us.errors import NotFoundError

from live_bitcoin_tracker.model import Window
from live_bitcoin_tracker.paths import cache_dir
from live_bitcoin_tracker.timeframes import FIFTEEN_MIN, Timeframe

HISTORY_CACHE = cache_dir() / "history.json"  # the 15-minute frame; the others use history-<key>.json


def history_cache(timeframe: Timeframe) -> Path:
    return HISTORY_CACHE if timeframe.key == "15m" else cache_dir() / f"history-{timeframe.key}.json"
PAUSE_BETWEEN_FETCHES = 0.4  # stay clear of the Cloudflare 1015 rate limit (per-window paths only)
BREAKER_AFTER = 3  # consecutive failed windows before later ones are tried once, without backoff
BULK_CHUNK = 100  # slugs per events.list request
BULK_TRIES = 2
NO_MARKET = "no such market"  # Polymarket has not published (or never had) a market for this window


def with_retry(fn, tries: int = 4, sleep=time.sleep):
    for attempt in range(tries):
        try:
            return fn()
        except NotFoundError:
            raise  # a 404 will not change by asking again right away
        except Exception:
            if attempt == tries - 1:
                raise
            sleep(3 * (attempt + 1))


def _price(d) -> float | None:
    try:
        return float(d["value"])
    except (TypeError, KeyError, ValueError):
        return None


def _gap(start: datetime, reason: str, timeframe: Timeframe = FIFTEEN_MIN) -> Window:
    return Window(start=start, open=None, close=None, error=reason[:60] or "unknown error", length=timeframe.length(start))


def _window_from_event(start: datetime, event: dict, timeframe: Timeframe = FIFTEEN_MIN) -> Window:
    markets = event.get("markets") or []
    if not markets:
        return _gap(start, "market has no data", timeframe)
    market = markets[0]
    terms = market.get("assetPriceTerms") or {}
    return Window(
        start=start,
        open=_price(terms.get("priceToBeat")),
        close=_price(terms.get("settlementPrice")),
        status=(market.get("status") or "").removeprefix("MARKET_STATUS_"),
        length=timeframe.length(start),
    )


def _attach_volume(client, window: Window, sleep=time.sleep, timeframe: Timeframe = FIFTEEN_MIN) -> None:
    try:
        data = with_retry(lambda: client.markets.bbo(timeframe.market_slug(window.start)), 4, sleep)["marketData"]
        window.volume = float(data.get("sharesTraded") or 0)
    except Exception:
        pass  # volume is cosmetic; keep the window


def fetch_window(client, start: datetime, sleep=time.sleep, tries: int = 4, with_volume: bool = False,
                 timeframe: Timeframe = FIFTEEN_MIN) -> Window:
    """One window from the API. Never raises: a failure becomes a gap with `error` set."""
    event = None
    try:
        for slug in timeframe.event_slugs(start):  # the daily frame also tries the neighbouring UTC hour
            try:
                event = with_retry(lambda: client.events.retrieve_by_slug(slug), tries, sleep)["event"]
                break
            except NotFoundError:
                continue
        if event is None:
            return _gap(start, NO_MARKET, timeframe)
        window = _window_from_event(start, event, timeframe)
    except Exception as e:
        return _gap(start, str(e) or type(e).__name__, timeframe)
    if with_volume and not window.error:
        _attach_volume(client, window, sleep, timeframe)
    return window


def fetch_windows_bulk(client, starts: list[datetime], sleep=time.sleep, timeframe: Timeframe = FIFTEEN_MIN) -> dict[datetime, Window]:
    """Many windows with one request per 100 slugs: a window the API does not know becomes a gap in place."""
    found: dict[datetime, Window] = {}
    per_request = max(1, BULK_CHUNK // len(timeframe.event_slugs(starts[0]))) if starts else BULK_CHUNK
    for i in range(0, len(starts), per_request):
        chunk = starts[i : i + per_request]
        slugs = [slug for s in chunk for slug in timeframe.event_slugs(s)]
        response = with_retry(lambda: client.events.list({"slug": slugs, "limit": BULK_CHUNK}), BULK_TRIES, sleep)
        by_slug = {e["slug"]: e for e in response.get("events", [])}
        for start in chunk:
            event = next((by_slug[slug] for slug in timeframe.event_slugs(start) if slug in by_slug), None)
            found[start] = _gap(start, NO_MARKET, timeframe) if event is None else _window_from_event(start, event, timeframe)
    return found


def _fetch_each(client, starts: list[datetime], sleep=time.sleep, timeframe: Timeframe = FIFTEEN_MIN) -> dict[datetime, Window]:
    """Fallback: one request per window, with a circuit breaker so an outage does not stall for minutes."""
    found, failures = {}, 0
    for start in starts:
        window = fetch_window(client, start, sleep, tries=4 if failures < BREAKER_AFTER else 1, timeframe=timeframe)
        failures = failures + 1 if window.error else 0
        found[start] = window
        sleep(PAUSE_BETWEEN_FETCHES)
    return found


def _read_cache(path: Path | None) -> dict[str, dict]:
    if path is None:
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def load_history(client, now: datetime, hours: float = 24, cache_path: Path | None = None,
                 sleep=time.sleep, with_volume: bool = False, timeframe: Timeframe = FIFTEEN_MIN) -> list[Window]:
    """Windows from `hours` ago through the live one, oldest first (hours*4 + 1 entries).

    For the hourly and daily frames `hours` is ignored: they show their own `count` past windows plus the live one.

    Settled windows are cached and never refetched. Volume costs one extra request per window, so it is opt-in.
    """
    current = timeframe.floor(now)
    if timeframe is FIFTEEN_MIN:
        starts = [current - timedelta(minutes=15 * i) for i in range(int(hours * 4), -1, -1)]
    else:
        starts = timeframe.past_starts(now) + [current]
    cache = _read_cache(cache_path)
    windows: dict[datetime, Window] = {}
    for start in starts:
        entry = cache.get(start.isoformat())
        if entry and not (with_volume and entry.get("volume") is None):
            windows[start] = Window(start=start, length=timeframe.length(start), **entry)
    need = [s for s in starts if s not in windows]
    if need:
        try:
            fetched = fetch_windows_bulk(client, need, sleep, timeframe)
        except Exception:
            fetched = _fetch_each(client, need, sleep, timeframe)
        if with_volume:
            for window in fetched.values():
                if not window.error:
                    _attach_volume(client, window, sleep, timeframe)
                    sleep(PAUSE_BETWEEN_FETCHES)
        for start, window in fetched.items():
            if window.settled:
                cache[start.isoformat()] = {"open": window.open, "close": window.close,
                                            "status": window.status, "volume": window.volume}
        windows.update(fetched)
        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(cache))
    return [windows[s] for s in starts]

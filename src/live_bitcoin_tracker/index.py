"""Polymarket's own BTC reference index price (public, no keys): the index the markets settle on."""

import math

from live_bitcoin_tracker.proxy import http_get_json

INDEX_URL = ("https://gateway.polymarket.us/v1/asset-prices/history"
             "?assets=crypto:btc&bucket=ASSET_PRICE_BUCKET_1S&to=0&from={from_ts}")
LOOKBACK_SECONDS = 15  # recent enough to be live, wide enough to hold a real tick if one second is missing


def _btc_candles(payload) -> list | None:
    """The BTC series' candle list, or None when the payload has no usable BTC series."""
    try:
        series = next(s for s in payload["series"] if (s.get("asset") or {}).get("symbol") == "btc")
    except (TypeError, KeyError, StopIteration, AttributeError):
        series = None
    if series is None:  # tolerate a single-series reply that omits the asset field
        try:
            series = payload["series"][0] if len(payload["series"]) == 1 and "asset" not in payload["series"][0] else None
        except (TypeError, KeyError, IndexError):
            return None
    if series is None:
        return None
    return series.get("candles") or []


def _real_tick(candle) -> tuple[float, int] | None:
    """(close, unix seconds) of a candle that holds a real publication; None for gap fills and bad data."""
    if not candle.get("tickCount"):
        return None
    try:
        price = float(candle["close"])
        when = int(candle["timestamp"])
    except (KeyError, TypeError, ValueError):
        return None
    return (price, when) if math.isfinite(price) and price > 0 else None


def parse_index(payload) -> tuple[float, int] | None:
    """(price, unix seconds) of the newest real BTC index tick, or None. Gap-filled candles (tickCount 0) are skipped."""
    candles = _btc_candles(payload)
    for candle in reversed(candles or []):
        if not candle.get("tickCount"):
            continue
        return _real_tick(candle)  # the newest real candle decides, even if its data is bad
    return None


def parse_index_history(payload) -> list[tuple[int, float]]:
    """Every real tick as (unix seconds, price), oldest first. Gap fills and bad prices are skipped."""
    ticks = (_real_tick(c) for c in (_btc_candles(payload) or []))
    return sorted((when, price) for price, when in filter(None, ticks))


def fetch_index(get_json=http_get_json, now: float | None = None) -> tuple[float, int] | None:
    """Latest index tick as (price, unix seconds); None on any failure so callers can fall back."""
    import time

    try:
        return parse_index(get_json(INDEX_URL.format(from_ts=int((now or time.time()) - LOOKBACK_SECONDS))))
    except Exception:
        return None


def fetch_index_history(since: int, get_json=http_get_json) -> list[tuple[int, float]]:
    """Index ticks from `since` (unix seconds) to now as (seconds, price); [] on any failure."""
    try:
        return parse_index_history(get_json(INDEX_URL.format(from_ts=int(since))))
    except Exception:
        return []

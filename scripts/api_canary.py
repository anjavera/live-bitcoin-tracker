"""Weekly check that Polymarket's public API still looks the way the app expects.

For each frame (15 min, hourly, daily) it fetches the last finished window and the live order book through the
app's own code, so a renamed or missing field fails here before it breaks the widget. Needs no API keys.
Exit status 0 = all good, 1 = something changed (the failures are printed, one per line).
"""

import sys
from datetime import datetime, timezone

from polymarket_us.errors import NotFoundError

from live_bitcoin_tracker.client import get_public_client
from live_bitcoin_tracker.feed import parse_book
from live_bitcoin_tracker.history import fetch_window, with_retry
from live_bitcoin_tracker.timeframes import TIMEFRAMES, Timeframe


def check_settled(client, tf: Timeframe, now: datetime) -> str | None:
    start = tf.prev(tf.floor(now))
    window = fetch_window(client, start, timeframe=tf)
    if window.error:
        return f"{tf.key}: last finished window {start:%Y-%m-%d %H:%M}Z unreadable ({window.error})"
    if not window.settled:
        return f"{tf.key}: last finished window {start:%Y-%m-%d %H:%M}Z has no open/close price (status {window.status!r})"
    return None


def check_book(client, tf: Timeframe, now: datetime) -> str | None:
    start = tf.floor(now)
    for slug in tf.market_slugs(start):
        try:
            tick = parse_book(with_retry(lambda: client.markets.book(slug)))
        except NotFoundError:
            continue
        except Exception as e:
            return f"{tf.key}: order book for {slug} unreadable ({e})"
        if tick.up_price is None:
            return f"{tf.key}: order book for {slug} has no Up price"
        return None
    return f"{tf.key}: no live market found for window {start:%Y-%m-%d %H:%M}Z"


def main() -> int:
    client, now = get_public_client(), datetime.now(timezone.utc)
    problems = [p for tf in TIMEFRAMES for p in (check_settled(client, tf, now), check_book(client, tf, now)) if p]
    for p in problems:
        print("FAIL", p)
    if not problems:
        print(f"ok: {', '.join(tf.key for tf in TIMEFRAMES)} history and live order book read correctly")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

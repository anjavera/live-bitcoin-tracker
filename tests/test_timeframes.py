"""Window maths for the three Polymarket US BTC Up/Down time frames: 15 minutes, 1 hour and 1 day (5 PM ET to 5 PM ET)."""

from datetime import datetime, timedelta, timezone

import pytest

from live_bitcoin_tracker.timeframes import DAILY, FIFTEEN_MIN, HOURLY, TIMEFRAMES, by_key

UTC = timezone.utc


def utc(*args):
    return datetime(*args, tzinfo=UTC)


def test_registry_has_the_three_frames_in_display_order():
    assert [t.key for t in TIMEFRAMES] == ["15m", "1h", "1d"]
    assert by_key("1h") is HOURLY and by_key("nope") is FIFTEEN_MIN  # unknown keys fall back to the default
    assert (FIFTEEN_MIN.count, HOURLY.count, DAILY.count) == (96, 24, 30)


def test_fifteen_minute_floor_and_slugs():
    now = utc(2026, 10, 8, 5, 7, 31)
    start = FIFTEEN_MIN.floor(now)
    assert start == utc(2026, 10, 8, 5, 0) and FIFTEEN_MIN.end(start) == utc(2026, 10, 8, 5, 15)
    assert FIFTEEN_MIN.event_slug(start) == "btc-updown-15m-2026-10-08-0500z"
    assert FIFTEEN_MIN.market_slug(start) == "cpc-btc-updown-15m-2026-10-08-0500z"
    assert FIFTEEN_MIN.next(start) == utc(2026, 10, 8, 5, 15) and FIFTEEN_MIN.prev(start) == utc(2026, 10, 8, 4, 45)


def test_hourly_floor_and_slugs_match_the_live_api_names():
    now = utc(2026, 10, 8, 5, 59, 59)
    start = HOURLY.floor(now)
    assert start == utc(2026, 10, 8, 5, 0) and HOURLY.end(start) == utc(2026, 10, 8, 6, 0)
    assert HOURLY.event_slug(start) == "btc-updown-1h-2026-10-08-0500z"
    assert HOURLY.market_slug(start) == "cpc-btc-updown-1h-2026-10-08-0500z"
    assert HOURLY.floor(utc(2026, 10, 8, 6, 0)) == utc(2026, 10, 8, 6, 0)  # the boundary belongs to the new hour


def test_daily_runs_5pm_et_to_5pm_et_and_slug_uses_the_utc_start():
    # October: EDT, 5 PM ET = 21:00 UTC. This is the live event btc-updown-1d-2026-10-07-2100z.
    now = utc(2026, 10, 8, 5, 0)
    start = DAILY.floor(now)
    assert start == utc(2026, 10, 7, 21, 0) and DAILY.end(start) == utc(2026, 10, 8, 21, 0)
    assert DAILY.event_slug(start) == "btc-updown-1d-2026-10-07-2100z"
    assert DAILY.market_slug(start) == "cpc-btc-updown-1d-2026-10-07-2100z"
    assert DAILY.floor(utc(2026, 10, 8, 21, 0)) == utc(2026, 10, 8, 21, 0)  # at the close the next day begins
    assert DAILY.floor(utc(2026, 10, 8, 20, 59, 59)) == utc(2026, 10, 7, 21, 0)


def test_daily_follows_daylight_saving_so_the_close_moves_to_22_utc_in_winter():
    start = DAILY.floor(utc(2026, 11, 2, 12, 0))  # after the clocks went back on 1 Nov 2026: EST, 5 PM ET = 22:00 UTC
    assert start == utc(2026, 11, 1, 22, 0) and DAILY.end(start) == utc(2026, 11, 2, 22, 0)
    assert DAILY.event_slug(start) == "btc-updown-1d-2026-11-01-2200z"
    long_day = utc(2026, 10, 31, 21, 0)  # EDT start, EST end: 25 hours
    assert DAILY.end(long_day) - long_day == timedelta(hours=25)
    short_day = utc(2027, 3, 13, 22, 0)  # EST start, EDT end (clocks forward on 14 Mar 2027): 23 hours
    assert DAILY.end(short_day) - short_day == timedelta(hours=23)
    assert DAILY.next(long_day) == utc(2026, 11, 1, 22, 0) and DAILY.prev(utc(2026, 11, 1, 22, 0)) == long_day


def test_daily_slug_candidates_cover_a_one_hour_naming_difference():
    start = utc(2026, 11, 1, 22, 0)
    assert DAILY.event_slugs(start) == ["btc-updown-1d-2026-11-01-2200z", "btc-updown-1d-2026-11-01-2100z",
                                        "btc-updown-1d-2026-11-01-2300z"]
    assert FIFTEEN_MIN.event_slugs(utc(2026, 10, 8, 5, 0)) == ["btc-updown-15m-2026-10-08-0500z"]


@pytest.mark.parametrize("tf", TIMEFRAMES)
def test_past_starts_are_oldest_first_and_end_just_before_the_live_window(tf):
    now = utc(2026, 11, 3, 10, 20)
    starts = tf.past_starts(now)
    assert len(starts) == tf.count and starts == sorted(starts)
    assert tf.next(starts[-1]) == tf.floor(now)
    assert all(tf.next(a) == b for a, b in zip(starts, starts[1:]))


def test_seconds_remaining_counts_to_the_real_close_and_never_goes_negative():
    start = DAILY.floor(utc(2026, 10, 8, 5, 0))
    assert DAILY.seconds_remaining(utc(2026, 10, 8, 20, 59, 0), start) == 60
    assert DAILY.seconds_remaining(utc(2026, 10, 9, 3, 0), start) == 0
    assert FIFTEEN_MIN.seconds_remaining(utc(2026, 10, 8, 5, 14, 30), utc(2026, 10, 8, 5, 0)) == 30


def test_row_labels_are_et_by_default_and_show_the_whole_window():
    assert FIFTEEN_MIN.row_label(utc(2026, 10, 8, 5, 0)) == "10-08 01:00-01:15"
    assert HOURLY.row_label(utc(2026, 10, 8, 5, 0)) == "10-08 01:00-02:00"
    assert DAILY.row_label(utc(2026, 10, 7, 21, 0)) == "10-07 17:00 → 10-08 17:00"
    assert HOURLY.row_label(utc(2026, 10, 8, 5, 0), tz=UTC) == "10-08 05:00-06:00"


def test_colour_band_scale_grows_with_the_window_length():
    assert (FIFTEEN_MIN.band_scale, HOURLY.band_scale, DAILY.band_scale) == (1, 2, 10)
    assert {t.chart_bucket for t in TIMEFRAMES} == {"ASSET_PRICE_BUCKET_1S", "ASSET_PRICE_BUCKET_5S", "ASSET_PRICE_BUCKET_1M"}

from datetime import datetime, timedelta, timezone

from live_bitcoin_tracker.gui.series import ChartPoint, append_point, window_points, y_range

START = datetime(2026, 10, 2, 21, 0, tzinfo=timezone.utc)
T0 = int(START.timestamp())


def test_window_points_drops_outside_window():
    ticks = [(T0 - 1, 1.0), (T0, 2.0), (T0 + 899, 3.0), (T0 + 900, 4.0)]
    assert window_points(ticks, START) == [ChartPoint(T0, 2.0), ChartPoint(T0 + 899, 3.0)]


def test_window_points_sorted_one_per_second():
    ticks = [(T0 + 5, 9.0), (T0 + 1, 1.0), (T0 + 5, 10.0)]
    assert window_points(ticks, START) == [ChartPoint(T0 + 1, 1.0), ChartPoint(T0 + 5, 10.0)]


def test_append_point_replaces_same_second():
    pts = [ChartPoint(T0, 1.0)]
    out = append_point(pts, T0, 2.0, START)
    assert out == [ChartPoint(T0, 2.0)]


def test_append_point_ignores_outside_window_and_keeps_order():
    pts = [ChartPoint(T0 + 10, 1.0)]
    assert append_point(pts, T0 - 5, 2.0, START) == pts
    assert append_point(pts, T0 + 900, 2.0, START) == pts
    assert append_point(pts, T0 + 3, 2.0, START) == [ChartPoint(T0 + 3, 2.0), ChartPoint(T0 + 10, 1.0)]


def test_y_range_includes_beat_and_pads():
    lo, hi = y_range([ChartPoint(T0, 100.0), ChartPoint(T0 + 1, 110.0)], 120.0)
    assert lo < 100.0 and hi > 120.0


def test_y_range_min_span_20():
    lo, hi = y_range([ChartPoint(T0, 100.0)], None)
    assert hi - lo >= 20.0 and lo < 100.0 < hi


def test_y_range_empty():
    assert y_range([], None) == (0.0, 1.0)


def test_y_range_beat_only():
    lo, hi = y_range([], 500.0)
    assert lo < 500.0 < hi


def test_window_points_last_input_wins_for_a_repeated_second():
    ticks = [(T0 + 5, 10.0), (T0 + 5, 9.0)]
    assert window_points(ticks, START) == [ChartPoint(T0 + 5, 9.0)]
